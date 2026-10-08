"""openlabs lab verify — supported verification with L0-L6 evidence."""

from __future__ import annotations

from typing import Any

from openlabs_cli.compose_ops import planned_compose_step
from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.errors import UsageError
from openlabs_cli.lab_discovery import LabSelectionError, ResolvedLab, resolve_lab
from openlabs_cli.lab_verification import VerificationFailure, run_verification
from openlabs_cli.verification import adapters

LEVELS = tuple(f"L{i}" for i in range(7))


def _usage() -> UsageError:
    return UsageError("usage: openlabs lab verify <lab> [--level Ln]")


def _parse_args(args: list[str]) -> tuple[str, str | None]:
    stop_after: str | None = None
    positional: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--level":
            if index + 1 >= len(args):
                raise UsageError("usage: openlabs lab verify <lab> [--level Ln]")
            stop_after = args[index + 1]
            index += 2
            continue
        if token.startswith("--"):
            raise UsageError(f"unknown option: {token}")
        positional.append(token)
        index += 1
    if len(positional) != 1:
        raise _usage()
    if stop_after is not None and stop_after not in LEVELS:
        raise UsageError(f"--level must be one of {', '.join(LEVELS)}")
    return positional[0], stop_after


def _resolve(ctx: CliContext, selector: str) -> ResolvedLab | CliResult:
    selection = resolve_lab(ctx.repo_root, selector)
    if isinstance(selection, LabSelectionError):
        from openlabs_cli.commands.lab import selection_failure

        return selection_failure(selection)
    return selection


def _level_human_lines(levels: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for step in levels:
        if not step.get("ok"):
            suffix = f" — {step.get('detail')}" if step.get("detail") else ""
            lines.append(f"{step['level']}: failed ({step.get('seconds')}s){suffix}")
            continue
        suffix = f" — {step['detail']}" if step.get("detail") else ""
        lines.append(f"{step['level']}: ok ({step.get('seconds')}s){suffix}")
    return lines


def handle_lab_verify(ctx: CliContext, args: list[str]) -> CliResult:
    selector, stop_after = _parse_args(args)
    resolved = _resolve(ctx, selector)
    if isinstance(resolved, CliResult):
        return resolved

    entry = resolved.entry
    slug = entry["slug"]
    status = entry.get("status")
    lab_field = selector if selector.startswith("labs/") else slug

    if ctx.dry_run:
        planned = [
            "L0 metadata and required files",
            "L1 compose render with player port",
            "L2 image build",
            "L3 start and readiness",
            "L4 public smoke checks",
            "L5 intended-solve adapter",
            planned_compose_step(["down", "--remove-orphans"]),
            "second start L3-L5 and L6 teardown",
        ]
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "verify",
                "lab": lab_field,
                "planned": planned,
                "levels": [],
            },
            human_lines=["lab verify dry-run: no containers changed"],
            meta={"reset_safe": True},
        )

    if entry.get("blockers") and "container_name" in entry["blockers"]:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "verify", "lab": slug, "blockers": entry["blockers"]},
            diagnostics=[
                Diagnostic(
                    "lifecycle.compose.unsafe_container_name",
                    "compose file declares container_name; verification blocked",
                )
            ],
            human_lines=["compose declares container_name; choose a supported lab"],
        )

    if status != "supported":
        try:
            report = run_verification(
                ctx,
                resolved,
                stop_after="L1",
                include_second_cycle=False,
                allow_experimental=True,
            )
        except VerificationFailure as error:
            report = error.report
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={
                "action": "verify",
                "lab": slug,
                "levels": report.levels,
                "supported_verification": False,
            },
            diagnostics=[
                Diagnostic(
                    "lifecycle.lab.unsupported_operation",
                    "experimental lab lacks supported intended-solve verification",
                )
            ],
            human_lines=[
                "generic metadata checks may run; supported verification requires a supported lab",
                *_level_human_lines(report.levels),
            ],
            meta={"redacted": False},
        )

    if not adapters.has_supported_l5(slug):
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "verify", "lab": slug, "supported_verification": False},
            diagnostics=[
                Diagnostic(
                    "lifecycle.lab.unsupported_operation",
                    "no intended-solve verification adapter registered for this lab",
                )
            ],
            human_lines=["supported verification is not available for this lab"],
        )

    try:
        report = run_verification(
            ctx,
            resolved,
            stop_after=stop_after,
            reference=None,
            include_second_cycle=stop_after is None,
        )
    except VerificationFailure as error:
        report = error.report
        detail = error.detail
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={
                "action": "verify",
                "lab": slug,
                "levels": report.levels,
                "failed_level": report.failed_level,
                "project": report.project,
                "port": report.port,
            },
            diagnostics=[
                Diagnostic(
                    "lifecycle.cli.internal",
                    f"{report.failed_level} failed: {detail}",
                )
            ],
            human_lines=[
                f"{report.failed_level} failed: {detail}",
                *_level_human_lines(report.levels),
            ],
            meta={"redacted": True, "reset_safe": True},
        )

    human = _level_human_lines(report.levels)
    human.append(
        f"lab {slug}: verification passed (project {report.project}, port {report.port})"
    )
    return CliResult(
        command="lab",
        ok=True,
        exit_code=0,
        data={
            "action": "verify",
            "lab": slug,
            "levels": report.levels,
            "project": report.project,
            "port": report.port,
            "supported_verification": True,
        },
        human_lines=human,
        meta={"redacted": False, "reset_safe": True},
    )
