"""Setup run logging under .openlabs/logs/."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from diagnostic_registry import redact_sensitive

from openlabs_cli.bundle_io import atomic_write_json


def log_dir(repo_root: Path, slug: str) -> Path:
    return repo_root / ".openlabs" / "logs" / slug


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_setup_log(
    repo_root: Path,
    *,
    slug: str,
    run_id: str,
    stages: list[str],
    detail: str,
) -> Path:
    directory = log_dir(repo_root, slug)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{run_id}.log"
    payload = {
        "run_id": run_id,
        "lab": slug,
        "stages_completed": stages,
        "detail": redact_sensitive(detail),
    }
    atomic_write_json(path, payload)
    rel = path.relative_to(repo_root).as_posix()
    return path


def relative_evidence(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()
