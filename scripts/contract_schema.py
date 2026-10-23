#!/usr/bin/env python3
"""Dependency-free checks against contracts/lab.schema.json.

Validates parsed JSON records, not raw YAML. Full JSON Schema is defined in
lab.schema.json; this module implements the subset the repository relies on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "contracts" / "lab.schema.json"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
TRACKS = frozenset({"web", "binary", "crypto", "network", "osint"})
DIFFICULTIES = frozenset({"easy", "medium", "hard", "insane"})
STATUSES = frozenset({"experimental", "supported"})
REQUIRED = (
    "contract_version",
    "name",
    "track",
    "difficulty",
    "description",
    "flag_hash",
    "status",
    "techniques",
)
OPTIONAL = frozenset({"checkpoint_flag_hash", "port"})
ALLOWED = frozenset(REQUIRED) | OPTIONAL


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_schema_document(schema: dict[str, Any]) -> list[str]:
    """Sanity-check the schema file itself."""
    errors: list[str] = []
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("schema: missing or wrong $schema dialect")
    if not schema.get("$id"):
        errors.append("schema: missing $id")
    if schema.get("type") != "object":
        errors.append("schema: root type must be object")
    if schema.get("additionalProperties") is not False:
        errors.append("schema: additionalProperties must be false")
    missing = [key for key in REQUIRED if key not in schema.get("properties", {})]
    if missing:
        errors.append(f"schema: properties missing {missing}")
    return errors


def validate_lab_record(data: Any, *, path: str = "$") -> list[str]:
    """Return structural validation errors for one v1 lab record."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{path}: expected object, got {type(data).__name__}"]

    unknown = sorted(set(data) - ALLOWED)
    for key in unknown:
        errors.append(f"{path}: unknown property `{key}`")

    for key in REQUIRED:
        if key not in data:
            errors.append(f"{path}: missing required property `{key}`")

    if errors:
        return errors

    version = data["contract_version"]
    if version != 1:
        errors.append(f"{path}.contract_version: must be 1, got {version!r}")

    name = data["name"]
    if not isinstance(name, str) or not NAME_RE.match(name):
        errors.append(f"{path}.name: invalid slug {name!r}")

    track = data["track"]
    if track not in TRACKS:
        errors.append(f"{path}.track: must be one of {sorted(TRACKS)}")

    difficulty = data["difficulty"]
    if difficulty not in DIFFICULTIES:
        errors.append(f"{path}.difficulty: must be one of {sorted(DIFFICULTIES)}")

    description = data["description"]
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{path}.description: must be a non-empty string")

    flag_hash = data["flag_hash"]
    if not isinstance(flag_hash, str) or not HASH_RE.match(flag_hash):
        errors.append(f"{path}.flag_hash: must be 64 lowercase hex characters")

    status = data["status"]
    if status not in STATUSES:
        errors.append(f"{path}.status: must be one of {sorted(STATUSES)}")

    techniques = data["techniques"]
    if not isinstance(techniques, list):
        errors.append(f"{path}.techniques: must be an array")
    else:
        seen: set[str] = set()
        for index, slug in enumerate(techniques):
            if not isinstance(slug, str) or not NAME_RE.match(slug):
                errors.append(f"{path}.techniques[{index}]: invalid slug {slug!r}")
            elif slug in seen:
                errors.append(f"{path}.techniques: duplicate slug {slug!r}")
            else:
                seen.add(slug)

    if "checkpoint_flag_hash" in data:
        checkpoint = data["checkpoint_flag_hash"]
        if not isinstance(checkpoint, str) or not HASH_RE.match(checkpoint):
            errors.append(f"{path}.checkpoint_flag_hash: must be 64 lowercase hex characters")

    if "port" in data:
        port = data["port"]
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            errors.append(f"{path}.port: must be integer 1..65535")

    return errors


def lab_yml_meta_to_record(meta: dict[str, str]) -> dict[str, Any]:
    """Map flat lab.yml key strings to a v1 JSON record for schema checks."""

    def parse_bracket_list(text: str) -> list[str]:
        text = text.strip()
        if not (text.startswith("[") and text.endswith("]")):
            return []
        return [item.strip() for item in text[1:-1].split(",") if item.strip()]

    techniques_raw = meta.get("techniques", "").strip()
    techniques = parse_bracket_list(techniques_raw) if techniques_raw else []

    record: dict[str, Any] = {
        "contract_version": 1,
        "name": meta.get("name", "").strip(),
        "track": meta.get("track", "").strip(),
        "difficulty": meta.get("difficulty", "").strip(),
        "description": meta.get("description", "").strip(),
        "flag_hash": meta.get("flag_hash", "").strip(),
        "status": meta.get("status", "").strip(),
        "techniques": techniques,
    }
    if meta.get("checkpoint_flag_hash", "").strip():
        record["checkpoint_flag_hash"] = meta["checkpoint_flag_hash"].strip()
    port_raw = meta.get("port", "").strip()
    if port_raw:
        if port_raw.isdigit():
            record["port"] = int(port_raw)
        else:
            record["port"] = port_raw  # let validator report type error
    return record
