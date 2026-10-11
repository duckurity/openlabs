#!/usr/bin/env python3
"""Bounded, redacted JSON evidence for CI lifecycle artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from diagnostic_registry import redact_mapping

DEFAULT_MAX_BYTES = 256 * 1024
FLAG_PLAINTEXT_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")
EVIDENCE_VERSION = "openlabs.evidence.v1"


def prepare_evidence_document(data: dict[str, Any]) -> dict[str, Any]:
    prepared = redact_mapping(dict(data))
    if isinstance(prepared, dict):
        meta = prepared.get("meta")
        if not isinstance(meta, dict):
            meta = {}
            prepared["meta"] = meta
        meta["redacted"] = True
    return prepared  # type: ignore[return-value]


def _shrink_for_limit(data: dict[str, Any], *, max_bytes: int) -> tuple[dict[str, Any], int, bool]:
    current = prepare_evidence_document(data)
    encoded = (json.dumps(current, indent=2) + "\n").encode("utf-8")
    original_bytes = len(encoded)
    if original_bytes <= max_bytes:
        return current, original_bytes, False

    working = dict(current)
    steps = working.get("steps")
    if isinstance(steps, list):
        while len(steps) > 1:
            steps.pop()
            working["truncated"] = True
            working["original_bytes"] = original_bytes
            encoded = (json.dumps(working, indent=2) + "\n").encode("utf-8")
            if len(encoded) <= max_bytes:
                working["written_bytes"] = len(encoded)
                return working, original_bytes, True
        working["steps"] = steps[:1] if steps else []

    working.pop("raw_stdout", None)
    working.pop("raw_stderr", None)
    working["truncated"] = True
    working["original_bytes"] = original_bytes
    encoded = (json.dumps(working, indent=2) + "\n").encode("utf-8")
    if len(encoded) > max_bytes:
        minimal = {
            "version": working.get("version", EVIDENCE_VERSION),
            "truncated": True,
            "original_bytes": original_bytes,
            "written_bytes": max_bytes,
            "detail": "evidence exceeded size limit after truncation",
            "meta": {"redacted": True},
        }
        encoded = (json.dumps(minimal, indent=2) + "\n").encode("utf-8")
        if len(encoded) > max_bytes:
            encoded = encoded[: max_bytes - 1]
            if not encoded.endswith(b"\n"):
                encoded += b"\n"
        working = json.loads(encoded.decode("utf-8", errors="replace"))
        if not isinstance(working, dict):
            working = minimal
    else:
        working["written_bytes"] = len(encoded)
    return working, original_bytes, True


def write_bounded_json(path: Path, data: dict[str, Any], *, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    bounded, _original, _truncated = _shrink_for_limit(data, max_bytes=max_bytes)
    text = json.dumps(bounded, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def assert_no_plaintext_secrets(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    matches = FLAG_PLAINTEXT_RE.findall(text)
    if matches:
        print(
            f"evidence artifact {path.name}: found {len(matches)} plaintext flag pattern(s)",
            file=sys.stderr,
        )
        raise SystemExit(1)


def bound_file(source: Path, dest: Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("evidence source must be a JSON object")
    wrapped = {
        "version": EVIDENCE_VERSION,
        "source": source.name,
        **data,
    }
    write_bounded_json(dest, wrapped, max_bytes=max_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    bound = sub.add_parser("bound", help="read raw JSON, write bounded redacted copy")
    bound.add_argument("source", type=Path)
    bound.add_argument("dest", type=Path)
    bound.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)

    scan = sub.add_parser("scan-secrets", help="fail if plaintext flags appear in file")
    scan.add_argument("path", type=Path)

    args = parser.parse_args()
    if args.command == "bound":
        bound_file(args.source, args.dest, max_bytes=args.max_bytes)
        return 0
    if args.command == "scan-secrets":
        assert_no_plaintext_secrets(args.path)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
