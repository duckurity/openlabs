#!/usr/bin/env python3
"""Prove duck-cross through the M0-03 L0-L6 reference lifecycle.

Usage:
    python3 scripts/prove_reference_lab.py
    python3 scripts/prove_reference_lab.py --json evidence.json

Requires Docker Compose v2 on Linux x86_64. Uses a namespaced compose project
and tears down only resources created for this run. Delegates to the shared
openlabs verification engine (M2-08).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.lab_discovery import LabSelectionError, resolve_lab  # noqa: E402
from openlabs_cli.lab_verification import (  # noqa: E402
    ReferenceVerificationOptions,
    VerificationFailure,
    VerificationReport,
    capture_failure_logs,
    reference_teardown,
    run_verification,
)
from openlabs_cli.runner import SubprocessCommandRunner  # noqa: E402

REFERENCE = ReferenceVerificationOptions()


@dataclass
class StepResult:
    level: str
    ok: bool
    seconds: float
    detail: str = ""


@dataclass
class RunReport:
    lab: str = "duck-cross"
    project: str = REFERENCE.project
    port: int = REFERENCE.host_port
    docker_version: str = ""
    compose_version: str = ""
    steps: list[StepResult] = field(default_factory=list)
    resources_created: list[str] = field(default_factory=list)
    resources_removed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lab": self.lab,
            "project": self.project,
            "port": self.port,
            "docker_version": self.docker_version,
            "compose_version": self.compose_version,
            "steps": [step.__dict__ for step in self.steps],
            "resources_created": self.resources_created,
            "resources_removed": self.resources_removed,
        }


def _report_from_engine(engine_report: VerificationReport) -> RunReport:
    report = RunReport()
    report.lab = engine_report.lab
    report.project = engine_report.project
    report.port = engine_report.port
    report.docker_version = engine_report.docker_version
    report.compose_version = engine_report.compose_version
    report.resources_created = list(engine_report.resources_created)
    report.resources_removed = list(engine_report.resources_removed)
    for step in engine_report.levels:
        report.steps.append(
            StepResult(
                level=str(step["level"]),
                ok=bool(step["ok"]),
                seconds=float(step["seconds"]),
                detail=str(step.get("detail") or ""),
            )
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="write structured evidence JSON")
    args = parser.parse_args()

    ctx = CliContext(repo_root=REPO_ROOT, runner=SubprocessCommandRunner())
    selection = resolve_lab(REPO_ROOT, "duck-cross")
    if isinstance(selection, LabSelectionError):
        print(selection.message, file=sys.stderr)
        return 1

    exit_code = 0
    report = RunReport()
    try:
        engine_report = run_verification(
            ctx,
            selection,
            reference=REFERENCE,
            include_second_cycle=True,
        )
        report = _report_from_engine(engine_report)
    except VerificationFailure as error:
        exit_code = 1
        report = _report_from_engine(error.report)
        print(error, file=sys.stderr)
        logs = capture_failure_logs(ctx, selection, reference=REFERENCE)
        if logs:
            print("--- compose logs (redacted) ---", file=sys.stderr)
            print(logs, file=sys.stderr)
    finally:
        reference_teardown(ctx, selection, REFERENCE)

    if exit_code != 0:
        if args.json:
            args.json.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
        return 1

    for step in report.steps:
        if not step.ok:
            continue
        suffix = f" — {step.detail}" if step.detail else ""
        print(f"{step.level}: ok ({step.seconds}s){suffix}")

    if args.json:
        args.json.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")

    print(
        f"reference lab {report.lab}: all levels passed "
        f"(project {report.project}, port {report.port})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
