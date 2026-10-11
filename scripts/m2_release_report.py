#!/usr/bin/env python3
"""Generate the M2 release evidence report for issue #133.

    python3 scripts/m2_release_report.py --check --wiki wiki/M2-Release-Evidence.md
    python3 scripts/m2_release_report.py --write-wiki wiki/M2-Release-Evidence.md
    python3 scripts/m2_release_report.py --json m2-release-evidence.json

Exit codes:
    0  report ok; --check passes
    1  validation failure or stale wiki
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
FIXTURE = SCRIPTS / "fixtures" / "m2_release_evidence.json"
REPORT_VERSION = "openlabs.m2_release.v1"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ACTIONS_RUN_RE = re.compile(r"^https://github\.com/duckurity/openlabs/actions/runs/\d+$")

sys.path.insert(0, str(SCRIPTS))

import baseline_report  # noqa: E402
from openlabs_cli.version import (  # noqa: E402
    CLI_VERSION,
    ENVELOPE_VERSION,
    LAB_CONTRACT_VERSION,
)


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def load_hosted_evidence(fixture: dict) -> dict:
    rel = fixture.get("hosted_evidence_fixture")
    if not rel:
        raise ValueError("hosted_evidence_fixture missing from m2_release_evidence.json")
    path = REPO_ROOT / rel
    return json.loads(path.read_text(encoding="utf-8"))


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def wiki_content_for_check(text: str) -> str:
    kept: list[str] = []
    for line in text.splitlines():
        if line.startswith("Reviewed on `"):
            continue
        if line.startswith("| Reviewed commit |"):
            continue
        if line.startswith("| Release evidence commit |"):
            continue
        kept.append(line)
    return "\n".join(kept).rstrip() + "\n"


def validate_hosted_evidence(fixture: dict, hosted: dict) -> list[str]:
    errors: list[str] = []
    url = fixture.get("hosted_ci_run_url")
    if not url or not ACTIONS_RUN_RE.fullmatch(str(url)):
        errors.append("hosted_ci_run_url must be a duckurity/openlabs Actions run URL")
    if url and hosted.get("hosted_ci_run_url") != url:
        errors.append("hosted evidence fixture CI URL must match m2_release_evidence.json")
    commit = hosted.get("release_commit")
    if not commit or not COMMIT_RE.fullmatch(str(commit)):
        errors.append("hosted evidence release_commit must be a 40-char git sha")
    job_url = hosted.get("tier1_ci_job_url")
    if not job_url or "actions/runs/" not in str(job_url):
        errors.append("hosted evidence tier1_ci_job_url missing")
    steps = hosted.get("lifecycle_steps")
    if not isinstance(steps, list) or len(steps) < 6:
        errors.append("hosted evidence lifecycle_steps must list six CLI steps")
    else:
        for step in steps:
            if not step.get("ok") or step.get("seconds") is None:
                errors.append(f"hosted evidence step {step.get('name')} missing ok/seconds")
    reset = hosted.get("reset_and_second_start")
    if not isinstance(reset, dict):
        errors.append("hosted evidence reset_and_second_start missing")
    elif reset.get("reset_step") != "lab_reset" or reset.get("second_start_step") != "lab_start":
        errors.append("hosted evidence must document reset then second start")
    if hosted.get("ci_conclusion") != "success":
        errors.append("hosted evidence ci_conclusion must be success")
    if hosted.get("cleanup_ok") is not True:
        errors.append("hosted evidence cleanup_ok must be true")
    return errors


def build_report() -> dict:
    fixture = load_fixture()
    hosted = load_hosted_evidence(fixture)
    commit = baseline_report.git_reviewed_commit()
    inventory = baseline_report.run_validate_inventory()
    manifest = baseline_report.supported_manifest(inventory)
    errors: list[str] = []
    ref = fixture["reference_lab"]
    if not any(row["path"] == ref for row in manifest):
        errors.append(f"supported manifest missing reference lab {ref}")
    if baseline_report.exit_code_for_report(inventory) != 0:
        errors.append("validate inventory exit non-zero")
    errors.extend(validate_hosted_evidence(fixture, hosted))

    return {
        "version": REPORT_VERSION,
        "parent_issue": fixture["parent_issue"],
        "reviewed_commit": commit,
        "reviewed_on": baseline_report.git_reviewed_on_utc(commit),
        "release_evidence_commit": hosted["release_commit"],
        "cli_version": CLI_VERSION,
        "envelope_version": ENVELOPE_VERSION,
        "lab_contract_version": LAB_CONTRACT_VERSION,
        "catalog": inventory["catalog"],
        "supported_manifest": manifest,
        "fixture": fixture,
        "hosted": hosted,
        "errors": errors,
    }


def render_wiki(report: dict) -> str:
    fixture = report["fixture"]
    hosted = report["hosted"]
    cat = report["catalog"]
    ci_url = fixture["hosted_ci_run_url"]
    job_url = hosted["tier1_ci_job_url"]
    lines = [
        "# M2 release evidence",
        "",
        "Completion record for milestone **M2 - One-command lab lifecycle** and "
        "[#133 M2-10](https://github.com/duckurity/openlabs/issues/133).",
        "",
        f"Reviewed on `{report['reviewed_on']}`. Regenerate with "
        "`python3 scripts/m2_release_report.py --write-wiki wiki/M2-Release-Evidence.md`.",
        "",
        "## Release markers",
        "",
        "| Item | Value |",
        "|:---|:---|",
        f"| CLI version | `{report['cli_version']}` |",
        f"| Command envelope | `{report['envelope_version']}` |",
        f"| Lab contract | `{report['lab_contract_version']}` |",
        f"| Reviewed commit | `{report['reviewed_commit'][:12]}` |",
        f"| Release evidence commit | `{report['release_evidence_commit'][:12]}` |",
        "",
        "## Supported manifest",
        "",
        f"- Supported: **{cat['supported_count']}**",
        f"- Experimental: **{cat['experimental_count']}**",
        f"- Catalogued: **{cat['supported_count'] + cat['experimental_count']}**",
        "",
        "| Path | Name | Reference |",
        "|:---|:---|:---|",
    ]
    for row in report["supported_manifest"]:
        ref = "yes" if row.get("reference") else "no"
        lines.append(f"| `{row['path']}` | {row['name']} | {ref} |")

    lines.extend(
        [
            "",
            "## Platform and CI evidence",
            "",
            f"- Tier 1 platform: {fixture['tier1_platform']}",
            f"- Reference lab: `{fixture['reference_lab']}`",
            f"- Hosted CI run: [{ci_url}]({ci_url}) ({hosted['ci_conclusion']})",
            f"- Tier 1 proof job: [{hosted['tier1_ci_job_name']}]({job_url})",
            f"- Release evidence commit: `{report['release_evidence_commit']}`",
            f"- Uploaded artifacts: {', '.join(f'`{name}`' for name in hosted['artifact_names'])}",
            "",
            "CI job **Prove duck-cross L0-L6** runs:",
            "",
            "1. `python3 scripts/prove_reference_lab.py` (legacy L0–L6 prove)",
            "2. Bounded prove artifact via `scripts/evidence_artifact.py`",
            "3. `python3 scripts/run_m2_tier1_lifecycle.py` (CLI lifecycle evidence)",
            "4. Secret scan on both JSON artifacts",
            "",
            "### Tier 1 CLI lifecycle timings (hosted)",
            "",
            "| Step | Ok | Seconds |",
            "|:---|:---:|---:|",
        ]
    )
    for step in hosted["lifecycle_steps"]:
        ok = "yes" if step.get("ok") else "no"
        lines.append(f"| `{step['name']}` | {ok} | {step.get('seconds')} |")

    reset = hosted["reset_and_second_start"]
    lines.extend(
        [
            "",
            "### Reset and second start proof",
            "",
            f"- `{reset['reset_step']}` completed in **{reset['reset_seconds']}s**",
            f"- `{reset['second_start_step']}` completed in **{reset['second_start_seconds']}s** "
            f"(second start after verify reset cycle)",
            f"- Cleanup ok: **{hosted['cleanup_ok']}**",
            "",
            "Tier 1 CLI lifecycle command order:",
            "",
        ]
    )
    for step in fixture["tier1_lifecycle_steps"]:
        lines.append(f"- `./openlabs --json --non-interactive {step} {fixture['reference_lab_slug']}`")

    lines.extend(
        [
            "",
            "## Player and maintainer docs",
            "",
            "- [OpenLabs CLI](OpenLabs-CLI)",
            "- [Platform support tiers](Platform-Support-Tiers)",
            "- [OpenLabs state and logs](OpenLabs-State-and-Logs)",
            "- [CLI troubleshooting](CLI-Troubleshooting)",
            "",
            "## Known limitations",
            "",
        ]
    )
    for item in fixture["known_limitations"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Deferred work", ""])
    for item in fixture["deferred_work"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## M2 delivery checklist",
            "",
            "| Step | Issue | Evidence |",
            "|:---:|:---|:---|",
        ]
    )
    for row in fixture["issues"]:
        lines.append(
            f"| {row['id']} | "
            f"[#{row['number']}](https://github.com/duckurity/openlabs/issues/{row['number']}) | "
            f"{escape_cell(row['evidence'])} |"
        )

    approval = fixture["approval"]
    lines.extend(
        [
            "",
            "## Release approval (manual)",
            "",
            "Senior maintainer approval is required before closing #133.",
            "",
            "| Reviewer | Date | Outcome | Notes |",
            "|:---|:---|:---|:---|",
            f"| {approval.get('reviewer') or '_pending_'} | "
            f"{approval.get('date') or '_pending_'} | "
            f"{approval.get('outcome') or '_pending_'} | "
            f"{escape_cell(approval.get('notes') or '')} |",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on report or wiki drift")
    parser.add_argument("--json", type=Path, metavar="FILE", help="write evidence JSON")
    parser.add_argument("--write-wiki", type=Path, metavar="FILE", help="write wiki page")
    parser.add_argument(
        "--wiki",
        type=Path,
        metavar="FILE",
        help="with --check, fail if wiki differs from generated output",
    )
    args = parser.parse_args()

    if not FIXTURE.is_file():
        print(f"missing fixture {FIXTURE}", file=sys.stderr)
        return 2

    report = build_report()
    errors = list(report.get("errors", []))

    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.write_wiki:
        args.write_wiki.write_text(render_wiki(report), encoding="utf-8")

    if args.check:
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            print(f"m2 release report check failed ({len(errors)} problems)", file=sys.stderr)
            return 1
        if args.wiki:
            expected = render_wiki(report)
            actual = args.wiki.read_text(encoding="utf-8") if args.wiki.is_file() else ""
            if wiki_content_for_check(actual) != wiki_content_for_check(expected):
                print(
                    f"wiki stale: regenerate with --write-wiki {args.wiki}",
                    file=sys.stderr,
                )
                return 1
        print(
            f"m2 release ok: cli {report['cli_version']}, "
            f"{report['catalog']['supported_count']} supported labs"
        )
        return 0

    if not args.json and not args.write_wiki:
        print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
