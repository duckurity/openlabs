#!/usr/bin/env python3
"""Prove duck-cross through the M0-03 L0-L6 reference lifecycle.

Usage:
    python3 scripts/prove_reference_lab.py
    python3 scripts/prove_reference_lab.py --json evidence.json

Requires Docker Compose v2 on Linux x86_64. Uses a namespaced compose project
and tears down only resources created for this run.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from check import flag_stage  # noqa: E402
from openlabs_contract import legacy_string_map, load_lab_metadata, read_player_flag_hashes  # noqa: E402
from validate import check_lab, check_compose  # noqa: E402

LAB = REPO_ROOT / "labs" / "web" / "duck-cross"
COMPOSE_FILE = LAB / "docker-compose.yml"
PROJECT = "openlabs-ref-duck-cross"
PORT = 8377
BASE_URL = f"http://127.0.0.1:{PORT}"
START_TIMEOUT_S = 60
POLL_INTERVAL_S = 0.5

FLAG_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")
REQUIRED_FILES = ("lab.yml", "README.md", "docker-compose.yml", "Dockerfile")


@dataclass
class StepResult:
    level: str
    ok: bool
    seconds: float
    detail: str = ""


@dataclass
class RunReport:
    lab: str = "duck-cross"
    project: str = PROJECT
    port: int = PORT
    docker_version: str = ""
    compose_version: str = ""
    steps: list[StepResult] = field(default_factory=list)
    resources_created: list[str] = field(default_factory=list)
    resources_removed: list[str] = field(default_factory=list)

    def add(self, level: str, ok: bool, started: float, detail: str = "") -> None:
        self.steps.append(
            StepResult(level=level, ok=ok, seconds=round(time.time() - started, 2), detail=detail)
        )
        if not ok:
            raise LifecycleError(level, detail)

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


class LifecycleError(Exception):
    def __init__(self, level: str, detail: str) -> None:
        super().__init__(f"{level} failed: {detail}")
        self.level = level
        self.detail = detail


def redact(text: str) -> str:
    return FLAG_RE.sub("duck{...redacted...}", text)


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        detail = redact((result.stderr or result.stdout or "").strip())
        raise LifecycleError("compose", detail or f"exit {result.returncode}")
    return result


def compose_cmd(*args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "-p",
        PROJECT,
        *args,
    ]


def http_get(path: str, timeout: float = 10.0) -> tuple[int, str]:
    request = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        return error.code, body


def wait_ready(report: RunReport) -> None:
    deadline = time.time() + START_TIMEOUT_S
    while time.time() < deadline:
        try:
            status, body = http_get("/")
            if status == 200 and "duck cross" in body:
                return
        except OSError:
            pass
        time.sleep(POLL_INTERVAL_S)
    raise LifecycleError("L3", f"service not ready within {START_TIMEOUT_S}s")


def list_project_resources() -> list[str]:
    result = run(compose_cmd("ps", "-a", "--format", "{{.Name}}"), check=False)
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return names


def level_l0(report: RunReport) -> None:
    started = time.time()
    missing = [name for name in REQUIRED_FILES if not (LAB / name).is_file()]
    if missing:
        report.add("L0", False, started, f"missing files: {', '.join(missing)}")
    errors = check_lab(LAB)
    if errors:
        report.add("L0", False, started, "; ".join(errors))
    result = load_lab_metadata(LAB / "lab.yml")
    if result.record is None:
        report.add("L0", False, started, "lab.yml failed metadata parse")
        return
    meta = legacy_string_map(result.record)
    if meta.get("status") != "supported":
        report.add("L0", False, started, "lab.yml status must be supported for reference proof")
    if meta.get("name") != "duck-cross":
        report.add("L0", False, started, "unexpected lab name")
    report.add("L0", True, started, "metadata and required files valid")


def level_l1(report: RunReport) -> None:
    started = time.time()
    error = check_compose(COMPOSE_FILE, LAB)
    if error:
        report.add("L1", False, started, error)
    rendered = run(compose_cmd("config"), check=False).stdout
    if "8377" not in rendered:
        report.add("L1", False, started, f"compose config missing port {PORT}")
    report.add("L1", True, started, "compose renders with player port")


def level_l2(report: RunReport) -> None:
    started = time.time()
    run(compose_cmd("build", "--pull=false"))
    report.add("L2", True, started, "image build succeeded")


def level_l3(report: RunReport) -> None:
    started = time.time()
    run(compose_cmd("up", "-d"))
    wait_ready(report)
    report.resources_created = list_project_resources()
    report.add("L3", True, started, f"ready at {BASE_URL}")


def level_l4(report: RunReport) -> None:
    started = time.time()
    status, body = http_get("/")
    if status != 200 or "duck cross" not in body:
        report.add("L4", False, started, "player entry page failed")
    status, body = http_get("/api/reports/1")
    if status != 200 or "mill lane" not in body:
        report.add("L4", False, started, "public report workflow failed")
    report.add("L4", True, started, "entry page and public report API ok")


def level_l5(report: RunReport) -> None:
    started = time.time()
    status, body = http_get("/api/reports/6")
    if status != 200:
        report.add("L5", False, started, "restricted report not reachable")
    match = FLAG_RE.search(body)
    if not match:
        report.add("L5", False, started, "no flag in intended solve path")
    flag = match.group(0)
    for report_id in ("1", "2", "3", "4", "5"):
        _, public_body = http_get(f"/api/reports/{report_id}")
        if FLAG_RE.search(public_body):
            report.add("L5", False, started, f"flag leaked in public report {report_id}")
    stage = flag_stage(flag, read_player_flag_hashes(LAB))
    if stage != "final":
        report.add("L5", False, started, "checker rejected intended flag")
    report.add("L5", True, started, "intended IDOR path verifies with check.py")


def teardown(report: RunReport, label: str) -> None:
    started = time.time()
    run(compose_cmd("down", "-v", "--remove-orphans"))
    remaining = list_project_resources()
    if remaining:
        report.add(label, False, started, f"leftover resources: {', '.join(remaining)}")
    report.resources_removed.extend(report.resources_created)
    report.resources_created = []
    report.add(label, True, started, "compose down removed namespaced resources")


def capture_failure_logs() -> str:
    logs = run(compose_cmd("logs", "--no-color"), check=False)
    return redact(logs.stdout or logs.stderr or "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="write structured evidence JSON")
    args = parser.parse_args()

    report = RunReport()
    report.docker_version = run(["docker", "version", "--format", "{{.Server.Version}}"], check=False).stdout.strip()
    report.compose_version = run(["docker", "compose", "version", "--short"], check=False).stdout.strip()

    try:
        run(compose_cmd("down", "-v", "--remove-orphans"), check=False)
        level_l0(report)
        level_l1(report)
        level_l2(report)
        level_l3(report)
        level_l4(report)
        level_l5(report)
        teardown(report, "L6")
        level_l3(report)
        level_l4(report)
        level_l5(report)
        teardown(report, "L6-second-start")
    except LifecycleError as error:
        print(error, file=sys.stderr)
        logs = capture_failure_logs()
        if logs:
            print("--- compose logs (redacted) ---", file=sys.stderr)
            print(logs, file=sys.stderr)
        if args.json:
            args.json.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
        return 1
    finally:
        run(compose_cmd("down", "-v", "--remove-orphans"), check=False)

    for step in report.steps:
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
