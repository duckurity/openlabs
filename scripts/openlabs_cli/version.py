"""CLI version markers."""

from __future__ import annotations

CLI_VERSION = "0.2.0"
LAB_CONTRACT_VERSION = 1
ENVELOPE_VERSION = "openlabs.command.v1"


def version_lines() -> list[str]:
    return [
        f"openlabs {CLI_VERSION}",
        f"command envelope: {ENVELOPE_VERSION}",
        f"lab contract: {LAB_CONTRACT_VERSION}",
    ]
