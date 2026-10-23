#!/usr/bin/env python3
"""Tests for host port policy (M2-06)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from openlabs_cli.port_policy import resolve_host_port  # noqa: E402


def test_explicit_occupied_port_fails() -> None:
    result = resolve_host_port(
        declared_port=8377,
        explicit_port=8377,
        allow_dynamic=True,
        port_open=lambda _port: True,
    )
    assert not result.ok
    assert result.error_key == "lifecycle.port.conflict"


def test_dynamic_port_when_declared_busy() -> None:
    busy = {8377}

    def probe(port: int) -> bool:
        return port in busy

    result = resolve_host_port(
        declared_port=8377,
        explicit_port=None,
        allow_dynamic=True,
        port_open=probe,
    )
    assert result.ok
    assert result.dynamic is True
    assert result.host_port != 8377


def test_declared_free_uses_declared() -> None:
    result = resolve_host_port(
        declared_port=8377,
        explicit_port=None,
        allow_dynamic=True,
        port_open=lambda _port: False,
    )
    assert result.ok
    assert result.host_port == 8377
    assert result.dynamic is False


def main() -> int:
    tests = [
        test_explicit_occupied_port_fails,
        test_dynamic_port_when_declared_busy,
        test_declared_free_uses_declared,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs port: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs port: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
