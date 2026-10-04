#!/usr/bin/env python3
"""Golden JSON checks for contracts/cli-v1.md."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from cli_contract import (  # noqa: E402
    COMMANDS,
    ENVELOPE_VERSION,
    ISSUE_ACTIONS,
    LAB_ACTIONS,
    iter_fixture_files,
    validate_all_fixtures,
)


def _fixture_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_fixture_validation() -> int:
    errors = validate_all_fixtures()
    if errors:
        print("cli contract fixtures:")
        for line in errors:
            print(f"  {line}")
        return 1
    count = len(iter_fixture_files())
    print(f"cli contract fixtures: passed {count}")
    return 0


def run_coverage() -> int:
    """Ensure at least one golden fixture exists per top-level command."""
    paths = iter_fixture_files()
    missing = []
    for command in sorted(COMMANDS):
        if not any(command in path.parts for path in paths):
            missing.append(command)
    if missing:
        print(f"cli contract coverage: missing fixtures for {missing}")
        return 1
    lab_fixtures = [p for p in paths if "lab" in p.parts]
    issue_fixtures = [p for p in paths if "issue" in p.parts]
    for action in sorted(LAB_ACTIONS):
        if not any(f'"action": "{action}"' in _fixture_text(p) for p in lab_fixtures):
            print(f"cli contract coverage: missing lab action fixture for {action!r}")
            return 1
    for action in sorted(ISSUE_ACTIONS):
        if not any(f'"action": "{action}"' in _fixture_text(p) for p in issue_fixtures):
            print(f"cli contract coverage: missing issue action fixture for {action!r}")
            return 1
    if not any("prove" in _fixture_text(p) for p in lab_fixtures):
        print("cli contract coverage: missing lab prove fixture")
        return 1
    if not any("reset" in _fixture_text(p) for p in lab_fixtures):
        print("cli contract coverage: missing lab reset fixture")
        return 1
    print(f"cli contract coverage: ok ({ENVELOPE_VERSION}, lab actions {sorted(LAB_ACTIONS)})")
    return 0


def main() -> int:
    for step in (run_fixture_validation, run_coverage):
        code = step()
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
