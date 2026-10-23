"""openlabs doctor (read-only checks and repo-local fixes)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.environment_probe import (
    checks_payload,
    diagnostics_from_report,
    run_environment_probe,
)
from openlabs_cli.errors import UsageError
from openlabs_cli.repo_config import (
    catalog_cache_path,
    load_config,
    planned_repo_fixes,
    refresh_catalog_cache,
    write_config,
)

SCRIPTS = Path(__file__).resolve().parents[2]


def _parse_doctor_args(args: list[str]) -> tuple[bool, str]:
    fix = False
    rest = list(args)
    if rest and rest[0] == "--fix":
        fix = True
        rest = rest[1:]
    if rest and rest[0] not in {"run", "help", "--help"}:
        raise UsageError(f"unknown doctor action {rest[0]!r}")
    return fix, "run"


def _run_script(ctx: CliContext, name: str, argv: list[str]) -> tuple[int, str]:
    if ctx.runner is None:
        return 127, "runner unavailable"
    script = SCRIPTS / name
    proc_argv = [sys.executable, str(script), *argv]
    result = ctx.runner.run(proc_argv, cwd=ctx.repo_root, timeout=120.0)
    output = (result.stdout or "") + (result.stderr or "")
    if len(output) > 800:
        output = output[:797] + "..."
    return result.returncode, output.strip()


def _validate_blocking(ctx: CliContext) -> tuple[bool, list[Diagnostic]]:
    sys.path.insert(0, str(SCRIPTS))
    from validate import run_validate  # noqa: E402

    records, _unc = run_validate(compose=False)
    diagnostics: list[Diagnostic] = []
    blocked = False
    for record in records:
        if record.ok or record.status == "experimental":
            continue
        blocked = True
        message = record.errors[0] if record.errors else f"{record.path} failed validation"
        key = "contract.context.name_directory_mismatch"
        if "does not match directory" in message:
            key = "contract.context.name_directory_mismatch"
        diagnostics.append(Diagnostic(key, message))
        break
    return not blocked, diagnostics


def handle_doctor(ctx: CliContext, args: list[str]) -> CliResult:
    fix, action = _parse_doctor_args(args)
    report = run_environment_probe(ctx)
    env_diagnostics = [
        Diagnostic(key, message) for key, message in diagnostics_from_report(report)
    ]

    validate_ok, validate_diags = _validate_blocking(ctx)
    catalog_code, _catalog_out = _run_script(ctx, "sync_catalog_public.py", ["--check"])
    triage_code, _triage_out = _run_script(ctx, "lab_triage_inventory.py", ["--check"])
    catalog_ok = catalog_code == 0
    triage_ok = triage_code == 0

    data: dict[str, object] = {
        "action": action,
        "checks": checks_payload(report),
        "tier": report.tier,
        "validate_ok": validate_ok,
        "catalog_ok": catalog_ok,
        "triage_ok": triage_ok,
    }
    if fix:
        data["fix"] = True

    diagnostics = env_diagnostics + validate_diags
    ok = validate_ok and catalog_ok and triage_ok and not report.missing
    exit_code = 0 if ok else 1

    if not validate_ok and validate_diags:
        data["summary"] = "catalog drift detected"

    if fix and ctx.dry_run:
        data["planned_fixes"] = planned_repo_fixes(ctx.repo_root)
        return CliResult(
            command="doctor",
            ok=True,
            exit_code=0,
            data=data,
            diagnostics=diagnostics,
            human_lines=["doctor fix dry-run: no repo-local changes applied"],
            meta={"reset_safe": True},
        )

    if fix and not ctx.dry_run:
        if load_config(ctx.repo_root) is None:
            write_config(ctx.repo_root, tier=report.tier)
        refresh_catalog_cache(ctx.repo_root)
        data["applied_fixes"] = planned_repo_fixes(ctx.repo_root)
        human = ["doctor applied repo-local fixes"]
        return CliResult(
            command="doctor",
            ok=ok,
            exit_code=exit_code,
            data=data,
            diagnostics=diagnostics,
            human_lines=human,
            meta={"reset_safe": True},
        )

    human = ["doctor summary:"]
    human.append(f"  tier: {report.tier}")
    human.append(f"  validate: {'ok' if validate_ok else 'failed'}")
    human.append(f"  catalog: {'ok' if catalog_ok else 'drift'}")
    human.append(f"  triage: {'ok' if triage_ok else 'drift'}")
    if report.missing:
        human.append("  environment missing: " + ", ".join(report.missing))
    if report.guidance:
        human.extend(report.guidance)

    return CliResult(
        command="doctor",
        ok=ok,
        exit_code=exit_code,
        data=data,
        diagnostics=diagnostics,
        human_lines=human,
        meta={"redacted": True},
    )
