#!/usr/bin/env python3
"""Validate M0 baseline fixtures and report invariants."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
FIXTURES = SCRIPTS / "fixtures"
EXIT_CRITERIA = FIXTURES / "m0_exit_criteria.json"
BRANCH_PROTECTION = FIXTURES / "m0_branch_protection.json"
REFERENCE = "labs/web/duck-cross"


def main() -> int:
    failures = 0
    criteria = json.loads(EXIT_CRITERIA.read_text(encoding="utf-8"))
    if criteria.get("reference_supported_lab") != REFERENCE:
        print("m0_exit_criteria: reference_supported_lab must be duck-cross")
        failures += 1
    issues = criteria.get("issues", [])
    if len(issues) < 9:
        print("m0_exit_criteria: expected at least 9 M0 issues")
        failures += 1
    numbers = {item["number"] for item in issues}
    if criteria.get("parent_issue") not in numbers:
        print("m0_exit_criteria: parent_issue 72 must appear in issues list")
        failures += 1

    protection = json.loads(BRANCH_PROTECTION.read_text(encoding="utf-8"))
    names = {item["name"] for item in protection.get("required_status_checks", [])}
    if "CI required" not in names:
        print("m0_branch_protection: missing CI required check")
        failures += 1

    wiki = SCRIPTS.parent / "wiki" / "M0-Baseline-Evidence.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "baseline_report.py"),
            "--check",
            "--wiki",
            str(wiki),
        ],
        cwd=SCRIPTS.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        failures += 1

    if failures:
        print(f"failed {failures} baseline report checks")
        return 1
    print("baseline report fixtures and generator ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
