#!/usr/bin/env python3
"""Reset safety tests for openlabs lab lifecycle (M2-07)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from openlabs_cli.compose_ops import assert_safe_compose_subcommand  # noqa: E402
from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.lab_lifecycle import handle_lab_reset  # noqa: E402
from openlabs_cli.lab_runtime import assert_safe_compose_argv  # noqa: E402
from openlabs_cli.runner import CommandResult  # noqa: E402
from openlabs_cli.state_store import build_state_payload, write_state  # noqa: E402


class _RecordingRunner:
    def __init__(self, *, ps_output: str = "") -> None:
        self.calls: list[list[str]] = []
        self.ps_output = ps_output

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> CommandResult:
        _ = cwd, timeout
        self.calls.append(list(argv))
        if "ps" in argv:
            return CommandResult(0, self.ps_output, "")
        return CommandResult(0, "", "")


def test_compose_subcommand_rejects_prune() -> None:
    try:
        assert_safe_compose_subcommand(["down", "--remove-orphans", "&&", "docker", "system", "prune"])
    except ValueError as exc:
        assert "prune" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError for prune subcommand")


def test_reset_never_targets_foreign_project() -> None:
    runner = _RecordingRunner(ps_output="container-id\n")
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    write_state(
        REPO_ROOT,
        build_state_payload(
            slug="duck-cross",
            compose_project="openlabs-safe-duck-cross",
            host_port=8377,
            lifecycle="ready",
            compose_file="labs/web/duck-cross/docker-compose.yml",
            container_port=8377,
        ),
    )
    foreign = "openlabs-evil-other-lab"
    try:
        result = handle_lab_reset(ctx, ["duck-cross"])
        assert result.ok
        for call in runner.calls:
            project = call[call.index("-p") + 1]
            assert project == "openlabs-safe-duck-cross"
            assert project != foreign
            assert "prune" not in call
    finally:
        state_file = REPO_ROOT / ".openlabs/state/duck-cross.json"
        if state_file.is_file():
            state_file.unlink()


def test_reset_no_op_does_not_invoke_compose_when_absent() -> None:
    runner = _RecordingRunner()
    ctx = CliContext(repo_root=REPO_ROOT, runner=runner)
    write_state(
        REPO_ROOT,
        build_state_payload(
            slug="duck-cross",
            compose_project="openlabs-safe-duck-cross",
            host_port=8377,
            lifecycle="stopped",
            compose_file="labs/web/duck-cross/docker-compose.yml",
            container_port=8377,
        ),
    )
    try:
        result = handle_lab_reset(ctx, ["duck-cross"])
        assert result.ok
        assert result.data.get("no_op") is True
        assert not any("down" in call for call in runner.calls)
    finally:
        state_file = REPO_ROOT / ".openlabs/state/duck-cross.json"
        if state_file.is_file():
            state_file.unlink()


def test_compose_argv_rejects_system_token() -> None:
    try:
        assert_safe_compose_argv(["docker", "compose", "system", "df"])
    except ValueError as exc:
        assert "system" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError for system token")


def main() -> int:
    tests = [
        test_compose_subcommand_rejects_prune,
        test_reset_never_targets_foreign_project,
        test_reset_no_op_does_not_invoke_compose_when_absent,
        test_compose_argv_rejects_system_token,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs reset safety: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs reset safety: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
