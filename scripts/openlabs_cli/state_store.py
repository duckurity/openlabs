"""Atomic lab state and per-lab locking."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from openlabs_cli.bundle_io import atomic_write_json

STATE_VERSION = "openlabs.state.v1"
LIFECYCLE_VALUES = frozenset(
    {
        "unconfigured",
        "configured",
        "building",
        "starting",
        "ready",
        "stopped",
        "failed",
        "resetting",
    }
)


class LabLockError(Exception):
    def __init__(self, slug: str) -> None:
        super().__init__(f"lab {slug!r} is locked by another openlabs process")
        self.slug = slug


def state_dir(repo_root: Path) -> Path:
    return repo_root / ".openlabs" / "state"


def lock_dir(repo_root: Path) -> Path:
    return repo_root / ".openlabs" / "locks"


def state_path(repo_root: Path, slug: str) -> Path:
    return state_dir(repo_root) / f"{slug}.json"


def load_state(repo_root: Path, slug: str) -> dict[str, Any] | None:
    path = state_path(repo_root, slug)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("version") != STATE_VERSION:
        return None
    return data


def build_state_payload(
    *,
    slug: str,
    compose_project: str,
    host_port: int,
    lifecycle: str,
    compose_file: str,
    container_port: int,
    evidence_path: str | None = None,
) -> dict[str, Any]:
    if lifecycle not in LIFECYCLE_VALUES:
        raise ValueError(f"invalid lifecycle {lifecycle!r}")
    payload: dict[str, Any] = {
        "version": STATE_VERSION,
        "lab": slug,
        "compose_project": compose_project,
        "host_port": host_port,
        "container_port": container_port,
        "compose_file": compose_file,
        "lifecycle": lifecycle,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if evidence_path:
        payload["evidence_path"] = evidence_path
    return payload


def write_state(repo_root: Path, payload: dict[str, Any]) -> Path:
    slug = payload["lab"]
    path = state_path(repo_root, slug)
    atomic_write_json(path, payload)
    return path


@contextmanager
def lab_lock(repo_root: Path, slug: str) -> Iterator[None]:
    directory = lock_dir(repo_root)
    directory.mkdir(parents=True, exist_ok=True)
    lock_file = directory / f"{slug}.lock"
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError as exc:
        raise LabLockError(slug) from exc
    try:
        yield
    finally:
        try:
            lock_file.unlink(missing_ok=True)
        except OSError:
            pass
