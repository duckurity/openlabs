"""Catalog discovery and lab selection for the OpenLabs CLI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lab_inventory import lab_name, lab_status

COMPOSE_NAMES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
)
CANONICAL_PATH_RE = re.compile(r"^labs/[a-z]+/[^/]+$")
CONTAINER_NAME_RE = re.compile(r"^\s*container_name\s*:", re.MULTILINE)
SHORT_PORT_RE = re.compile(r"^\s*-\s*(?P<value>[^#]+?)(?:\s+#.*)?$")
IP_PORT_RE = re.compile(
    r"^(?:(?:\d{1,3}\.){3}\d{1,3}:)?(?P<published>\d{1,5}):\d{1,5}(?:/(?:tcp|udp))?$"
)
ENV_DEFAULT_PORT_RE = re.compile(
    r"^\$\{(?P<var>[A-Za-z_][A-Za-z0-9_]*)(?::-(?P<published>\d+))?\}:\d{1,5}$"
)


@dataclass(frozen=True)
class ResolvedLab:
    lab_dir: Path
    entry: dict[str, Any]


@dataclass(frozen=True)
class LabSelectionError:
    message: str
    exit_code: int = 2
    key: str = "lifecycle.cli.usage"


def labs_dir(repo_root: Path) -> Path:
    return repo_root / "labs"


def discover_catalog_labs(repo_root: Path) -> list[Path]:
    root = labs_dir(repo_root)
    if not root.is_dir():
        return []
    labs: list[Path] = []
    for track in sorted(root.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and not lab.name.startswith((".", "_")):
                if (lab / "lab.yml").is_file():
                    labs.append(lab)
    return labs


def discover_uncatalogued_dirs(repo_root: Path) -> list[Path]:
    root = labs_dir(repo_root)
    if not root.is_dir():
        return []
    uncatalogued: list[Path] = []
    for track in sorted(root.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and not lab.name.startswith((".", "_")):
                if not (lab / "lab.yml").is_file():
                    uncatalogued.append(lab)
    return uncatalogued


def compose_path(lab: Path) -> Path | None:
    return next((lab / name for name in COMPOSE_NAMES if (lab / name).is_file()), None)


def compose_file_name(lab: Path) -> str | None:
    path = compose_path(lab)
    if path is None:
        return None
    return path.name


def _published_port(value: str) -> int | None:
    value = value.strip().strip("\"'")
    env_default = ENV_DEFAULT_PORT_RE.fullmatch(value)
    if env_default:
        return int(env_default.group("published"))
    numeric = IP_PORT_RE.fullmatch(value)
    if numeric:
        return int(numeric.group("published"))
    return None


def derive_host_port(lab: Path) -> int | None:
    from openlabs_contract import load_lab_metadata

    meta = load_lab_metadata(lab / "lab.yml")
    if meta.record is not None and meta.record.port is not None:
        return meta.record.port

    path = compose_path(lab)
    if path is None:
        return None

    ports: list[int] = []
    ports_indent: int | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"^(?P<indent>\s*)ports:\s*(?P<inline>\[.*\])?\s*(?:#.*)?$", raw):
            ports_indent = len(match.group("indent"))
            inline = match.group("inline")
            if inline:
                for value in re.findall(r"[\"']([^\"']+)[\"']", inline):
                    if port := _published_port(value):
                        ports.append(port)
                ports_indent = None
            continue
        if ports_indent is None:
            continue
        indent = len(raw) - len(raw.lstrip())
        if raw.strip() and indent <= ports_indent:
            ports_indent = None
            continue
        entry = SHORT_PORT_RE.match(raw)
        if entry and (port := _published_port(entry.group("value"))):
            ports.append(port)

    return ports[0] if ports else None


def detect_blockers(lab: Path) -> list[str]:
    path = compose_path(lab)
    if path is None:
        return []
    text = path.read_text(encoding="utf-8")
    if CONTAINER_NAME_RE.search(text):
        return ["container_name"]
    return []


def build_lab_entry(lab: Path, repo_root: Path) -> dict[str, Any]:
    from openlabs_contract import load_lab_metadata

    rel = lab.relative_to(repo_root).as_posix()
    meta = load_lab_metadata(lab / "lab.yml")
    record = meta.record
    track = record.track if record else lab.parent.name
    difficulty = record.difficulty if record else "unknown"
    slug = record.name if record else lab.name
    status = lab_status(lab)
    blockers = detect_blockers(lab)
    lifecycle_eligible = status == "supported" and not blockers
    return {
        "slug": slug,
        "path": rel,
        "track": track,
        "difficulty": difficulty,
        "status": status,
        "port": derive_host_port(lab),
        "compose_file": compose_file_name(lab),
        "lifecycle_eligible": lifecycle_eligible,
        "blockers": blockers,
    }


def list_catalog(repo_root: Path) -> dict[str, Any]:
    labs = discover_catalog_labs(repo_root)
    supported: list[dict[str, Any]] = []
    experimental: list[dict[str, Any]] = []
    for lab in labs:
        entry = build_lab_entry(lab, repo_root)
        if entry["status"] == "supported":
            supported.append(entry)
        else:
            experimental.append(entry)
    supported.sort(key=lambda item: item["slug"])
    experimental.sort(key=lambda item: item["slug"])
    return {
        "action": "list",
        "counts": {"supported": len(supported), "experimental": len(experimental)},
        "supported": supported,
        "experimental": experimental,
    }


def format_list_human(payload: dict[str, Any]) -> list[str]:
    lines = [
        f"supported ({payload['counts']['supported']}):",
    ]
    if payload["supported"]:
        for item in payload["supported"]:
            port = item["port"] if item["port"] is not None else "-"
            lines.append(
                f"  {item['slug']}  {item['path']}  port {port}  lifecycle eligible"
            )
    else:
        lines.append("  (none)")
    lines.append(f"experimental ({payload['counts']['experimental']}):")
    if payload["experimental"]:
        for item in payload["experimental"]:
            port = item["port"] if item["port"] is not None else "-"
            blockers = ", ".join(item["blockers"]) if item["blockers"] else "none"
            lines.append(
                f"  {item['slug']}  {item['path']}  port {port}  blockers {blockers}"
            )
    else:
        lines.append("  (none)")
    return lines


def _slug_index(repo_root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for lab in discover_catalog_labs(repo_root):
        slug = lab_name(lab)
        index[slug] = lab
    return index


def _uncatalogued_paths(repo_root: Path) -> set[str]:
    return {path.relative_to(repo_root).as_posix() for path in discover_uncatalogued_dirs(repo_root)}


def _lab_within_catalog_root(lab_resolved: Path, repo_root: Path) -> bool:
    labs_root = (repo_root / "labs").resolve()
    try:
        lab_resolved.relative_to(labs_root)
    except ValueError:
        return False
    return True


def resolve_lab(repo_root: Path, selector: str) -> ResolvedLab | LabSelectionError:
    raw = selector.strip()
    if not raw:
        return LabSelectionError("lab selector is required")

    repo_root = repo_root.resolve()
    slug_map = _slug_index(repo_root)
    uncatalogued = _uncatalogued_paths(repo_root)

    if "/" in raw or raw.startswith("labs"):
        canonical = raw.replace("\\", "/").strip("/")
        if canonical.startswith("./"):
            canonical = canonical[2:]
        if not CANONICAL_PATH_RE.fullmatch(canonical):
            return LabSelectionError(
                f"lab path must be canonical labs/<track>/<lab>; got {raw!r}"
            )
        candidate = repo_root / canonical
        if not candidate.is_dir():
            return LabSelectionError(f"lab path not found: {canonical}")
        try:
            resolved = candidate.resolve()
        except OSError:
            return LabSelectionError(f"lab path not accessible: {canonical}")
        if not _lab_within_catalog_root(resolved, repo_root):
            return LabSelectionError(f"lab path escapes catalog root: {canonical}")
        if canonical in uncatalogued or not (resolved / "lab.yml").is_file():
            return LabSelectionError(f"lab {canonical!r} is not catalogued")
        rel = resolved.relative_to(repo_root).as_posix()
        slug_paths = {lab.relative_to(repo_root).as_posix() for lab in discover_catalog_labs(repo_root)}
        if rel not in slug_paths:
            return LabSelectionError(f"lab {canonical!r} is not catalogued")
        return ResolvedLab(resolved, build_lab_entry(resolved, repo_root))

    if raw in slug_map:
        lab = slug_map[raw]
        return ResolvedLab(lab.resolve(), build_lab_entry(lab, repo_root))

    if raw in uncatalogued or f"labs/{raw}" in uncatalogued:
        return LabSelectionError(f"lab {raw!r} is not catalogued")

    matches = [slug for slug in slug_map if slug.startswith(raw) or raw in slug]
    if len(matches) > 1:
        return LabSelectionError(f"ambiguous lab selector {raw!r}; use an exact slug or canonical path")
    return LabSelectionError(f"unknown lab {raw!r}")
