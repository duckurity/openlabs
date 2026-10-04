#!/usr/bin/env python3
"""Tests for environment probes and tier classification (M2-05)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.environment_probe import (  # noqa: E402
    ProbeOverrides,
    classify_tier,
    run_environment_probe,
)
from openlabs_cli.runner import CommandResult  # noqa: E402


class _MapRunner:
    def __init__(self, responses: dict[tuple[str, ...], CommandResult]) -> None:
        self.responses = responses

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> CommandResult:
        _ = cwd, timeout
        key = tuple(argv)
        if key in self.responses:
            return self.responses[key]
        return CommandResult(127, "", "command not mocked")


def _ctx(*, port: int | None = None) -> CliContext:
    runner = _MapRunner(
        {
            ("docker", "--version"): CommandResult(0, "Docker version 26.0.0", ""),
            ("docker", "info"): CommandResult(0, "Server:\n Docker Engine", ""),
            ("docker", "compose", "version"): CommandResult(
                0, "Docker Compose version v2.24.0", ""
            ),
            ("git", "--version"): CommandResult(0, "git version 2.43.0", ""),
        }
    )
    return CliContext(repo_root=REPO_ROOT, runner=runner, port=port)


def test_tier1_linux_x86_64() -> None:
    report = run_environment_probe(
        _ctx(),
        overrides=ProbeOverrides(
            system="Linux",
            machine="x86_64",
            wsl=False,
            python_version=(3, 12, 0),
            disk_free_bytes=5_000_000_000,
            memory_available_kb=2_000_000,
        ),
    )
    assert report.tier == "tier1"
    assert report.runtime == "docker"
    assert not report.missing


def test_tier2_wsl() -> None:
    report = run_environment_probe(
        _ctx(),
        overrides=ProbeOverrides(system="Linux", machine="x86_64", wsl=True, python_version=(3, 12, 0)),
    )
    assert report.tier == "tier2"


def test_tier2_macos() -> None:
    report = run_environment_probe(
        _ctx(),
        overrides=ProbeOverrides(system="Darwin", machine="x86_64", wsl=False, python_version=(3, 12, 0)),
    )
    assert report.tier == "tier2"


def test_tier3_arm64() -> None:
    report = run_environment_probe(
        _ctx(),
        overrides=ProbeOverrides(system="Linux", machine="aarch64", wsl=False, python_version=(3, 12, 0)),
    )
    assert report.tier == "tier3"


def test_missing_docker_client() -> None:
    runner = _MapRunner(
        {
            ("docker", "--version"): CommandResult(127, "", "not found"),
            ("git", "--version"): CommandResult(0, "git version 2.43.0", ""),
        }
    )
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    report = run_environment_probe(
        ctx,
        overrides=ProbeOverrides(
            runtime="unknown",
            docker_client="",
            docker_daemon_ok=False,
            compose_version="",
            python_version=(3, 12, 0),
        ),
    )
    assert "docker_client" in report.missing
    keys = [item.diagnostic_key for item in report.checks if item.diagnostic_key]
    assert "environment.docker.client_missing" in keys


def test_daemon_unavailable_separate_from_client() -> None:
    runner = _MapRunner(
        {
            ("docker", "--version"): CommandResult(0, "Docker version 26.0.0", ""),
            ("docker", "info"): CommandResult(1, "", "Cannot connect to the Docker daemon"),
            ("docker", "compose", "version"): CommandResult(1, "", "daemon down"),
            ("git", "--version"): CommandResult(0, "git version 2.43.0", ""),
        }
    )
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    report = run_environment_probe(
        ctx,
        overrides=ProbeOverrides(
            runtime="docker",
            docker_client="Docker version 26.0.0",
            docker_daemon_ok=False,
            compose_version="",
            python_version=(3, 12, 0),
        ),
    )
    assert "docker_client" not in report.missing
    assert "docker_daemon" in report.missing


def test_permission_denied() -> None:
    report = run_environment_probe(
        _ctx(),
        overrides=ProbeOverrides(
            docker_permission_denied=True,
            docker_daemon_ok=False,
            python_version=(3, 12, 0),
        ),
    )
    assert "docker_permission" in report.missing


def test_podman_runtime_unsupported() -> None:
    tier = classify_tier(
        system="Linux",
        machine="x86_64",
        wsl=False,
        python_ok=True,
        docker_client_ok=True,
        compose_ok=True,
        runtime="podman",
    )
    assert tier == "unsupported"


def test_low_disk_and_memory() -> None:
    report = run_environment_probe(
        _ctx(),
        overrides=ProbeOverrides(
            disk_free_bytes=100_000,
            memory_available_kb=100_000,
            python_version=(3, 12, 0),
        ),
    )
    assert "disk" in report.missing
    assert "memory" in report.missing


def test_port_conflict_diagnostic() -> None:
    ctx = _ctx(port=8377)
    report = run_environment_probe(
        ctx,
        overrides=ProbeOverrides(python_version=(3, 12, 0), port_in_use=True),
    )
    assert "port" in report.missing
    keys = [item.diagnostic_key for item in report.checks if item.diagnostic_key]
    assert "lifecycle.port.conflict" in keys


def main() -> int:
    tests = [
        test_tier1_linux_x86_64,
        test_tier2_wsl,
        test_tier2_macos,
        test_tier3_arm64,
        test_missing_docker_client,
        test_daemon_unavailable_separate_from_client,
        test_permission_denied,
        test_podman_runtime_unsupported,
        test_low_disk_and_memory,
        test_port_conflict_diagnostic,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs environment: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs environment: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
