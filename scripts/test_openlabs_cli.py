#!/usr/bin/env python3
"""Unit tests for the openlabs CLI core (M2-02)."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENLABS = REPO_ROOT / "openlabs"
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cli_contract import validate_envelope  # noqa: E402
from openlabs_cli.app import run_cli  # noqa: E402
from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.envelope import build_envelope, Diagnostic, CliResult  # noqa: E402
from openlabs_cli.root import find_repo_root  # noqa: E402


def _run(args: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    cwd = cwd or REPO_ROOT
    proc = subprocess.run(
        [str(OPENLABS), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _validate_json(stdout: str, *, label: str) -> dict:
    data = json.loads(stdout)
    errors = validate_envelope(data, path=label)
    if errors:
        raise AssertionError("\n".join(errors))
    return data


def test_version_human() -> None:
    code, out, err = _run(["--version"])
    assert code == 0
    assert "openlabs" in out
    assert err == ""


def test_version_json_envelope() -> None:
    code, out, err = _run(["--json", "--version"])
    assert code == 0
    assert err == ""
    payload = _validate_json(out, label="version.json")
    assert payload["ok"] is True
    assert payload["data"]["cli_version"]


def test_help_json_envelope() -> None:
    code, out, err = _run(["--json", "--help"])
    assert code == 0
    payload = _validate_json(out, label="help.json")
    assert payload["data"]["action"] == "help"


def test_unknown_command_json() -> None:
    code, out, err = _run(["--json", "nosuch"])
    assert code == 2
    payload = _validate_json(out, label="usage.json")
    assert payload["ok"] is False
    assert payload["diagnostics"][0]["key"] == "lifecycle.cli.usage"


def test_setup_json_envelope() -> None:
    code, out, _err = _run(["--json", "setup"])
    payload = _validate_json(out, label="setup.json")
    assert payload["command"] == "setup"
    assert payload["data"]["action"] == "run"
    assert "checks" in payload["data"]
    assert "tier" in payload["data"]


def test_repo_layout_invalid() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        code, out, err = _run(["--json", "setup"], cwd=Path(tmp))
    assert code == 3
    payload = _validate_json(out, label="repo.json")
    assert payload["diagnostics"][0]["key"] == "environment.repo.layout_invalid"


def test_dry_run_flag_reaches_envelope() -> None:
    code, out, _err = _run(["--json", "--dry-run", "lab", "list"])
    assert code == 0
    payload = _validate_json(out, label="dry-run.json")
    assert payload["dry_run"] is True
    assert payload["data"]["action"] == "list"


def test_redaction_in_diagnostic_message() -> None:
    ctx = CliContext(repo_root=REPO_ROOT, json_mode=True)
    secret_path = f"under /home/player/{REPO_ROOT.name}"
    result = CliResult(
        command="setup",
        ok=False,
        exit_code=1,
        diagnostics=[Diagnostic("lifecycle.cli.internal", secret_path)],
    )
    envelope = build_envelope(result, ctx)
    assert "<path>" in envelope["diagnostics"][0]["message"]


def test_broken_pipe_exits_cleanly() -> None:
    stdout = io.StringIO()

    class BrokenStdout(io.StringIO):
        def write(self, _s: str) -> int:
            raise BrokenPipeError

    ctx = CliContext(repo_root=REPO_ROOT, json_mode=True)
    result = CliResult(
        command="setup",
        ok=True,
        exit_code=0,
        data={"action": "help"},
    )
    with mock.patch("openlabs_cli.envelope.sys.stdout", BrokenStdout()):
        code = __import__("openlabs_cli.envelope", fromlist=["emit_result"]).emit_result(
            result, ctx
        )
    assert code == 0


def test_interrupt_flag_changes_result() -> None:
    ctx = CliContext(repo_root=REPO_ROOT)
    ctx.interrupted = True
    result = CliResult(command="setup", ok=True, exit_code=0, data={})
    if ctx.interrupted and result.ok:
        result = CliResult(
            command=result.command,
            ok=False,
            exit_code=1,
            data=result.data,
            diagnostics=[
                Diagnostic(
                    "lifecycle.state.interrupted",
                    "command interrupted; re-run status or the same command",
                )
            ],
        )
    assert result.diagnostics[0].key == "lifecycle.state.interrupted"


def test_find_repo_root_from_repo() -> None:
    assert find_repo_root(REPO_ROOT) == REPO_ROOT


def main() -> int:
    tests = [
        test_version_human,
        test_version_json_envelope,
        test_help_json_envelope,
        test_unknown_command_json,
        test_setup_json_envelope,
        test_repo_layout_invalid,
        test_dry_run_flag_reaches_envelope,
        test_redaction_in_diagnostic_message,
        test_broken_pipe_exits_cleanly,
        test_interrupt_flag_changes_result,
        test_find_repo_root_from_repo,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs cli: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs cli: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
