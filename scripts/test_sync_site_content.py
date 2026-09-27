#!/usr/bin/env python3
"""Tests for sync_site_content author URL helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from sync_site_content import github_login_from_git_name  # noqa: E402


def main() -> int:
    failures = 0
    cases = [
        ("mirnashams01-star", "mirnashams01-star"),
        ("moayedellah", "moayedellah"),
        ("Ziad Osama El-Boshy", ""),
        ("", ""),
        ("bad--name", ""),
    ]
    for name, expected in cases:
        got = github_login_from_git_name(name)
        if got != expected:
            failures += 1
            print(f"github_login_from_git_name({name!r}): got {got!r}, want {expected!r}")
    fixture = Path(__file__).resolve().parent / "fixtures" / "lab_author_github.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    if data.get("labs", {}).get("labs/web/firmdrama") != "ziadelboshy":
        failures += 1
        print("lab_author_github.json must map firmdrama to ziadelboshy")
    if failures:
        print(f"failed {failures} cases")
        return 1
    print(f"passed {len(cases)} author login cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
