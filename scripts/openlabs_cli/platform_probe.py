"""Host platform summary for bundles (no network)."""

from __future__ import annotations

import platform
import sys


def platform_summary() -> dict[str, str]:
    machine = platform.machine() or "unknown"
    system = platform.system() or "unknown"
    release = platform.release() or "unknown"
    return {
        "os": system,
        "release": release,
        "machine": machine,
        "python": sys.version.split()[0],
    }
