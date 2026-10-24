"""Scoped SealDesk lifecycle and checker-digest helpers."""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Mapping, Sequence
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

LAB_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = LAB_ROOT / "docker-compose.yml"
LAB_METADATA = LAB_ROOT / "lab.yml"
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_CONTAINER_ID = re.compile(r"[0-9a-f]{12,64}\Z")
_HASH_LINE = re.compile(
    rb"(?m)^(flag_hash:[ \t]*)([0-9a-f]{64})([ \t]*(?:\#[^\r\n]*)?)(\r?)$"
)


class OperatorError(RuntimeError):
    """A safe local operation could not be completed or verified."""


def compose_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Remove ambient Compose and daemon selectors from child process config."""
    environment = os.environ if source is None else source
    blocked = {"DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}
    cleaned = {
        key: value
        for key, value in environment.items()
        if not key.startswith("COMPOSE_") and key not in blocked
    }
    cleaned["COMPOSE_DISABLE_ENV_FILE"] = "1"
    return cleaned


def parse_flag_hash_output(output: str) -> str:
    """Accept only the non-secret checker digest emitted by app.state."""
    try:
        payload = json.loads(output)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("The local runtime returned an invalid checker digest.") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != {"flag_hash"}
        or not isinstance(payload["flag_hash"], str)
        or not _HASH.fullmatch(payload["flag_hash"])
    ):
        raise ValueError("The local runtime returned an invalid checker digest.")
    return payload["flag_hash"]


def require_current_flag_hash(metadata_digest: str, runtime_digest: str) -> None:
    """Refuse lifecycle writes when checker metadata does not match live state."""
    if (
        not isinstance(metadata_digest, str)
        or not isinstance(runtime_digest, str)
        or not _HASH.fullmatch(metadata_digest)
        or not _HASH.fullmatch(runtime_digest)
    ):
        raise OperatorError("The local checker digest is invalid; no lifecycle change was made.")
    if not hmac.compare_digest(metadata_digest, runtime_digest):
        raise OperatorError("The checker digest is stale; synchronize it before resetting.")


def update_flag_hash(path: Path, digest: str) -> bool:
    """Atomically update exactly one metadata digest while preserving file style."""
    if not isinstance(digest, str) or not _HASH.fullmatch(digest):
        raise ValueError("Expected one lowercase SHA-256 flag digest.")
    metadata = Path(path)
    original = metadata.read_bytes()
    field_count = len(re.findall(rb"(?m)^flag_hash:", original))
    matches = list(_HASH_LINE.finditer(original))
    if field_count != 1 or len(matches) != 1:
        raise ValueError("lab.yml must contain exactly one valid flag_hash field.")
    match = matches[0]
    updated = (
        original[:match.start(2)]
        + digest.encode("ascii")
        + original[match.end(2):]
    )
    if updated == original:
        return False

    old_mode = stat.S_IMODE(metadata.stat().st_mode)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=metadata.parent, prefix=".sealdesk-", suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, old_mode)
        os.replace(temporary, metadata)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def _tmpfs_matches(identity: dict[str, object], service: str) -> bool:
    if not isinstance(service, str) or service not in {"sealdesk", "ingress"}:
        return False
    options = "rw,noexec,nosuid,nodev,size=16m,uid=10001,gid=10001,mode=0700"
    expected = (
        {"/run/sealdesk": options, "/tmp": options}
        if service == "sealdesk"
        else {"/tmp": options}
    )
    tmpfs = identity.get("tmpfs")
    if not isinstance(tmpfs, dict) or set(tmpfs) != set(expected):
        return False
    if any(
        not isinstance(value, str)
        or len(value.split(",")) != len(expected[path].split(","))
        or set(value.split(",")) != set(expected[path].split(","))
        for path, value in tmpfs.items()
    ):
        return False

    mounts = identity.get("mounts")
    if not isinstance(mounts, list) or len(mounts) > len(expected):
        return False
    expected_mounts = {("tmpfs", path, True) for path in expected}
    actual_mounts = set()
    for mount in mounts:
        if not isinstance(mount, dict):
            return False
        mount_type = mount.get("type")
        destination = mount.get("destination")
        if not isinstance(mount_type, str) or not isinstance(destination, str):
            return False
        if mount.get("rw") is not True:
            return False
        actual_mounts.add((mount_type, destination, True))
    return len(actual_mounts) == len(mounts) and actual_mounts.issubset(expected_mounts)


def is_owned_container(identity: object, service: str) -> bool:
    """Validate one hardened service without assuming the stack topology."""
    if not isinstance(identity, dict) or not isinstance(service, str):
        return False
    if service not in {"sealdesk", "ingress"}:
        return False
    labels = identity.get("labels")
    ports = identity.get("ports")
    container_id = identity.get("container_id")
    if (
        not isinstance(labels, dict)
        or labels.get("org.openlabs.lab") != "sealdesk"
        or labels.get("com.docker.compose.project") != "sealdesk"
        or labels.get("com.docker.compose.service") != service
        or not isinstance(container_id, str)
        or not _CONTAINER_ID.fullmatch(container_id)
        or not isinstance(ports, dict)
        or set(ports) != {"8000/tcp"}
    ):
        return False

    bindings = ports["8000/tcp"]
    if service == "sealdesk":
        expected_bindings = bindings in (None, [])
        expected_image = "sealdesk:local"
        expected_networks = {"sealdesk_default"}
        expected_memory, expected_cpus = 268435456, 1000000000
    else:
        expected_bindings = bindings == [
            {"HostIp": "127.0.0.1", "HostPort": "8080"}
        ]
        expected_image = "sealdesk-ingress:local"
        expected_networks = {"sealdesk_default", "sealdesk_ingress"}
        expected_memory, expected_cpus = 67108864, 250000000

    network_names = identity.get("network_names")
    if (
        not expected_bindings
        or identity.get("image") != expected_image
        or not isinstance(network_names, list)
        or any(not isinstance(name, str) for name in network_names)
        or len(network_names) != len(set(network_names))
        or set(network_names) != expected_networks
        or not isinstance(identity.get("network_mode"), str)
        or identity.get("network_mode") not in expected_networks
        or not _tmpfs_matches(identity, service)
    ):
        return False

    cap_drop = identity.get("cap_drop")
    cap_add = identity.get("cap_add")
    return (
        identity.get("state") == "running"
        and identity.get("user") == "10001:10001"
        and identity.get("read_only") is True
        and identity.get("init") is True
        and identity.get("restart_policy") == "no"
        and identity.get("privileged") is False
        and cap_drop == ["ALL"]
        and cap_add in (None, [])
        and identity.get("security_options") == ["no-new-privileges:true"]
        and identity.get("pid_mode") in ("", "private")
        and identity.get("ipc_mode") in ("", "private")
        and identity.get("pids_limit") == 64
        and identity.get("memory_limit") == expected_memory
        and identity.get("memory_swap_limit") == expected_memory
        and identity.get("nano_cpus") == expected_cpus
    )


def is_owned_instance(identity: object) -> bool:
    """Require an isolated app and its only loopback-published ingress relay."""
    if not isinstance(identity, dict):
        return False
    services = identity.get("services")
    networks = identity.get("networks")
    if (
        not isinstance(services, dict)
        or set(services) != {"sealdesk", "ingress"}
        or not isinstance(networks, dict)
        or set(networks) != {"sealdesk_default", "sealdesk_ingress"}
    ):
        return False
    app = services["sealdesk"]
    ingress = services["ingress"]
    if (
        not is_owned_container(app, "sealdesk")
        or not is_owned_container(ingress, "ingress")
        or app["container_id"] == ingress["container_id"]
    ):
        return False

    expected_labels = {
        "org.openlabs.lab": "sealdesk",
        "com.docker.compose.project": "sealdesk",
    }
    backend = networks["sealdesk_default"]
    ingress_network = networks["sealdesk_ingress"]
    if not isinstance(backend, dict) or not isinstance(ingress_network, dict):
        return False
    for network in (backend, ingress_network):
        labels = network.get("labels")
        if not isinstance(labels, dict) or any(
            labels.get(key) != value for key, value in expected_labels.items()
        ):
            return False
        if network.get("driver") != "bridge" or network.get("enable_ipv6") is not False:
            return False

    backend_peers = backend.get("attached_container_ids")
    ingress_peers = ingress_network.get("attached_container_ids")
    return (
        backend.get("name") == "sealdesk_default"
        and backend.get("internal") is True
        and isinstance(backend_peers, list)
        and backend_peers == sorted([app["container_id"], ingress["container_id"]])
        and ingress_network.get("name") == "sealdesk_ingress"
        and ingress_network.get("internal") is False
        and isinstance(ingress_peers, list)
        and ingress_peers == [ingress["container_id"]]
    )


def _run(
    command: Sequence[str], *, timeout: float = 20, cwd: Path = LAB_ROOT
) -> str:
    try:
        result = subprocess.run(
            list(command),
            cwd=cwd,
            env=compose_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise OperatorError("A required local Docker command could not be completed.") from error
    if result.returncode != 0:
        raise OperatorError("A required local Docker command failed; no diagnostic output was retained.")
    return result.stdout


def _docker(context: str, *arguments: str) -> list[str]:
    return ["docker", "--context", context, *arguments]


def _local_context() -> str:
    try:
        context = _run(["docker", "context", "show"]).strip()
        if not context or "\n" in context:
            raise OperatorError("The active Docker context could not be verified.")
        endpoint = _run(_docker(
            context,
            "context", "inspect", "--format", '{{(index .Endpoints "docker").Host}}', context,
        )).strip()
    except OperatorError:
        raise
    if not endpoint.startswith(("npipe://", "unix://")):
        raise OperatorError("SealDesk lifecycle operations require a local Docker Engine context.")
    return context


def compose_command(context: str, *arguments: str) -> list[str]:
    """Pin Compose to this lab directory and its explicitly named project."""
    return [
        *_docker(context, "compose"),
        "--project-directory", str(LAB_ROOT),
        "--project-name", "sealdesk",
        "--file", str(COMPOSE_FILE),
        *arguments,
    ]


def _container_id(context: str, service: str) -> str:
    if not isinstance(service, str) or service not in {"sealdesk", "ingress"}:
        raise OperatorError("The requested service is outside the SealDesk project.")
    output = _run(compose_command(context, "ps", "--all", "--quiet", service))
    identifiers = [line.strip() for line in output.splitlines() if line.strip()]
    if len(identifiers) != 1 or not _CONTAINER_ID.fullmatch(identifiers[0]):
        raise OperatorError(f"Exactly one SealDesk {service} container must exist.")
    return identifiers[0]


def _inspect_identity(context: str, container_id: str) -> dict[str, object]:
    template = (
        '{{json .Config.Labels}}|{{json .NetworkSettings.Ports}}|{{.Config.User}}|'
        '{{.HostConfig.ReadonlyRootfs}}|{{json .HostConfig.CapDrop}}|'
        '{{json .HostConfig.CapAdd}}|{{json .HostConfig.SecurityOpt}}|'
        '{{.HostConfig.Privileged}}|{{.HostConfig.NetworkMode}}|'
        '{{.HostConfig.PidMode}}|{{.HostConfig.IpcMode}}|{{json .Mounts}}|'
        '{{.HostConfig.PidsLimit}}|{{.HostConfig.Memory}}|'
        '{{.HostConfig.MemorySwap}}|{{.HostConfig.NanoCpus}}|{{json .HostConfig.Tmpfs}}|'
        '{{json .NetworkSettings.Networks}}|{{.Config.Image}}|{{.State.Status}}|'
        '{{.HostConfig.Init}}|{{.HostConfig.RestartPolicy.Name}}'
    )
    output = _run(_docker(context, "inspect", "--format", template, container_id)).strip()
    fields = output.split("|", maxsplit=21)
    if len(fields) != 22:
        raise OperatorError("The local SealDesk container could not be identified safely.")
    try:
        labels, ports, cap_drop, cap_add, security_options, raw_mounts, tmpfs, raw_networks = (
            json.loads(fields[0]), json.loads(fields[1]), json.loads(fields[4]),
            json.loads(fields[5]), json.loads(fields[6]), json.loads(fields[11]),
            json.loads(fields[16]), json.loads(fields[17]),
        )
        if not isinstance(raw_mounts, list) or not isinstance(raw_networks, dict):
            raise ValueError("invalid mount or network map")
        mounts = [
            {
                "type": mount.get("Type"),
                "destination": mount.get("Destination"),
                "rw": mount.get("RW"),
            }
            for mount in raw_mounts
            if isinstance(mount, dict)
        ]
        if len(mounts) != len(raw_mounts):
            raise ValueError("invalid mount entry")
        identity = {
            "labels": labels,
            "ports": ports,
            "user": fields[2],
            "read_only": fields[3].lower() == "true",
            "cap_drop": cap_drop,
            "cap_add": cap_add,
            "security_options": security_options,
            "privileged": fields[7].lower() == "true",
            "network_mode": fields[8],
            "pid_mode": fields[9],
            "ipc_mode": fields[10],
            "mounts": mounts,
            "container_id": container_id,
            "pids_limit": int(fields[12]),
            "memory_limit": int(fields[13]),
            "memory_swap_limit": int(fields[14]),
            "nano_cpus": int(fields[15]),
            "tmpfs": tmpfs,
            "network_names": sorted(raw_networks),
            "image": fields[18],
            "state": fields[19],
            "init": fields[20].lower() == "true",
            "restart_policy": fields[21],
        }
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise OperatorError("The local SealDesk container configuration is malformed.") from error
    return identity


def _inspect_project_network(context: str, name: str) -> dict[str, object]:
    if not isinstance(name, str) or name not in {"sealdesk_default", "sealdesk_ingress"}:
        raise OperatorError("The requested network is outside the SealDesk project.")
    template = (
        '{{.Name}}|{{.Internal}}|{{.Driver}}|{{.EnableIPv6}}|'
        '{{json .Labels}}|{{json .Containers}}'
    )
    output = _run(_docker(context, "network", "inspect", "--format", template, name)).strip()
    fields = output.split("|", maxsplit=5)
    if len(fields) != 6:
        raise OperatorError("The local SealDesk network could not be identified safely.")
    try:
        labels = json.loads(fields[4])
        containers = json.loads(fields[5])
        if containers is None:
            containers = {}
        if not isinstance(containers, dict):
            raise ValueError("invalid network attachments")
        return {
            "name": fields[0],
            "internal": fields[1].lower() == "true",
            "driver": fields[2],
            "enable_ipv6": fields[3].lower() == "true",
            "labels": labels,
            "attached_container_ids": sorted(containers),
        }
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise OperatorError("The local SealDesk network configuration is malformed.") from error


def _owned_app(context: str) -> tuple[str, dict[str, object]]:
    container_id = _container_id(context, "sealdesk")
    identity = _inspect_identity(context, container_id)
    if not is_owned_container(identity, "sealdesk"):
        raise OperatorError("The container is not the expected isolated SealDesk application.")
    return container_id, identity


def _owned_stack(
    context: str,
) -> tuple[str, str, dict[str, object]]:
    app_id = _container_id(context, "sealdesk")
    ingress_id = _container_id(context, "ingress")
    stack: dict[str, object] = {
        "services": {
            "sealdesk": _inspect_identity(context, app_id),
            "ingress": _inspect_identity(context, ingress_id),
        },
        "networks": {
            "sealdesk_default": _inspect_project_network(context, "sealdesk_default"),
            "sealdesk_ingress": _inspect_project_network(context, "sealdesk_ingress"),
        },
    }
    if not is_owned_instance(stack):
        raise OperatorError("The project is not the expected isolated SealDesk app and ingress stack.")
    return app_id, ingress_id, stack


def _read_running_flag_hash(context: str, container_id: str) -> str:
    output = _run(_docker(
        context, "exec", container_id, "python", "-B", "-c",
        "from app.state import main; raise SystemExit(main())", "--flag-hash-json",
    ))
    try:
        return parse_flag_hash_output(output.strip())
    except ValueError as error:
        raise OperatorError("The local runtime did not return one valid checker digest.") from error


def _health_check() -> None:
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open("http://127.0.0.1:8080/health", timeout=4) as response:
            body = json.loads(response.read(1024).decode("utf-8"))
    except (OSError, URLError, TimeoutError, UnicodeError, json.JSONDecodeError) as error:
        raise OperatorError("The recreated local SealDesk service failed its loopback health check.") from error
    if response.status != 200 or body != {"service": "sealdesk", "status": "ok"}:
        raise OperatorError("The recreated local SealDesk service failed its loopback health check.")


def sync_flag_hash() -> bool:
    """Sync the current local runtime hash into this lab's checker metadata."""
    context = _local_context()
    app_id, _ingress_id, _stack = _owned_stack(context)
    digest = _read_running_flag_hash(context, app_id)
    return update_flag_hash(LAB_METADATA, digest)


def reset_instance() -> None:
    """Rotate only app state while ingress is closed, then reopen when ready."""
    context = _local_context()
    old_app_id, old_ingress_id, _old_stack = _owned_stack(context)
    old_digest = _validated_metadata_hash()
    old_runtime_digest = _read_running_flag_hash(context, old_app_id)
    require_current_flag_hash(old_digest, old_runtime_digest)

    _run(compose_command(context, "stop", "--timeout", "5", "ingress"), timeout=20)
    ingress_closed = True
    try:
        _run(compose_command(
            context,
            "up", "--detach", "--no-deps", "--force-recreate", "--no-build",
            "--pull", "never", "--wait", "--wait-timeout", "45", "sealdesk",
        ), timeout=75)
        new_app_id, _new_identity = _owned_app(context)
        if hmac.compare_digest(old_app_id, new_app_id):
            raise OperatorError("The local SealDesk application was not recreated; checker state was not updated.")

        new_digest = _read_running_flag_hash(context, new_app_id)
        if hmac.compare_digest(old_digest, new_digest):
            raise OperatorError("The recreated runtime did not rotate its flag; checker state was not updated.")
        update_flag_hash(LAB_METADATA, new_digest)

        _run(compose_command(
            context,
            "up", "--detach", "--no-deps", "--no-build", "--pull", "never",
            "--wait", "--wait-timeout", "45", "ingress",
        ), timeout=75)
        _health_check()
        final_app_id, final_ingress_id, _final_stack = _owned_stack(context)
        if (
            not hmac.compare_digest(new_app_id, final_app_id)
            or not hmac.compare_digest(old_ingress_id, final_ingress_id)
        ):
            raise OperatorError("SealDesk service identity changed during reset verification.")
        ingress_closed = False
    except (OSError, ValueError, OperatorError):
        if ingress_closed:
            try:
                _run(compose_command(context, "stop", "--timeout", "5", "ingress"), timeout=20)
            except (OSError, ValueError, OperatorError):
                pass
        raise


def _validated_metadata_hash() -> str:
    content = LAB_METADATA.read_bytes()
    if len(re.findall(rb"(?m)^flag_hash:", content)) != 1:
        raise OperatorError("lab.yml must contain exactly one flag_hash before reset.")
    match = _HASH_LINE.search(content)
    if match is None:
        raise OperatorError("lab.yml flag_hash is not a lowercase SHA-256 digest.")
    return match.group(2).decode("ascii")


def main(action: str) -> int:
    try:
        if action == "sync":
            changed = sync_flag_hash()
            print("SealDesk checker digest synchronized." if changed else "SealDesk checker digest is current.")
        elif action == "reset":
            reset_instance()
            print("SealDesk reset complete. Runtime state rotated and checker digest synchronized.")
        else:
            print("usage: run reset.py or scripts/sync_flag_hash.py", file=sys.stderr)
            return 2
    except (OSError, ValueError, OperatorError) as error:
        print(f"SealDesk {action} failed: {error}", file=sys.stderr)
        return 1
    return 0


def reset_main() -> int:
    return main("reset")


def sync_main() -> int:
    return main("sync")
