#!/usr/bin/env python3
"""Tests for openlabs lab setup (M2-06)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENLABS = REPO_ROOT / "openlabs"
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cli_contract import validate_envelope  # noqa: E402
from openlabs_cli.commands.lab import handle_lab  # noqa: E402
from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.lab_setup import handle_lab_setup  # noqa: E402
from openlabs_cli.runner import CommandResult  # noqa: E402


class _RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> CommandResult:
        _ = cwd, timeout
        self.calls.append(list(argv))
        return CommandResult(0, "ok", "")


def _run(args: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        [str(OPENLABS), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _json(stdout: str, *, label: str) -> dict:
    data = json.loads(stdout)
    errors = validate_envelope(data, path=label)
    if errors:
        raise AssertionError("\n".join(errors))
    return data


def test_dry_run_creates_no_openlabs_artifacts() -> None:
    before = list((REPO_ROOT / ".openlabs").rglob("*")) if (REPO_ROOT / ".openlabs").exists() else []
    code, out, _err = _run(["--json", "--dry-run", "lab", "setup", "duck-cross"])
    assert code == 0
    payload = _json(out, label="dry-run-setup.json")
    assert payload["dry_run"] is True
    assert payload["data"]["planned"]
    after = list((REPO_ROOT / ".openlabs").rglob("*")) if (REPO_ROOT / ".openlabs").exists() else []
    assert before == after


def test_dry_run_json_envelope_fields() -> None:
    code, out, _err = _run(["--json", "--dry-run", "lab", "setup", "duck-cross"])
    assert code == 0
    payload = _json(out, label="setup-dry.json")
    assert payload["data"]["host_port"] == 8377
    assert payload["data"]["project"].startswith("openlabs-")
    assert payload["meta"]["reset_safe"] is True


def test_container_name_blocked_before_docker() -> None:
    runner = _RecordingRunner()
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    result = handle_lab(ctx, ["setup", "vault-api"])
    assert result.exit_code == 1
    assert not runner.calls
    assert result.diagnostics[0].key == "lifecycle.compose.unsafe_container_name"


def test_experimental_blocked_before_docker() -> None:
    runner = _RecordingRunner()
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    result = handle_lab_setup(ctx, ["cloudvault"])
    assert result.exit_code == 1
    assert not runner.calls
    assert result.diagnostics[0].key == "lifecycle.lab.unsupported_operation"


def main() -> int:
    tests = [
        test_dry_run_creates_no_openlabs_artifacts,
        test_dry_run_json_envelope_fields,
        test_container_name_blocked_before_docker,
        test_experimental_blocked_before_docker,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs lab setup: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs lab setup: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
