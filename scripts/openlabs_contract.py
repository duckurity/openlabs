#!/usr/bin/env python3
"""Shared OpenLabs lab.yml parser and v1 typed model.

Parses the approved flat YAML subset into an immutable record. Repository-context
checks (directory name, technique pages) are separate from syntax parsing.

Until M1-06, on-disk files may omit ``contract_version``; the parser treats that
as version ``1`` so the current catalog loads without semantic change.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contract_schema import validate_lab_record

REPO_ROOT = Path(__file__).resolve().parent.parent

META_KEY_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?:\s*(?P<value>.*))?$"
)
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_KEYS = frozenset(
    {
        "contract_version",
        "name",
        "track",
        "difficulty",
        "description",
        "flag_hash",
        "status",
        "techniques",
        "checkpoint_flag_hash",
        "port",
    }
)
SUPPORTED_CONTRACT_VERSION = 1


@dataclass(frozen=True)
class ContractDiagnostic:
    """Registry-ready diagnostic (OL IDs attach in M1-05)."""

    key: str
    message: str
    line: int | None = None
    field: str | None = None

    def format(self) -> str:
        where = f"line {self.line}: " if self.line else ""
        field = f"`{self.field}`: " if self.field else ""
        return f"{where}{field}{self.message}"


@dataclass(frozen=True)
class LabMetadataRecord:
    """Immutable v1 lab metadata."""

    contract_version: int
    name: str
    track: str
    difficulty: str
    description: str
    flag_hash: str
    status: str
    techniques: tuple[str, ...]
    checkpoint_flag_hash: str | None = None
    port: int | None = None
    source: Path | None = None

    def to_schema_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "contract_version": self.contract_version,
            "name": self.name,
            "track": self.track,
            "difficulty": self.difficulty,
            "description": self.description,
            "flag_hash": self.flag_hash,
            "status": self.status,
            "techniques": list(self.techniques),
        }
        if self.checkpoint_flag_hash is not None:
            data["checkpoint_flag_hash"] = self.checkpoint_flag_hash
        if self.port is not None:
            data["port"] = self.port
        return data


@dataclass(frozen=True)
class LoadResult:
    record: LabMetadataRecord | None
    diagnostics: tuple[ContractDiagnostic, ...]


def _sort_diagnostics(items: list[ContractDiagnostic]) -> tuple[ContractDiagnostic, ...]:
    return tuple(sorted(items, key=lambda d: (d.line or 0, d.key, d.message)))


def strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote == '"' and char == "\\" and not escaped:
            escaped = True
            continue
        if char in "\"'" and not escaped:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        elif char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        escaped = False
    return value.rstrip()


def parse_yaml_scalar(value: str, line_number: int) -> tuple[str | None, ContractDiagnostic | None]:
    value = strip_inline_comment(value).strip()
    if not value:
        return "", None
    if value[0] not in "\"'":
        return value, None
    quote = value[0]
    if len(value) < 2 or value[-1] != quote:
        return None, ContractDiagnostic(
            key="contract.parse.unterminated_quote",
            message="unterminated quoted value",
            line=line_number,
        )
    if quote == "'":
        return value[1:-1].replace("''", "'"), None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None, ContractDiagnostic(
            key="contract.parse.invalid_scalar",
            message="invalid double-quoted value",
            line=line_number,
        )
    if not isinstance(decoded, str):
        return None, ContractDiagnostic(
            key="contract.parse.invalid_scalar",
            message="double-quoted value must be a string",
            line=line_number,
        )
    return decoded, None


def parse_bracket_list(text: str, line_number: int, field: str) -> tuple[tuple[str, ...] | None, ContractDiagnostic | None]:
    text = text.strip()
    if not text:
        return (), None
    if not (text.startswith("[") and text.endswith("]")):
        return None, ContractDiagnostic(
            key="contract.parse.invalid_techniques",
            message="techniques must be a bracket list like `[idor, ssrf]`",
            line=line_number,
            field=field,
        )
    items = [item.strip() for item in text[1:-1].split(",") if item.strip()]
    return tuple(items), None


def parse_contract_version(raw: str, line_number: int) -> tuple[int | None, ContractDiagnostic | None]:
    scalar, err = parse_yaml_scalar(raw, line_number)
    if err:
        return None, err
    assert scalar is not None
    if not scalar.isdigit():
        return None, ContractDiagnostic(
            key="contract.parse.invalid_contract_version",
            message="contract_version must be integer 1",
            line=line_number,
            field="contract_version",
        )
    value = int(scalar)
    if value != SUPPORTED_CONTRACT_VERSION:
        return None, ContractDiagnostic(
            key="contract.parse.unsupported_contract_version",
            message=f"unsupported contract_version {value}; only 1 is supported in M1",
            line=line_number,
            field="contract_version",
        )
    return value, None


def parse_port(raw: str, line_number: int) -> tuple[int | None, ContractDiagnostic | None]:
    scalar, err = parse_yaml_scalar(raw, line_number)
    if err:
        return None, err
    assert scalar is not None
    if not scalar.isdigit():
        return None, ContractDiagnostic(
            key="contract.parse.invalid_port",
            message="port must be an integer",
            line=line_number,
            field="port",
        )
    return int(scalar), None


def parse_lab_yml_text(text: str, source: Path | None = None) -> LoadResult:
    """Parse flat lab.yml text into a v1 record or structured diagnostics."""
    diagnostics: list[ContractDiagnostic] = []
    fields: dict[str, tuple[str, int]] = {}

    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        line_number = index + 1
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        match = META_KEY_RE.match(raw)
        if not match or match.group("indent"):
            diagnostics.append(
                ContractDiagnostic(
                    key="contract.parse.indented_key",
                    message="expected an unindented key: value mapping",
                    line=line_number,
                )
            )
            index += 1
            continue

        key = match.group("key")
        if key not in ALLOWED_KEYS:
            diagnostics.append(
                ContractDiagnostic(
                    key="contract.parse.unknown_field",
                    message=f"unknown field `{key}`",
                    line=line_number,
                    field=key,
                )
            )
            index += 1
            continue

        if key in fields:
            diagnostics.append(
                ContractDiagnostic(
                    key="contract.parse.duplicate_key",
                    message=f"duplicate key `{key}`",
                    line=line_number,
                    field=key,
                )
            )
            index += 1
            continue

        value = strip_inline_comment(match.group("value") or "").strip()
        if not value and index + 1 < len(lines) and re.match(r"^\s+-\s+\S", lines[index + 1]):
            diagnostics.append(
                ContractDiagnostic(
                    key="contract.parse.unsupported_list_syntax",
                    message="YAML list syntax is not supported; use bracket lists for techniques",
                    line=line_number,
                    field=key,
                )
            )
            index += 1
            continue
        if value in {"|", ">"}:
            diagnostics.append(
                ContractDiagnostic(
                    key="contract.parse.unsupported_block_scalar",
                    message="block scalars are not supported in v1 lab.yml",
                    line=line_number,
                    field=key,
                )
            )
            index += 1
            continue

        fields[key] = (value, line_number)
        index += 1

    if diagnostics:
        return LoadResult(None, _sort_diagnostics(diagnostics))

    contract_version = SUPPORTED_CONTRACT_VERSION
    if "contract_version" in fields:
        raw, line_no = fields["contract_version"]
        parsed, err = parse_contract_version(raw, line_no)
        if err:
            diagnostics.append(err)
        elif parsed is not None:
            contract_version = parsed

    techniques: tuple[str, ...] = ()
    if "techniques" in fields:
        raw, line_no = fields["techniques"]
        parsed, err = parse_bracket_list(raw, line_no, "techniques")
        if err:
            diagnostics.append(err)
        elif parsed is not None:
            techniques = parsed

    port: int | None = None
    if "port" in fields:
        raw, line_no = fields["port"]
        parsed, err = parse_port(raw, line_no)
        if err:
            diagnostics.append(err)
        else:
            port = parsed

    def scalar_field(name: str, *, required: bool) -> str | None:
        if name not in fields:
            if required:
                diagnostics.append(
                    ContractDiagnostic(
                        key="contract.parse.missing_required",
                        message=f"missing required field `{name}`",
                        field=name,
                    )
                )
            return None
        raw, line_no = fields[name]
        parsed, err = parse_yaml_scalar(raw, line_no)
        if err:
            diagnostics.append(err)
            return None
        if parsed is None:
            return None
        if required and not parsed.strip():
            diagnostics.append(
                ContractDiagnostic(
                    key="contract.parse.empty_required",
                    message=f"required field `{name}` is empty",
                    line=line_no,
                    field=name,
                )
            )
            return None
        return parsed.strip() if parsed else parsed

    name = scalar_field("name", required=True)
    track = scalar_field("track", required=True)
    difficulty = scalar_field("difficulty", required=True)
    description = scalar_field("description", required=True)
    flag_hash = scalar_field("flag_hash", required=True)
    status = scalar_field("status", required=True)
    checkpoint = scalar_field("checkpoint_flag_hash", required=False)

    if diagnostics:
        return LoadResult(None, _sort_diagnostics(diagnostics))

    assert name and track and difficulty and description and flag_hash and status
    record = LabMetadataRecord(
        contract_version=contract_version,
        name=name,
        track=track,
        difficulty=difficulty,
        description=description,
        flag_hash=flag_hash,
        status=status,
        techniques=techniques,
        checkpoint_flag_hash=checkpoint,
        port=port,
        source=source,
    )

    for message in validate_lab_record(record.to_schema_dict(), path=str(source or "lab.yml")):
        diagnostics.append(
            ContractDiagnostic(
                key="contract.schema.invalid_field",
                message=message,
                field=_field_from_schema_message(message),
            )
        )

    if diagnostics:
        return LoadResult(None, _sort_diagnostics(diagnostics))
    return LoadResult(record, ())


def _field_from_schema_message(message: str) -> str | None:
    if ".`" in message or "property `" in message:
        match = re.search(r"`([^`]+)`", message)
        if match:
            return match.group(1)
    return None


def load_lab_metadata(lab_yml: Path) -> LoadResult:
    """Load and validate one lab.yml file."""
    path = lab_yml.resolve()
    if not path.is_file():
        return LoadResult(
            None,
            (
                ContractDiagnostic(
                    key="contract.parse.missing_file",
                    message=f"missing lab.yml at {path}",
                ),
            ),
        )
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return LoadResult(
            None,
            (
                ContractDiagnostic(
                    key="contract.parse.invalid_encoding",
                    message="lab.yml is not valid UTF-8",
                ),
            ),
        )
    return parse_lab_yml_text(text, source=path)


def validate_lab_context(record: LabMetadataRecord, lab_dir: Path) -> tuple[ContractDiagnostic, ...]:
    """Repository-context validation separate from parsing."""
    errors: list[ContractDiagnostic] = []
    if record.name != lab_dir.name:
        errors.append(
            ContractDiagnostic(
                key="contract.context.name_directory_mismatch",
                message=f"name {record.name!r} does not match directory {lab_dir.name!r}",
                field="name",
            )
        )
    if record.track != lab_dir.parent.name:
        errors.append(
            ContractDiagnostic(
                key="contract.context.track_directory_mismatch",
                message=f"track {record.track!r} does not match directory track {lab_dir.parent.name!r}",
                field="track",
            )
        )
    for slug in record.techniques:
        technique_path = REPO_ROOT / "content" / "technique" / f"{slug}.mdx"
        if not technique_path.is_file():
            errors.append(
                ContractDiagnostic(
                    key="contract.context.technique_page_missing",
                    message=f"technique {slug!r} has no page at content/technique/{slug}.mdx",
                    field="techniques",
                )
            )
    return _sort_diagnostics(errors)


def legacy_string_map(record: LabMetadataRecord) -> dict[str, str]:
    """String map for callers that still expect flat lab.yml key strings."""
    data: dict[str, str] = {
        "contract_version": str(record.contract_version),
        "name": record.name,
        "track": record.track,
        "difficulty": record.difficulty,
        "description": record.description,
        "flag_hash": record.flag_hash,
        "status": record.status,
        "techniques": "[" + ", ".join(record.techniques) + "]",
    }
    if record.checkpoint_flag_hash:
        data["checkpoint_flag_hash"] = record.checkpoint_flag_hash
    if record.port is not None:
        data["port"] = str(record.port)
    return data


TRACKS = frozenset({"web", "binary", "crypto", "network", "osint"})

PLAYER_HASH_LINE_RE = re.compile(r"^(flag_hash|checkpoint_flag_hash): ([0-9a-f]{64})$")
PLAYER_HASH_PREFIX_RE = re.compile(r"^[ \t]*(flag_hash|checkpoint_flag_hash)\b")


def format_validate_error(diag: ContractDiagnostic) -> str:
    """Map contract diagnostics to validate.py-style error strings."""
    if diag.key in {"contract.parse.missing_required", "contract.parse.empty_required"} and diag.field:
        return f"lab.yml: missing or empty `{diag.field}`"
    if diag.key == "contract.parse.invalid_techniques":
        return "lab.yml: `techniques` must be a bracket list like `[idor, ssrf]`"
    if diag.key == "contract.context.name_directory_mismatch":
        name_match = re.search(r"name '([^']*)' does not match directory '([^']*)'", diag.message)
        if name_match:
            return (
                f"lab.yml: `name` {name_match.group(1)!r} does not match directory "
                f"{name_match.group(2)!r}"
            )
    if diag.key == "contract.context.track_directory_mismatch":
        track_match = re.search(
            r"track '([^']*)' does not match directory track '([^']*)'", diag.message
        )
        if track_match:
            return (
                f"lab.yml: `track` {track_match.group(1)!r} must match directory track "
                f"{track_match.group(2)!r}"
            )
    if diag.key == "contract.context.technique_page_missing":
        slug_match = re.search(r"technique '([^']*)'", diag.message)
        if slug_match:
            slug = slug_match.group(1)
            return f"lab.yml: technique {slug!r} has no page at content/technique/{slug}.mdx"
    if diag.key == "contract.schema.invalid_field":
        if "flag_hash" in diag.message:
            return "lab.yml: `flag_hash` must be 64 lowercase hex characters"
        name_match = re.search(r"invalid slug '([^']*)'", diag.message)
        if name_match:
            return f"lab.yml: `name` {name_match.group(1)!r} must be lowercase and hyphenated"
        status_match = re.search(r"got '([^']*)'", diag.message)
        if ".status:" in diag.message and status_match:
            return (
                f"lab.yml: `status` {status_match.group(1)!r} must be one of "
                f"{sorted({'experimental', 'supported'})}"
            )
        if ".track:" in diag.message:
            return f"lab.yml: `track` must be one of {sorted(TRACKS)}"
        if ".difficulty:" in diag.message:
            return f"lab.yml: `difficulty` must be one of {sorted({'easy', 'medium', 'hard', 'insane'})}"
    if diag.line:
        return f"lab.yml: line {diag.line}: {diag.message}"
    return f"lab.yml: {diag.message}"


def collect_metadata_errors(lab_dir: Path) -> list[str]:
    """Parse and validate lab.yml metadata plus repository context."""
    result = load_lab_metadata(lab_dir / "lab.yml")
    errors = [format_validate_error(diag) for diag in result.diagnostics]
    if result.record is None:
        return errors
    if lab_dir.parent.name not in TRACKS:
        errors.append(
            f"directory {lab_dir.parent.name!r} is not a track ({sorted(TRACKS)})"
        )
    for diag in validate_lab_context(result.record, lab_dir):
        errors.append(format_validate_error(diag))
    return errors


def read_player_flag_hashes(lab_dir: Path) -> dict[str, str]:
    """Read flag hashes for check.py with strict line formatting rules."""
    metadata = lab_dir / "lab.yml"
    result = load_lab_metadata(metadata)
    if result.record is None:
        raise ValueError(format_validate_error(result.diagnostics[0]))

    hashes: dict[str, str] = {}
    for line_number, line in enumerate(metadata.read_text(encoding="utf-8").splitlines(), start=1):
        field = PLAYER_HASH_PREFIX_RE.match(line)
        if field is None:
            continue
        key = field.group(1)
        match = PLAYER_HASH_LINE_RE.fullmatch(line)
        if match is None:
            raise ValueError(
                f"lab.yml in {lab_dir} has invalid {key} on line {line_number}; "
                f"expected `{key}: <64 lowercase hex characters>`"
            )
        if key in hashes:
            raise ValueError(f"lab.yml in {lab_dir} has duplicate {key} on line {line_number}")
        hashes[key] = match.group(2)

    if "flag_hash" not in hashes:
        raise ValueError(f"lab.yml in {lab_dir} has no flag_hash")
    record = result.record
    if record.checkpoint_flag_hash and "checkpoint_flag_hash" not in hashes:
        raise ValueError(f"lab.yml in {lab_dir} has no checkpoint_flag_hash")
    if hashes["flag_hash"] != record.flag_hash:
        raise ValueError(f"lab.yml in {lab_dir} has inconsistent flag_hash values")
    checkpoint = record.checkpoint_flag_hash
    if checkpoint and hashes.get("checkpoint_flag_hash") != checkpoint:
        raise ValueError(f"lab.yml in {lab_dir} has inconsistent checkpoint_flag_hash values")
    return hashes
