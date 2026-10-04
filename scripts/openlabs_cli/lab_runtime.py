"""Shared runtime helpers for lab lifecycle commands."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

from diagnostic_registry import redact_sensitive

from openlabs_cli.compose_ops import FORBIDDEN_COMPOSE_TOKENS
from openlabs_cli.context import CliContext

READY_TIMEOUT_S = 60
POLL_INTERVAL_S = 0.5


def assert_safe_compose_argv(argv: list[str]) -> None:
    for part in argv:
        if part.lower() in FORBIDDEN_COMPOSE_TOKENS:
            raise ValueError(f"compose argv {argv!r} is not allowed for OpenLabs lifecycle")


def run_compose(ctx: CliContext, argv: list[str], *, timeout: float = 600.0) -> tuple[int, str]:
    assert_safe_compose_argv(argv)
    if ctx.runner is None:
        return 127, "runner unavailable"
    result = ctx.runner.run(argv, cwd=ctx.repo_root, timeout=timeout)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, redact_sensitive(output.strip())


def http_ready(base_url: str) -> bool:
    request = urllib.request.Request(f"{base_url}/", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            body = response.read().decode("utf-8", "replace")
            return response.status == 200 and "duck cross" in body.lower()
    except (OSError, urllib.error.URLError):
        return False


def wait_ready(base_url: str, *, timeout_s: float = READY_TIMEOUT_S) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if http_ready(base_url):
            return True
        time.sleep(POLL_INTERVAL_S)
    return False


def compose_running(ctx: CliContext, argv_prefix: list[str]) -> bool:
    argv = [*argv_prefix, "ps", "-q"]
    code, out = run_compose(ctx, argv, timeout=30.0)
    if code != 0:
        return False
    return bool(out.strip())


def project_in_argv(argv: list[str], project: str) -> bool:
    if "-p" not in argv:
        return False
    index = argv.index("-p")
    return index + 1 < len(argv) and argv[index + 1] == project
