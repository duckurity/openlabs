#!/usr/bin/env python3
"""Sync openlabs brand assets and wiki content.

Subcommands:
    bump   Rewrite `?v=` parameters in README.md and wiki/*.md from the
           content hash of each referenced asset, and normalize the lab
           count in the README heading. Idempotent.
    wiki   Copy wiki/*.md into the openlabs.wiki.git repository, commit,
           and push. Use --no-push to prepare without pushing.

Zero dependencies beyond the standard library and git.

Usage:
    python3 scripts/sync_wiki.py bump
    python3 scripts/sync_wiki.py wiki [--no-push]
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
WIKI_DIR = REPO_ROOT / "wiki"
DEFAULT_WIKI_URL = "https://github.com/Duckurity/openlabs.wiki.git"
CI_USER = "github-actions[bot]"
CI_EMAIL = "github-actions[bot]@users.noreply.github.com"

ASSET_RE = re.compile(
    r'((?:src|srcset)=")([^"]*?\.github/assets/[^"?]+?)(\?v=[0-9a-f]+)?(")'
)
LABS_HEADING_RE = re.compile(
    r"(## Labs <sub>)(\d+)( live</sub>)"
)


def count_labs() -> int:
    labs_root = REPO_ROOT / "labs"
    if not labs_root.is_dir():
        return 0
    n = 0
    for track in labs_root.iterdir():
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        n += sum(
            1 for lab in track.iterdir()
            if lab.is_dir() and not lab.name.startswith((".", "_"))
        )
    return n


def resolve_asset(url: str) -> Path | None:
    """Map an asset URL to a file under the repository."""
    marker = "/.github/assets/"
    if marker in url:
        tail = url.split(marker, 1)[1]
        return REPO_ROOT / ".github/assets" / tail
    if url.startswith(".github/assets/"):
        return REPO_ROOT / url
    return None


def bump_file(path: Path, changed: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    out = []
    pos = 0
    for m in ASSET_RE.finditer(text):
        out.append(text[pos:m.start()])
        pre, url, _, post = m.group(1), m.group(2), m.group(3), m.group(4)
        local = resolve_asset(url)
        if local is None or not local.is_file():
            out.append(m.group(0))
        else:
            digest = hashlib.sha256(local.read_bytes()).hexdigest()[:8]
            out.append(f"{pre}{url}?v={digest}{post}")
            if m.group(3) != f"?v={digest}":
                changed.append(f"{path.name}: {url} -> ?v={digest}")
        pos = m.end()
    out.append(text[pos:])
    new = "".join(out)

    n_labs = count_labs()
    def sub_count(m: re.Match) -> str:
        if m.group(2) != str(n_labs):
            changed.append(f"{path.name}: labs count -> {n_labs}")
        return f"{m.group(1)}{n_labs}{m.group(3)}"
    new = LABS_HEADING_RE.sub(sub_count, new)

    if new != text:
        path.write_text(new, encoding="utf-8")


def cmd_bump() -> int:
    changed: list[str] = []
    targets = [README, *sorted(WIKI_DIR.glob("*.md"))]
    for path in targets:
        if path.is_file():
            bump_file(path, changed)
    if changed:
        for line in changed:
            print(line)
    else:
        print("asset versions up to date")
    return 0


def wiki_url() -> tuple[str, str]:
    """Return (clone url, push url). Push url embeds a token when one is set."""
    import os
    url = os.environ.get("WIKI_URL", DEFAULT_WIKI_URL)
    push = url
    token = os.environ.get("WIKI_PUSH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        repo = os.environ.get("GITHUB_REPOSITORY", "Duckurity/openlabs")
        push = f"https://x-access-token:{token}@github.com/{repo}.wiki.git"
    return url, push


def run_git(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], check=True,
                          capture_output=True, text=True, **kw)


def cmd_wiki(no_push: bool) -> int:
    if not WIKI_DIR.is_dir():
        print("wiki/ missing", file=sys.stderr)
        return 1
    clone_url, push_url = wiki_url()
    workdir = Path(tempfile.mkdtemp(prefix="openlabs-wiki-"))
    wiki_repo = workdir / "wiki.git"
    try:
        run_git(["clone", "--depth", "1", clone_url, str(wiki_repo)])
        for src in sorted(WIKI_DIR.glob("*.md")):
            shutil.copy2(src, wiki_repo / src.name)
        run_git(["add", "-A"], cwd=wiki_repo)
        status = run_git(["status", "--porcelain"], cwd=wiki_repo)
        if not status.stdout.strip():
            print("wiki up to date")
            return 0
        sha = run_git(["rev-parse", "--short", "HEAD"], cwd=REPO_ROOT).stdout.strip()
        run_git(["-c", f"user.name={CI_USER}", "-c", f"user.email={CI_EMAIL}",
                 "commit", "-m", f"docs: sync wiki from openlabs@{sha}"],
                cwd=wiki_repo)
        if no_push:
            print(f"prepared commit in {wiki_repo} (not pushed)")
            return 0
        run_git(["push", push_url, "HEAD:master"], cwd=wiki_repo)
        print(f"wiki pushed from openlabs@{sha}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"git failed: {e.cmd}\n{e.stderr}", file=sys.stderr)
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bump", help="rewrite asset version parameters")
    w = sub.add_parser("wiki", help="sync wiki content to the wiki repo")
    w.add_argument("--no-push", action="store_true",
                   help="commit locally in the temp clone, do not push")
    args = ap.parse_args()
    if args.cmd == "bump":
        return cmd_bump()
    return cmd_wiki(no_push=args.no_push)


if __name__ == "__main__":
    raise SystemExit(main())
