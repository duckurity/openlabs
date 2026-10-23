#!/usr/bin/env python3
"""Validate M2 player documentation coverage."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
WIKI = REPO_ROOT / "wiki"

sys.path.insert(0, str(SCRIPTS))

from diagnostic_registry import load_registry, requires_explain_metadata  # noqa: E402

CLI_GUIDE = WIKI / "OpenLabs-CLI.md"
TIER_GUIDE = WIKI / "Platform-Support-Tiers.md"
TROUBLESHOOTING = WIKI / "CLI-Troubleshooting.md"

MUTATING_DRY_RUN_MARKERS = (
    "setup",
    "doctor --fix",
    "issue bundle",
    "lab setup",
    "lab start",
    "lab verify",
    "lab stop",
    "lab reset",
)


def test_runtime_ids_in_troubleshooting() -> bool:
    text = TROUBLESHOOTING.read_text(encoding="utf-8")
    failures: list[str] = []
    for entry in load_registry().entries:
        if not requires_explain_metadata(entry):
            continue
        if entry.id not in text:
            failures.append(entry.id)
    if failures:
        print(f"CLI-Troubleshooting.md missing runtime ids: {', '.join(failures)}")
        return False
    return True


def test_cli_guide_dry_run_coverage() -> bool:
    text = CLI_GUIDE.read_text(encoding="utf-8")
    if "--dry-run" not in text:
        print("OpenLabs-CLI.md must document --dry-run")
        return False
    missing = [marker for marker in MUTATING_DRY_RUN_MARKERS if marker not in text]
    if missing:
        print(f"OpenLabs-CLI.md missing mutating command markers: {', '.join(missing)}")
        return False
    return True


def test_tier_limitations() -> bool:
    text = TIER_GUIDE.read_text(encoding="utf-8")
    lowered = text.lower()
    required = ("tier 2", "tier 3", "no release guarantee", "missing evidence")
    missing = [phrase for phrase in required if phrase not in lowered]
    if missing:
        print(f"Platform-Support-Tiers.md missing: {', '.join(missing)}")
        return False
    if "experimental" not in text.lower() or "not lifecycle-guaranteed" not in text.lower():
        print("Platform-Support-Tiers.md must state experimental labs are not lifecycle-guaranteed")
        return False
    return True


def main() -> int:
    failures = 0
    for check in (
        test_runtime_ids_in_troubleshooting,
        test_cli_guide_dry_run_coverage,
        test_tier_limitations,
    ):
        if not check():
            failures += 1
    if failures:
        print(f"m2 docs tests: failed {failures}", file=sys.stderr)
        return 1
    print("m2 docs tests: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
