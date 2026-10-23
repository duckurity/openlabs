"""Discover the OpenLabs repository root."""

from __future__ import annotations

from pathlib import Path

MARKERS = ("AGENTS.md", "scripts/validate.py", "labs")


def is_repo_root(path: Path) -> bool:
    if not path.is_dir():
        return False
    if not (path / "AGENTS.md").is_file():
        return False
    if not (path / "scripts" / "validate.py").is_file():
        return False
    if not (path / "labs").is_dir():
        return False
    return True


def find_repo_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if is_repo_root(candidate):
            return candidate
    return None
