#!/usr/bin/env python3
"""Verify lab triage registry covers every lab directory."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "lab_triage_inventory.py"


def main() -> int:
    wiki = REPO_ROOT / "wiki" / "Lab-Triage-Inventory.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--check",
            "--wiki",
            str(wiki),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="")
        return result.returncode
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
