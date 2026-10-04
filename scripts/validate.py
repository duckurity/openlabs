#!/usr/bin/env python3
"""Validate lab structure, metadata, and flag hygiene.

Usage:
    python3 scripts/validate.py
    python3 scripts/validate.py --compose
    python3 scripts/validate.py --status supported --json report.json

Exit codes:
    0  no blocking failures; supported catalog non-empty
    1  supported lab failed validation
    2  usage error
    3  supported catalog is empty

Experimental failures are advisory and do not change the exit code unless
they also appear in the supported set. JSON uses version openlabs.inventory.v1.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from lab_inventory import (
    EXIT_BLOCKING,
    EXIT_CATALOG,
    EXIT_OK,
    EXIT_USAGE,
    LabRecord,
    STATUS_SELECTIONS,
    build_inventory_report,
    discover_catalog,
    exit_code_for_report,
    format_github_step_summary,
    format_terminal_summary,
    in_selection,
    lab_name,
    lab_status,
)
from openlabs_contract import collect_metadata_errors, load_lab_metadata

REPO_ROOT = Path(__file__).resolve().parent.parent
LABS_DIR = REPO_ROOT / "labs"

TRACKS = {"web", "binary", "crypto", "network", "osint"}
DIFFICULTIES = {"easy", "medium", "hard", "insane"}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FLAG_PLAINTEXT_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")

STATUSES = frozenset({"experimental", "supported"})
COMPOSE_NAMES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
)


def check_lab_status(meta: dict[str, str]) -> list[str]:
    """Validate the lab catalog status field."""
    errors: list[str] = []
    raw = meta.get("status", "").strip()
    if not raw:
        errors.append("lab.yml: missing or empty `status`")
        return errors
    if raw not in STATUSES:
        errors.append(
            f"lab.yml: `status` {raw!r} must be one of {sorted(STATUSES)}"
        )
    return errors


def discover_uncatalogued_dirs() -> list[Path]:
    """Return track lab directories that have no lab.yml (not catalogued)."""
    if not LABS_DIR.is_dir():
        return []
    uncatalogued: list[Path] = []
    for track in sorted(LABS_DIR.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and not lab.name.startswith((".", "_")):
                if not (lab / "lab.yml").is_file():
                    uncatalogued.append(lab)
    return uncatalogued


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

    errors.extend(collect_metadata_errors(lab))
    result = load_lab_metadata(meta_path)
    if result.record is not None:
        for slug in result.record.techniques:
            if not NAME_RE.match(slug):
                errors.append(
                    f"lab.yml: technique {slug!r} must be lowercase and hyphenated"
                )

    for file in (meta_path, brief):
        if file.is_file() and FLAG_PLAINTEXT_RE.search(file.read_text(encoding="utf-8")):
            errors.append(f"{file.name}: plaintext flag found; only flag_hash may appear here")

    return errors


def compose_check_env(lab_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    example = lab_dir / ".env.example"
    if example.is_file():
        for line in example.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in env:
                env[key] = value.strip()
    env.setdefault("FLAG", "duck{compose_validate_placeholder}")
    return env


def check_compose(compose_file: Path, lab_dir: Path) -> str | None:
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "config", "-q"],
        capture_output=True,
        text=True,
        env=compose_check_env(lab_dir),
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
                if (lab / "lab.yml").is_file():
                    labs.append(lab)
    return labs


def run_validate(*, compose: bool) -> tuple[list[LabRecord], list[Path]]:
    labs, uncatalogued = discover_catalog()
    records: list[LabRecord] = []
    for lab in labs:
        errors = check_lab(lab)
        if compose:
            for compose_name in COMPOSE_NAMES:
                compose_file = lab / compose_name
                if compose_file.is_file():
                    error = check_compose(compose_file, lab)
                    if error:
                        errors.append(error)
        status = lab_status(lab)
        records.append(
            LabRecord(
                path=lab.relative_to(REPO_ROOT).as_posix(),
                name=lab_name(lab),
                status=status,
                ok=not errors,
                errors=errors,
            )
        )
    return records, uncatalogued


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compose",
        action="store_true",
        help="also validate compose files with `docker compose config`",
    )
    parser.add_argument(
        "--status",
        choices=sorted(STATUS_SELECTIONS),
        default="all",
        help="filter JSON results; blocking exit uses supported failures",
    )
    parser.add_argument(
        "--json",
        type=Path,
        metavar="FILE",
        help="write structured inventory JSON",
    )
    parser.add_argument(
        "--write-github-summary",
        action="store_true",
        help="append GitHub Actions step summary when GITHUB_STEP_SUMMARY is set",
    )
    args = parser.parse_args()

    if args.status not in STATUS_SELECTIONS:
        print(f"invalid --status {args.status!r}", file=sys.stderr)
        return EXIT_USAGE

    records, uncatalogued = run_validate(compose=args.compose)
    if not records:
        print("no catalogued labs found")
        return EXIT_CATALOG

    report = build_inventory_report(
        records,
        selection=args.status,
        uncatalogued=uncatalogued,
        tool="validate" + ("+compose" if args.compose else ""),
    )

    for record in records:
        if not in_selection(record.status, args.status) or record.ok:
            continue
        print(f"{record.path}:")
        for error in record.errors:
            print(f"  - {error}")

    print(format_terminal_summary(report))

    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.write_github_summary:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as handle:
                handle.write(format_github_step_summary(report))

    if args.status == "experimental":
        return EXIT_OK
    return exit_code_for_report(report)


if __name__ == "__main__":
    sys.exit(main())
