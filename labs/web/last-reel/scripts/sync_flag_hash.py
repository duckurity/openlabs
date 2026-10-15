"""Synchronize only the running instance's digest into lab.yml."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.control import assert_ownership, operator_lock, sync

if __name__ == "__main__":
    with operator_lock():
        assert_ownership()
        sync()
    print("Current instance checker digest synchronized. No plaintext flag read out.")
