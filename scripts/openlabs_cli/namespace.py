"""Deterministic Docker Compose project names for OpenLabs."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

PROJECT_MAX = 63
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def repo_fingerprint(repo_root: Path) -> str:
    digest = hashlib.sha256(str(repo_root.resolve()).encode("utf-8")).hexdigest()
    return digest[:6]


def compose_project_name(repo_root: Path, slug: str) -> str:
    if not SLUG_RE.fullmatch(slug):
        raise ValueError(f"invalid lab slug {slug!r}")
    base = f"openlabs-{repo_fingerprint(repo_root)}-{slug}"
    normalized = re.sub(r"[^a-z0-9-]", "-", base.lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized[:PROJECT_MAX]
