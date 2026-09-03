#!/usr/bin/env python3
"""Sync openlabs brand assets and wiki content.

Subcommands:
    bump   Rewrite `?v=` parameters in README.md and wiki/*.md from the
           content hash of each referenced asset, and normalize the lab
           count in the README heading. Idempotent. Safe to run repeatedly.
    wiki   Copy wiki/*.md into the openlabs.wiki.git repository, commit,
           and push. The push uses a temporary git credential helper so
           the token never appears in argv or remote URLs. Use --no-push
           to prepare a commit in a temp clone without pushing.

Zero dependencies beyond the standard library and git.

Environment:
    WIKI_PUSH_TOKEN   Fine-grained PAT with contents:write on
                      <org>/<repo>.wiki. Required for `wiki` to push.
                      Falls back to GITHUB_TOKEN when set.
    WIKI_URL          Override the wiki clone URL (default:
                      https://github.com/Duckurity/openlabs.wiki.git).
    GITHUB_REPOSITORY Used to derive the push URL when WIKI_PUSH_TOKEN
                      or GITHUB_TOKEN is set.

Usage:
    python3 scripts/sync_wiki.py bump
    python3 scripts/sync_wiki.py wiki [--no-push]
"""

from __future__ import annotations

import argparse
import hashlib
import os
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
GIT_TIMEOUT = 120  # seconds for any single git invocation

# Matches `src="..."` and `srcset="..."` attributes that reference assets
# under `.github/assets/`. Captures the prefix, URL, optional `?v=`, and
# closing quote so we can rewrite with a content-hash version.
ASSET_RE = re.compile(
    r'((?:src|srcset)=")([^"]*?\.github/assets/[^"?]+?)(\?v=[0-9a-f]+)?(")'
)
# README heading that announces the live lab count.
LABS_HEADING_RE = re.compile(
    r"(## Labs <sub>)(\d+)( live</sub>)"
)


def die(msg: str, code: int = 1) -> None:
    print(f"{Path(sys.argv[0]).name}: {msg}", file=sys.stderr)
    sys.exit(code)


def count_labs() -> int:
    """Count lab directories across tracks, mirroring validate.py rules."""
    labs_root = REPO_ROOT / "labs"
    if not labs_root.is_dir():
        return 0
    n = 0
    for track in sorted(labs_root.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        n += sum(
            1 for lab in track.iterdir()
            if lab.is_dir() and not lab.name.startswith((".", "_"))
        )
    return n


def resolve_asset(url: str) -> Path | None:
    """Map an asset URL to a file under the repository, or None if it is
    not a `.github/assets/` reference we own."""
    marker = "/.github/assets/"
    if marker in url:
        tail = url.split(marker, 1)[1]
        return REPO_ROOT / ".github/assets" / tail
    if url.startswith(".github/assets/"):
        return REPO_ROOT / url
    return None


def bump_file(path: Path, changes: list[str]) -> None:
    """Rewrite asset version parameters and the lab count in `path`."""
    text = path.read_text(encoding="utf-8")
    rebuilt: list[str] = []
    pos = 0
    warnings = 0
    for m in ASSET_RE.finditer(text):
        rebuilt.append(text[pos:m.start()])
        pre, url, old_qs, post = m.group(1), m.group(2), m.group(3), m.group(4)
        local = resolve_asset(url)
        if local is None or not local.is_file():
            rebuilt.append(m.group(0))
            warnings += 1
        else:
            digest = hashlib.sha256(local.read_bytes()).hexdigest()[:8]
            new_qs = f"?v={digest}"
            if old_qs != new_qs:
                changes.append(f"{path.name}: {url} -> {new_qs}")
            rebuilt.append(f"{pre}{url}{new_qs}{post}")
        pos = m.end()
    rebuilt.append(text[pos:])
    new = "".join(rebuilt)

    n_labs = count_labs()
    def sub_count(m: re.Match) -> str:
        if m.group(2) != str(n_labs):
            changes.append(f"{path.name}: labs count -> {n_labs}")
        return f"{m.group(1)}{n_labs}{m.group(3)}"
    new, n_subs = LABS_HEADING_RE.subn(sub_count, new)
    if n_subs == 0 and "## Labs" in text and "live</sub>" in text:
        # Heading text exists but did not match the expected pattern.
        changes.append(f"{path.name}: warning: ## Labs <sub>N live</sub> "
                       f"heading found but did not match expected pattern")

    if warnings:
        print(f"{path.name}: warning: {warnings} asset reference(s) could "
              f"not be resolved", file=sys.stderr)
    if new != text:
        path.write_text(new, encoding="utf-8")


def cmd_bump() -> int:
    if not README.is_file():
        die("README.md missing at repo root")
    targets = [README]
    if WIKI_DIR.is_dir():
        targets.extend(sorted(WIKI_DIR.glob("*.md")))
    changes: list[str] = []
    for path in targets:
        bump_file(path, changes)
    if changes:
        for line in changes:
            print(line)
    else:
        print("asset versions up to date")
    return 0


def wiki_url() -> str:
    """Return the wiki clone URL."""
    return os.environ.get("WIKI_URL", DEFAULT_WIKI_URL)


def make_credential_helper(workdir: Path) -> Path:
    """Write an executable git credential helper that emits the token from
    the OPENLABS_WIKI_TOKEN environment variable.

    The token never appears in the helper file, argv, or a remote URL, so
    it cannot leak through process listings, logs, or commit metadata."""
    helper = workdir / "git-cred-helper.sh"
    helper.write_text(
        "#!/bin/sh\n"
        "printf 'username=x-access-token\\npassword=%s\\n' "
        "\"$OPENLABS_WIKI_TOKEN\"\n"
    )
    helper.chmod(0o700)
    return helper


def in_ci() -> bool:
    return bool(os.environ.get("GITHUB_ACTIONS") or
                os.environ.get("CI") == "true")


def resolve_committer() -> tuple[str, str]:
    """Return (user.name, user.email) for the wiki commit.

    In CI we use the github-actions bot identity. Locally we fall back to
    the repository's existing git config so the user keeps attribution."""
    if in_ci():
        return CI_USER, CI_EMAIL
    name = subprocess.run(
        ["git", "config", "user.name"], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=GIT_TIMEOUT,
    ).stdout.strip()
    email = subprocess.run(
        ["git", "config", "user.email"], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=GIT_TIMEOUT,
    ).stdout.strip()
    if not name or not email:
        die("local git user.name and user.email must be configured for "
            "wiki sync (or run in CI)")
    return name, email


def run_git(args: list[str], env: dict[str, str] | None = None,
            **kw) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True,
        text=True, timeout=GIT_TIMEOUT, env=env, **kw,
    )


def push_with_token(wiki_repo: Path, clone_url: str, token: str,
                    refspec: str) -> None:
    """Push using a temporary credential helper so the token never reaches
    the remote URL or process arguments."""
    with tempfile.TemporaryDirectory(prefix="openlabs-cred-") as cred_dir:
        helper = make_credential_helper(Path(cred_dir))
        env = {**os.environ, "OPENLABS_WIKI_TOKEN": token}
        run_git(
            ["-c", f"credential.helper={helper}", "push", clone_url, refspec],
            cwd=wiki_repo, env=env,
        )


def cmd_wiki(no_push: bool) -> int:
    if not WIKI_DIR.is_dir():
        die("wiki/ missing at repo root")
    files = sorted(WIKI_DIR.glob("*.md"))
    if not files:
        die("wiki/ contains no .md files")

    token = os.environ.get("WIKI_PUSH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    clone_url = wiki_url()
    user, email = resolve_committer()
    workdir = Path(tempfile.mkdtemp(prefix="openlabs-wiki-"))
    wiki_repo = workdir / "wiki.git"
    try:
        run_git(["clone", "--depth", "1", clone_url, str(wiki_repo)])
        for src in files:
            shutil.copy2(src, wiki_repo / src.name)
        run_git(["add", "-A"], cwd=wiki_repo)
        status = run_git(["status", "--porcelain"], cwd=wiki_repo)
        if not status.stdout.strip():
            print("wiki up to date")
            return 0
        sha = run_git(
            ["rev-parse", "--short", "HEAD"], cwd=REPO_ROOT
        ).stdout.strip()
        run_git(
            ["-c", f"user.name={user}", "-c", f"user.email={email}",
             "commit", "-m", f"docs: sync wiki from openlabs@{sha}"],
            cwd=wiki_repo,
        )
        if no_push:
            print(f"prepared commit in {wiki_repo} (not pushed)")
            return 0
        if token:
            push_with_token(wiki_repo, clone_url, token, "HEAD:master")
        else:
            print("note: no WIKI_PUSH_TOKEN set; pushing with local "
                  "git credentials")
            run_git(["push", clone_url, "HEAD:master"], cwd=wiki_repo)
        print(f"wiki pushed from openlabs@{sha}")
        return 0
    except subprocess.CalledProcessError as exc:
        cmd = " ".join(exc.cmd) if isinstance(exc.cmd, list) else exc.cmd
        print(f"git failed: {cmd}\n{exc.stderr}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired as exc:
        print(f"git timed out: {exc.cmd}", file=sys.stderr)
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
