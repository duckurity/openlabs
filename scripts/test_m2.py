#!/usr/bin/env python3
"""Local entry point for non-Docker M2 CLI and lifecycle gates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

STEPS = (
    "test_run_m2_tier1_lifecycle.py",
    "test_openlabs_cli.py",
    "test_openlabs_issue.py",
    "test_openlabs_lab_discovery.py",
    "test_openlabs_environment.py",
    "test_openlabs_doctor.py",
    "test_openlabs_state.py",
    "test_openlabs_namespace.py",
    "test_openlabs_port.py",
    "test_openlabs_lab_setup.py",
    "test_openlabs_lifecycle.py",
    "test_openlabs_reset_safety.py",
    "test_openlabs_verify.py",
    "test_cli_contract_fixtures.py",
    "test_diagnostic_registry.py",
)


def run_step(name: str) -> int:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / name)],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print(f"m2 gate: {name} failed", file=sys.stderr)
        return result.returncode
    return 0


def main() -> int:
    for name in STEPS:
        code = run_step(name)
        if code != 0:
            return code
    print(f"m2 gate: passed {len(STEPS)} suites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
