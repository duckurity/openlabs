#!/usr/bin/env python3
"""Validate GitHub issue form YAML under .github/ISSUE_TEMPLATE/."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = REPO_ROOT / ".github" / "ISSUE_TEMPLATE"
LABELS_FIXTURE = (
    REPO_ROOT / "scripts" / "fixtures" / "issue_form_labels.json"
)
PRIVATE_ADVISORY = (
    "https://github.com/duckurity/openlabs/security/advisories/new"
)


def load_allowed_labels() -> set[str]:
    data = json.loads(LABELS_FIXTURE.read_text(encoding="utf-8"))
    return set(data["labels"])


def forbidden_urls() -> list[str]:
    data = json.loads(LABELS_FIXTURE.read_text(encoding="utf-8"))
    return list(data.get("forbidden_contact_url_substrings", []))


def extract_labels(text: str) -> list[str]:
    labels: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("labels:"):
            continue
        rest = line.split(":", 1)[1].strip()
        if rest.startswith("["):
            labels.extend(re.findall(r'"([^"]+)"', rest))
            labels.extend(re.findall(r"'([^']+)'", rest))
        elif not rest:
            offset = index + 1
            while offset < len(lines) and lines[offset].startswith("  - "):
                labels.append(lines[offset].split("-", 1)[1].strip())
                offset += 1
        break
    return labels


def validate_form(path: Path, allowed: set[str]) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for key in ("name:", "description:", "body:"):
        if key not in text:
            errors.append(f"{path.name}: missing {key.rstrip(':')}")
    for label in extract_labels(text):
        if label not in allowed:
            errors.append(f"{path.name}: unknown label {label!r}")
    if "type: markdown" not in text and path.name != "config.yml":
        errors.append(f"{path.name}: missing redaction or security markdown block")
    if path.name == "lab-bug.yml":
        for needle in (
            "id: docker-version",
            "id: compose-version",
            "id: failing-command",
            "id: command-output",
            "id: architecture",
        ):
            if needle not in text:
                errors.append(f"{path.name}: missing field {needle}")
    return errors


def validate_config(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if "blank_issues_enabled: false" not in text:
        errors.append("config.yml: blank_issues_enabled must be false")
    if PRIVATE_ADVISORY not in text:
        errors.append("config.yml: missing private vulnerability reporting link")
    for forbidden in forbidden_urls():
        if forbidden in text:
            errors.append(f"config.yml: forbidden contact URL contains {forbidden!r}")
    if "template=question.yml" not in text:
        errors.append("config.yml: question form link missing")
    return errors


def main() -> int:
    if not TEMPLATE_DIR.is_dir():
        print("missing .github/ISSUE_TEMPLATE", file=sys.stderr)
        return 2
    allowed = load_allowed_labels()
    errors: list[str] = []
    config = TEMPLATE_DIR / "config.yml"
    if config.is_file():
        errors.extend(validate_config(config))
    for path in sorted(TEMPLATE_DIR.glob("*.yml")):
        if path.name == "config.yml":
            continue
        errors.extend(validate_form(path, allowed))
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"issue form validation failed ({len(errors)} problems)", file=sys.stderr)
        return 1
    count = len(list(TEMPLATE_DIR.glob("*.yml"))) - 1
    print(f"issue forms ok ({count} templates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
