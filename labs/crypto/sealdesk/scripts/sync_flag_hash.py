"""Synchronize the local SealDesk runtime's accepted flag digest."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.control import sync_main


if __name__ == "__main__":
    raise SystemExit(sync_main())
