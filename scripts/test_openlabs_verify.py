#!/usr/bin/env python3
"""Tests for openlabs lab verify (M2-08)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENLABS = REPO_ROOT / "openlabs"
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cli_contract import validate_envelope  # noqa: E402
from openlabs_cli.commands.lab import handle_lab  # noqa: E402
from openlabs_cli.context import CliContext  # noqa: E402
from openlabs_cli.lab_discovery import resolve_lab  # noqa: E402
from openlabs_cli.lab_verification import VerificationReport, run_verification  # noqa: E402

FLAG_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")


def _run(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        [str(OPENLABS), *args],
        cwd=REPO_ROOT,
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


def test_dry_run_verify_envelope() -> None:
    code, out, _err = _run(["--json", "--dry-run", "lab", "verify", "duck-cross"])
    assert code == 0
    payload = _json(out, label="verify-dry-run.json")
    assert payload["data"]["action"] == "verify"
    assert payload["meta"]["reset_safe"] is True


def test_unknown_verify_flag_rejected() -> None:
    code, _out, err = _run(["lab", "verify", "duck-cross", "--nope"])
    assert code != 0
    assert "unknown option" in (err or _out).lower() or code == 2


def test_partial_level_stops_after_l3() -> None:
    ctx = CliContext(repo_root=REPO_ROOT, runner=None)
    resolved = resolve_lab(REPO_ROOT, "duck-cross")
    assert not hasattr(resolved, "message")

    def fake_run(*_args, **_kwargs) -> VerificationReport:
        report = VerificationReport(lab="duck-cross", project="openlabs-test", port=8377)
        report.add_level("L0", True, 0.0, "metadata valid")
        report.add_level("L1", True, 0.0, "compose ok")
        report.add_level("L2", True, 0.0, "build ok")
        report.add_level("L3", True, 0.0, "ready")
        return report

    with patch("openlabs_cli.lab_verify.run_verification", side_effect=fake_run):
        result = handle_lab(ctx, ["verify", "duck-cross", "--level", "L3"])
    assert result.ok
    levels = [step["level"] for step in result.data["levels"]]
    assert levels == ["L0", "L1", "L2", "L3"]
    assert "L4" not in levels


def test_experimental_lab_not_supported_verification() -> None:
    ctx = CliContext(repo_root=REPO_ROOT, runner=None)
    experimental = next(
        lab
        for lab in json.loads(
            subprocess.run(
                [str(OPENLABS), "--json", "lab", "list"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            ).stdout
        )["data"]["experimental"]
    )
    slug = experimental["slug"]
    with patch(
        "openlabs_cli.lab_verify.run_verification",
        return_value=VerificationReport(lab=slug, project="p", port=1, levels=[]),
    ):
        result = handle_lab(ctx, ["verify", slug])
    assert not result.ok
    assert result.data.get("supported_verification") is False
    assert any(d.key == "lifecycle.lab.unsupported_operation" for d in result.diagnostics)


def test_failure_output_has_no_plaintext_flag() -> None:
    from openlabs_cli.lab_verification import VerificationFailure

    ctx = CliContext(repo_root=REPO_ROOT, runner=None)
    resolved = resolve_lab(REPO_ROOT, "duck-cross")
    report = VerificationReport(lab="duck-cross", project="p", port=8377)
    report.add_level("L5", False, 0.1, "checker rejected intended flag")

    def boom(*_a, **_k):
        raise VerificationFailure("L5", "checker rejected intended flag", report)

    with patch("openlabs_cli.lab_verify.run_verification", side_effect=boom):
        result = handle_lab(ctx, ["verify", "duck-cross"])
    blob = json.dumps(result.data) + " ".join(result.human_lines)
    for diag in result.diagnostics:
        blob += diag.message
    assert not FLAG_RE.search(blob)


def main() -> int:
    tests = [
        test_dry_run_verify_envelope,
        test_unknown_verify_flag_rejected,
        test_partial_level_stops_after_l3,
        test_experimental_lab_not_supported_verification,
        test_failure_output_has_no_plaintext_flag,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs lab verify: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs lab verify: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
