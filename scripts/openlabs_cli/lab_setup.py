"""Supported lab setup transaction (M2-06)."""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from diagnostic_registry import redact_sensitive

from openlabs_cli.compose_ops import compose_argv, planned_setup_steps
from openlabs_cli.context import CliContext
from openlabs_cli.envelope import CliResult, Diagnostic
from openlabs_cli.environment_probe import run_environment_probe
from openlabs_cli.errors import UsageError
from openlabs_cli.lab_discovery import (
    LabSelectionError,
    ResolvedLab,
    compose_path,
    derive_host_port,
    resolve_lab,
)
from openlabs_cli.namespace import compose_project_name
from openlabs_cli.port_policy import resolve_host_port
from openlabs_cli.setup_log import new_run_id, relative_evidence, write_setup_log
from openlabs_cli.state_store import (
    LabLockError,
    build_state_payload,
    lab_lock,
    load_state,
    write_state,
)

CONTAINER_PORT_RE = re.compile(r":(\d{1,5})\s*(?:/(?:tcp|udp))?\s*(?:\"|'|\s|$)")
READY_TIMEOUT_S = 60
POLL_INTERVAL_S = 0.5


def _container_port(lab_dir: Path, *, fallback: int) -> int:
    path = compose_path(lab_dir)
    if path is None:
        return fallback
    for line in path.read_text(encoding="utf-8").splitlines():
        if "ports:" in line or not line.strip().startswith("-"):
            continue
        match = CONTAINER_PORT_RE.search(line)
        if match:
            parts = line.split(":")
            if len(parts) >= 3:
                return int(parts[-1].split("/")[0].strip().strip("\"'"))
    return fallback


def _run(ctx: CliContext, argv: list[str], *, timeout: float = 600.0) -> tuple[int, str]:
    if ctx.runner is None:
        return 127, "runner unavailable"
    result = ctx.runner.run(argv, cwd=ctx.repo_root, timeout=timeout)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, redact_sensitive(output.strip())


def _http_ready(base_url: str) -> bool:
    request = urllib.request.Request(f"{base_url}/", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            body = response.read().decode("utf-8", "replace")
            return response.status == 200 and "duck cross" in body.lower()
    except (OSError, urllib.error.URLError):
        return False


def _wait_ready(base_url: str) -> bool:
    deadline = time.time() + READY_TIMEOUT_S
    while time.time() < deadline:
        if _http_ready(base_url):
            return True
        time.sleep(POLL_INTERVAL_S)
    return False


def _verify_duck_cross(base_url: str) -> tuple[bool, str]:
    if not _http_ready(base_url):
        return False, "player entry page failed"
    try:
        request = urllib.request.Request(f"{base_url}/api/reports/1", method="GET")
        with urllib.request.urlopen(request, timeout=10.0) as response:
            body = response.read().decode("utf-8", "replace")
        if response.status != 200 or "mill lane" not in body.lower():
            return False, "public report workflow failed"
    except (OSError, urllib.error.URLError):
        return False, "public report workflow failed"
    return True, "supported verification passed"


def _fail_setup(
    *,
    slug: str,
    project: str,
    host_port: int | None,
    stages: list[str],
    key: str,
    message: str,
    lifecycle: str = "failed",
    repo_root: Path,
    compose_file: str,
    container_port: int,
    evidence: str | None = None,
) -> CliResult:
    if lifecycle != "unconfigured":
        write_state(
            repo_root,
            build_state_payload(
                slug=slug,
                compose_project=project,
                host_port=host_port or 0,
                lifecycle=lifecycle,
                compose_file=compose_file,
                container_port=container_port,
                evidence_path=evidence,
            ),
        )
    data: dict[str, Any] = {
        "action": "setup",
        "lab": slug,
        "host_port": host_port,
        "completed_stages": stages,
        "next_actions": ["run openlabs lab status", "run openlabs lab reset", "run openlabs lab setup"],
    }
    return CliResult(
        command="lab",
        ok=False,
        exit_code=1,
        data=data,
        diagnostics=[Diagnostic(key, message)],
        human_lines=[message],
    )


def handle_lab_setup(ctx: CliContext, args: list[str]) -> CliResult:
    if len(args) != 1:
        raise UsageError("usage: openlabs lab setup <lab>")
    selection = resolve_lab(ctx.repo_root, args[0])
    if isinstance(selection, LabSelectionError):
        from openlabs_cli.commands.lab import selection_failure

        return selection_failure(selection)
    resolved: ResolvedLab = selection
    entry = resolved.entry
    slug = entry["slug"]
    lab_rel = entry["path"]
    lab_dir = resolved.lab_dir
    compose_file = entry.get("compose_file") or "docker-compose.yml"
    compose_rel = f"{lab_rel}/{compose_file}"

    if entry.get("blockers"):
        if "container_name" in entry["blockers"]:
            return CliResult(
                command="lab",
                ok=False,
                exit_code=1,
                data={"action": "setup", "lab": slug, "blockers": entry["blockers"]},
                diagnostics=[
                    Diagnostic(
                        "lifecycle.compose.unsafe_container_name",
                        "compose file declares container_name; lifecycle mutation blocked",
                    )
                ],
                human_lines=["compose declares container_name; choose a supported lab"],
            )
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "setup", "lab": slug},
            diagnostics=[
                Diagnostic(
                    "lifecycle.lab.unsupported_operation",
                    "lab is experimental or blocked for guaranteed lifecycle setup",
                )
            ],
            human_lines=["lab is not eligible for guaranteed lifecycle setup"],
        )

    if entry.get("status") != "supported":
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "setup", "lab": slug},
            diagnostics=[
                Diagnostic(
                    "lifecycle.lab.unsupported_operation",
                    "only supported labs implement openlabs lab setup in this milestone",
                )
            ],
            human_lines=["only supported labs can run lab setup"],
        )

    project = compose_project_name(ctx.repo_root, slug)
    declared = entry.get("port") or derive_host_port(lab_dir) or 8377
    container_port = _container_port(lab_dir, fallback=int(declared))
    port = resolve_host_port(
        declared_port=int(declared),
        explicit_port=ctx.port,
        allow_dynamic=ctx.port is None,
    )
    if not port.ok:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "setup", "lab": slug, "host_port": declared},
            diagnostics=[Diagnostic(port.error_key or "lifecycle.port.conflict", port.message or "port conflict")],
            human_lines=[port.message or "port conflict"],
        )

    host_port = port.host_port
    planned = planned_setup_steps(
        slug=slug,
        lab_rel=lab_rel,
        compose_file=compose_file,
        project=project,
    )

    if ctx.dry_run:
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "setup",
                "lab": slug,
                "path": lab_rel,
                "project": project,
                "host_port": host_port,
                "planned": planned,
            },
            human_lines=["lab setup dry-run: no state, files, or containers changed"],
            meta={"reset_safe": True},
        )

    existing = load_state(ctx.repo_root, slug)
    if existing and existing.get("lifecycle") == "ready":
        return CliResult(
            command="lab",
            ok=True,
            exit_code=0,
            data={
                "action": "setup",
                "lab": slug,
                "project": project,
                "host_port": existing.get("host_port", host_port),
                "already_ready": True,
                "url": f"http://127.0.0.1:{existing.get('host_port', host_port)}/",
            },
            human_lines=["lab already ready; no changes applied"],
            meta={"reset_safe": True},
        )

    env = run_environment_probe(ctx)
    if env.missing:
        message = "environment preflight failed; run openlabs setup"
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "setup", "lab": slug, "missing": list(env.missing)},
            human_lines=[message],
        )

    stages: list[str] = ["preflight", "resolve"]
    run_id = new_run_id()

    try:
        with lab_lock(ctx.repo_root, slug):
            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=host_port,
                    lifecycle="configured",
                    compose_file=compose_rel,
                    container_port=container_port,
                ),
            )
            stages.append("configure")

            config_argv = compose_argv(
                ctx.repo_root,
                lab_dir=lab_dir,
                slug=slug,
                project=project,
                host_port=host_port,
                container_port=container_port,
                subcommand=["config", "-q"],
            )
            code, detail = _run(ctx, config_argv, timeout=120.0)
            if code != 0:
                log_path = write_setup_log(
                    ctx.repo_root,
                    slug=slug,
                    run_id=run_id,
                    stages=stages,
                    detail=detail,
                )
                _rollback(ctx, lab_dir, slug, project, host_port, container_port)
                return _fail_setup(
                    slug=slug,
                    project=project,
                    host_port=host_port,
                    stages=stages,
                    key="lifecycle.cli.internal",
                    message="compose config failed during lab setup",
                    repo_root=ctx.repo_root,
                    compose_file=compose_rel,
                    container_port=container_port,
                    evidence=relative_evidence(ctx.repo_root, log_path),
                )
            stages.append("compose_validate")

            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=host_port,
                    lifecycle="building",
                    compose_file=compose_rel,
                    container_port=container_port,
                ),
            )
            build_argv = compose_argv(
                ctx.repo_root,
                lab_dir=lab_dir,
                slug=slug,
                project=project,
                host_port=host_port,
                container_port=container_port,
                subcommand=["build", "--pull=false"],
            )
            code, detail = _run(ctx, build_argv, timeout=900.0)
            if code != 0:
                log_path = write_setup_log(
                    ctx.repo_root,
                    slug=slug,
                    run_id=run_id,
                    stages=stages,
                    detail=detail,
                )
                _rollback(ctx, lab_dir, slug, project, host_port, container_port)
                return _fail_setup(
                    slug=slug,
                    project=project,
                    host_port=host_port,
                    stages=stages,
                    key="lifecycle.state.interrupted",
                    message="previous lab setup stopped mid-build; run lab status then lab reset or lab setup",
                    lifecycle="building",
                    repo_root=ctx.repo_root,
                    compose_file=compose_rel,
                    container_port=container_port,
                    evidence=relative_evidence(ctx.repo_root, log_path),
                )
            stages.append("build")

            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=host_port,
                    lifecycle="starting",
                    compose_file=compose_rel,
                    container_port=container_port,
                ),
            )
            up_argv = compose_argv(
                ctx.repo_root,
                lab_dir=lab_dir,
                slug=slug,
                project=project,
                host_port=host_port,
                container_port=container_port,
                subcommand=["up", "-d"],
            )
            code, detail = _run(ctx, up_argv, timeout=300.0)
            if code != 0:
                log_path = write_setup_log(
                    ctx.repo_root,
                    slug=slug,
                    run_id=run_id,
                    stages=stages,
                    detail=detail,
                )
                _rollback(ctx, lab_dir, slug, project, host_port, container_port)
                return _fail_setup(
                    slug=slug,
                    project=project,
                    host_port=host_port,
                    stages=stages,
                    key="lifecycle.cli.internal",
                    message="compose up failed during lab setup",
                    repo_root=ctx.repo_root,
                    compose_file=compose_rel,
                    container_port=container_port,
                    evidence=relative_evidence(ctx.repo_root, log_path),
                )
            stages.append("start")

            base_url = f"http://127.0.0.1:{host_port}"
            if not _wait_ready(base_url):
                log_path = write_setup_log(
                    ctx.repo_root,
                    slug=slug,
                    run_id=run_id,
                    stages=stages,
                    detail="readiness timeout",
                )
                _rollback(ctx, lab_dir, slug, project, host_port, container_port)
                return _fail_setup(
                    slug=slug,
                    project=project,
                    host_port=host_port,
                    stages=stages,
                    key="lifecycle.cli.internal",
                    message="lab service did not become ready in time",
                    repo_root=ctx.repo_root,
                    compose_file=compose_rel,
                    container_port=container_port,
                    evidence=relative_evidence(ctx.repo_root, log_path),
                )
            stages.append("readiness")

            ok_verify, verify_detail = _verify_duck_cross(base_url)
            if not ok_verify:
                log_path = write_setup_log(
                    ctx.repo_root,
                    slug=slug,
                    run_id=run_id,
                    stages=stages,
                    detail=verify_detail,
                )
                _rollback(ctx, lab_dir, slug, project, host_port, container_port)
                return _fail_setup(
                    slug=slug,
                    project=project,
                    host_port=host_port,
                    stages=stages,
                    key="lifecycle.cli.internal",
                    message=verify_detail,
                    repo_root=ctx.repo_root,
                    compose_file=compose_rel,
                    container_port=container_port,
                    evidence=relative_evidence(ctx.repo_root, log_path),
                )
            stages.append("verify")

            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=host_port,
                    lifecycle="ready",
                    compose_file=compose_rel,
                    container_port=container_port,
                ),
            )
    except LabLockError as exc:
        return CliResult(
            command="lab",
            ok=False,
            exit_code=1,
            data={"action": "setup", "lab": slug},
            diagnostics=[Diagnostic("lifecycle.cli.internal", str(exc))],
            human_lines=[str(exc)],
        )

    url = f"http://127.0.0.1:{host_port}/"
    human = [
        f"lab {slug} is ready at {url}",
        f"compose project {project}",
    ]
    if port.dynamic:
        human.append(f"host port {host_port} selected because {declared} was busy")
    return CliResult(
        command="lab",
        ok=True,
        exit_code=0,
        data={
            "action": "setup",
            "lab": slug,
            "path": lab_rel,
            "project": project,
            "host_port": host_port,
            "url": url,
            "completed_stages": stages,
        },
        human_lines=human,
        meta={"reset_safe": True},
    )


def _rollback(
    ctx: CliContext,
    lab_dir: Path,
    slug: str,
    project: str,
    host_port: int,
    container_port: int,
) -> None:
    argv = compose_argv(
        ctx.repo_root,
        lab_dir=lab_dir,
        slug=slug,
        project=project,
        host_port=host_port,
        container_port=container_port,
        subcommand=["down", "--remove-orphans"],
    )
    _run(ctx, argv, timeout=120.0)
