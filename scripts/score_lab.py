#!/usr/bin/env python3
"""Score a lab 0-100 across five static categories. Zero dependencies.

Imported by scripts/sync_site_content.py (display) and run in CI as a
blocking gate. Hermetic: local file checks only, no network, no Docker.

    python3 scripts/score_lab.py                 # score every lab
    python3 scripts/score_lab.py --min 70        # exit 1 below threshold
    python3 scripts/score_lab.py labs/web/duck-cross

Categories: structure 25, secrets 25, Dockerfile 20, compose 15, docs 15.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import check_lab, parse_flat_yaml

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


def lab_files(lab: Path) -> list[Path]:
    return [p for p in lab.rglob("*") if p.is_file() and ".git" not in p.parts]


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
    return dockerfile.read_text(encoding="utf-8") if dockerfile.is_file() else ""


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


def discover() -> list[Path]:
    labs: list[Path] = []
    for track in sorted(LABS.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and not lab.name.startswith((".", "_")):
                labs.append(lab)
    return labs


def main() -> int:
    raw = sys.argv[1:]
    args: list[str] = []
    minimum = THRESHOLD
    skip_next = False
    for i, arg in enumerate(raw):
        if skip_next:
            skip_next = False
            continue
        if arg.startswith("--min="):
            minimum = int(arg.split("=", 1)[1])
        elif arg == "--min" and i + 1 < len(raw):
            minimum = int(raw[i + 1])
            skip_next = True
        else:
            args.append(arg)
    targets = [Path(a) for a in args] if args else discover()
    if not targets:
        print("score: no labs found")
        return 1
    results = [score_lab(lab) for lab in targets]
    print(json.dumps(results, indent=2))
    failing = [r for r in results if r["score"] < minimum]
    if failing:
        names = ", ".join(f"{r['name']} ({r['score']})" for r in failing)
        print(f"score: below threshold {minimum}: {names}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
