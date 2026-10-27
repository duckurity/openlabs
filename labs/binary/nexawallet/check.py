#!/usr/bin/env python3
"""
nexawallet — flag verification script.

Checks a candidate flag against this lab directory's lab.yml flag_hash.
No dependencies beyond the Python standard library (no PyYAML needed),
since this lab is delivered as a BYOD artifact (no server-side checker
service is part of the lab itself).

Usage:
    python3 check.py "duck{...}"
    python3 check.py            # will prompt interactively
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

LAB_YML = Path(__file__).resolve().parent / "lab.yml"
FLAG_RE = re.compile(r"^duck\{[a-z0-9_]{16,40}\}$")
HASH_LINE_RE = re.compile(r"^flag_hash:\s*([0-9a-fA-F]{64})\s*$", re.MULTILINE)


def load_expected_hash() -> str:
    if not LAB_YML.is_file():
        print(f"[-] Could not find lab.yml next to this script ({LAB_YML}).",
              file=sys.stderr)
        sys.exit(2)

    text = LAB_YML.read_text(encoding="utf-8")
    m = HASH_LINE_RE.search(text)
    if not m:
        print("[-] Could not find a flag_hash field in lab.yml.", file=sys.stderr)
        sys.exit(2)
    return m.group(1).lower()


def main() -> None:
    if len(sys.argv) > 2:
        print("Usage: python3 check.py [\"duck{...}\"]", file=sys.stderr)
        sys.exit(2)

    candidate = sys.argv[1] if len(sys.argv) == 2 else input("Flag: ").strip()

    if not FLAG_RE.match(candidate):
        print("[-] That doesn't match the expected flag format "
              "(duck{...}, lowercase letters/digits/underscores, 16-40 chars).")
        sys.exit(1)

    expected = load_expected_hash()
    actual = hashlib.sha256(candidate.encode("utf-8")).hexdigest()

    if actual == expected:
        print("[+] Correct! That's the flag for this lab.")
        sys.exit(0)
    else:
        print("[-] That flag doesn't match this lab. Keep going.")
        sys.exit(1)


if __name__ == "__main__":
    main()
