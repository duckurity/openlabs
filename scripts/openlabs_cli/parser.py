"""Argument parsing for the openlabs CLI."""

from __future__ import annotations

from dataclasses import dataclass, field

from openlabs_cli.errors import UsageError

GLOBAL_FLAGS = frozenset({"--json", "--dry-run", "--non-interactive", "--help", "--version"})
LAB_FLAGS = frozenset({"--json", "--dry-run", "--non-interactive", "--help", "--port"})


@dataclass
class GlobalOptions:
    json_mode: bool = False
    dry_run: bool = False
    non_interactive: bool = False
    show_help: bool = False
    show_version: bool = False
    port: int | None = None


@dataclass
class ParsedInvocation:
    options: GlobalOptions = field(default_factory=GlobalOptions)
    command: str | None = None
    args: list[str] = field(default_factory=list)


def _parse_flag_block(argv: list[str], *, allowed: frozenset[str], allow_port: bool) -> tuple[GlobalOptions, list[str]]:
    options = GlobalOptions()
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--json":
            options.json_mode = True
        elif token == "--dry-run":
            options.dry_run = True
        elif token == "--non-interactive":
            options.non_interactive = True
        elif token == "--help":
            options.show_help = True
        elif token == "--version":
            options.show_version = True
        elif token == "--port":
            if not allow_port:
                raise UsageError("--port is only valid for openlabs lab")
            index += 1
            if index >= len(argv):
                raise UsageError("--port requires a value")
            try:
                options.port = int(argv[index])
            except ValueError as exc:
                raise UsageError("--port must be an integer") from exc
            if not 1 <= options.port <= 65535:
                raise UsageError("--port must be between 1 and 65535")
        elif token.startswith("-") and token not in allowed:
            raise UsageError(f"unknown option {token}")
        else:
            break
        index += 1
    return options, argv[index:]


def parse_argv(argv: list[str]) -> ParsedInvocation:
    options, rest = _parse_flag_block(argv, allowed=GLOBAL_FLAGS, allow_port=False)
    if options.show_version:
        return ParsedInvocation(options=options)
    if not rest:
        if options.show_help:
            return ParsedInvocation(options=options)
        raise UsageError("missing command; try openlabs --help")
    command = rest[0]
    tail = rest[1:]
    if command not in {"setup", "doctor", "issue", "lab"}:
        raise UsageError(f"unknown command {command!r}")
    if command == "lab":
        lab_options, lab_rest = _parse_flag_block(tail, allowed=LAB_FLAGS, allow_port=True)
        options.json_mode = options.json_mode or lab_options.json_mode
        options.dry_run = options.dry_run or lab_options.dry_run
        options.non_interactive = options.non_interactive or lab_options.non_interactive
        options.show_help = options.show_help or lab_options.show_help
        if lab_options.port is not None:
            options.port = lab_options.port
        return ParsedInvocation(options=options, command=command, args=lab_rest)
    return ParsedInvocation(options=options, command=command, args=tail)


def root_usage() -> str:
    return "\n".join(
        [
            "usage: openlabs [--json] [--dry-run] [--non-interactive] [--version] <command> ...",
            "",
            "commands:",
            "  setup    prepare the local environment",
            "  doctor   repository health checks",
            "  issue    explain diagnostics or build a local bundle",
            "  lab      lab lifecycle and maintainer actions",
        ]
    )
