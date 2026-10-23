#!/usr/bin/env python3
"""Validate openlabs.command.v1 JSON fixtures for M1-07."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from diagnostic_registry import ID_RE, load_registry, redact_sensitive

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "scripts" / "fixtures" / "cli_contract"
ENVELOPE_VERSION = "openlabs.command.v1"
COMMANDS = frozenset({"setup", "doctor", "issue", "lab"})
LAB_ACTIONS = frozenset(
    {
        "list",
        "setup",
        "start",
        "status",
        "verify",
        "stop",
        "validate",
        "score",
        "check",
        "compose",
        "prove",
        "reset",
    }
)
ISSUE_ACTIONS = frozenset({"explain", "bundle"})
# Reserved for the M2 CLI; emitters land in M2-02+ (registry parity via test merge).
CLI_EMITTER_KEYS = frozenset(
    {
        "lifecycle.interaction.non_interactive_required",
        "lifecycle.platform.unsupported_architecture",
        "lifecycle.port.conflict",
        "lifecycle.compose.unsafe_container_name",
        "lifecycle.state.interrupted",
        "lifecycle.lab.unsupported_operation",
        "environment.docker.client_missing",
        "environment.docker.daemon_unavailable",
        "environment.repo.layout_invalid",
        "lifecycle.cli.usage",
        "lifecycle.cli.internal",
        "lifecycle.cli.not_implemented",
        "lifecycle.cli.unknown_diagnostic",
    }
)
LEVELS = frozenset({f"L{i}" for i in range(7)})
FLAG_PLAINTEXT_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_diagnostic_item(item: Any, *, path: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(item, dict):
        return [f"{path}: diagnostic must be an object"]
    for key in ("id", "key", "message"):
        if key not in item:
            errors.append(f"{path}: missing diagnostic `{key}`")
    diag_id = item.get("id")
    key = item.get("key")
    message = item.get("message")
    if isinstance(diag_id, str) and not ID_RE.fullmatch(diag_id):
        errors.append(f"{path}: invalid diagnostic id {diag_id!r}")
    if isinstance(key, str):
        try:
            registry_id = load_registry().by_key()[key].id
            if isinstance(diag_id, str) and diag_id != registry_id:
                errors.append(
                    f"{path}: diagnostic id {diag_id!r} does not match registry key {key!r}"
                )
        except KeyError:
            errors.append(f"{path}: unknown diagnostic key {key!r}")
    if isinstance(message, str):
        if FLAG_PLAINTEXT_RE.search(message):
            errors.append(f"{path}: diagnostic message contains plaintext flag")
    return errors


def validate_envelope(data: Any, *, path: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{path}: envelope must be an object"]
    version = data.get("version")
    if version != ENVELOPE_VERSION:
        errors.append(f"{path}: version must be {ENVELOPE_VERSION!r}")
    command = data.get("command")
    if command not in COMMANDS:
        errors.append(f"{path}: command must be one of {sorted(COMMANDS)}")
    for key in ("ok", "exit_code", "dry_run", "data", "diagnostics"):
        if key not in data:
            errors.append(f"{path}: missing `{key}`")
    ok = data.get("ok")
    exit_code = data.get("exit_code")
    if isinstance(ok, bool) and isinstance(exit_code, int):
        if ok and exit_code != 0:
            errors.append(f"{path}: ok true requires exit_code 0")
        if not ok and exit_code == 0:
            errors.append(f"{path}: ok false requires non-zero exit_code")
    if not isinstance(data.get("data"), dict):
        errors.append(f"{path}: data must be an object")
    diagnostics = data.get("diagnostics")
    if not isinstance(diagnostics, list):
        errors.append(f"{path}: diagnostics must be an array")
    else:
        for index, item in enumerate(diagnostics):
            errors.extend(validate_diagnostic_item(item, path=f"{path}.diagnostics[{index}]"))
    meta = data.get("meta")
    if meta is not None:
        if not isinstance(meta, dict):
            errors.append(f"{path}: meta must be an object")
        elif "reset_safe" in meta and not isinstance(meta["reset_safe"], bool):
            errors.append(f"{path}: meta.reset_safe must be boolean")
    if command == "lab":
        action = data.get("data", {}).get("action")
        if action not in LAB_ACTIONS:
            errors.append(f"{path}: lab data.action must be one of {sorted(LAB_ACTIONS)}")
        levels = data.get("data", {}).get("levels")
        if levels is not None:
            if not isinstance(levels, list):
                errors.append(f"{path}: data.levels must be an array")
            else:
                for index, step in enumerate(levels):
                    if not isinstance(step, dict):
                        errors.append(f"{path}: data.levels[{index}] must be an object")
                        continue
                    level = step.get("level")
                    if level not in LEVELS:
                        errors.append(f"{path}: invalid level {level!r}")
    if command == "issue":
        action = data.get("data", {}).get("action")
        if action not in ISSUE_ACTIONS:
            errors.append(f"{path}: issue data.action must be one of {sorted(ISSUE_ACTIONS)}")
        if action == "bundle":
            bundle = data.get("data", {}).get("bundle")
            if bundle is not None and not isinstance(bundle, dict):
                errors.append(f"{path}: data.bundle must be an object")
    return errors


def iter_fixture_files() -> list[Path]:
    if not FIXTURES.is_dir():
        return []
    return sorted(FIXTURES.rglob("*.json"))


def validate_all_fixtures() -> list[str]:
    errors: list[str] = []
    paths = iter_fixture_files()
    if not paths:
        errors.append(f"no fixtures under {FIXTURES.relative_to(REPO_ROOT)}")
        return errors
    for path in paths:
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            data = load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{rel}: invalid JSON ({exc})")
            continue
        errors.extend(validate_envelope(data, path=rel))
    return errors
