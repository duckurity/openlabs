#!/usr/bin/env python3
"""Sanity-check CI routing fixtures against labs.yml scope logic."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from ci_routing import (  # noqa: E402
    compute_pull_request_scope,
    labs_workflow_permissions_read_only,
    load_path_filters,
)

FIXTURE = SCRIPTS / "fixtures" / "ci_routing_matrix.json"
REQUIRED_KEYS = frozenset(
    {
        "run_validate",
        "run_security",
        "run_content",
        "run_pdf",
        "run_reference",
    }
)
CONTRACT_PATHS = (
    "scripts/test_contract.py",
    "scripts/openlabs_contract.py",
    "contracts/lab.schema.json",
    "contracts/diagnostics.json",
    "contracts/cli-v1.md",
)


def check_structure(data: dict) -> int:
    failures = 0
    if data.get("required_check") != "CI required":
        print("required_check must be 'CI required'", file=sys.stderr)
        failures += 1
    for case in data.get("examples", []):
        if case.get("labs_workflow_triggers") is False:
            continue
        missing = REQUIRED_KEYS - case.keys()
        if missing:
            failures += 1
            print(f"{case.get('change')}: missing keys {sorted(missing)}")
    return failures


def check_routing_examples(data: dict, filters: dict) -> int:
    failures = 0
    routed = 0
    for case in data.get("examples", []):
        if case.get("labs_workflow_triggers") is False:
            continue
        changed = case.get("changed_files")
        if not changed:
            continue
        actor = case.get("actor", "contributor")
        scope = compute_pull_request_scope(
            actor=actor,
            changed_files=list(changed),
            filters=filters,
        )
        routed += 1
        for key in REQUIRED_KEYS:
            expected = case.get(key)
            actual = scope.get(key)
            if expected is not actual:
                failures += 1
                print(
                    f"{case.get('change')}: {key} expected {expected}, got {actual} "
                    f"(files={changed})"
                )
    if routed == 0:
        print("routing examples: no changed_files cases to verify", file=sys.stderr)
        failures += 1
    return failures


def check_contract_paths_in_filters(filters: dict) -> int:
    from ci_routing import path_matches_pattern

    patterns = filters.get("lab_scripts", ())
    failures = 0
    for path in CONTRACT_PATHS:
        if not any(path_matches_pattern(path, pattern) for pattern in patterns):
            failures += 1
            print(f"lab_scripts filter missing contract path coverage for {path}")
    return failures


def check_permissions() -> int:
    if labs_workflow_permissions_read_only():
        return 0
    print("labs.yml: expected top-level contents: read permissions", file=sys.stderr)
    return 1


def main() -> int:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    failures = check_structure(data)
    try:
        filters = load_path_filters()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    failures += check_contract_paths_in_filters(filters)
    failures += check_routing_examples(data, filters)
    failures += check_permissions()
    if failures:
        print(f"failed {failures} routing checks")
        return 1
    count = len(data.get("examples", []))
    print(f"passed {count} routing examples and labs.yml scope invariants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
