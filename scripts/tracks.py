#!/usr/bin/env python3
"""Load the canonical OpenLabs track registry."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACK_REGISTRY_PATH = REPO_ROOT / "contracts" / "tracks.json"
TRACK_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRACK_REGISTRY_VERSION = 1


@dataclass(frozen=True)
class TrackDefinition:
    """One validated track registry entry."""

    slug: str
    label: str
    focus: str


def load_track_registry(path: Path = TRACK_REGISTRY_PATH) -> tuple[TrackDefinition, ...]:
    """Load and validate the track registry."""
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"track registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"track registry is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("track registry root must be an object")
    if set(data) != {"registry_version", "tracks"}:
        raise ValueError("track registry keys must be registry_version and tracks")
    if (
        type(data["registry_version"]) is not int
        or data["registry_version"] != TRACK_REGISTRY_VERSION
    ):
        raise ValueError(
            f"track registry version must be {TRACK_REGISTRY_VERSION}, "
            f"got {data['registry_version']!r}"
        )

    raw_tracks = data["tracks"]
    if not isinstance(raw_tracks, list) or not raw_tracks:
        raise ValueError("track registry tracks must be a non-empty array")

    tracks: list[TrackDefinition] = []
    seen: set[str] = set()
    required = {"slug", "label", "focus"}
    for index, entry in enumerate(raw_tracks):
        if not isinstance(entry, dict) or set(entry) != required:
            raise ValueError(
                f"track registry entry {index} must contain slug, label, and focus"
            )
        slug = entry["slug"]
        label = entry["label"]
        focus = entry["focus"]
        if not isinstance(slug, str) or not TRACK_SLUG_RE.fullmatch(slug):
            raise ValueError(f"track registry entry {index} has invalid slug {slug!r}")
        if slug in seen:
            raise ValueError(f"track registry has duplicate slug {slug!r}")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"track registry entry {index} has an empty label")
        if not isinstance(focus, str) or not focus.strip():
            raise ValueError(f"track registry entry {index} has an empty focus")
        seen.add(slug)
        tracks.append(TrackDefinition(slug=slug, label=label, focus=focus))

    return tuple(tracks)


TRACK_DEFINITIONS = load_track_registry()
TRACK_SLUGS = tuple(track.slug for track in TRACK_DEFINITIONS)
TRACK_SLUG_SET = frozenset(TRACK_SLUGS)
