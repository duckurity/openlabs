"""Canonical public lab catalog derived from lab.yml metadata and status."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_inventory import catalog_counts, discover_catalog  # noqa: E402
from openlabs_contract import load_lab_metadata  # noqa: E402
from validate import LABS_DIR  # noqa: E402

CATALOG_VERSION = "openlabs.catalog-public.v1"


@dataclass(frozen=True)
class PublicLab:
    path: str
    name: str
    track: str
    difficulty: str
    description: str
    status: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "name": self.name,
            "track": self.track,
            "difficulty": self.difficulty,
            "description": self.description,
            "status": self.status,
        }


def discover_all_lab_dirs() -> list[Path]:
    labs: list[Path] = []
    if not LABS_DIR.is_dir():
        return labs
    for track in sorted(LABS_DIR.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and not lab.name.startswith((".", "_")):
                labs.append(lab)
    return labs


def read_public_lab(lab: Path) -> PublicLab | None:
    yml = lab / "lab.yml"
    if not yml.is_file():
        return None
    result = load_lab_metadata(yml)
    if result.record is None:
        return None
    record = result.record
    status = record.status.strip()
    if status not in ("experimental", "supported"):
        return None
    name = record.name.strip() or lab.name
    return PublicLab(
        path=lab.relative_to(REPO_ROOT).as_posix(),
        name=name,
        track=record.track.strip() or lab.parent.name,
        difficulty=record.difficulty.strip(),
        description=record.description.strip(),
        status=status,
    )


def build_public_catalog() -> dict:
    catalogued, uncatalogued = discover_catalog()
    counts = catalog_counts(catalogued)
    supported: list[PublicLab] = []
    experimental: list[PublicLab] = []
    for lab in catalogued:
        row = read_public_lab(lab)
        if row is None:
            continue
        if row.status == "supported":
            supported.append(row)
        else:
            experimental.append(row)
    supported.sort(key=lambda row: row.name)
    experimental.sort(key=lambda row: row.name)
    return {
        "version": CATALOG_VERSION,
        "supported_count": counts["supported_count"],
        "experimental_count": counts["experimental_count"],
        "catalogued_count": len(supported) + len(experimental),
        "maintainer": {
            "uncatalogued_count": len(uncatalogued),
            "uncatalogued_paths": [
                p.relative_to(REPO_ROOT).as_posix() for p in uncatalogued
            ],
            "directory_count": len(discover_all_lab_dirs()),
        },
        "supported": [row.to_dict() for row in supported],
        "experimental": [row.to_dict() for row in experimental],
    }


def public_counts() -> tuple[int, int]:
    data = build_public_catalog()
    return data["supported_count"], data["experimental_count"]
