"""openlabs setup (repository preflight)."""

from __future__ import annotations

from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.environment_probe import (
    checks_payload,
    diagnostics_from_report,
    run_environment_probe,
)
from openlabs_cli.errors import UsageError
from openlabs_cli.repo_config import config_path, load_config, write_config


def _parse_action(args: list[str]) -> str:
    if not args or args[0] in {"run", "help", "--help"}:
        return "run"
    raise UsageError(f"unknown setup action {args[0]!r}")


def handle_setup(ctx: CliContext, args: list[str]) -> CliResult:
    action = _parse_action(args)
    report = run_environment_probe(ctx)
    diagnostics = [
        Diagnostic(key, message) for key, message in diagnostics_from_report(report)
    ]
    data: dict[str, object] = {
        "action": action,
        "checks": checks_payload(report),
        "missing": list(report.missing),
        "tier": report.tier,
    }
    if report.guidance:
        data["guidance"] = list(report.guidance)

    blocking = bool(report.missing)
    needs_config = load_config(ctx.repo_root) is None

    if ctx.dry_run:
        planned = [".openlabs/config.json"] if needs_config and not blocking else []
        if planned:
            data["planned_writes"] = planned
        human = ["setup dry-run: no repo-local files written"]
        if planned:
            human.append(f"planned writes: {', '.join(planned)}")
        return CliResult(
            command="setup",
            ok=not blocking,
            exit_code=0 if not blocking else 1,
            data=data,
            diagnostics=diagnostics,
            human_lines=human,
            meta={"reset_safe": True},
        )

    if needs_config and ctx.non_interactive:
        prompt = "create .openlabs/config.json"
        data["prompt"] = prompt
        return CliResult(
            command="setup",
            ok=False,
            exit_code=1,
            data=data,
            diagnostics=[
                Diagnostic(
                    "lifecycle.interaction.non_interactive_required",
                    "confirmation required; re-run without --non-interactive",
                )
            ],
            human_lines=["confirmation required; re-run without --non-interactive"],
        )

    if blocking:
        human = ["setup blocked; fix missing prerequisites:"]
        human.extend(f"  - {name}" for name in report.missing)
        return CliResult(
            command="setup",
            ok=False,
            exit_code=1,
            data=data,
            diagnostics=diagnostics,
            human_lines=human,
        )

    if needs_config:
        write_config(ctx.repo_root, tier=report.tier)
        data["config"] = str(config_path(ctx.repo_root).relative_to(ctx.repo_root))

    human = [f"setup complete (tier {report.tier})"]
    if report.guidance:
        human.extend(report.guidance)
    return CliResult(
        command="setup",
        ok=True,
        exit_code=0,
        data=data,
        diagnostics=diagnostics,
        human_lines=human,
        meta={"reset_safe": True},
    )
