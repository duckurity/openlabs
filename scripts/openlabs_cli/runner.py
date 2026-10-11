"""Subprocess runner abstraction for tests."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

EXECUTABLE_NOT_FOUND = 127
COMMAND_TIMEOUT = 124


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> CommandResult: ...


class SubprocessCommandRunner:
    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout: float | None = None,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                timeout=timeout,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            program = argv[0] if argv else "command"
            return CommandResult(
                returncode=EXECUTABLE_NOT_FOUND,
                stdout="",
                stderr=f"{program}: executable not found",
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            if not stderr:
                stderr = "command timed out"
            return CommandResult(
                returncode=COMMAND_TIMEOUT,
                stdout=stdout,
                stderr=stderr,
            )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
