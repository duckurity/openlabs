#!/usr/bin/env python3
"""Score a lab 0-100 across five static categories. Zero dependencies.

Imported by scripts/sync_site_content.py (display) and run in CI as a
blocking gate on supported labs. Hermetic: local file checks only, no
network, no Docker.

    python3 scripts/score_lab.py
    python3 scripts/score_lab.py --min 70
    python3 scripts/score_lab.py --json score-report.json
    python3 scripts/score_lab.py labs/web/duck-cross

Exit codes:
    0  no supported lab below threshold; supported catalog non-empty
    1  supported lab below threshold
    2  usage error
    3  supported catalog is empty

Experimental scores below threshold are advisory only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab_inventory import (  # noqa: E402
    EXIT_CATALOG,
    EXIT_OK,
    EXIT_USAGE,
    LabRecord,
    STATUS_SELECTIONS,
    build_inventory_report,
    catalog_counts,
    discover_catalog,
    exit_code_for_report,
    format_github_step_summary,
    format_terminal_summary,
    in_selection,
    lab_name,
    lab_status,
)
from validate import check_lab, parse_flat_yaml  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LABS = ROOT / "labs"

THRESHOLD = 70

SECRET_RES = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
)

FLAG_PLAINTEXT_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")

# Hermetic scoring: ignore vendored trees that are not part of the lab image.
_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "__pycache__",
        "dist",
        "node_modules",
        "vendor",
    }
)


def lab_files(lab: Path) -> list[Path]:
    files: list[Path] = []
    for path in lab.rglob("*"):
        if not path.is_file():
            continue
        if _SKIP_DIR_NAMES.intersection(path.relative_to(lab).parts):
            continue
        files.append(path)
    return sorted(files)


def score_structure(lab: Path) -> tuple[int, list[str]]:
    errors = check_lab(lab)
    if errors:
        return 0, [f"structure: {e}" for e in errors[:3]]
    return 25, []


def score_secrets(lab: Path) -> tuple[int, list[str]]:
    notes: list[str] = []
    deductions = 0
    for path in lab_files(lab):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(lab).as_posix()
        for pattern in SECRET_RES:
            if pattern.search(text):
                deductions += 5
                notes.append(f"secrets: {rel} matches {pattern.pattern[:24]}…")
        if rel != "lab.yml" and not rel.startswith("app/"):
            if FLAG_PLAINTEXT_RE.search(text):
                deductions += 10
                notes.append(f"secrets: plaintext flag outside app/ in {rel}")
    return max(0, 25 - deductions), notes


def read_dockerfile(lab: Path) -> str:
    dockerfile = lab / "Dockerfile"
    if dockerfile.is_file():
        return dockerfile.read_text(encoding="utf-8")
    compose = read_compose(lab)
    if not compose:
        return ""
    match = re.search(
        r"(?ms)^\s*build:\s*\n\s*context:\s*(\S+)\s*\n\s*dockerfile:\s*(\S+)",
        compose,
    )
    if match:
        context = lab / match.group(1).strip("\"'")
        dockerfile_name = match.group(2).strip("\"'")
        candidate = context / dockerfile_name
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*build:\s*(\./[^\s#]+)", compose)
    if match:
        context = lab / match.group(1).strip("\"'")
        candidate = context / "Dockerfile"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return ""


def score_dockerfile(lab: Path) -> tuple[int, list[str]]:
    text = read_dockerfile(lab)
    if not text:
        return 0, ["dockerfile: missing Dockerfile"]
    score, notes = 20, []
    from_lines = [l for l in text.splitlines() if l.upper().startswith("FROM ")]
    if not from_lines:
        score -= 8
        notes.append("dockerfile: no FROM line")
    else:
        image = from_lines[0].split(maxsplit=1)[1]
        if ":" not in image.split("/")[-1] or image.endswith(":latest"):
            score -= 8
            notes.append("dockerfile: base image not pinned to a version tag")
    if not re.search(r"(?m)^USER\s+\S+", text):
        score -= 6
        notes.append("dockerfile: no USER directive (runs as root)")
    if re.search(r"(?m)^ADD\s+", text):
        score -= 3
        notes.append("dockerfile: prefer COPY over ADD")
    if re.search(r"curl[^\n]*\|\s*(?:sudo\s+)?(?:ba)?sh", text) or re.search(
        r"wget[^\n]*\|\s*(?:sudo\s+)?(?:ba)?sh", text
    ):
        score -= 3
        notes.append("dockerfile: pipes a download into a shell")
    return max(0, score), notes


def read_compose(lab: Path) -> str:
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        path = lab / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def score_compose(lab: Path, readme: str) -> tuple[int, list[str]]:
    text = read_compose(lab)
    if not text:
        return 0, ["compose: missing compose file"]
    score, notes = 15, []
    if not re.search(r"(?m)^\s*ports\s*:", text):
        score -= 6
        notes.append("compose: no published ports")
    if not re.search(r"(?m)^\s*restart\s*:", text):
        score -= 4
        notes.append("compose: no explicit restart policy")
    port_match = re.search(r'"(\d{2,5}):\d{2,5}"', text)
    if port_match and port_match.group(1) not in readme:
        score -= 5
        notes.append("compose: host port not stated in the brief")
    return max(0, score), notes


def score_docs(lab: Path, readme: str) -> tuple[int, list[str]]:
    score, notes = 15, []
    for section in ("## Brief", "## Setup", "## Goal"):
        if section not in readme:
            score -= 3
            notes.append(f"docs: README missing {section}")
    if not (lab / f"{lab.name}.pdf").is_file():
        score -= 3
        notes.append("docs: no challenge-sheet PDF beside the lab")
    meta = parse_flat_yaml((lab / "lab.yml").read_text(encoding="utf-8")) if (lab / "lab.yml").is_file() else {}
    if not meta.get("techniques", "").strip("[] "):
        score -= 3
        notes.append("docs: lab.yml names no techniques")
    return max(0, score), notes


def grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def score_lab(lab: Path) -> dict:
    readme_path = lab / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    parts = [
        score_structure(lab),
        score_secrets(lab),
        score_dockerfile(lab),
        score_compose(lab, readme),
        score_docs(lab, readme),
    ]
    total = sum(score for score, _ in parts)
    notes = [note for _, part_notes in parts for note in part_notes]
    return {
        "name": lab.name,
        "score": total,
        "grade": grade(total),
        "notes": notes,
        "breakdown": {
            "structure": parts[0][0],
            "secrets": parts[1][0],
            "dockerfile": parts[2][0],
            "compose": parts[3][0],
            "docs": parts[4][0],
        },
    }


def run_score(
    targets: list[Path], *, minimum: int
) -> list[LabRecord]:
    records: list[LabRecord] = []
    for lab in targets:
        result = score_lab(lab)
        total = result["score"]
        ok = total >= minimum
        errors: list[str] = []
        if not ok:
            errors.append(f"score {total} below threshold {minimum} (grade {result['grade']})")
            errors.extend(result["notes"])
        records.append(
            LabRecord(
                path=lab.relative_to(ROOT).as_posix(),
                name=lab_name(lab),
                status=lab_status(lab),
                ok=ok,
                errors=errors,
            )
        )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "labs",
        nargs="*",
        type=Path,
        help="lab paths (default: every catalogued lab)",
    )
    parser.add_argument("--min", type=int, default=THRESHOLD, metavar="N")
    parser.add_argument(
        "--status",
        choices=sorted(STATUS_SELECTIONS),
        default="all",
        help="filter JSON results; blocking exit uses supported scores",
    )
    parser.add_argument("--json", type=Path, metavar="FILE")
    parser.add_argument(
        "--write-github-summary",
        action="store_true",
        help="append GitHub Actions step summary when GITHUB_STEP_SUMMARY is set",
    )
    args = parser.parse_args()

    if args.status not in STATUS_SELECTIONS:
        print(f"invalid --status {args.status!r}", file=sys.stderr)
        return EXIT_USAGE

    all_labs, uncatalogued = discover_catalog()
    targets = args.labs if args.labs else all_labs
    if not targets:
        print("score: no labs found", file=sys.stderr)
        return EXIT_CATALOG

    records = run_score(targets, minimum=args.min)
    report = build_inventory_report(
        records,
        selection=args.status,
        uncatalogued=uncatalogued,
        tool="score_lab",
        catalog=catalog_counts(all_labs),
    )
    report["threshold"] = args.min

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
    raise SystemExit(main())
