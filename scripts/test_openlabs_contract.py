#!/usr/bin/env python3
"""Parser and model tests for scripts/openlabs_contract.py."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from openlabs_contract import (  # noqa: E402
    load_lab_metadata,
    validate_lab_context,
)
from validate import LABS_DIR  # noqa: E402

FIXTURES = REPO_ROOT / "scripts" / "fixtures" / "openlabs_contract"

VALID_CASES = (
    "valid/explicit-version",
    "valid/quoted-description",
)

INVALID_CASES = (
    ("invalid/duplicate-key", "contract.parse.duplicate_key"),
    ("invalid/unknown-field", "contract.parse.unknown_field"),
    ("invalid/indented-key", "contract.parse.indented_key"),
)

FORBIDDEN_PARSER_DEFS = (
    re.compile(r"^\s*def parse_flat_yaml\s*\(", re.MULTILINE),
    re.compile(r"^\s*def parse_lab_yml\s*\(", re.MULTILINE),
)
PARSER_EXEMPT = frozenset({"openlabs_contract.py"})


def run_fixture_cases() -> int:
    failures = 0
    for rel in VALID_CASES:
        path = FIXTURES / rel / "lab.yml"
        result = load_lab_metadata(path)
        if result.record is None:
            failures += 1
            print(f"{rel}: expected valid, got diagnostics:")
            for diag in result.diagnostics:
                print(f"  [{diag.key}] {diag.format()}")
    for rel, want_key in INVALID_CASES:
        path = FIXTURES / rel / "lab.yml"
        result = load_lab_metadata(path)
        if result.record is not None:
            failures += 1
            print(f"{rel}: expected invalid")
            continue
        keys = {diag.key for diag in result.diagnostics}
        if want_key not in keys:
            failures += 1
            print(f"{rel}: expected key {want_key}, got {sorted(keys)}")
    if failures:
        print(f"fixtures: failed {failures}")
        return 1
    print(f"fixtures: passed {len(VALID_CASES) + len(INVALID_CASES)} cases")
    return 0


def run_catalog_context() -> int:
    failures = 0
    labs: list[Path] = []
    for track in sorted(LABS_DIR.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and (lab / "lab.yml").is_file():
                labs.append(lab)
    for lab in labs:
        yml = lab / "lab.yml"
        result = load_lab_metadata(yml)
        if result.record is None:
            failures += 1
            print(f"{lab.relative_to(REPO_ROOT)}: load failed:")
            for diag in result.diagnostics:
                print(f"  [{diag.key}] {diag.format()}")
            continue
        context = validate_lab_context(result.record, lab)
        if context:
            failures += 1
            print(f"{lab.relative_to(REPO_ROOT)}: context errors:")
            for diag in context:
                print(f"  [{diag.key}] {diag.format()}")
    if failures:
        print(f"catalog context: failed {failures} labs")
        return 1
    print(f"catalog context: passed {len(labs)} labs")
    return 0


def run_no_duplicate_parsers() -> int:
    failures = 0
    for path in sorted(SCRIPTS.rglob("*.py")):
        if path.name in PARSER_EXEMPT or path.name.startswith("test_"):
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PARSER_DEFS:
            if pattern.search(text):
                failures += 1
                print(f"{path.relative_to(REPO_ROOT)}: duplicate lab.yml parser definition")
                break
    if failures:
        print(f"duplicate parsers: failed {failures} files")
        return 1
    print("duplicate parsers: none outside openlabs_contract.py")
    return 0


def main() -> int:
    for step in (run_fixture_cases, run_catalog_context, run_no_duplicate_parsers):
        code = step()
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
