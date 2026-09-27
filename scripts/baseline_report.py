#!/usr/bin/env python3
"""Generate the M0 baseline evidence report for issue #72.

Collects the reviewed commit, catalog manifest, validation summary, platform
evidence pointers, known blockers, and M0 exit criteria links. Does not run
Docker lifecycle proof (use prove_reference_lab.py or CI for L0-L6).

    python3 scripts/baseline_report.py --check
    python3 scripts/baseline_report.py --json m0-baseline-evidence.json
    python3 scripts/baseline_report.py --write-wiki wiki/M0-Baseline-Evidence.md

Exit codes:
    0  report ok; --check passes
    1  validation or fixture failure; stale wiki
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
EXIT_CRITERIA = SCRIPTS / "fixtures" / "m0_exit_criteria.json"
BRANCH_PROTECTION = SCRIPTS / "fixtures" / "m0_branch_protection.json"
REPORT_VERSION = "openlabs.baseline.v1"
REFERENCE_LAB = "labs/web/duck-cross"

sys.path.insert(0, str(SCRIPTS))

from lab_inventory import (  # noqa: E402
    LabRecord,
    build_inventory_report,
    exit_code_for_report,
    lab_name,
    lab_status,
)
from validate import check_lab, discover_labs, discover_uncatalogued_dirs  # noqa: E402


def git_reviewed_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_commit_timestamp_iso(commit: str) -> str:
    result = subprocess.run(
        ["git", "show", "-s", "--format=%cI", commit],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_reviewed_on_utc(commit: str) -> str:
    """Calendar date of the committer timestamp in UTC.

    Do not slice ``%cI``; GitHub merge commits often carry a +03:00 offset that
    rolls the local calendar day ahead of UTC and breaks wiki --check on CI.
    """
    result = subprocess.run(
        ["git", "show", "-s", "--format=%ct", commit],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    ts = int(result.stdout.strip())
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def run_validate_inventory() -> dict:
    records: list[LabRecord] = []
    for lab in discover_labs():
        errors = check_lab(lab)
        records.append(
            LabRecord(
                path=lab.relative_to(REPO_ROOT).as_posix(),
                name=lab_name(lab),
                status=lab_status(lab),
                ok=not errors,
                errors=errors,
            )
        )
    uncatalogued = discover_uncatalogued_dirs()
    return build_inventory_report(
        records,
        selection="all",
        uncatalogued=uncatalogued,
        tool="baseline_report",
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def supported_manifest(inventory: dict) -> list[dict]:
    rows: list[dict] = []
    for item in inventory["results"]:
        if item["status"] != "supported":
            continue
        rows.append(
            {
                "path": item["path"],
                "name": item["name"],
                "ok": item["ok"],
                "reference": item["path"] == REFERENCE_LAB,
            }
        )
    rows.sort(key=lambda row: row["path"])
    return rows


def experimental_labs(inventory: dict) -> list[dict]:
    rows = [
        {
            "path": item["path"],
            "name": item["name"],
            "ok": item["ok"],
            "errors": item["errors"],
        }
        for item in inventory["results"]
        if item["status"] == "experimental"
    ]
    rows.sort(key=lambda row: row["path"])
    return rows


def triage_blockers() -> dict:
    from lab_triage_inventory import build_report  # noqa: E402

    triage = build_report()
    follow_ups: list[str] = []
    for row in triage["rows"]:
        title = (row.get("decision") or {}).get("follow_up_title", "").strip()
        if title and title not in follow_ups:
            follow_ups.append(title)
    return {
        "directory_count": triage["directory_count"],
        "uncatalogued_count": triage["uncatalogued_count"],
        "follow_up_titles": follow_ups,
    }


def local_ci_commands() -> list[dict]:
    return [
        {
            "ci_job": "Validate labs",
            "commands": [
                "python3 scripts/validate.py",
                "python3 scripts/test_validate_status.py",
                "python3 scripts/test_status_aware_inventory.py",
                "python3 scripts/test_lab_triage_inventory.py",
                "python3 scripts/test_sync_catalog_public.py",
                "python3 scripts/test_ci_routing_matrix.py",
                "python3 scripts/test_baseline_report.py",
                "python3 scripts/baseline_report.py --check",
            ],
        },
        {
            "ci_job": "Validate compose files (when in scope)",
            "commands": ["python3 scripts/validate.py --compose"],
        },
        {
            "ci_job": "Prove duck-cross L0-L6",
            "commands": [
                "python3 scripts/prove_reference_lab.py --json reference-lab-evidence.json"
            ],
        },
        {
            "ci_job": "Security scan",
            "commands": [
                "gitleaks detect --source . --config .gitleaks.toml --redact --verbose",
                "python3 scripts/score_lab.py --min 70 --json score-report.json",
            ],
        },
        {
            "ci_job": "Content contracts",
            "commands": [
                "python3 scripts/sync_catalog_public.py --check",
                "python3 scripts/sync_site_content.py",
                "pnpm install --frozen-lockfile",
                "pnpm exec contentbit doctor --strict-seo",
            ],
        },
        {
            "ci_job": "Build lab sheets",
            "commands": ["python3 scripts/make_lab_pdf.py --all --strict"],
        },
        {
            "ci_job": "Lint workflows",
            "commands": [
                "bash scripts/lint_workflows.sh",
                "python3 scripts/validate_issue_forms.py",
                "python3 scripts/test_ci_routing_matrix.py",
            ],
        },
    ]


def build_report() -> dict:
    commit = git_reviewed_commit()
    commit_timestamp = git_commit_timestamp_iso(commit)
    inventory = run_validate_inventory()
    manifest = supported_manifest(inventory)
    validate_exit = exit_code_for_report(inventory)
    exit_criteria = load_json(EXIT_CRITERIA)
    protection = load_json(BRANCH_PROTECTION)

    errors: list[str] = []
    if not any(row["reference"] for row in manifest):
        errors.append(f"supported manifest missing reference lab {REFERENCE_LAB}")
    if validate_exit != 0:
        errors.append(f"validate inventory exit {validate_exit}")

    return {
        "version": REPORT_VERSION,
        "parent_issue": 72,
        "reviewed_commit": commit,
        "reviewed_on": git_reviewed_on_utc(commit),
        "commit_timestamp": commit_timestamp,
        "catalog": inventory["catalog"],
        "uncatalogued": inventory["uncatalogued"],
        "supported_manifest": manifest,
        "experimental_labs": experimental_labs(inventory),
        "validation": {
            "exit_code": validate_exit,
            "blocking_count": len(inventory["blocking"]),
            "advisory_count": len(inventory["advisory"]),
        },
        "platform_evidence": {
            "reference_lab": REFERENCE_LAB,
            "lifecycle_script": "scripts/prove_reference_lab.py",
            "ci_job": "Prove duck-cross L0-L6",
            "platform": "Linux x86_64 with Docker Compose v2",
            "note": "Run the script locally or read CI artifacts; this report does not start containers.",
        },
        "known_blockers": triage_blockers(),
        "m0_exit_criteria": exit_criteria,
        "branch_protection": protection,
        "local_ci_commands": local_ci_commands(),
        "errors": errors,
    }


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render_wiki(report: dict) -> str:
    cat = report["catalog"]
    lines = [
        "## Purpose",
        "",
        "Auditable M0 completion record for "
        "[#72](https://github.com/duckurity/openlabs/issues/72) (M0-09). "
        "Use it before enabling branch protection on `main`. Depends on "
        "[#71](https://github.com/duckurity/openlabs/issues/71) (**CI required**).",
        "",
        f"Reviewed on `{report['reviewed_on']}`. Regenerate with "
        "`python3 scripts/baseline_report.py --write-wiki wiki/M0-Baseline-Evidence.md`. "
        "Write `--json` when you need the reviewed git commit and full inventory snapshot.",
        "",
        "## Catalog manifest",
        "",
        f"- Supported: **{cat['supported_count']}**",
        f"- Experimental: **{cat['experimental_count']}**",
        f"- Invalid status: **{cat['invalid_status_count']}**",
        f"- Uncatalogued directories: **{len(report['uncatalogued'])}**",
        "",
        "## Supported manifest",
        "",
        "At least one lab must be the verified reference (`duck-cross`).",
        "",
        "| Path | Name | Validates | Reference |",
        "|:---|:---|:---:|:---:|",
    ]
    for row in report["supported_manifest"]:
        ref = "yes" if row["reference"] else "no"
        ok = "yes" if row["ok"] else "no"
        lines.append(f"| `{row['path']}` | {row['name']} | {ok} | {ref} |")

    lines.extend(
        [
            "",
            "## Validation results",
            "",
            f"- Inventory exit code: **{report['validation']['exit_code']}** "
            "(0 means supported catalog is non-empty and no blocking failures).",
            f"- Blocking supported failures: **{report['validation']['blocking_count']}**",
            f"- Advisory experimental findings: **{report['validation']['advisory_count']}**",
            "",
            "```bash",
            "python3 scripts/validate.py --json validate-report.json",
            "python3 scripts/score_lab.py --min 70 --json score-report.json",
            "```",
            "",
            "## Platform evidence",
            "",
            f"- Reference lab: `{report['platform_evidence']['reference_lab']}`",
            f"- Lifecycle script: `{report['platform_evidence']['lifecycle_script']}`",
            f"- CI job: **{report['platform_evidence']['ci_job']}**",
            f"- Platform: {report['platform_evidence']['platform']}",
            "",
            report["platform_evidence"]["note"],
            "",
            "## Known blockers",
            "",
            "### Uncatalogued directories",
            "",
        ]
    )
    if report["uncatalogued"]:
        for path in report["uncatalogued"]:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none")

    lines.extend(["", "### Experimental labs (not promoted)", ""])
    for row in report["experimental_labs"]:
        note = "validates" if row["ok"] else f"issues: {'; '.join(row['errors'])}"
        lines.append(f"- `{row['path']}` ({note})")

    blockers = report["known_blockers"]
    lines.extend(
        [
            "",
            "### Triage follow-ups (from M0-05)",
            "",
            f"Directories inventoried: **{blockers['directory_count']}**. "
            f"Uncatalogued: **{blockers['uncatalogued_count']}**.",
            "",
        ]
    )
    for title in blockers["follow_up_titles"]:
        lines.append(f"- {title}")

    lines.extend(
        [
            "",
            "## Local commands matching CI",
            "",
            "Run these from a clean checkout when reproducing **CI required** scope on `main`.",
            "",
        ]
    )
    for block in report["local_ci_commands"]:
        lines.append(f"### {block['ci_job']}")
        lines.append("")
        lines.append("```bash")
        lines.extend(block["commands"])
        lines.append("```")
        lines.append("")

    lines.extend(["## M0 exit checklist", ""])
    lines.append("| Issue | Title | Evidence |")
    lines.append("|:---|:---|:---|")
    for item in report["m0_exit_criteria"]["issues"]:
        url = f"https://github.com/duckurity/openlabs/issues/{item['number']}"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[#{item['number']}]({url}) ({item['id']})",
                    escape_cell(item["title"]),
                    escape_cell(item["evidence"]),
                ]
            )
            + " |"
        )

    protection = report["branch_protection"]
    record = protection["verification_record"]
    lines.extend(
        [
            "",
            "## Branch protection (manual)",
            "",
            "Configure in GitHub after [#71](https://github.com/duckurity/openlabs/issues/71) "
            "merge proves **CI required**. Record verification in "
            "[Branch protection record](Branch-Protection-Record).",
            "",
            "### Required status checks",
            "",
        ]
    )
    for check in protection["required_status_checks"]:
        when = check.get("when")
        extra = f" {when}" if when else ""
        lines.append(f"- **{check['name']}** (`{check['workflow']}`){extra}")

    lines.extend(["", "### Recommended rules", ""])
    for rule in protection["recommended_rules"]:
        lines.append(f"- {rule['setting']}: {rule['value']}")

    lines.extend(
        [
            "",
            "### Maintainer bypass policy",
            "",
            protection["maintainer_bypass_policy"],
            "",
            "### Verification record (fill manually)",
            "",
            "| Field | Value |",
            "|:---|:---|",
            f"| Verified by | {record['verified_by'] or '_pending_'} |",
            f"| Verified on | {record['verified_on'] or '_pending_'} |",
            f"| Settings export or screenshot | {record['settings_export_url'] or '_pending_'} |",
            f"| Protected-branch test PR | {record['protected_branch_test_pr'] or '_pending_'} |",
            f"| Notes | {escape_cell(record['notes'])} |",
            "",
        ]
    )
    return "\n".join(lines)


def check_report(report: dict) -> list[str]:
    return list(report.get("errors", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on report or wiki drift")
    parser.add_argument("--json", type=Path, metavar="FILE", help="write evidence JSON")
    parser.add_argument(
        "--write-wiki",
        type=Path,
        metavar="FILE",
        help="write wiki baseline page",
    )
    parser.add_argument(
        "--wiki",
        type=Path,
        metavar="FILE",
        help="with --check, fail if wiki differs from generated output",
    )
    args = parser.parse_args()

    if not EXIT_CRITERIA.is_file() or not BRANCH_PROTECTION.is_file():
        print("missing M0 fixtures under scripts/fixtures/", file=sys.stderr)
        return 2

    report = build_report()
    errors = check_report(report)

    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.write_wiki:
        content = render_wiki(report)
        args.write_wiki.write_text(content, encoding="utf-8")

    if args.check:
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            print(f"baseline report check failed ({len(errors)} problems)", file=sys.stderr)
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
            f"baseline ok: commit {report['reviewed_commit'][:12]}, "
            f"{report['catalog']['supported_count']} supported labs"
        )
        return 0

    if not args.json and not args.write_wiki:
        print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
