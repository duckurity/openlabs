#!/usr/bin/env python3
"""Tests for structured subprocess failures in the CLI runner."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from openlabs_cli.runner import (  # noqa: E402
    COMMAND_TIMEOUT,
    EXECUTABLE_NOT_FOUND,
    SubprocessCommandRunner,
)


def test_missing_executable_returns_127() -> None:
    runner = SubprocessCommandRunner()
    result = runner.run(
        ["/no/such/openlabs/binary"],
        cwd=REPO_ROOT,
        timeout=1.0,
    )
    assert result.returncode == EXECUTABLE_NOT_FOUND
    assert "not found" in result.stderr.lower() or "executable" in result.stderr.lower()


def test_timeout_returns_124() -> None:
    runner = SubprocessCommandRunner()
    result = runner.run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=REPO_ROOT,
        timeout=0.1,
    )
    assert result.returncode == COMMAND_TIMEOUT


def main() -> int:
    tests = (test_missing_executable_returns_127, test_timeout_returns_124)
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs runner: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs runner: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
