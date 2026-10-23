#!/usr/bin/env python3
"""Contract schema fixtures and catalog representation checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from contract_schema import (  # noqa: E402
    lab_yml_meta_to_record,
    load_schema,
    validate_lab_record,
    validate_schema_document,
)
from openlabs_contract import load_lab_metadata  # noqa: E402
from validate import LABS_DIR  # noqa: E402

FIXTURES = REPO_ROOT / "scripts" / "fixtures" / "contract_schema"
VALID = FIXTURES / "valid"
INVALID = FIXTURES / "invalid"


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def run_valid_fixtures() -> int:
    failures = 0
    for path in sorted(VALID.glob("*.json")):
        data = load_json(path)
        errors = validate_lab_record(data, path=f"fixture:{path.name}")
        if errors:
            failures += 1
            print(f"{path.name}: expected valid, got errors:")
            for line in errors:
                print(f"  {line}")
    if failures:
        print(f"valid fixtures: failed {failures}")
        return 1
    count = len(list(VALID.glob("*.json")))
    print(f"valid fixtures: passed {count}")
    return 0


def run_invalid_fixtures() -> int:
    failures = 0
    for path in sorted(INVALID.glob("*.json")):
        data = load_json(path)
        errors = validate_lab_record(data, path=f"fixture:{path.name}")
        if not errors:
            failures += 1
            print(f"{path.name}: expected invalid, passed schema")
    if failures:
        print(f"invalid fixtures: failed {failures}")
        return 1
    count = len(list(INVALID.glob("*.json")))
    print(f"invalid fixtures: rejected {count}")
    return 0


def run_catalog_representation() -> int:
    failures = 0
    labs: list[Path] = []
    for track in sorted(LABS_DIR.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        for lab in sorted(track.iterdir()):
            if lab.is_dir() and (lab / "lab.yml").is_file():
                labs.append(lab)
    for lab in labs:
        result = load_lab_metadata(lab / "lab.yml")
        if result.record is None:
            failures += 1
            print(f"{lab.relative_to(REPO_ROOT)}: failed to load lab.yml")
            for diag in result.diagnostics:
                print(f"  {diag.format()}")
            continue
        errors = validate_lab_record(
            result.record.to_schema_dict(),
            path=str(lab.relative_to(REPO_ROOT)),
        )
        if errors:
            failures += 1
            print(f"{lab.relative_to(REPO_ROOT)}:")
            for line in errors:
                print(f"  {line}")
    if failures:
        print(f"catalog representation: failed {failures} labs")
        return 1
    print(f"catalog representation: passed {len(labs)} labs")
    return 0


def main() -> int:
    schema_errors = validate_schema_document(load_schema())
    if schema_errors:
        print("schema document:")
        for line in schema_errors:
            print(f"  {line}")
        return 1
    print("schema document: ok")

    for step in (run_valid_fixtures, run_invalid_fixtures, run_catalog_representation):
        code = step()
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
