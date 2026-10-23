"""Command handlers."""

from __future__ import annotations

from openlabs_cli.commands.doctor import handle_doctor
from openlabs_cli.commands.issue import handle_issue
from openlabs_cli.commands.lab import handle_lab
from openlabs_cli.commands.setup import handle_setup

__all__ = [
    "handle_doctor",
    "handle_issue",
    "handle_lab",
    "handle_setup",
]
