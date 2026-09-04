#!/usr/bin/env python3
"""Sync labs/ into content/labs/ for the Next.js site.

Reads labs/<track>/<lab>/lab.yml and README.md, writes
content/labs/<lab>.mdx with frontmatter the site consumes.
Generated files carry a header. Do not edit by hand.

Usage:
  python3 scripts/sync_site_content.py
  python3 scripts/sync_site_content.py --check
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABS = ROOT / "labs"
OUT = ROOT / "content" / "labs"

PORT_RE = re.compile(r"localhost:(\d{2,5})")
COMPOSE_PORT_RE = re.compile(r'"(\d{2,5}):\d{2,5}"')


def parse_lab_yml(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def read_port(track: str, name: str, readme: str) -> str:
    match = PORT_RE.search(readme)
    if match:
        return match.group(1)
    for candidate in ("docker-compose.yml", "compose.yml"):
        compose = LABS / track / name / candidate
        if compose.exists():
            found = COMPOSE_PORT_RE.search(compose.read_text(encoding="utf-8"))
            if found:
                return found.group(1)
    return "8080"


def humanize(name: str) -> str:
    return name.replace("-", " ").capitalize()


def strip_h1(readme: str) -> str:
    lines = readme.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).lstrip("\n")


def render_mdx(meta: dict[str, str], readme: str, port: str) -> str:
    title = humanize(meta["name"])
    body = strip_h1(readme)
    header = (
        f"{{/* Generated from labs/{meta['track']}/{meta['name']}/lab.yml "
        "and README.md. Do not edit by hand. "
        "Run scripts/sync_site_content.py. */}"
    )
    return f"""---
title: {title}
description: {meta["description"]}
track: {meta["track"]}
difficulty: {meta["difficulty"]}
port: "{port}"
---

{header}

{body}
"""


def sync() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for lab_yml in sorted(LABS.glob("*/*/lab.yml")):
        if "_template" in lab_yml.parts:
            continue
        track = lab_yml.parent.parent.name
        meta = parse_lab_yml(lab_yml)
        readme_path = lab_yml.parent / "README.md"
        readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
        port = read_port(track, meta.get("name", lab_yml.parent.name), readme)
        meta.setdefault("name", lab_yml.parent.name)
        meta.setdefault("track", track)
        out_path = OUT / f'{meta["name"]}.mdx'
        content = render_mdx(meta, readme, port)
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != content:
            out_path.write_text(content, encoding="utf-8")
        written.append(out_path.name)
    # Remove stale files.
    for existing in OUT.glob("*.mdx"):
        if existing.name not in written and existing.name != "index.mdx":
            existing.unlink()
    return written


def main() -> int:
    check = "--check" in sys.argv
    if check:
        before = {p.name: p.read_text(encoding="utf-8") for p in OUT.glob("*.mdx")}
        written = sync()
        after = {p.name: p.read_text(encoding="utf-8") for p in OUT.glob("*.mdx")}
        if before != after:
            print(f"content out of date. ran sync, wrote: {', '.join(written)}")
            return 1
        print("content up to date")
        return 0
    written = sync()
    print(f"synced {len(written)} labs: {', '.join(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
