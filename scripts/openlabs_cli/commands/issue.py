"""openlabs issue explain and bundle."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from diagnostic_registry import (
    build_explain_payload,
    format_explain_human,
    lookup_entry_by_id,
    normalize_diagnostic_id,
    redact_mapping,
    redact_sensitive,
)

from openlabs_cli.bundle_io import atomic_write_json, planned_bundle_path
from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.errors import UsageError
from openlabs_cli.platform_probe import platform_summary
from openlabs_cli.version import CLI_VERSION, ENVELOPE_VERSION, LAB_CONTRACT_VERSION


def _docker_versions(ctx: CliContext) -> dict[str, str | None]:
    if ctx.runner is None:
        return {"client": None, "compose": None}
    client = ctx.runner.run(["docker", "--version"], cwd=ctx.repo_root, timeout=5.0)
    compose = ctx.runner.run(["docker", "compose", "version"], cwd=ctx.repo_root, timeout=5.0)
    client_text = client.stdout.strip() if client.returncode == 0 else None
    compose_text = compose.stdout.strip() if compose.returncode == 0 else None
    return {
        "client": redact_sensitive(client_text) if client_text else None,
        "compose": redact_sensitive(compose_text) if compose_text else None,
    }


def handle_explain(ctx: CliContext, args: list[str]) -> CliResult:
    if len(args) != 2:
        raise UsageError("usage: openlabs issue explain OL-####")
    registry_id = normalize_diagnostic_id(args[1])
    if registry_id is None:
        message = f"invalid diagnostic id {args[1]!r}"
        return CliResult(
            command="issue",
            ok=False,
            exit_code=1,
            data={"action": "explain", "id": args[1]},
            diagnostics=[Diagnostic("lifecycle.cli.unknown_diagnostic", message)],
            human_lines=[message],
        )
    entry = lookup_entry_by_id(registry_id)
    if entry is None:
        message = f"unknown diagnostic id {registry_id}"
        return CliResult(
            command="issue",
            ok=False,
            exit_code=1,
            data={"action": "explain", "id": registry_id},
            diagnostics=[Diagnostic("lifecycle.cli.unknown_diagnostic", message)],
            human_lines=[message],
        )
    payload = build_explain_payload(entry)
    return CliResult(
        command="issue",
        ok=True,
        exit_code=0,
        data=payload,
        human_lines=format_explain_human(payload),
    )


def build_bundle_payload(ctx: CliContext, *, lab: str | None) -> dict[str, Any]:
    repo_display = redact_sensitive(str(ctx.repo_root))
    bundle: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": repo_display,
        "cli_version": CLI_VERSION,
        "command_envelope": ENVELOPE_VERSION,
        "lab_contract_version": LAB_CONTRACT_VERSION,
        "platform": platform_summary(),
        "docker": _docker_versions(ctx),
        "lab": redact_sensitive(lab) if lab else None,
        "diagnostics": [],
        "notes": "",
    }
    return redact_mapping(bundle)


def handle_bundle(ctx: CliContext, args: list[str]) -> CliResult:
    lab = args[1] if len(args) > 1 else None
    if lab is not None and lab.startswith("-"):
        raise UsageError("usage: openlabs issue bundle [lab]")
    payload = build_bundle_payload(ctx, lab=lab)
    target = planned_bundle_path(ctx.repo_root)
    if ctx.dry_run:
        return CliResult(
            command="issue",
            ok=True,
            exit_code=0,
            data={
                "action": "bundle",
                "planned_path": redact_sensitive(str(target)),
                "bundle": payload,
            },
            meta={"redacted": True},
            human_lines=[f"would write bundle to {target.name}"],
        )
    atomic_write_json(target, {"bundle": payload})
    return CliResult(
        command="issue",
        ok=True,
        exit_code=0,
        data={"action": "bundle", "path": redact_sensitive(str(target)), "bundle": payload},
        meta={"redacted": True},
        human_lines=[f"wrote bundle to {target.relative_to(ctx.repo_root)}"],
    )


def handle_issue(ctx: CliContext, args: list[str]) -> CliResult:
    if not args:
        raise UsageError("issue requires explain OL-#### or bundle")
    action = args[0]
    if action == "explain":
        return handle_explain(ctx, args)
    if action == "bundle":
        return handle_bundle(ctx, args[1:])
    raise UsageError(f"unknown issue action {action!r}")
