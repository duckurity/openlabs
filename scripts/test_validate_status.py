#!/usr/bin/env python3
"""Run lab status validator fixtures from scripts/fixtures/validate_status/."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate import check_lab_status, parse_flat_yaml  # noqa: E402

FIXTURES = REPO_ROOT / "scripts" / "fixtures" / "validate_status"

CASES: tuple[tuple[str, bool, int, int], ...] = (
    ("valid-supported", False, 0, 0),
    ("valid-experimental", False, 0, 0),
    ("missing-status", False, 0, 1),
    ("invalid-status", False, 1, 0),
    ("missing-status", True, 1, 0),
)


def run_case(name: str, require_status: bool) -> tuple[list[str], list[str]]:
    lab_yml = FIXTURES / name / "lab.yml"
    if not lab_yml.is_file():
        raise FileNotFoundError(f"missing fixture {lab_yml}")
    meta = parse_flat_yaml(lab_yml.read_text(encoding="utf-8"))
    return check_lab_status(meta, require_status=require_status)


def main() -> int:
    failures = 0
    for name, require_status, want_errors, want_warnings in CASES:
        errors, warnings = run_case(name, require_status)
        if len(errors) != want_errors or len(warnings) != want_warnings:
            failures += 1
            mode = "require_status" if require_status else "migration"
            print(f"{name} ({mode}):")
            print(f"  expected errors={want_errors}, warnings={want_warnings}")
            print(f"  got errors={len(errors)}, warnings={len(warnings)}")
            for line in errors:
                print(f"    error: {line}")
            for line in warnings:
                print(f"    warning: {line}")
    if failures:
        print(f"failed {failures} of {len(CASES)} status fixtures")
        return 1
    print(f"passed {len(CASES)} status fixtures")
    return 0


if __name__ == "__main__":
    sys.exit(main())
