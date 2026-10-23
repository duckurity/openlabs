#!/usr/bin/env python3
"""Run Tier 1 duck-cross lifecycle via openlabs and emit bounded evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from cli_contract import validate_envelope  # noqa: E402
from evidence_artifact import EVIDENCE_VERSION, write_bounded_json  # noqa: E402
from openlabs_cli.compose_ops import compose_argv_from_state  # noqa: E402
from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.lab_discovery import resolve_lab  # noqa: E402
from openlabs_cli.lab_runtime import run_compose  # noqa: E402
from openlabs_cli.runner import SubprocessCommandRunner  # noqa: E402
from openlabs_cli.state_store import load_state  # noqa: E402

LAB = "duck-cross"
STEP_TIMEOUT_S = 900.0
OPENLABS = REPO_ROOT / "openlabs"

LIFECYCLE_STEPS: tuple[tuple[str, list[str]], ...] = (
    ("lab_setup", ["lab", "setup", LAB]),
    ("lab_verify", ["lab", "verify", LAB]),
    ("lab_reset", ["lab", "reset", LAB]),
    ("lab_start", ["lab", "start", LAB]),
    ("lab_status", ["lab", "status", LAB]),
    ("lab_stop", ["lab", "stop", LAB]),
)


def _global_argv(tail: list[str]) -> list[str]:
    return [str(OPENLABS), "--json", "--non-interactive", *tail]


def run_openlabs_step(
    argv: list[str],
    *,
    step_name: str,
    cwd: Path,
    timeout: float = STEP_TIMEOUT_S,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    started = time.time()
    if runner is None:
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return {
                "name": step_name,
                "ok": False,
                "exit_code": 127,
                "seconds": round(time.time() - started, 2),
                "diagnostic_key": "environment.docker.client_missing",
                "detail": "openlabs executable or docker client unavailable",
                "stdout": "",
                "stderr": "",
            }
        except subprocess.TimeoutExpired:
            return {
                "name": step_name,
                "ok": False,
                "exit_code": 124,
                "seconds": round(time.time() - started, 2),
                "diagnostic_key": "lifecycle.cli.internal",
                "detail": f"command timed out after {timeout}s",
                "stdout": "",
                "stderr": "",
            }
    else:
        try:
            completed = runner(argv, cwd=cwd, timeout=timeout)
        except FileNotFoundError:
            return {
                "name": step_name,
                "ok": False,
                "exit_code": 127,
                "seconds": round(time.time() - started, 2),
                "diagnostic_key": "environment.docker.client_missing",
                "detail": "openlabs executable or docker client unavailable",
                "stdout": "",
                "stderr": "",
            }
        except subprocess.TimeoutExpired:
            return {
                "name": step_name,
                "ok": False,
                "exit_code": 124,
                "seconds": round(time.time() - started, 2),
                "diagnostic_key": "lifecycle.cli.internal",
                "detail": f"command timed out after {timeout}s",
                "stdout": "",
                "stderr": "",
            }

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    record: dict[str, Any] = {
        "name": step_name,
        "ok": completed.returncode == 0,
        "exit_code": completed.returncode,
        "seconds": round(time.time() - started, 2),
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
    }
    if stdout.strip():
        try:
            envelope = json.loads(stdout)
            record["envelope"] = envelope
            errors = validate_envelope(envelope, path="tier1-step.json")
            if errors:
                record["ok"] = False
                record["envelope_errors"] = errors
                record["detail"] = "invalid openlabs.command.v1 envelope"
            elif isinstance(envelope, dict) and not envelope.get("ok", False):
                record["ok"] = False
                diagnostics = envelope.get("diagnostics") or []
                if diagnostics and isinstance(diagnostics[0], dict):
                    record["diagnostic_key"] = diagnostics[0].get("key")
                record["detail"] = "openlabs returned ok false"
        except json.JSONDecodeError:
            record["ok"] = False
            record["detail"] = "stdout was not valid JSON"
    elif completed.returncode != 0:
        record["detail"] = stderr.strip() or "command failed with no JSON stdout"
    return record


def _cleanup(ctx: CliContext) -> dict[str, Any]:
    started = time.time()
    steps: list[dict[str, Any]] = []
    ok = True
    detail = "cleanup complete"
    selection = resolve_lab(ctx.repo_root, LAB)
    if not hasattr(selection, "lab_dir"):
        return {
            "ok": False,
            "detail": "duck-cross not found for cleanup",
            "seconds": round(time.time() - started, 2),
            "steps": steps,
        }
    state = load_state(ctx.repo_root, LAB)
    if state:
        try:
            argv = compose_argv_from_state(
                ctx.repo_root,
                lab_dir=selection.lab_dir,
                state=state,
                subcommand=["down", "--remove-orphans"],
            )
            code, out = run_compose(ctx, argv, timeout=120.0)
            steps.append({"action": "compose_down", "ok": code == 0, "detail": out[:200]})
            if code != 0:
                ok = False
                detail = "compose down during cleanup failed"
        except OSError as exc:
            ok = False
            detail = str(exc)
    reset_argv = _global_argv(["lab", "reset", LAB])
    reset = run_openlabs_step(reset_argv, step_name="cleanup_reset", cwd=ctx.repo_root, timeout=120.0)
    steps.append({"action": "lab_reset", **{k: reset.get(k) for k in ("ok", "exit_code", "detail")}})
    if not reset.get("ok", False):
        ok = False
        detail = "lab reset during cleanup failed"
    return {
        "ok": ok,
        "detail": detail,
        "seconds": round(time.time() - started, 2),
        "steps": steps,
    }


def run_tier1_lifecycle(
    *,
    repo_root: Path,
    output: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> tuple[int, dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    failed = False
    ctx = CliContext(repo_root=repo_root, runner=SubprocessCommandRunner())
    cleanup: dict[str, Any] = {"ok": True, "detail": "not run", "seconds": 0.0, "steps": []}
    document: dict[str, Any] = {
        "version": EVIDENCE_VERSION,
        "lab": LAB,
        "steps": steps,
        "cleanup": cleanup,
        "truncated": False,
        "meta": {"redacted": True},
    }
    try:
        for name, tail in LIFECYCLE_STEPS:
            record = run_openlabs_step(
                _global_argv(tail),
                step_name=name,
                cwd=repo_root,
                runner=runner,
            )
            record["step"] = name
            steps.append(record)
            if not record.get("ok", False):
                failed = True
    finally:
        cleanup = _cleanup(ctx)
        document["steps"] = steps
        document["cleanup"] = cleanup
        if output is not None:
            write_bounded_json(output, document)

    if not cleanup.get("ok", True):
        failed = True

    return (1 if failed else 0), document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True, help="write bounded evidence JSON")
    args = parser.parse_args()
    code, _doc = run_tier1_lifecycle(repo_root=REPO_ROOT, output=args.json)
    return code


if __name__ == "__main__":
    sys.exit(main())
