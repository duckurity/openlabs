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

import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import check_lab
from score_lab import score_lab

ROOT = Path(__file__).resolve().parent.parent
LABS = ROOT / "labs"
OUT = ROOT / "content" / "labs"
CONTENT = ROOT / "content"
PUBLIC = ROOT / "public"

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

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


PORT_RE = re.compile(r"localhost:(\d{2,5})")
COMPOSE_PORT_RE = re.compile(r'"(\d{2,5}):\d{2,5}"')
CACHE_DIR = ROOT / ".cache"
GITHUB_CACHE = CACHE_DIR / "github.json"
GITHUB_TTL = 7 * 24 * 3600


def repo_slug() -> str:
    """Owner/Repo from the origin remote, defaulting to the known repo."""
    try:
        out = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Duckurity/openlabs"
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", out)
    return match.group(1) if match else "Duckurity/openlabs"


def github_cache_load() -> dict:
    try:
        return json.loads(GITHUB_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def github_cache_save(cache: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    GITHUB_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def github_api(path: str) -> object | None:
    """GET a GitHub API path. Returns None offline, unauthenticated-limited,
    or on any failure — callers always fall back to local git data."""
    import os

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "openlabs-sync",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(
            f"https://api.github.com{path}", headers=headers
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def login_from_email(email: str) -> str:
    if email.endswith("@users.noreply.github.com"):
        return email.split("@")[0].split("+")[-1]
    return ""


def commit_login(owner_repo: str, sha: str, cache: dict) -> str:
    """GitHub login for a commit sha, cached. Empty when unresolvable."""
    key = f"commit:{sha}"
    entry = cache.get(key)
    if entry and time.time() - entry.get("ts", 0) < GITHUB_TTL:
        return entry.get("login", "")
    login = ""
    data = github_api(f"/repos/{owner_repo}/commits/{sha}")
    if isinstance(data, dict):
        author = data.get("author") or {}
        if isinstance(author, dict) and author.get("login"):
            login = str(author["login"])
    if login:
        cache[key] = {"login": login, "ts": time.time()}
    return login


def introducing_pr(owner_repo: str, lab_rel: str, cache: dict) -> dict:
    """Oldest merged PR touching a lab directory. Empty when unresolvable."""
    key = f"pr:{lab_rel}"
    entry = cache.get(key)
    if entry and time.time() - entry.get("ts", 0) < GITHUB_TTL:
        return entry
    result: dict = {}
    page = 1
    merged: list[dict] = []
    while True:
        data = github_api(
            f"/repos/{owner_repo}/pulls?state=closed&per_page=100&page={page}"
        )
        if not isinstance(data, list) or not data:
            break
        merged.extend(pr for pr in data if pr.get("merged_at"))
        if len(data) < 100:
            break
        page += 1
        if page > 10:
            break
    merged.sort(key=lambda pr: pr.get("merged_at", ""))
    for pr in merged:
        number = pr.get("number")
        files = github_api(f"/repos/{owner_repo}/pulls/{number}/files?per_page=100")
        if not isinstance(files, list):
            continue
        if any(str(f.get("filename", "")).startswith(lab_rel + "/") for f in files):
            merger = (pr.get("merged_by") or {}).get("login", "")
            result = {"number": number, "merger": merger}
            break
    if result:
        cache[key] = {**result, "ts": time.time()}
    return result


def github_people(lab_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    """(creator, verifier) identities for a lab directory.

    Creator comes from local git history (hermetic). Logins resolve via
    noreply emails first, then the cached GitHub API. The verifier is the
    merger of the introducing PR. Anything unresolvable is omitted and
    the card hides that row.
    """
    owner_repo = repo_slug()
    cache = github_cache_load()
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--no-merges", "--format=%H|%an|%ae|%ad",
             "--date=short", "--", str(lab_dir)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=True,
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}, {}
    if not out:
        return {}, {}
    sha, _, rest = out[0].partition("|")
    name, _, email_date = rest.partition("|")
    email, _, date = email_date.partition("|")
    lab_rel = lab_dir.relative_to(ROOT).as_posix()

    creator: dict[str, str] = {"author_name": name.strip()}
    if date.strip():
        creator["author_date"] = date.strip()
    login = login_from_email(email.strip()) or commit_login(owner_repo, sha.strip(), cache)
    if login:
        creator["author_url"] = f"https://github.com/{login}"
        creator["author_avatar"] = f"https://github.com/{login}.png"
    else:
        creator["author_url"] = (
            f"https://github.com/{owner_repo}/commits/main/{lab_rel}"
        )

    verifier: dict[str, str] = {}
    pr = introducing_pr(owner_repo, lab_rel, cache)
    merger = pr.get("merger", "")
    if merger and merger != login:
        verifier = {
            "verifier_name": merger,
            "verifier_url": f"https://github.com/{merger}",
            "verifier_avatar": f"https://github.com/{merger}.png",
        }

    github_cache_save(cache)
    return creator, verifier


def render_mdx(
    meta: dict[str, str],
    readme: str,
    port: str,
    verified: bool,
    author: dict[str, str],
    techniques: list[tuple[str, str]],
    score: dict,
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
        f"score: {score['score']}",
        f"score_grade: {score['grade']}",
    ]
    if techniques:
        extra.append("linksTo:")
        extra.extend(f"  - technique/{slug}" for slug, _ in techniques)
    for key in (
        "author_name",
        "author_url",
        "author_avatar",
        "author_date",
        "verifier_name",
        "verifier_url",
        "verifier_avatar",
    ):
        if author.get(key):
            value = author[key].replace('"', '')
            extra.append(f'{key}: "{value}"')
    extra.append(f"ogImage: /og/labs-{meta['name']}.png")
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
        author, verifier = github_people(lab_yml.parent)
        author.update(verifier)
        score = score_lab(lab_yml.parent)
        techniques = [
            (slug, title)
            for slug in parse_bracket_list(meta.get("techniques", ""))
            if (title := technique_title(slug)) is not None
        ]
        content = render_mdx(meta, readme, port, verified, author, techniques, score)
        if not out_path.exists() or out_path.read_text(encoding="utf-8") != content:
            out_path.write_text(content, encoding="utf-8")
        written.append(out_path.name)
    # Remove stale files.
    for existing in OUT.glob("*.mdx"):
        if existing.name not in written and existing.name != "index.mdx":
            existing.unlink()
    return written


def base_url() -> str:
    """Site base URL, mirroring lib/constants.ts fallback."""
    match = re.search(r"'(https://[^']+)'", (ROOT / "lib" / "constants.ts").read_text(encoding="utf-8"))
    return match.group(1) if match else "https://openlabs.duckurity.com"


def page_meta(path: Path) -> dict[str, str] | None:
    """Title/description/slug for a content page, or None without title."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip("\"'")
    if not meta.get("title"):
        return None
    slug = meta.get("slug") or path.relative_to(CONTENT).with_suffix("").as_posix()
    if slug.endswith("/index"):
        slug = slug[: -len("/index")]
    meta["slug"] = slug
    meta["url"] = base_url().rstrip("/") + ("" if slug in ("", "/") else f"/{slug.lstrip('/')}")

    return meta


def strip_body(path: Path) -> str:
    """Page body without frontmatter, comments, imports, or JSX tags."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    body = text[match.end() :] if match else text
    body = re.sub(r"\{\/\*.*?\*\/\}", "", body, flags=re.DOTALL)
    out: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("import ") or stripped.startswith("export "):
            continue
        if re.fullmatch(r"</?[A-Z][^>]*>?", stripped):
            continue
        out.append(line.rstrip())
    return "\n".join(out).strip() + "\n"


def collect_pages() -> list[tuple[Path, dict[str, str]]]:
    pages: list[tuple[Path, dict[str, str]]] = []
    paths = sorted(
        (ROOT / "content").rglob("*.mdx"),
        key=lambda p: (p.parent.as_posix(), p.stem != "index", p.name),
    )
    for path in paths:
        meta = page_meta(path)
        if meta:
            pages.append((path, meta))
    return pages


def read_public_texts() -> dict[str, str]:
    return {
        name: (PUBLIC / name).read_text(encoding="utf-8")
        for name in ("llms.txt", "llms-full.txt")
        if (PUBLIC / name).is_file()
    }


def build_llms() -> list[str]:
    """Write public/llms.txt (curated map) and public/llms-full.txt.

    Sources are public content files only. Flag plaintext and hashes
    never enter these files: only content/*.mdx is read.
    """
    base = base_url().rstrip("/")
    pages = collect_pages()
    by_slug = {meta["slug"]: (path, meta) for path, meta in pages}

    def bucket(slug: str) -> str:
        if slug in ("", "/"):
            return "guides"
        if slug == "labs" or slug.startswith("labs/"):
            return "labs"
        if slug.startswith("technique/"):
            return "guides"
        return "guides"

    groups: dict[str, list[dict[str, str]]] = {"labs": [], "guides": [], "rules": []}
    for _, meta in pages:
        slug = meta["slug"]
        if slug in ("rules", "faq", "contribute"):
            groups["rules"].append(meta)
        else:
            groups[bucket(slug)].append(meta)

    def item(meta: dict[str, str], note: str) -> str:
        return f"- [{meta['title']}]({meta['url']}): {note}"

    labs_lines = [item(m, m.get("description", "")[:110]) for m in groups["labs"]]
    guides_lines = [item(m, m.get("description", "")[:110]) for m in groups["guides"]]
    rules_lines = [item(m, m.get("description", "")[:110]) for m in groups["rules"]]

    llms = f"""# openlabs

> openlabs is an open source library of Docker-based security labs. Each lab is one vulnerable service, one brief, and one flag.

Read a page in full at its URL. Open a brief, run the service, find the flag. Verify with `python3 scripts/check.py labs/<track>/<lab>` from the repo root. Each lab documents one host port and runs offline after images are pulled. Flags look like `duck{{...}}`; this file carries no flags.

## Labs

{chr(10).join(labs_lines)}

## Guides

{chr(10).join(guides_lines)}

## Rules

{chr(10).join(rules_lines)}

## Optional

- [Repository](https://github.com/Duckurity/openlabs): source, labs, and issue forms.
- [Sitemap]({base}/sitemap.xml): every page for discovery.
"""
    full_parts = [
        "# openlabs",
        "",
        "> openlabs is an open source library of Docker-based security labs. Each lab is one vulnerable service, one brief, and one flag.",
        "",
    ]
    for _, meta in pages:
        path = by_slug[meta["slug"]][0]
        full_parts.append(f"## {meta['title']}")
        full_parts.append("")
        full_parts.append(f"Source: {meta['url']}")
        full_parts.append("")
        full_parts.append(strip_body(path))
    full = "\n".join(full_parts).rstrip() + "\n"

    written: list[str] = []
    for name, text in (("llms.txt", llms), ("llms-full.txt", full)):
        out = PUBLIC / name
        if not out.is_file() or out.read_text(encoding="utf-8") != text:
            out.write_text(text, encoding="utf-8")
        written.append(name)
    return written


def main() -> int:
    check = "--check" in sys.argv
    if check:
        before = {p.name: p.read_text(encoding="utf-8") for p in OUT.glob("*.mdx")}
        before_txt = read_public_texts()
        written = sync()
        built_txt = build_llms()
        after = {p.name: p.read_text(encoding="utf-8") for p in OUT.glob("*.mdx")}
        after_txt = read_public_texts()
        if before != after or before_txt != after_txt:
            print(f"content out of date. ran sync, wrote: {', '.join(written)}")
            return 1
        print("content up to date")
        return 0
    written = sync()
    built_txt = build_llms()
    print(f"synced {len(written)} labs: {', '.join(written)}")
    print(f"wrote public texts: {', '.join(built_txt)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
