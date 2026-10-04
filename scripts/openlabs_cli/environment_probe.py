"""Environment and platform probes for setup and doctor."""

from __future__ import annotations

import platform
import re
import shutil
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

from diagnostic_registry import redact_sensitive

from openlabs_cli.context import CliContext

OUTPUT_LIMIT = 512
MIN_DISK_BYTES = 1_000_000_000
MIN_MEMORY_KB = 512_000
PYTHON_MIN = (3, 12)


def compose_probe_ok(*, exit_code: int, text: str) -> bool:
    if exit_code != 0 or not text.strip():
        return False
    if re.search(r"v2|version 2", text, re.I):
        return True
    match = re.search(r"Docker Compose version v?(?P<major>\d+)", text, re.I)
    return bool(match and int(match.group("major")) >= 2)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    diagnostic_key: str | None = None
    guidance: str | None = None


@dataclass(frozen=True)
class EnvironmentReport:
    checks: tuple[CheckResult, ...]
    tier: str
    runtime: str
    missing: tuple[str, ...]
    guidance: tuple[str, ...]


@dataclass
class ProbeOverrides:
    system: str | None = None
    machine: str | None = None
    release: str | None = None
    python_version: tuple[int, int, int] | None = None
    wsl: bool | None = None
    git_ok: bool | None = None
    docker_client: str | None = None
    docker_daemon_ok: bool | None = None
    docker_permission_denied: bool | None = None
    compose_version: str | None = None
    runtime: str | None = None
    disk_free_bytes: int | None = None
    memory_available_kb: int | None = None
    port_in_use: bool | None = None


def _clip(text: str) -> str:
    cleaned = redact_sensitive(text.strip())
    if len(cleaned) <= OUTPUT_LIMIT:
        return cleaned
    return cleaned[: OUTPUT_LIMIT - 3] + "..."


def _run(ctx: CliContext, argv: list[str], *, timeout: float = 5.0) -> tuple[int, str, str]:
    if ctx.runner is None:
        return 127, "", "runner unavailable"
    result = ctx.runner.run(argv, cwd=ctx.repo_root, timeout=timeout)
    return result.returncode, _clip(result.stdout), _clip(result.stderr)


def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def detect_runtime(ctx: CliContext, overrides: ProbeOverrides | None) -> str:
    if overrides and overrides.runtime is not None:
        return overrides.runtime
    code, out, err = _run(ctx, ["docker", "info"])
    merged = f"{out}\n{err}".lower()
    if "podman" in merged:
        return "podman"
    client_code, _client_out, _client_err = _run(ctx, ["docker", "--version"])
    if client_code == 0:
        return "docker"
    code, out, _err = _run(ctx, ["podman", "--version"])
    if code == 0 and out:
        return "podman"
    return "unknown"


def classify_tier(
    *,
    system: str,
    machine: str,
    wsl: bool,
    python_ok: bool,
    docker_client_ok: bool,
    compose_ok: bool,
    runtime: str,
) -> str:
    if runtime == "podman":
        return "unsupported"
    normalized = machine.lower()
    arm = normalized in {"aarch64", "arm64", "armv8", "armv7l"}
    if system == "Darwin" or wsl:
        return "tier2"
    if arm:
        return "tier3"
    if (
        system == "Linux"
        and normalized in {"x86_64", "amd64"}
        and python_ok
        and docker_client_ok
        and compose_ok
    ):
        return "tier1"
    if runtime == "docker" and compose_ok:
        return "tier2"
    return "unsupported"


def guidance_for_missing(name: str, *, system: str, wsl: bool) -> str:
    if name == "docker_client":
        if system == "Darwin":
            return "Install Docker Desktop for macOS, then re-run openlabs setup."
        if wsl:
            return "Install Docker Desktop with WSL integration enabled, then re-run openlabs setup."
        return "Install Docker Engine and ensure the docker binary is on PATH."
    if name == "docker_daemon":
        if system == "Darwin" or wsl:
            return "Start Docker Desktop and wait until docker info succeeds."
        return "Start the Docker daemon (system service) and retry."
    if name == "docker_permission":
        return "Add your user to the docker group or use a rootless Docker setup; do not use sudo with openlabs."
    if name == "compose":
        return "Install Docker Compose v2 (docker compose plugin) and retry."
    if name == "git":
        return "Install Git and ensure git is on PATH."
    if name == "python":
        return "Use Python 3.12 or newer to match Tier 1 CI expectations."
    if name == "disk":
        return "Free at least 1 GiB on the filesystem that holds this repository."
    if name == "memory":
        return "Close other workloads; OpenLabs needs roughly 512 MiB of available memory."
    if name == "port":
        return "Stop the service using the requested port or pass --port with a free value."
    return "Review openlabs doctor output and fix the reported prerequisite."


def run_environment_probe(
    ctx: CliContext,
    *,
    overrides: ProbeOverrides | None = None,
) -> EnvironmentReport:
    ov = overrides or ProbeOverrides()
    system = ov.system or platform.system() or "unknown"
    machine = ov.machine or platform.machine() or "unknown"
    release = ov.release or platform.release() or "unknown"
    py = ov.python_version or sys.version_info[:3]
    wsl = ov.wsl if ov.wsl is not None else is_wsl()

    checks: list[CheckResult] = []
    missing: list[str] = []
    guidance: list[str] = []

    checks.append(
        CheckResult(
            name="repo_root",
            ok=True,
            detail=redact_sensitive(str(ctx.repo_root.resolve())),
        )
    )
    checks.append(
        CheckResult(
            name="os",
            ok=True,
            detail=f"{system} {release} ({machine})",
        )
    )

    python_ok = py >= PYTHON_MIN
    checks.append(
        CheckResult(
            name="python",
            ok=python_ok,
            detail=f"{py[0]}.{py[1]}.{py[2]}",
            guidance=None if python_ok else guidance_for_missing("python", system=system, wsl=wsl),
        )
    )
    if not python_ok:
        missing.append("python")

    if ov.git_ok is None:
        git_code, git_out, _git_err = _run(ctx, ["git", "--version"])
        git_ok = git_code == 0
        git_detail = git_out or "git unavailable"
    else:
        git_ok = ov.git_ok
        git_detail = "git available" if git_ok else "git unavailable"
    checks.append(
        CheckResult(
            name="git",
            ok=git_ok,
            detail=git_detail,
            guidance=None if git_ok else guidance_for_missing("git", system=system, wsl=wsl),
        )
    )
    if not git_ok:
        missing.append("git")

    runtime = detect_runtime(ctx, ov)
    checks.append(
        CheckResult(
            name="runtime",
            ok=runtime == "docker",
            detail=runtime,
            diagnostic_key=None if runtime == "docker" else None,
            guidance=(
                None
                if runtime == "docker"
                else "OpenLabs targets Docker Engine or Docker Desktop; Podman is detection-only."
            ),
        )
    )
    if runtime not in {"docker"}:
        missing.append("docker_runtime")

    if ov.docker_client is None:
        client_code, client_out, client_err = _run(ctx, ["docker", "--version"])
        client_ok = client_code == 0 and bool(client_out or client_err)
        client_detail = client_out or client_err or "docker client missing"
    else:
        client_ok = bool(ov.docker_client)
        client_detail = ov.docker_client or "docker client missing"
    checks.append(
        CheckResult(
            name="docker_client",
            ok=client_ok,
            detail=client_detail,
            diagnostic_key=None if client_ok else "environment.docker.client_missing",
            guidance=None if client_ok else guidance_for_missing("docker_client", system=system, wsl=wsl),
        )
    )
    if not client_ok:
        missing.append("docker_client")

    permission_denied = False
    if ov.docker_permission_denied is not None:
        permission_denied = ov.docker_permission_denied
    elif client_ok:
        _info_code, _info_out, info_err = _run(ctx, ["docker", "info"])
        permission_denied = "permission denied" in info_err.lower()

    daemon_ok = False
    daemon_detail = "daemon not checked"
    daemon_key = None
    if ov.docker_daemon_ok is not None:
        daemon_ok = ov.docker_daemon_ok
        daemon_detail = "docker daemon reachable" if daemon_ok else "docker daemon unavailable"
        if not daemon_ok and not permission_denied:
            daemon_key = "environment.docker.daemon_unavailable"
    elif client_ok and not permission_denied:
        info_code, _info_out, info_err = _run(ctx, ["docker", "info"])
        daemon_ok = info_code == 0
        daemon_detail = "docker daemon reachable" if daemon_ok else _clip(info_err or "docker info failed")
        if not daemon_ok:
            daemon_key = "environment.docker.daemon_unavailable"
    elif permission_denied:
        daemon_detail = "docker permission denied"
    checks.append(
        CheckResult(
            name="docker_daemon",
            ok=daemon_ok and not permission_denied,
            detail=daemon_detail,
            diagnostic_key=daemon_key,
            guidance=(
                guidance_for_missing("docker_permission", system=system, wsl=wsl)
                if permission_denied
                else (
                    None
                    if daemon_ok
                    else guidance_for_missing("docker_daemon", system=system, wsl=wsl)
                )
            ),
        )
    )
    if permission_denied:
        missing.append("docker_permission")
        checks.append(
            CheckResult(
                name="docker_permission",
                ok=False,
                detail="permission denied while contacting docker",
                guidance=guidance_for_missing("docker_permission", system=system, wsl=wsl),
            )
        )
    elif not daemon_ok and client_ok:
        missing.append("docker_daemon")

    if ov.compose_version is None:
        compose_code, compose_out, compose_err = _run(ctx, ["docker", "compose", "version"])
        compose_text = compose_out or compose_err
        compose_ok = compose_probe_ok(exit_code=compose_code, text=compose_text)
        compose_detail = _clip(compose_text) if compose_text else "compose unavailable"
    else:
        compose_text = ov.compose_version
        compose_ok = compose_probe_ok(exit_code=0, text=compose_text)
        compose_detail = _clip(compose_text)
    checks.append(
        CheckResult(
            name="compose",
            ok=compose_ok,
            detail=compose_detail,
            guidance=None if compose_ok else guidance_for_missing("compose", system=system, wsl=wsl),
        )
    )
    if not compose_ok:
        missing.append("compose")

    if ov.disk_free_bytes is None:
        disk_free = shutil.disk_usage(ctx.repo_root).free
    else:
        disk_free = ov.disk_free_bytes
    disk_ok = disk_free >= MIN_DISK_BYTES
    checks.append(
        CheckResult(
            name="disk",
            ok=disk_ok,
            detail=f"{disk_free // (1024 * 1024)} MiB free",
            guidance=None if disk_ok else guidance_for_missing("disk", system=system, wsl=wsl),
        )
    )
    if not disk_ok:
        missing.append("disk")

    mem_kb = ov.memory_available_kb
    if mem_kb is None:
        mem_kb = _memory_available_kb()
    mem_ok = mem_kb is None or mem_kb >= MIN_MEMORY_KB
    mem_detail = "unknown" if mem_kb is None else f"{mem_kb // 1024} MiB available"
    checks.append(
        CheckResult(
            name="memory",
            ok=mem_ok,
            detail=mem_detail,
            guidance=None if mem_ok else guidance_for_missing("memory", system=system, wsl=wsl),
        )
    )
    if not mem_ok:
        missing.append("memory")

    port_ok = True
    if ctx.port is not None:
        if ov.port_in_use is None:
            port_ok = not _local_port_open(ctx.port)
        else:
            port_ok = not ov.port_in_use
        checks.append(
            CheckResult(
                name="port",
                ok=port_ok,
                detail=f"127.0.0.1:{ctx.port}",
                diagnostic_key=None if port_ok else "lifecycle.port.conflict",
                guidance=None if port_ok else guidance_for_missing("port", system=system, wsl=wsl),
            )
        )
        if not port_ok:
            missing.append("port")

    for item in checks:
        if item.guidance and item.guidance not in guidance:
            guidance.append(item.guidance)

    tier = classify_tier(
        system=system,
        machine=machine,
        wsl=wsl,
        python_ok=python_ok,
        docker_client_ok=client_ok,
        compose_ok=compose_ok,
        runtime=runtime,
    )
    if tier == "tier3":
        checks = list(checks) + [
            CheckResult(
                name="tier",
                ok=True,
                detail="tier3",
                guidance="Tier 3 hosts need per-lab evidence; guaranteed duck-cross lifecycle targets Tier 1 Linux x86_64.",
            )
        ]
    return EnvironmentReport(
        checks=tuple(checks),
        tier=tier,
        runtime=runtime,
        missing=tuple(dict.fromkeys(missing)),
        guidance=tuple(guidance),
    )


def _memory_available_kb() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _local_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def checks_payload(report: EnvironmentReport) -> list[dict[str, object]]:
    return [{"name": item.name, "ok": item.ok} for item in report.checks]


def diagnostics_from_report(report: EnvironmentReport) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for check in report.checks:
        if check.ok or not check.diagnostic_key:
            continue
        message = check.detail or check.name
        items.append((check.diagnostic_key, message))
    return items
