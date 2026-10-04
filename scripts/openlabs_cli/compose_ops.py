"""Compose helpers with repo-local port overrides."""

from __future__ import annotations

import re
from pathlib import Path

from openlabs_cli.lab_discovery import compose_path

FORBIDDEN_COMPOSE_TOKENS = frozenset({"prune", "system"})


def assert_safe_compose_subcommand(subcommand: list[str]) -> None:
    joined = " ".join(subcommand).lower()
    for token in FORBIDDEN_COMPOSE_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", joined):
            raise ValueError(f"compose subcommand {subcommand!r} is not allowed for OpenLabs lifecycle")


def planned_compose_step(subcommand: list[str]) -> str:
    return "docker compose " + " ".join(subcommand)


def override_path(repo_root: Path, slug: str) -> Path:
    return repo_root / ".openlabs" / "overrides" / f"{slug}.ports.yml"


def write_port_override(
    repo_root: Path,
    *,
    slug: str,
    service: str,
    host_port: int,
    container_port: int,
) -> Path:
    path = override_path(repo_root, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "services:",
                f"  {service}:",
                "    ports:",
                f'      - "127.0.0.1:{host_port}:{container_port}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def primary_service(lab_dir: Path) -> str:
    compose = compose_path(lab_dir)
    if compose is None:
        return "web"
    for line in compose.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and not stripped.startswith(("services:", "version:", "name:")):
            name = stripped[:-1].strip()
            if name and name not in {"services", "networks", "volumes"}:
                return name
    return "web"


def compose_files(repo_root: Path, lab_dir: Path, slug: str, *, host_port: int, container_port: int) -> list[Path]:
    base = compose_path(lab_dir)
    if base is None:
        raise FileNotFoundError("compose file missing")
    service = primary_service(lab_dir)
    override = write_port_override(
        repo_root,
        slug=slug,
        service=service,
        host_port=host_port,
        container_port=container_port,
    )
    return [base, override]


def compose_argv(
    repo_root: Path,
    *,
    lab_dir: Path,
    slug: str,
    project: str,
    host_port: int,
    container_port: int,
    subcommand: list[str],
) -> list[str]:
    assert_safe_compose_subcommand(subcommand)
    files = compose_files(repo_root, lab_dir, slug, host_port=host_port, container_port=container_port)
    argv = ["docker", "compose"]
    for file in files:
        argv.extend(["-f", str(file)])
    argv.extend(["-p", project])
    argv.extend(subcommand)
    return argv


def compose_argv_from_state(
    repo_root: Path,
    *,
    lab_dir: Path,
    state: dict[str, object],
    subcommand: list[str],
) -> list[str]:
    assert_safe_compose_subcommand(subcommand)
    slug = str(state["lab"])
    project = str(state["compose_project"])
    host_port = int(state["host_port"])
    container_port = int(state["container_port"])
    compose_rel = str(state["compose_file"])
    base = repo_root / compose_rel
    if not base.is_file():
        base = compose_path(lab_dir)
    if base is None:
        raise FileNotFoundError("compose file missing")
    override = override_path(repo_root, slug)
    if not override.is_file():
        service = primary_service(lab_dir)
        write_port_override(
            repo_root,
            slug=slug,
            service=service,
            host_port=host_port,
            container_port=container_port,
        )
    argv = ["docker", "compose", "-f", str(base)]
    if override.is_file():
        argv.extend(["-f", str(override)])
    argv.extend(["-p", project])
    argv.extend(subcommand)
    return argv


def planned_setup_steps(*, slug: str, lab_rel: str, compose_file: str, project: str) -> list[str]:
    compose_rel = f"{lab_rel}/{compose_file}"
    return [
        f"write .openlabs/state/{slug}.json",
        f"docker compose -f {compose_rel} -p {project} build",
        f"docker compose -f {compose_rel} -p {project} up -d",
    ]
