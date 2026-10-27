#!/usr/bin/env python3
"""Tests for sync_site_content author URL helpers."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from sync_site_content import github_login_from_git_name, render_mdx  # noqa: E402


def main() -> int:
    failures = 0
    cases = [
        ("mirnashams01-star", "mirnashams01-star"),
        ("suhila1.c", "suhila1.c"),
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
    link_cases = [([], "play", "/play"), ([("idor", "IDOR")], "technique/idor", "/technique/idor")]
    meta = {"name": "fixture", "track": "web", "difficulty": "easy",
            "description": "A fixture lab.", "status": "experimental"}
    for techniques, target, href in link_cases:
        page = render_mdx(meta, "# Fixture\n\n## Brief\nA fixture.\n", "8080", False,
                          {}, techniques, {"score": 94, "grade": "A"})
        if f"  - {target}\n" not in page or f"]({href})" not in page:
            failures += 1
            print(f"render_mdx: expected a usable outgoing link to {target}")
        if not techniques and page.endswith("\n\n"):
            failures += 1
            print("render_mdx: empty-technique output has an extra blank line at EOF")
    if failures:
        print(f"failed {failures} cases")
        return 1
    print(f"passed {len(cases)} author login cases and {len(link_cases)} lab link cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
