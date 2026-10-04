#!/usr/bin/env python3
"""Tests for openlabs lab lifecycle commands (M2-07)."""

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
from openlabs_cli.runner import CommandResult  # noqa: E402
from openlabs_cli.state_store import build_state_payload, write_state  # noqa: E402


class _RecordingRunner:
    def __init__(self, *, ps_output: str = "container-id\n") -> None:
        self.calls: list[list[str]] = []
        self.ps_output = ps_output

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> CommandResult:
        _ = cwd, timeout
        self.calls.append(list(argv))
        if "ps" in argv:
            return CommandResult(0, self.ps_output, "")
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


def _seed_state(tmp: Path, *, lifecycle: str = "stopped") -> None:
    write_state(
        tmp,
        build_state_payload(
            slug="duck-cross",
            compose_project="openlabs-test-duck-cross",
            host_port=8377,
            lifecycle=lifecycle,
            compose_file="labs/web/duck-cross/docker-compose.yml",
            container_port=8377,
        ),
    )


def test_dry_run_lifecycle_commands_exit_zero() -> None:
    for action in ("start", "status", "stop", "reset"):
        code, out, _err = _run(["--json", "--dry-run", "lab", action, "duck-cross"])
        assert code == 0, action
        payload = _json(out, label=f"dry-run-{action}.json")
        assert payload["dry_run"] is True
        assert payload["data"]["action"] == action
        if action in {"start", "stop", "reset"}:
            assert payload["data"]["planned"]
            assert payload["meta"]["reset_safe"] is True


def test_start_uses_namespaced_compose_argv() -> None:
    from unittest.mock import patch

    runner = _RecordingRunner(ps_output="")
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    _seed_state(REPO_ROOT, lifecycle="stopped")
    try:
        with patch("openlabs_cli.lab_lifecycle.wait_ready", return_value=True):
            result = handle_lab(ctx, ["start", "duck-cross"])
        assert result.ok
        assert any(call[-2:] == ["up", "-d"] for call in runner.calls)
        for call in runner.calls:
            assert "-p" in call
            assert call[call.index("-p") + 1] == "openlabs-test-duck-cross"
            assert call.count("-f") >= 1
            assert "prune" not in call
            assert "system" not in call
    finally:
        state_file = REPO_ROOT / ".openlabs/state/duck-cross.json"
        if state_file.is_file():
            state_file.unlink()


def test_stop_idempotent_when_compose_absent() -> None:
    runner = _RecordingRunner(ps_output="")
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    _seed_state(REPO_ROOT, lifecycle="ready")
    try:
        result = handle_lab(ctx, ["stop", "duck-cross"])
        assert result.ok
        assert result.data.get("no_op") is True
        assert not any("stop" in call for call in runner.calls)
    finally:
        state_file = REPO_ROOT / ".openlabs/state/duck-cross.json"
        if state_file.is_file():
            state_file.unlink()


def test_status_reports_drift_when_compose_stopped() -> None:
    runner = _RecordingRunner(ps_output="")
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    _seed_state(REPO_ROOT, lifecycle="ready")
    try:
        result = handle_lab(ctx, ["status", "duck-cross"])
        assert result.ok
        assert result.data["drift"] is True
        assert result.data["compose"] == "stopped"
    finally:
        state_file = REPO_ROOT / ".openlabs/state/duck-cross.json"
        if state_file.is_file():
            state_file.unlink()


def test_status_interrupted_when_building() -> None:
    runner = _RecordingRunner()
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    _seed_state(REPO_ROOT, lifecycle="building")
    try:
        result = handle_lab(ctx, ["status", "duck-cross"])
        assert not result.ok
        assert result.diagnostics[0].key == "lifecycle.state.interrupted"
    finally:
        state_file = REPO_ROOT / ".openlabs/state/duck-cross.json"
        if state_file.is_file():
            state_file.unlink()


def main() -> int:
    tests = [
        test_dry_run_lifecycle_commands_exit_zero,
        test_start_uses_namespaced_compose_argv,
        test_stop_idempotent_when_compose_absent,
        test_status_reports_drift_when_compose_stopped,
        test_status_interrupted_when_building,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs lab lifecycle: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs lab lifecycle: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
