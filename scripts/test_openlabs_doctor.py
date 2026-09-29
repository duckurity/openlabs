#!/usr/bin/env python3
"""Tests for openlabs doctor and setup handlers (M2-05)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENLABS = REPO_ROOT / "openlabs"
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cli_contract import validate_envelope  # noqa: E402
from openlabs_cli.commands.doctor import handle_doctor  # noqa: E402
from openlabs_cli.commands.setup import handle_setup  # noqa: E402
from openlabs_cli.environment_probe import ProbeOverrides  # noqa: E402
from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.repo_config import PLANNED_CATALOG_FIX, PLANNED_CONFIG_FIX  # noqa: E402
from openlabs_cli.runner import CommandResult, SubprocessCommandRunner  # noqa: E402


class _MapRunner:
    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> CommandResult:
        _ = cwd, timeout
        key = tuple(argv)
        responses = getattr(self, "responses", {})
        if key in responses:
            return responses[key]
        return CommandResult(127, "", "command not mocked")

    def __init__(self, responses: dict[tuple[str, ...], CommandResult] | None = None) -> None:
        self.responses = responses or {}


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


def _mini_repo(tmp: Path) -> Path:
    (tmp / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
    (tmp / "scripts").mkdir()
    (tmp / "scripts" / "validate.py").write_text("", encoding="utf-8")
    (tmp / "labs").mkdir()
    return tmp


def test_setup_non_interactive_requires_confirmation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _mini_repo(Path(tmp))
        runner = _MapRunner(
            {
                ("docker", "--version"): CommandResult(0, "Docker version 26.0.0", ""),
                ("docker", "info"): CommandResult(0, "Server:", ""),
                ("docker", "compose", "version"): CommandResult(0, "Compose v2.24.0", ""),
                ("git", "--version"): CommandResult(0, "git version 2.43.0", ""),
            }
        )
        ctx = CliContext(repo_root=root, json_mode=True, non_interactive=True, runner=runner)
        result = handle_setup(ctx, [])
        assert result.exit_code == 1
        assert result.diagnostics[0].key == "lifecycle.interaction.non_interactive_required"


def test_setup_dry_run_envelope() -> None:
    code, out, _err = _run(["--json", "--dry-run", "setup"])
    payload = _json(out, label="setup-dry.json")
    assert payload["dry_run"] is True
    assert payload["data"]["action"] == "run"
    assert "checks" in payload["data"]


def test_doctor_fix_dry_run_planned_fixes() -> None:
    from openlabs_cli.repo_config import config_path, load_config

    cfg = config_path(REPO_ROOT)
    backup: str | None = None
    if cfg.is_file():
        backup = cfg.read_text(encoding="utf-8")
        cfg.unlink()
    assert load_config(REPO_ROOT) is None
    try:
        code, out, err = _run(["--json", "--dry-run", "doctor", "--fix"])
        assert code == 0, f"exit={code} stderr={err!r} stdout={out[:500]!r}"
        payload = _json(out, label="doctor-fix-dry.json")
        assert payload["data"]["fix"] is True
        planned = payload["data"]["planned_fixes"]
        assert PLANNED_CONFIG_FIX in planned
        assert PLANNED_CATALOG_FIX in planned
    finally:
        if backup is not None:
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(backup, encoding="utf-8")
        elif cfg.is_file():
            cfg.unlink()


def test_doctor_json_read_only() -> None:
    code, out, _err = _run(["--json", "doctor"])
    payload = _json(out, label="doctor.json")
    assert payload["data"]["action"] == "run"
    assert "validate_ok" in payload["data"]


def test_doctor_handler_default_read_only_no_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _mini_repo(Path(tmp))
        ctx = CliContext(repo_root=root, runner=SubprocessCommandRunner())
        before = list(root.rglob("*"))
        result = handle_doctor(ctx, [])
        after = list(root.rglob("*"))
        assert before == after
        assert result.data["action"] == "run"
        assert "fix" not in result.data


def main() -> int:
    tests = [
        test_setup_non_interactive_requires_confirmation,
        test_setup_dry_run_envelope,
        test_doctor_fix_dry_run_planned_fixes,
        test_doctor_json_read_only,
        test_doctor_handler_default_read_only_no_writes,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs doctor: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs doctor: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
