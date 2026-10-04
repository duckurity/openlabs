"""Repo-local OpenLabs configuration under .openlabs/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from diagnostic_registry import redact_sensitive

CONFIG_VERSION = "openlabs.config.v1"
CONFIG_REL = ".openlabs/config.json"
CATALOG_CACHE_REL = ".openlabs/catalog-drift.json"

PLANNED_CONFIG_FIX = "write .openlabs/config.json with repo_root marker"
PLANNED_CATALOG_FIX = "refresh catalog drift cache under .openlabs/"


def config_path(repo_root: Path) -> Path:
    return repo_root / CONFIG_REL


def catalog_cache_path(repo_root: Path) -> Path:
    return repo_root / CATALOG_CACHE_REL


def load_config(repo_root: Path) -> dict[str, Any] | None:
    path = config_path(repo_root)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def build_config_payload(*, repo_root: Path, tier: str) -> dict[str, Any]:
    display_root = redact_sensitive(str(repo_root.resolve()))
    return {
        "version": CONFIG_VERSION,
        "repo_root": display_root,
        "tier": tier,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def write_config(repo_root: Path, *, tier: str) -> Path:
    from openlabs_cli.bundle_io import atomic_write_json

    path = config_path(repo_root)
    atomic_write_json(path, build_config_payload(repo_root=repo_root, tier=tier))
    return path


def refresh_catalog_cache(repo_root: Path) -> Path:
    from openlabs_cli.bundle_io import atomic_write_json

    path = catalog_cache_path(repo_root)
    payload = {
        "version": "openlabs.catalog_cache.v1",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": redact_sensitive(str(repo_root.resolve())),
    }
    atomic_write_json(path, payload)
    return path


def planned_repo_fixes(repo_root: Path) -> list[str]:
    fixes: list[str] = []
    if load_config(repo_root) is None:
        fixes.append(PLANNED_CONFIG_FIX)
    fixes.append(PLANNED_CATALOG_FIX)
    return fixes
