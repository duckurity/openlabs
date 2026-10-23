#!/usr/bin/env python3
"""Check a flag against a lab's hashes.

Usage:
    python3 scripts/check.py labs/web/duck-cross
    python3 scripts/check.py          # run from inside a lab directory

Zero dependencies. A valid `flag_hash` prints `solved` and exits 0. An
optional `checkpoint_flag_hash` prints `checkpoint solved` and exits 0.
Malformed hash fields and usage errors exit 2. A non-matching flag exits 1.

Hash fields must use the exact form `field_name: <64 lowercase hex characters>`.
Quoted values, inline comments, duplicate fields, and extra text are rejected.
"""

import hashlib
import hmac
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openlabs_contract import read_player_flag_hashes  # noqa: E402

FINAL_HASH_FIELD = "flag_hash"
CHECKPOINT_HASH_FIELD = "checkpoint_flag_hash"


def flag_stage(flag: str, hashes: dict[str, str]) -> str | None:
    """Return the matched stage without retaining or displaying the flag."""
    digest = hashlib.sha256(flag.encode("utf-8")).hexdigest()
    checkpoint = hashes.get(CHECKPOINT_HASH_FIELD)
    if checkpoint is not None and hmac.compare_digest(digest, checkpoint):
        return "checkpoint"
    if hmac.compare_digest(digest, hashes[FINAL_HASH_FIELD]):
        return "final"
    return None


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: check.py [lab directory]")
        return 2

    lab = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(".")
    metadata = lab / "lab.yml"
    if not metadata.is_file():
        print(f"no lab.yml in {lab}")
        return 2

    try:
        hashes = read_player_flag_hashes(lab)
    except OSError:
        print(f"could not read {metadata}")
        return 2
    except UnicodeError:
        print(f"lab.yml in {lab} is not valid UTF-8")
        return 2
    except ValueError as error:
        print(str(error))
        return 2

    try:
        flag = input("flag: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        print("flag input cancelled")
        return 2

    try:
        stage = flag_stage(flag, hashes)
    except UnicodeError:
        print("flag input could not be encoded as UTF-8")
        return 2

    if stage == "checkpoint":
        print("checkpoint solved")
        return 0
    if stage == "final":
        print("solved")
        return 0

    print("not solved")
    return 1


if __name__ == "__main__":
    sys.exit(main())
