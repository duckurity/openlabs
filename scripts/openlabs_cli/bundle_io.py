"""Atomic bundle writes under .openlabs/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def bundles_dir(repo_root: Path) -> Path:
    return repo_root / ".openlabs" / "bundles"


def bundle_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def planned_bundle_path(repo_root: Path, *, timestamp: str | None = None) -> Path:
    stamp = timestamp or bundle_timestamp()
    return bundles_dir(repo_root) / f"{stamp}.json"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
