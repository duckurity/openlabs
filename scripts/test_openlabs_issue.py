#!/usr/bin/env python3
"""Tests for openlabs issue explain and bundle (M2-03)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENLABS = REPO_ROOT / "openlabs"
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cli_contract import validate_envelope  # noqa: E402
from diagnostic_registry import load_registry, requires_explain_metadata  # noqa: E402


def _run(args: list[str], *, cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        [str(OPENLABS), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _json(stdout: str, *, label: str) -> dict:
    data = json.loads(stdout)
    errors = validate_envelope(data, path=label)
    if errors:
        raise AssertionError("\n".join(errors))
    return data


def test_explain_known_contract_id_json() -> None:
    code, out, _err = _run(["--json", "issue", "explain", "OL-0004"])
    assert code == 0
    payload = _json(out, label="explain.json")
    assert payload["data"]["id"] == "OL-0004"
    assert payload["data"]["cause"]
    assert payload["data"]["evidence"]


def test_explain_unknown_id_json() -> None:
    code, out, _err = _run(["--json", "issue", "explain", "OL-9999"])
    assert code == 1
    payload = _json(out, label="unknown.json")
    assert payload["diagnostics"][0]["key"] == "lifecycle.cli.unknown_diagnostic"


def test_explain_human() -> None:
    code, out, err = _run(["issue", "explain", "OL-0004"])
    assert code == 0
    assert "OL-0004" in out
    assert err == ""


def test_bundle_dry_run_json() -> None:
    code, out, _err = _run(["--json", "--dry-run", "issue", "bundle", "duck-cross"])
    assert code == 0
    payload = _json(out, label="bundle-dry.json")
    assert payload["dry_run"] is True
    assert payload["data"]["action"] == "bundle"
    assert "/home/" not in json.dumps(payload)


def test_bundle_writes_redacted_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "AGENTS.md").write_text("x", encoding="utf-8")
        (root / "scripts").mkdir()
        (root / "scripts" / "validate.py").write_text("", encoding="utf-8")
        (root / "labs").mkdir()
        code, _out, _err = _run(["issue", "bundle"], cwd=root)
        assert code == 0
        bundles = list((root / ".openlabs" / "bundles").glob("*.json"))
        assert len(bundles) == 1
        text = bundles[0].read_text(encoding="utf-8")
        assert "/home/" not in text
        assert "duck{" not in text


def test_runtime_registry_explain_metadata() -> None:
    registry = load_registry()
    for entry in registry.entries:
        if not requires_explain_metadata(entry):
            continue
        assert entry.docs_anchor, entry.id
        assert entry.area, entry.id
        assert entry.manual_fix or entry.safe_fix, entry.id


def main() -> int:
    tests = [
        test_explain_known_contract_id_json,
        test_explain_unknown_id_json,
        test_explain_human,
        test_bundle_dry_run_json,
        test_bundle_writes_redacted_file,
        test_runtime_registry_explain_metadata,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs issue: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs issue: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
