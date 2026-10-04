"""Build openlabs.command.v1 envelopes."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any

from diagnostic_registry import lookup_registry_id, redact_sensitive

from openlabs_cli.context import CliContext
from openlabs_cli.version import ENVELOPE_VERSION


@dataclass
class Diagnostic:
    key: str
    message: str

    def to_dict(self) -> dict[str, str]:
        text = redact_sensitive(self.message)
        diag_id = lookup_registry_id(self.key)
        if not text.startswith("["):
            text = f"[{diag_id}] {text}"
        return {"id": diag_id, "key": self.key, "message": text}


@dataclass
class CliResult:
    command: str
    ok: bool
    exit_code: int
    data: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    human_lines: list[str] = field(default_factory=list)

    @classmethod
    def usage(cls, command: str, message: str) -> CliResult:
        return cls(
            command=command,
            ok=False,
            exit_code=2,
            data={"error": message},
            diagnostics=[Diagnostic("lifecycle.cli.usage", message)],
            human_lines=[message],
        )

    @classmethod
    def not_implemented(cls, command: str, detail: str) -> CliResult:
        message = f"{detail} (not implemented yet)"
        return cls(
            command=command,
            ok=False,
            exit_code=1,
            data={"status": "not_implemented", "detail": detail},
            diagnostics=[Diagnostic("lifecycle.cli.not_implemented", message)],
            human_lines=[message],
        )

    @classmethod
    def repo_layout(cls) -> CliResult:
        message = "run openlabs from an OpenLabs repository checkout"
        return cls(
            command="setup",
            ok=False,
            exit_code=3,
            data={"error": "repo_root_not_found"},
            diagnostics=[Diagnostic("environment.repo.layout_invalid", message)],
            human_lines=[message],
        )


def build_envelope(result: CliResult, ctx: CliContext, *, duration_ms: int | None = None) -> dict[str, Any]:
    meta = dict(result.meta)
    if duration_ms is not None:
        meta.setdefault("duration_ms", duration_ms)
    if ctx.non_interactive:
        meta.setdefault("non_interactive", True)
    if ctx.dry_run:
        meta.setdefault("dry_run", ctx.dry_run)
    redacted = any("[OL-" in d.to_dict()["message"] for d in result.diagnostics)
    if redacted:
        meta.setdefault("redacted", True)
    envelope: dict[str, Any] = {
        "version": ENVELOPE_VERSION,
        "command": result.command,
        "ok": result.ok,
        "exit_code": result.exit_code,
        "dry_run": ctx.dry_run,
        "data": result.data,
        "diagnostics": [item.to_dict() for item in result.diagnostics],
    }
    if meta:
        envelope["meta"] = meta
    return envelope


def emit_result(result: CliResult, ctx: CliContext, *, duration_ms: int | None = None) -> int:
    if ctx.json_mode:
        payload = build_envelope(result, ctx, duration_ms=duration_ms)
        try:
            sys.stdout.write(__import__("json").dumps(payload, indent=2) + "\n")
        except BrokenPipeError:
            return 0
        return result.exit_code
    stream = sys.stderr if result.exit_code != 0 else sys.stdout
    for line in result.human_lines:
        try:
            print(line, file=stream)
        except BrokenPipeError:
            return 0
    return result.exit_code
