#!/usr/bin/env python3
"""Validate lab structure, metadata, and flag hygiene.

Usage:
    python3 scripts/validate.py              # structure and metadata
    python3 scripts/validate.py --compose    # also run `docker compose config`

Zero dependencies. Skips labs/_template/. Exits 1 when any lab fails.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LABS_DIR = REPO_ROOT / "labs"

TRACKS = {"web", "binary", "crypto", "network", "osint"}
DIFFICULTIES = {"easy", "medium", "hard", "insane"}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
FLAG_PLAINTEXT_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")

REQUIRED_KEYS = ("name", "track", "difficulty", "description", "flag_hash")
COMPOSE_NAMES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
)


def parse_flat_yaml(text: str) -> dict[str, str]:
    """Parse a flat key: value mapping. Ignores comments and blank lines."""
    data: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    return data


def check_lab(lab: Path) -> list[str]:
    errors: list[str] = []

    compose = next(
        (name for name in COMPOSE_NAMES if (lab / name).is_file()), None
    )
    if compose is None:
        errors.append("missing docker-compose.yml (or compose.yml)")

    brief = lab / "README.md"
    if not brief.is_file():
        errors.append("missing README.md")

    meta_path = lab / "lab.yml"
    if not meta_path.is_file():
        return errors + ["missing lab.yml"]

    meta = parse_flat_yaml(meta_path.read_text(encoding="utf-8"))

    for key in REQUIRED_KEYS:
        if not meta.get(key):
            errors.append(f"lab.yml: missing or empty `{key}`")
    if errors and any("missing or empty" in e for e in errors):
        return errors

    name = meta["name"]
    if not NAME_RE.match(name):
        errors.append(f"lab.yml: `name` {name!r} must be lowercase and hyphenated")
    elif name != lab.name:
        errors.append(f"lab.yml: `name` {name!r} does not match directory {lab.name!r}")

    if meta["track"] not in TRACKS:
        errors.append(f"lab.yml: `track` must be one of {sorted(TRACKS)}")
    elif lab.parent.name not in TRACKS:
        errors.append(f"directory {lab.parent.name!r} is not a track ({sorted(TRACKS)})")

    if meta["difficulty"] not in DIFFICULTIES:
        errors.append(f"lab.yml: `difficulty` must be one of {sorted(DIFFICULTIES)}")

    if not HASH_RE.match(meta["flag_hash"]):
        errors.append("lab.yml: `flag_hash` must be 64 lowercase hex characters")

    for file in (meta_path, brief):
        if file.is_file() and FLAG_PLAINTEXT_RE.search(file.read_text(encoding="utf-8")):
            errors.append(f"{file.name}: plaintext flag found; only flag_hash may appear here")

    return errors


def check_compose(compose_file: Path) -> str | None:
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "config", "-q"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        return f"{compose_file}: `docker compose config` failed ({detail})"
    return None


def discover_labs() -> list[Path]:
    if not LABS_DIR.is_dir():
        return []
    labs: list[Path] = []
    for track in sorted(LABS_DIR.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and not lab.name.startswith((".", "_")):
                labs.append(lab)
    return labs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compose",
        action="store_true",
        help="also validate compose files with `docker compose config`",
    )
    args = parser.parse_args()

    labs = discover_labs()
    if not labs:
        print("no labs found")
        return 1

    failures = 0
    for lab in labs:
        errors = check_lab(lab)
        if args.compose:
            for compose_name in COMPOSE_NAMES:
                compose_file = lab / compose_name
                if compose_file.is_file():
                    error = check_compose(compose_file)
                    if error:
                        errors.append(error)
        if errors:
            failures += 1
            print(f"{lab.relative_to(REPO_ROOT)}:")
            for error in errors:
                print(f"  - {error}")

    checked = "structure, metadata, and compose" if args.compose else "structure and metadata"
    if failures:
        print(f"failed {failures} of {len(labs)} labs ({checked})")
        return 1

    print(f"validated {len(labs)} labs ({checked})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
