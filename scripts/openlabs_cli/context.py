"""Runtime context passed to command handlers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openlabs_cli.runner import CommandRunner


@dataclass
class CliContext:
    repo_root: Path
    json_mode: bool = False
    dry_run: bool = False
    non_interactive: bool = False
    port: int | None = None
    runner: CommandRunner | None = None
    interrupted: bool = field(default=False, repr=False)
