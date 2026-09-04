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
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import check_lab

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


def parse_bracket_list(text: str) -> list[str]:
    text = text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return []
    return [item.strip() for item in text[1:-1].split(",") if item.strip()]


def technique_title(slug: str) -> str | None:
    """Title of a technique page, or None when the page does not exist."""
    path = ROOT / "content" / "technique" / f"{slug}.mdx"
    if not path.is_file():
        return None
    match = re.search(r"^title:\s*(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() if match else humanize(slug)


def strip_h1(readme: str) -> str:
    lines = readme.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).lstrip("\n")


def lab_author(lab_dir: Path) -> dict[str, str]:
    """First-commit author of a lab directory, with a GitHub profile link.

    Falls back to the lab's commit history page when no username can
    be derived from the author email.
    """
    info: dict[str, str] = {}
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--format=%an|%ae|%ad", "--date=short", "--", str(lab_dir)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=True,
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return info
    if not out:
        return info
    name, _, email_date = out[0].partition("|")
    email, _, date = email_date.partition("|")
    username = ""
    if email.endswith("@users.noreply.github.com"):
        username = email.split("@")[0].split("+")[-1]
    info["author_name"] = name.strip()
    if date.strip():
        info["author_date"] = date.strip()
    if username:
        info["author_url"] = f"https://github.com/{username}"
        info["author_avatar"] = f"https://github.com/{username}.png"
    else:
        rel = lab_dir.relative_to(ROOT).as_posix()
        info["author_url"] = f"https://github.com/Duckurity/openlabs/commits/main/{rel}"
    return info


def render_mdx(
    meta: dict[str, str],
    readme: str,
    port: str,
    verified: bool,
    author: dict[str, str],
    techniques: list[tuple[str, str]],
) -> str:
    title = humanize(meta["name"])
    body = strip_h1(readme)
    header = (
        f"{{/* Generated from labs/{meta['track']}/{meta['name']}/lab.yml "
        "and README.md. Do not edit by hand. "
        "Run scripts/sync_site_content.py. */}"
    )
    article = "an" if meta["difficulty"][0] in "aeiou" else "a"
    extra = [
        "type: lab",
        f"key: lab-{meta['name']}",
        f"slug: labs/{meta['name']}",
        f"intent: Solve {article} {meta['difficulty']} {meta['track']} lab in Docker.",
        "keywords:",
        f"  primary: {title} {meta['track']} security lab docker",
        "  secondary:",
        f"    - {meta['difficulty']} {meta['track']} practice",
        f"    - openlabs {meta['name']}",
        f"verified: {'true' if verified else 'false'}",
    ]
    if techniques:
        extra.append("linksTo:")
        extra.extend(f"  - technique/{slug}" for slug, _ in techniques)
    for key in ("author_name", "author_url", "author_avatar", "author_date"):
        if author.get(key):
            value = author[key].replace('"', '')
            extra.append(f'{key}: "{value}"')
    extra_block = "\n".join(extra)
    techniques_block = ""
    if techniques:
        links = "\n".join(
            f"- [{name}](/technique/{slug})" for slug, name in techniques
        )
        techniques_block = f"\n## Techniques\n\nPractise in this lab:\n\n{links}\n"
    return f"""---
title: {title}
description: {meta["description"]}
track: {meta["track"]}
difficulty: {meta["difficulty"]}
port: "{port}"
{extra_block}
---

{header}

{body}{techniques_block}
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
        verified = not check_lab(lab_yml.parent)
        author = lab_author(lab_yml.parent)
        techniques = [
            (slug, title)
            for slug in parse_bracket_list(meta.get("techniques", ""))
            if (title := technique_title(slug)) is not None
        ]
        content = render_mdx(meta, readme, port, verified, author, techniques)
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
