#!/usr/bin/env python3
"""Ensure lab MDX creator fields link to GitHub profiles, not commit history."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
CONTENT_LABS = REPO_ROOT / "content" / "labs"
FIXTURE = SCRIPTS / "fixtures" / "lab_creator_github.json"

sys.path.insert(0, str(SCRIPTS))

from validate import discover_labs  # noqa: E402
from sync_site_content import (  # noqa: E402
    GITHUB_PROFILE_URL_RE,
    parse_lab_yml,
)

AUTHOR_NAME_RE = re.compile(r'^author_name:\s*"([^"]+)"', re.MULTILINE)
AUTHOR_URL_RE = re.compile(r'^author_url:\s*"([^"]+)"', re.MULTILINE)
COMMITS_URL_RE = re.compile(r"/commits/")


def load_expected_logins() -> dict[str, str]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    labs = data.get("labs")
    if not isinstance(labs, dict):
        raise ValueError("lab_creator_github.json must contain a labs object")
    return {str(k): str(v) for k, v in labs.items()}


def read_author_fields(mdx_path: Path) -> tuple[str, str]:
    text = mdx_path.read_text(encoding="utf-8")
    name_m = AUTHOR_NAME_RE.search(text)
    url_m = AUTHOR_URL_RE.search(text)
    return (
        name_m.group(1).strip() if name_m else "",
        url_m.group(1).strip() if url_m else "",
    )


def main() -> int:
    expected = load_expected_logins()
    failures: list[str] = []
    catalogued = discover_labs()
    rel_paths = {lab.relative_to(REPO_ROOT).as_posix() for lab in catalogued}

    missing_fixture = sorted(rel_paths - set(expected.keys()))
    extra_fixture = sorted(set(expected.keys()) - rel_paths)
    if missing_fixture:
        failures.append(
            f"fixture missing {len(missing_fixture)} catalogued labs: {missing_fixture[:3]}"
        )
    if extra_fixture:
        failures.append(
            f"fixture has {len(extra_fixture)} stale paths: {extra_fixture[:3]}"
        )

    for lab in catalogued:
        rel = lab.relative_to(REPO_ROOT).as_posix()
        meta = parse_lab_yml(lab / "lab.yml")
        slug = meta.get("name", lab.name)
        mdx = CONTENT_LABS / f"{slug}.mdx"
        if not mdx.is_file():
            failures.append(f"{rel}: missing {mdx.relative_to(REPO_ROOT)}")
            continue
        name, url = read_author_fields(mdx)
        login = expected.get(rel, "")
        if not login:
            continue
        if not url or COMMITS_URL_RE.search(url):
            failures.append(f"{rel}: author_url must be a GitHub profile, got {url!r}")
            continue
        if not GITHUB_PROFILE_URL_RE.fullmatch(url):
            failures.append(f"{rel}: author_url invalid: {url!r}")
            continue
        url_login = url.rstrip("/").rsplit("/", 1)[-1]
        if url_login.lower() != login.lower():
            failures.append(
                f"{rel}: author_url login {url_login!r} != fixture {login!r}"
            )
        if name.lower() != login.lower():
            failures.append(
                f"{rel}: author_name {name!r} must match GitHub login {login!r}"
            )

    if failures:
        for line in failures:
            print(line, file=sys.stderr)
        print(f"lab author check failed ({len(failures)} problems)", file=sys.stderr)
        return 1
    print(f"lab author ok: {len(catalogued)} catalogued labs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
