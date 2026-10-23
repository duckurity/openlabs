#!/usr/bin/env python3
"""Reviewed lab directory triage inventory for M0-05.

Merges maintainer decisions (scripts/fixtures/lab_triage_registry.json) with
live validate and score output. Does not modify labs.

    python3 scripts/lab_triage_inventory.py --check
    python3 scripts/lab_triage_inventory.py --json triage-evidence.json
    python3 scripts/lab_triage_inventory.py --write-wiki wiki/Lab-Triage-Inventory.md

Exit codes:
    0  registry matches every lab directory
    1  missing or extra registry entries, or stale generated wiki
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
REGISTRY_PATH = SCRIPTS / "fixtures" / "lab_triage_registry.json"
REPORT_VERSION = "openlabs.triage.v1"
SCORE_THRESHOLD = 70

sys.path.insert(0, str(SCRIPTS))

from openlabs_contract import legacy_string_map, load_lab_metadata  # noqa: E402
from validate import (  # noqa: E402
    COMPOSE_NAMES,
    LABS_DIR,
    NAME_RE,
    check_lab,
    discover_labs,
    discover_uncatalogued_dirs,
)
from score_lab import score_lab  # noqa: E402


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


def has_compose(lab: Path) -> bool:
    return any((lab / name).is_file() for name in COMPOSE_NAMES)


def structural_blockers(lab: Path) -> list[str]:
    blockers: list[str] = []
    if not has_compose(lab):
        blockers.append("missing compose file")
    if not (lab / "README.md").is_file():
        blockers.append("missing README.md")
    yml = lab / "lab.yml"
    if yml.is_file():
        result = load_lab_metadata(yml)
        if result.record is None:
            blockers.append("lab.yml failed metadata parse")
        else:
            meta = legacy_string_map(result.record)
            name = meta.get("name", "").strip()
            if not name:
                blockers.append("lab.yml missing name")
            elif not NAME_RE.match(name):
                blockers.append(f"lab.yml name {name!r} fails NAME_RE")
            elif name != lab.name:
                blockers.append(f"lab.yml name {name!r} does not match directory {lab.name!r}")
            if not meta.get("status", "").strip():
                blockers.append("lab.yml missing status")
    elif not NAME_RE.match(lab.name):
        blockers.append(f"directory name {lab.name!r} fails NAME_RE")
    return blockers


def catalog_status(lab: Path) -> str:
    yml = lab / "lab.yml"
    if not yml.is_file():
        return "uncatalogued"
    result = load_lab_metadata(yml)
    if result.record is None:
        return "invalid"
    raw = result.record.status.strip()
    if raw in ("experimental", "supported"):
        return raw
    return "invalid"


def score_recommendations(score: int | None, notes: list[str]) -> list[str]:
    recs: list[str] = []
    if score is not None and score < SCORE_THRESHOLD:
        recs.append(f"score {score} is below threshold {SCORE_THRESHOLD}")
    for note in notes:
        if note.startswith(("docs:", "dockerfile:", "compose:", "structure:")):
            recs.append(note)
    return recs[:5]


def measure_lab(lab: Path) -> dict:
    rel = lab.relative_to(REPO_ROOT).as_posix()
    status = catalog_status(lab)
    structural = structural_blockers(lab)
    validate_errors = check_lab(lab) if (lab / "lab.yml").is_file() else []
    try:
        scored = score_lab(lab)
        score = scored["score"]
        notes = scored["notes"]
    except (OSError, UnicodeDecodeError):
        score = None
        notes = []
    return {
        "path": rel,
        "catalog_status": status,
        "score": score,
        "structural_blockers": structural,
        "validate_errors": validate_errors,
        "score_recommendations": score_recommendations(score, notes),
    }


def load_registry() -> dict:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if data.get("version") != REPORT_VERSION:
        raise ValueError(f"registry version must be {REPORT_VERSION!r}")
    return data


def build_report() -> dict:
    registry = load_registry()
    decisions = registry["labs"]
    rows: list[dict] = []
    for lab in discover_all_lab_dirs():
        rel = lab.relative_to(REPO_ROOT).as_posix()
        measured = measure_lab(lab)
        decision = decisions.get(rel)
        if decision is None:
            measured["decision"] = None
        else:
            measured["decision"] = decision
        rows.append(measured)
    rows.sort(key=lambda item: item["path"])
    return {
        "version": REPORT_VERSION,
        "reviewed_on": registry.get("reviewed_on"),
        "parent_issue": registry.get("parent_issue"),
        "score_threshold": SCORE_THRESHOLD,
        "directory_count": len(rows),
        "catalogued_count": len(discover_labs()),
        "uncatalogued_count": len(discover_uncatalogued_dirs()),
        "rows": rows,
    }


def check_registry_complete(report: dict) -> list[str]:
    errors: list[str] = []
    expected = {row["path"] for row in report["rows"]}
    registry = load_registry()["labs"]
    reg_keys = set(registry.keys())
    missing = expected - reg_keys
    extra = reg_keys - expected
    if missing:
        errors.append(f"registry missing {len(missing)} directories: {sorted(missing)[:3]}")
    if extra:
        errors.append(f"registry has {len(extra)} unknown paths: {sorted(extra)[:3]}")
    for row in report["rows"]:
        decision = row.get("decision")
        if not decision:
            errors.append(f"no decision for {row['path']}")
            continue
        action = decision.get("action", "")
        if action in ("keep_uncatalogued", "repair_then_catalog", "catalog_experimental_review"):
            if not decision.get("follow_up_title", "").strip():
                errors.append(f"{row['path']}: action {action} needs follow_up_title")
        if action == "remove_pending_approval" and not decision.get("blocker", "").strip():
            errors.append(f"{row['path']}: removal needs documented blocker")
    return errors


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_wiki(report: dict) -> str:
    today = report.get("reviewed_on") or date.today().isoformat()
    lines = [
        "## Purpose",
        "",
        "Parent triage for [#68](https://github.com/duckurity/openlabs/issues/68) "
        "(M0-05). Every directory under `labs/<track>/` has a recorded decision. "
        "Repairs happen in separate issues and pull requests. Do not infer "
        "`supported` from a score of 70 or higher.",
        "",
        f"Reviewed on `{today}`. Regenerate with "
        "`python3 scripts/lab_triage_inventory.py --write-wiki wiki/Lab-Triage-Inventory.md`.",
        "",
        "## Evidence commands",
        "",
        "```bash",
        "python3 scripts/lab_triage_inventory.py --json triage-evidence.json",
        "python3 scripts/validate.py --json validate-report.json",
        "python3 scripts/score_lab.py --min 70 --json score-report.json",
        "```",
        "",
        "## Summary",
        "",
        f"- Directories inventoried: **{report['directory_count']}** "
        f"(issue #68 opened at 24; `duckexchange` added after that count).",
        f"- Catalogued: **{report['catalogued_count']}**; "
        f"uncatalogued: **{report['uncatalogued_count']}**.",
        f"- Score gate reference: **{report['score_threshold']}** (recommendations only).",
        "",
        "## Inventory",
        "",
        "| Directory | Catalog status | Score | Structural blockers | Score recommendations | Action | Owner | Follow-up issue title |",
        "|:---|:---:|:---:|:---|:---|:---|:---|:---|",
    ]
    for row in report["rows"]:
        decision = row["decision"] or {}
        structural = "; ".join(row["structural_blockers"]) or "none"
        score = str(row["score"]) if row["score"] is not None else "n/a"
        recs = "; ".join(row["score_recommendations"]) or "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['path']}`",
                    row["catalog_status"],
                    score,
                    escape_cell(structural),
                    escape_cell(recs),
                    decision.get("action", ""),
                    decision.get("owner", ""),
                    escape_cell(decision.get("follow_up_title", "") or "none"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Follow-up issues to file",
            "",
            "Open one GitHub issue per title below. Link the issue back to #68. "
            "Do not batch unrelated labs in one remediation pull request.",
            "",
        ]
    )
    titles: list[str] = []
    for row in report["rows"]:
        title = (row.get("decision") or {}).get("follow_up_title", "").strip()
        if title and title not in titles:
            titles.append(title)
    for title in titles:
        lines.append(f"- {title}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify registry coverage")
    parser.add_argument(
        "--wiki",
        type=Path,
        metavar="FILE",
        help="with --check, fail if wiki file differs from generated output",
    )
    parser.add_argument("--json", type=Path, metavar="FILE", help="write evidence JSON")
    parser.add_argument(
        "--write-wiki",
        type=Path,
        metavar="FILE",
        help="write wiki inventory page",
    )
    args = parser.parse_args()
    if not REGISTRY_PATH.is_file():
        print(f"missing registry {REGISTRY_PATH}", file=sys.stderr)
        return 2

    report = build_report()
    errors = check_registry_complete(report)

    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.write_wiki:
        content = render_wiki(report)
        if args.write_wiki.exists():
            existing = args.write_wiki.read_text(encoding="utf-8")
            if existing != content:
                args.write_wiki.write_text(content, encoding="utf-8")
        else:
            args.write_wiki.write_text(content, encoding="utf-8")

    if args.check:
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            print(f"triage check failed ({len(errors)} problems)", file=sys.stderr)
            return 1
        if args.wiki:
            expected = render_wiki(report)
            actual = args.wiki.read_text(encoding="utf-8") if args.wiki.is_file() else ""
            if actual != expected:
                print(
                    f"wiki stale: regenerate with --write-wiki {args.wiki}",
                    file=sys.stderr,
                )
                return 1
        print(
            f"triage ok: {report['directory_count']} directories, "
            f"{report['uncatalogued_count']} uncatalogued"
        )
        return 0

    if not args.json and not args.write_wiki:
        print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
