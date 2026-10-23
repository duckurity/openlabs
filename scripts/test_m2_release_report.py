#!/usr/bin/env python3
"""Validate M2 release evidence fixture and generator."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
FIXTURE = SCRIPTS / "fixtures" / "m2_release_evidence.json"
HOSTED = SCRIPTS / "fixtures" / "m2_tier1_hosted_evidence.json"
WIKI = SCRIPTS.parent / "wiki" / "M2-Release-Evidence.md"
REFERENCE = "labs/web/duck-cross"
ACTIONS_RUN_RE = re.compile(r"^https://github\.com/duckurity/openlabs/actions/runs/\d+$")


def main() -> int:
    failures = 0
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    hosted = json.loads(HOSTED.read_text(encoding="utf-8"))
    if data.get("reference_lab") != REFERENCE:
        print("m2_release_evidence: reference_lab must be duck-cross")
        failures += 1
    issues = data.get("issues", [])
    if len(issues) < 10:
        print("m2_release_evidence: expected 10 M2 issues")
        failures += 1
    if data.get("parent_issue") != 133:
        print("m2_release_evidence: parent_issue must be 133")
        failures += 1
    url = data.get("hosted_ci_run_url")
    if not url or not ACTIONS_RUN_RE.fullmatch(url):
        print("m2_release_evidence: hosted_ci_run_url must be set to a valid Actions run")
        failures += 1
    if "TBD" in json.dumps(data) or data.get("hosted_ci_run_url") is None:
        print("m2_release_evidence: must not contain null/TBD CI placeholders")
        failures += 1
    steps = data.get("tier1_lifecycle_steps", [])
    if "lab reset" not in steps or "lab start" not in steps:
        print("m2_release_evidence: must include reset and second start steps")
        failures += 1
    if hosted.get("hosted_ci_run_url") != url:
        print("m2_tier1_hosted_evidence: CI URL must match release fixture")
        failures += 1
    if len(hosted.get("lifecycle_steps", [])) < 6:
        print("m2_tier1_hosted_evidence: lifecycle_steps incomplete")
        failures += 1
    reset = hosted.get("reset_and_second_start", {})
    if reset.get("second_start_step") != "lab_start":
        print("m2_tier1_hosted_evidence: missing second start proof")
        failures += 1

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "m2_release_report.py"),
            "--check",
            "--wiki",
            str(WIKI),
        ],
        cwd=SCRIPTS.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        failures += 1

    wiki_text = WIKI.read_text(encoding="utf-8") if WIKI.is_file() else ""
    if "TBD" in wiki_text or "hosted_ci_run_url: null" in wiki_text:
        print("M2-Release-Evidence.md must not contain TBD/null CI placeholders")
        failures += 1
    if hosted["release_commit"][:12] not in wiki_text:
        print("M2-Release-Evidence.md must cite release evidence commit")
        failures += 1

    if failures:
        print(f"failed {failures} m2 release report checks")
        return 1
    print("m2 release report fixtures and generator ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
