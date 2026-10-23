#!/usr/bin/env python3
"""Unit tests for status-aware lab inventory reports and exit codes."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lab_inventory import (  # noqa: E402
    EXIT_BLOCKING,
    EXIT_CATALOG,
    EXIT_OK,
    LabRecord,
    build_inventory_report,
    exit_code_for_report,
    in_selection,
)


def record(
    path: str,
    status: str,
    *,
    ok: bool,
    errors: list[str] | None = None,
) -> LabRecord:
    name = path.rsplit("/", 1)[-1]
    return LabRecord(
        path=path,
        name=name,
        status=status,
        ok=ok,
        errors=list(errors or []),
    )


def test_supported_failure_blocks() -> None:
    records = [
        record("labs/web/good", "supported", ok=True),
        record("labs/web/bad", "supported", ok=False, errors=["missing README.md"]),
    ]
    report = build_inventory_report(
        records, selection="all", uncatalogued=[], tool="validate"
    )
    assert len(report["blocking"]) == 1
    assert report["blocking"][0]["path"] == "labs/web/bad"
    assert exit_code_for_report(report) == EXIT_BLOCKING


def test_experimental_failure_advisory_only() -> None:
    records = [
        record("labs/web/good", "supported", ok=True),
        record("labs/web/wip", "experimental", ok=False, errors=["missing README.md"]),
    ]
    report = build_inventory_report(
        records, selection="all", uncatalogued=[], tool="validate"
    )
    assert not report["blocking"]
    assert len(report["advisory"]) == 1
    assert exit_code_for_report(report) == EXIT_OK


def test_missing_status_blocks() -> None:
    records = [
        record("labs/web/good", "supported", ok=True),
        record(
            "labs/web/nostatus",
            "invalid",
            ok=False,
            errors=["lab.yml: missing or empty `status`"],
        ),
    ]
    report = build_inventory_report(
        records, selection="all", uncatalogued=[], tool="validate"
    )
    assert len(report["blocking"]) == 1
    assert exit_code_for_report(report) == EXIT_BLOCKING


def test_uncatalogued_listed() -> None:
    records = [record("labs/web/good", "supported", ok=True)]
    uncatalogued = [REPO_ROOT / "labs/web/draft"]
    report = build_inventory_report(
        records,
        selection="all",
        uncatalogued=uncatalogued,
        tool="validate",
    )
    assert report["uncatalogued"] == ["labs/web/draft"]


def test_selection_filters_json_results() -> None:
    records = [
        record("labs/web/a", "supported", ok=True),
        record("labs/web/b", "experimental", ok=True),
    ]
    report = build_inventory_report(
        records, selection="supported", uncatalogued=[], tool="validate"
    )
    assert len(report["results"]) == 1
    assert report["results"][0]["status"] == "supported"
    assert in_selection("experimental", "supported") is False


def test_empty_supported_catalog() -> None:
    records = [record("labs/web/wip", "experimental", ok=True)]
    report = build_inventory_report(
        records, selection="all", uncatalogued=[], tool="validate"
    )
    assert report["catalog"]["supported_count"] == 0
    assert exit_code_for_report(report) == EXIT_CATALOG


def main() -> int:
    tests = [
        test_supported_failure_blocks,
        test_experimental_failure_advisory_only,
        test_missing_status_blocks,
        test_uncatalogued_listed,
        test_selection_filters_json_results,
        test_empty_supported_catalog,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"{test.__name__}: {exc}")
    if failures:
        print(f"failed {failures} of {len(tests)} inventory tests")
        return 1
    print(f"passed {len(tests)} inventory tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
