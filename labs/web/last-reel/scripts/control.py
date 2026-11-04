"""Scoped Compose lifecycle and digest-only metadata synchronization."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "last-reel"
SERVICES = {"last-reel", "last-reel-ingress"}
HEALTH_URL = "http://127.0.0.1:8080/health"
READER = "import json; from app.seed import digest; print(json.dumps(digest(),sort_keys=True))"


def run(*arguments: str, timeout: int = 150) -> str:
    environment = os.environ.copy()
    for key in ("COMPOSE_FILE", "COMPOSE_PROJECT_NAME", "COMPOSE_PROFILES", "COMPOSE_ENV_FILES"):
        environment.pop(key, None)
    environment["COMPOSE_DISABLE_ENV_FILE"] = "1"
    result = subprocess.run(list(arguments), cwd=ROOT, env=environment, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Preserve errors for the operator without exposing captured SQL/flags.
        raise RuntimeError(f"{arguments[0]} operation failed (exit {result.returncode}).")
    return result.stdout


def compose(*arguments: str) -> str:
    return run("docker", "compose", "--project-name", PROJECT, "--project-directory", str(ROOT), "--file", str(ROOT / "docker-compose.yml"), *arguments)


def assert_ownership() -> None:
    containers = run("docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=" + PROJECT).split()
    if containers:
        for record in json.loads(run("docker", "inspect", *containers)):
            labels = record["Config"].get("Labels", {})
            owner = labels.get("com.docker.compose.project.working_dir", "")
            if labels.get("org.openlabs.lab") != PROJECT or labels.get("com.docker.compose.service") not in SERVICES or os.path.normcase(os.path.abspath(owner)) != os.path.normcase(str(ROOT)):
                raise RuntimeError("Compose project collision. Refusing to affect containers outside this workspace.")
    for name in (PROJECT + "_backend", PROJECT + "_frontend"):
        ids = run("docker", "network", "ls", "-q", "--filter", "name=^" + name + "$").split()
        for record in json.loads(run("docker", "network", "inspect", *ids)) if ids else []:
            labels = record.get("Labels", {})
            if labels.get("org.openlabs.lab") != PROJECT or labels.get("com.docker.compose.project") != PROJECT:
                raise RuntimeError("Network-name collision. Refusing to adopt unrelated resources.")


@contextmanager
def operator_lock():
    directory = ROOT / ".runtime"
    directory.mkdir(exist_ok=True)
    with (directory / "operator.lock").open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("Another Last Reel operator action is running.") from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def validate_digest(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"generation_id", "flag_hash"} or not isinstance(value["generation_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", value["generation_id"]) or not isinstance(value["flag_hash"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["flag_hash"]):
        raise ValueError("Expected a generation identifier and SHA-256 digest only.")


def read_digest() -> dict[str, str]:
    value = json.loads(compose("exec", "-T", "last-reel", "python", "-c", READER))
    validate_digest(value)
    return value


def update_metadata(path: Path, value: dict[str, str]) -> bool:
    validate_digest(value)
    original = path.read_bytes()
    text = original.decode("utf-8")
    pattern = re.compile(r"^(flag_hash: )[a-f0-9]{64}(?=\r?$)", re.MULTILINE)
    if len(pattern.findall(text)) != 1:
        raise ValueError("lab.yml must contain one unquoted SHA-256 flag_hash scalar.")
    updated = pattern.sub(lambda match: match.group(1) + value["flag_hash"], text).encode("utf-8")
    if updated == original:
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".lab-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def sync() -> dict[str, str]:
    value = read_digest()
    update_metadata(ROOT / "lab.yml", value)
    if read_digest() != value:
        raise RuntimeError("Instance changed during hash synchronization. Repeat startup/reset.")
    return value


def verify_endpoint() -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(HEALTH_URL, timeout=3) as response:
        if response.status != 200 or json.load(response) != {"service": PROJECT, "status": "ok"}:
            raise RuntimeError("Published Last Reel health check failed.")


def start_or_reset(*, reset: bool) -> dict[str, str]:
    with operator_lock():
        assert_ownership()
        old = None
        if reset and compose("ps", "--status", "running", "-q", "last-reel").strip():
            old = read_digest()
        try:
            compose("stop", "--timeout", "5", "last-reel-ingress")
            arguments = ["up", "-d", "--no-build", "--pull", "never", "--no-deps", "--wait", "--wait-timeout", "60"]
            if reset:
                arguments.append("--force-recreate")
            compose(*arguments, "last-reel")
            state = sync()
            if old and (old["generation_id"] == state["generation_id"] or old["flag_hash"] == state["flag_hash"]):
                raise RuntimeError("Reset did not rotate the instance flag and generation.")
            compose("up", "-d", "--no-build", "--pull", "never", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "60", "last-reel-ingress")
            verify_endpoint()
            return state
        except (Exception, KeyboardInterrupt):
            try:
                compose("stop", "--timeout", "5", "last-reel-ingress")
            except Exception:
                pass  # Best-effort cleanup; the original failure is the useful one.
            raise
