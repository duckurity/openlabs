"""CLI application entry and dispatch."""

from __future__ import annotations

import signal
import time
from pathlib import Path

from openlabs_cli.commands import handle_doctor, handle_issue, handle_lab, handle_setup
from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic, emit_result
from openlabs_cli.errors import HandlerError, UsageError
from openlabs_cli.parser import ParsedInvocation, parse_argv, root_usage
from openlabs_cli.root import find_repo_root
from openlabs_cli.runner import SubprocessCommandRunner
from openlabs_cli.version import CLI_VERSION, ENVELOPE_VERSION, LAB_CONTRACT_VERSION, version_lines


def _help_result(scope: str, command: str = "setup") -> CliResult:
    text = root_usage() if scope == "root" else f"help for {command} is not expanded yet"
    return CliResult(
        command=command,
        ok=True,
        exit_code=0,
        data={"action": "help", "scope": scope, "usage": text},
        human_lines=[text],
    )


def _version_result() -> CliResult:
    return CliResult(
        command="setup",
        ok=True,
        exit_code=0,
        data={
            "cli_version": CLI_VERSION,
            "envelope": ENVELOPE_VERSION,
            "lab_contract_version": LAB_CONTRACT_VERSION,
        },
        human_lines=version_lines(),
    )


def dispatch(parsed: ParsedInvocation, ctx: CliContext) -> CliResult:
    options = parsed.options
    if options.show_version:
        return _version_result()
    if parsed.command is None:
        if options.show_help:
            return _help_result("root")
        raise UsageError("missing command; try openlabs --help")
    if options.show_help and not parsed.args:
        return _help_result("command", parsed.command)
    handlers = {
        "setup": handle_setup,
        "doctor": handle_doctor,
        "issue": handle_issue,
        "lab": handle_lab,
    }
    return handlers[parsed.command](ctx, parsed.args)


def run_cli(argv: list[str], *, ctx: CliContext | None = None) -> int:
    start = time.monotonic()
    try:
        parsed = parse_argv(argv)
    except UsageError as exc:
        temp_ctx = CliContext(repo_root=find_repo_root() or Path.cwd())
        temp_ctx.json_mode = "--json" in argv
        temp_ctx.dry_run = "--dry-run" in argv
        result = CliResult.usage("setup", str(exc))
        duration = int((time.monotonic() - start) * 1000)
        return emit_result(result, temp_ctx, duration_ms=duration)

    options = parsed.options

    if options.show_version and parsed.command is None:
        temp_ctx = ctx or CliContext(repo_root=find_repo_root() or Path.cwd())
        temp_ctx.json_mode = options.json_mode
        duration = int((time.monotonic() - start) * 1000)
        return emit_result(_version_result(), temp_ctx, duration_ms=duration)

    if parsed.command is None and options.show_help:
        temp_ctx = ctx or CliContext(repo_root=find_repo_root() or Path.cwd())
        temp_ctx.json_mode = options.json_mode
        duration = int((time.monotonic() - start) * 1000)
        return emit_result(_help_result("root"), temp_ctx, duration_ms=duration)

    repo_root = find_repo_root()
    if repo_root is None:
        temp_ctx = ctx or CliContext(repo_root=Path.cwd(), json_mode=options.json_mode)
        duration = int((time.monotonic() - start) * 1000)
        return emit_result(CliResult.repo_layout(), temp_ctx, duration_ms=duration)

    active = ctx or CliContext(
        repo_root=repo_root,
        json_mode=options.json_mode,
        dry_run=options.dry_run,
        non_interactive=options.non_interactive,
        port=options.port,
        runner=SubprocessCommandRunner(),
    )
    active.json_mode = options.json_mode
    active.dry_run = options.dry_run
    active.non_interactive = options.non_interactive
    active.port = options.port

    def _on_signal(_signum: int, _frame: object) -> None:
        active.interrupted = True

    previous = signal.signal(signal.SIGINT, _on_signal)
    try:
        result = dispatch(parsed, active)
        if active.interrupted and result.ok:
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
                human_lines=["command interrupted"],
            )
    except UsageError as exc:
        command = parsed.command or "setup"
        result = CliResult.usage(command, str(exc))
    except HandlerError as exc:
        result = CliResult(
            command=parsed.command or "setup",
            ok=False,
            exit_code=exc.exit_code,
            data={"error": str(exc)},
            diagnostics=[Diagnostic(exc.key, str(exc))],
            human_lines=[str(exc)],
        )
    except Exception as exc:  # noqa: BLE001
        result = CliResult(
            command=parsed.command or "setup",
            ok=False,
            exit_code=1,
            data={"error": "internal"},
            diagnostics=[Diagnostic("lifecycle.cli.internal", str(exc))],
            human_lines=["internal error; re-run with --json for structured output"],
        )
    finally:
        signal.signal(signal.SIGINT, previous)

    duration = int((time.monotonic() - start) * 1000)
    return emit_result(result, active, duration_ms=duration)
