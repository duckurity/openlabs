#!/usr/bin/env python3
"""Tests for Compose project namespacing (M2-06)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from openlabs_cli.namespace import compose_project_name  # noqa: E402


def test_project_name_is_deterministic() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = compose_project_name(root, "duck-cross")
        second = compose_project_name(root, "duck-cross")
        assert first == second
        assert first.startswith("openlabs-")
        assert first.endswith("-duck-cross")


def test_different_repos_do_not_share_project() -> None:
    with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
        a = compose_project_name(Path(one), "duck-cross")
        b = compose_project_name(Path(two), "duck-cross")
        assert a != b


def test_different_slugs_differ() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = compose_project_name(root, "duck-cross")
        b = compose_project_name(root, "other-lab")
        assert a != b


def main() -> int:
    tests = [
        test_project_name_is_deterministic,
        test_different_repos_do_not_share_project,
        test_different_slugs_differ,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs namespace: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs namespace: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
