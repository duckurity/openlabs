#!/usr/bin/env python3
"""Tests for openlabs.state.v1 storage and locking (M2-06)."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from openlabs_cli.state_store import (  # noqa: E402
    LabLockError,
    build_state_payload,
    lab_lock,
    load_state,
    state_path,
    write_state,
)


def test_atomic_state_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        payload = build_state_payload(
            slug="duck-cross",
            compose_project="openlabs-deadbe-duck-cross",
            host_port=8377,
            lifecycle="configured",
            compose_file="labs/web/duck-cross/docker-compose.yml",
            container_port=8377,
        )
        write_state(root, payload)
        loaded = load_state(root, "duck-cross")
        assert loaded is not None
        assert loaded["host_port"] == 8377
        raw = state_path(root, "duck-cross").read_text(encoding="utf-8")
        assert raw.endswith("\n")
        assert json.loads(raw)["version"] == "openlabs.state.v1"


def test_concurrent_lock_blocks_second_mutation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        barrier = threading.Barrier(2)

        def hold_lock() -> None:
            with lab_lock(root, "duck-cross"):
                barrier.wait(timeout=2.0)
                barrier.wait(timeout=2.0)

        thread = threading.Thread(target=hold_lock, daemon=True)
        thread.start()
        barrier.wait(timeout=2.0)
        try:
            with lab_lock(root, "duck-cross"):
                raise AssertionError("second lock should not succeed")
        except LabLockError:
            pass
        barrier.wait(timeout=2.0)
        thread.join(timeout=2.0)


def main() -> int:
    tests = [test_atomic_state_roundtrip, test_concurrent_lock_blocks_second_mutation]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs state: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs state: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
