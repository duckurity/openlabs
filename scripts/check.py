#!/usr/bin/env python3
"""Check a flag against a lab's flag_hash.

Usage:
    python3 scripts/check.py labs/web/duck-cross
    python3 scripts/check.py          # run from inside a lab directory

Zero dependencies. Prints `solved` and exits 0 on a correct flag, prints
`not solved` and exits 1 otherwise.
"""

import hashlib
import re
import sys
from pathlib import Path

HASH_LINE_RE = re.compile(r"^flag_hash:\s*([0-9a-f]{64})\s*$", re.MULTILINE)


def read_flag_hash(lab: Path) -> str | None:
    text = (lab / "lab.yml").read_text(encoding="utf-8")
    match = HASH_LINE_RE.search(text)
    return match.group(1) if match else None


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: check.py [lab directory]")
        return 2

    lab = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(".")
    if not (lab / "lab.yml").is_file():
        print(f"no lab.yml in {lab}")
        return 2

    stored = read_flag_hash(lab)
    if stored is None:
        print(f"lab.yml in {lab} has no flag_hash")
        return 2

    try:
        flag = input("flag: ").strip()
    except EOFError:
        print()
        return 2

    if hashlib.sha256(flag.encode("utf-8")).hexdigest() == stored:
        print("solved")
        return 0

    print("not solved")
    return 1


if __name__ == "__main__":
    sys.exit(main())
