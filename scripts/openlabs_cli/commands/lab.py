"""openlabs lab actions."""

from __future__ import annotations

from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.errors import UsageError
from openlabs_cli.lab_discovery import format_list_human, list_catalog


def handle_list(ctx: CliContext, args: list[str]) -> CliResult:
    if args:
        raise UsageError("usage: openlabs lab list")
    payload = list_catalog(ctx.repo_root)
    return CliResult(
        command="lab",
        ok=True,
        exit_code=0,
        data=payload,
        human_lines=format_list_human(payload),
    )


def handle_lab(ctx: CliContext, args: list[str]) -> CliResult:
    if not args:
        raise UsageError("lab requires an action")
    action = args[0]
    tail = args[1:]
    if action == "list":
        return handle_list(ctx, tail)
    if action == "setup":
        from openlabs_cli.lab_setup import handle_lab_setup

        return handle_lab_setup(ctx, tail)
    result = CliResult.not_implemented("lab", f"openlabs lab {action}")
    result.data["action"] = action
    return result


def selection_failure(error: object) -> CliResult:
    from openlabs_cli.lab_discovery import LabSelectionError

    if not isinstance(error, LabSelectionError):
        raise TypeError("expected LabSelectionError")
    return CliResult(
        command="lab",
        ok=False,
        exit_code=error.exit_code,
        data={"error": error.message},
        diagnostics=[Diagnostic(error.key, error.message)],
        human_lines=[error.message],
    )
