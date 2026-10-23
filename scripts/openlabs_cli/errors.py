"""CLI error types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UsageError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class HandlerError(Exception):
    message: str
    exit_code: int = 1
    key: str = "lifecycle.cli.internal"

    def __str__(self) -> str:
        return self.message
