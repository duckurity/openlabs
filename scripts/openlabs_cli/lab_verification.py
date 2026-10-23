"""Shared L0-L6 lab verification engine (M2-08)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from diagnostic_registry import redact_sensitive
from openlabs_contract import legacy_string_map, load_lab_metadata

from openlabs_cli.compose_ops import compose_argv, compose_argv_from_state
from openlabs_cli.context import CliContext
from openlabs_cli.lab_discovery import ResolvedLab, derive_host_port
from openlabs_cli.lab_runtime import run_compose, wait_ready
from openlabs_cli.namespace import compose_project_name
from openlabs_cli.port_policy import resolve_host_port
from openlabs_cli.state_store import build_state_payload, load_state, write_state
from openlabs_cli.verification import adapters
from validate import check_compose, check_lab

REQUIRED_FILES = ("lab.yml", "README.md", "docker-compose.yml", "Dockerfile")
CONTAINER_PORT_RE = re.compile(r":(\d{1,5})\s*(?:/(?:tcp|udp))?\s*(?:\"|'|\s|$)")


@dataclass(frozen=True)
class ReferenceVerificationOptions:
    project: str = "openlabs-ref-duck-cross"
    host_port: int = 8377
    teardown_volumes: bool = True
    second_teardown_level: str = "L6-second-start"


@dataclass
class VerificationReport:
    lab: str
    project: str
    port: int
    levels: list[dict[str, Any]] = field(default_factory=list)
    resources_created: list[str] = field(default_factory=list)
    resources_removed: list[str] = field(default_factory=list)
    docker_version: str = ""
    compose_version: str = ""
    failed_level: str | None = None

    def add_level(self, level: str, ok: bool, started: float, detail: str = "") -> None:
        self.levels.append(
            {
                "level": level,
                "ok": ok,
                "seconds": round(time.time() - started, 2),
                "detail": redact_sensitive(detail),
            }
        )


class VerificationFailure(Exception):
    def __init__(self, level: str, detail: str, report: VerificationReport) -> None:
        super().__init__(f"{level} failed: {detail}")
        self.level = level
        self.detail = detail
        self.report = report


def _container_port(lab_dir: Path, *, fallback: int) -> int:
    compose = lab_dir / "docker-compose.yml"
    if not compose.is_file():
        return fallback
    for line in compose.read_text(encoding="utf-8").splitlines():
        if "ports:" in line or not line.strip().startswith("-"):
            continue
        match = CONTAINER_PORT_RE.search(line)
        if match:
            parts = line.split(":")
            if len(parts) >= 3:
                return int(parts[-1].split("/")[0].strip().strip("\"'"))
    return fallback


def _capture_tool_versions(ctx: CliContext) -> tuple[str, str]:
    if ctx.runner is None:
        return "", ""
    docker = ctx.runner.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        cwd=ctx.repo_root,
        timeout=30.0,
    )
    compose = ctx.runner.run(
        ["docker", "compose", "version", "--short"],
        cwd=ctx.repo_root,
        timeout=30.0,
    )
    return (docker.stdout or "").strip(), (compose.stdout or "").strip()


def ensure_configured_state(ctx: CliContext, resolved: ResolvedLab) -> dict[str, Any]:
    slug = resolved.entry["slug"]
    existing = load_state(ctx.repo_root, slug)
    if existing:
        return existing
    entry = resolved.entry
    lab_dir = resolved.lab_dir
    lab_rel = entry["path"]
    compose_file = entry.get("compose_file") or "docker-compose.yml"
    compose_rel = f"{lab_rel}/{compose_file}"
    project = compose_project_name(ctx.repo_root, slug)
    declared = entry.get("port") or derive_host_port(lab_dir) or 8377
    container_port = _container_port(lab_dir, fallback=int(declared))
    port = resolve_host_port(
        declared_port=int(declared),
        explicit_port=ctx.port,
        allow_dynamic=ctx.port is None,
    )
    if not port.ok:
        raise VerificationFailure(
            "L0",
            port.message or "port conflict",
            VerificationReport(lab=slug, project=project, port=int(declared)),
        )
    payload = build_state_payload(
        slug=slug,
        compose_project=project,
        host_port=port.host_port,
        lifecycle="configured",
        compose_file=compose_rel,
        container_port=container_port,
    )
    write_state(ctx.repo_root, payload)
    return payload


def _compose_argv(
    ctx: CliContext,
    resolved: ResolvedLab,
    state: dict[str, Any],
    subcommand: list[str],
    *,
    reference: ReferenceVerificationOptions | None,
) -> list[str]:
    lab_dir = resolved.lab_dir
    slug = resolved.entry["slug"]
    if reference is not None:
        declared = int(resolved.entry.get("port") or derive_host_port(lab_dir) or reference.host_port)
        container_port = _container_port(lab_dir, fallback=declared)
        return compose_argv(
            ctx.repo_root,
            lab_dir=lab_dir,
            slug=slug,
            project=reference.project,
            host_port=reference.host_port,
            container_port=container_port,
            subcommand=subcommand,
        )
    return compose_argv_from_state(
        ctx.repo_root,
        lab_dir=lab_dir,
        state=state,
        subcommand=subcommand,
    )


def _list_project_resources(ctx: CliContext, argv_prefix: list[str]) -> list[str]:
    argv = [*argv_prefix, "ps", "-a", "--format", "{{.Name}}"]
    code, out = run_compose(ctx, argv, timeout=30.0)
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _record_fail(report: VerificationReport, level: str, started: float, detail: str) -> None:
    report.failed_level = level
    report.add_level(level, False, started, detail)
    raise VerificationFailure(level, detail, report)


def _maybe_stop(report: VerificationReport, stop_after: str | None, level: str) -> bool:
    return stop_after is not None and stop_after == level


def _run_l4_l5(
    ctx: CliContext,
    report: VerificationReport,
    resolved: ResolvedLab,
    *,
    slug: str,
    lab_dir: Path,
    host_port: int,
    stop_after: str | None,
) -> bool:
    base_url = f"http://127.0.0.1:{host_port}"
    started = time.time()
    ok_l4, detail_l4 = adapters.smoke_l4(slug, base_url)
    if not ok_l4:
        _record_fail(report, "L4", started, detail_l4)
    report.add_level("L4", True, started, detail_l4)
    if _maybe_stop(report, stop_after, "L4"):
        return True

    if not adapters.has_supported_l5(slug):
        _record_fail(report, "L5", time.time(), "no supported intended-solve adapter for this lab")
    started = time.time()
    ok_l5, detail_l5 = adapters.intended_l5(slug, base_url, lab_dir)
    if not ok_l5:
        _record_fail(report, "L5", started, detail_l5)
    report.add_level("L5", True, started, detail_l5)
    return _maybe_stop(report, stop_after, "L5")


def run_verification(
    ctx: CliContext,
    resolved: ResolvedLab,
    *,
    stop_after: str | None = None,
    reference: ReferenceVerificationOptions | None = None,
    include_second_cycle: bool = True,
    allow_experimental: bool = False,
) -> VerificationReport:
    entry = resolved.entry
    slug = entry["slug"]
    lab_dir = resolved.lab_dir
    lab_rel = entry["path"]
    compose_file = entry.get("compose_file") or "docker-compose.yml"
    compose_path = lab_dir / compose_file

    state: dict[str, Any]
    if reference is not None:
        project = reference.project
        host_port = reference.host_port
        state = {}
    else:
        state = ensure_configured_state(ctx, resolved)
        project = str(state["compose_project"])
        host_port = int(state["host_port"])

    report = VerificationReport(lab=slug, project=project, port=host_port)
    report.docker_version, report.compose_version = _capture_tool_versions(ctx)

    def argv(subcommand: list[str]) -> list[str]:
        return _compose_argv(ctx, resolved, state, subcommand, reference=reference)

    if not allow_experimental:
        down_pre = ["down", "--remove-orphans"]
        if reference and reference.teardown_volumes:
            down_pre.append("--volumes")
        run_compose(ctx, argv(down_pre), timeout=300.0)

    started = time.time()
    missing = [name for name in REQUIRED_FILES if not (lab_dir / name).is_file()]
    if missing:
        _record_fail(report, "L0", started, f"missing files: {', '.join(missing)}")
    errors = check_lab(lab_dir)
    if errors:
        _record_fail(report, "L0", started, "; ".join(errors))
    meta_result = load_lab_metadata(lab_dir / "lab.yml")
    if meta_result.record is None:
        _record_fail(report, "L0", started, "lab.yml failed metadata parse")
    meta = legacy_string_map(meta_result.record)
    if not allow_experimental:
        if meta.get("status") != "supported":
            _record_fail(report, "L0", started, "lab.yml status must be supported for reference proof")
    if meta.get("name") != slug:
        _record_fail(report, "L0", started, "unexpected lab name")
    detail_l0 = "metadata valid" if allow_experimental else "metadata and required files valid"
    report.add_level("L0", True, started, detail_l0)
    if _maybe_stop(report, stop_after, "L0"):
        return report

    started = time.time()
    error = check_compose(compose_path, lab_dir)
    if error:
        _record_fail(report, "L1", started, error)
    if not allow_experimental:
        code, rendered = run_compose(ctx, argv(["config"]), timeout=120.0)
        if code != 0:
            _record_fail(report, "L1", started, rendered or "compose config failed")
        if str(host_port) not in rendered:
            _record_fail(report, "L1", started, f"compose config missing port {host_port}")
    report.add_level("L1", True, started, "compose renders with player port")
    if _maybe_stop(report, stop_after, "L1") or allow_experimental:
        return report

    started = time.time()
    code, detail = run_compose(ctx, argv(["build", "--pull=false"]), timeout=900.0)
    if code != 0:
        _record_fail(report, "L2", started, detail or "image build failed")
    report.add_level("L2", True, started, "image build succeeded")
    if _maybe_stop(report, stop_after, "L2"):
        return report

    started = time.time()
    code, detail = run_compose(ctx, argv(["up", "-d"]), timeout=300.0)
    if code != 0:
        _record_fail(report, "L3", started, detail or "compose up failed")
    base_url = f"http://127.0.0.1:{host_port}"
    if not wait_ready(base_url):
        _record_fail(report, "L3", started, f"service not ready within timeout at {base_url}")
    report.resources_created = _list_project_resources(ctx, argv([]))
    report.add_level("L3", True, started, f"ready at {base_url}")
    if _maybe_stop(report, stop_after, "L3"):
        return report

    if _run_l4_l5(
        ctx,
        report,
        resolved,
        slug=slug,
        lab_dir=lab_dir,
        host_port=host_port,
        stop_after=stop_after,
    ):
        return report

    def teardown(label: str) -> None:
        started_l6 = time.time()
        down = ["down", "--remove-orphans"]
        if reference and reference.teardown_volumes:
            down.append("--volumes")
        code, down_detail = run_compose(ctx, argv(down), timeout=300.0)
        if code != 0:
            _record_fail(report, label, started_l6, down_detail or "compose down failed")
        remaining = _list_project_resources(ctx, argv([]))
        if remaining:
            _record_fail(report, label, started_l6, f"leftover resources: {', '.join(remaining)}")
        report.resources_removed.extend(report.resources_created)
        report.resources_created = []
        report.add_level(label, True, started_l6, "compose down removed namespaced resources")
        if not reference and state:
            write_state(
                ctx.repo_root,
                build_state_payload(
                    slug=slug,
                    compose_project=project,
                    host_port=host_port,
                    lifecycle="configured",
                    compose_file=str(state.get("compose_file") or f"{lab_rel}/{compose_file}"),
                    container_port=int(
                        state.get("container_port") or _container_port(lab_dir, fallback=host_port)
                    ),
                ),
            )

    teardown("L6")
    if _maybe_stop(report, stop_after, "L6") or not include_second_cycle:
        return report

    second_teardown = reference.second_teardown_level if reference else "L6"
    started = time.time()
    code, detail = run_compose(ctx, argv(["up", "-d"]), timeout=300.0)
    if code != 0:
        _record_fail(report, "L3", started, detail or "compose up failed on second start")
    if not wait_ready(base_url):
        _record_fail(report, "L3", started, "second start did not reach readiness")
    report.resources_created = _list_project_resources(ctx, argv([]))
    report.add_level("L3", True, started, f"ready at {base_url} after reset")
    if _maybe_stop(report, stop_after, "L3"):
        return report

    if _run_l4_l5(
        ctx,
        report,
        resolved,
        slug=slug,
        lab_dir=lab_dir,
        host_port=host_port,
        stop_after=stop_after,
    ):
        return report

    teardown(second_teardown)
    return report


def reference_teardown(
    ctx: CliContext,
    resolved: ResolvedLab,
    reference: ReferenceVerificationOptions,
) -> None:
    argv = _compose_argv(
        ctx,
        resolved,
        {},
        ["down", "--remove-orphans", "--volumes"],
        reference=reference,
    )
    run_compose(ctx, argv, timeout=300.0)


def capture_failure_logs(
    ctx: CliContext,
    resolved: ResolvedLab,
    *,
    reference: ReferenceVerificationOptions | None,
    state: dict[str, Any] | None = None,
) -> str:
    if state is None and reference is None:
        state = load_state(ctx.repo_root, resolved.entry["slug"]) or {}
    argv = _compose_argv(
        ctx,
        resolved,
        state or {},
        ["logs", "--no-color"],
        reference=reference,
    )
    code, out = run_compose(ctx, argv, timeout=60.0)
    _ = code
    return redact_sensitive(out)
