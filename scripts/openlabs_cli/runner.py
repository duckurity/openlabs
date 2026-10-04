"""Subprocess runner abstraction for tests."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


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
        completed = subprocess.run(
            argv,
            cwd=cwd,
            timeout=timeout,
            check=False,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
