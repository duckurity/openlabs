#!/usr/bin/env python3
"""Non-Docker tests for run_m2_tier1_lifecycle and evidence_artifact."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from cli_contract import validate_envelope  # noqa: E402
from diagnostic_registry import FLAG_PLAINTEXT_RE  # noqa: E402
from evidence_artifact import (  # noqa: E402
    assert_no_plaintext_secrets,
    bound_file,
    write_bounded_json,
)
import run_m2_tier1_lifecycle as tier1_mod  # noqa: E402
from run_m2_tier1_lifecycle import (  # noqa: E402
    LIFECYCLE_STEPS,
    run_openlabs_step,
    run_tier1_lifecycle,
)

def _temp_json(name: str) -> Path:
    directory = REPO_ROOT / ".tmp-test-artifacts"
    directory.mkdir(exist_ok=True)
    return directory / name


OK_ENVELOPE = {
    "version": "openlabs.command.v1",
    "command": "lab",
    "ok": True,
    "exit_code": 0,
    "dry_run": False,
    "data": {"action": "status", "lab": "duck-cross"},
    "diagnostics": [],
    "meta": {"redacted": False},
}


def _completed(code: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


def test_success_sequence_all_steps() -> None:
    calls: list[list[str]] = []

    def runner(argv: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        _ = cwd, timeout
        calls.append(list(argv))
        return _completed(0, json.dumps(OK_ENVELOPE))

    with mock.patch.object(
        tier1_mod,
        "_cleanup",
        return_value={"ok": True, "detail": "ok", "seconds": 0.0, "steps": []},
    ):
        out = _temp_json("success-evidence.json")
        code, doc = run_tier1_lifecycle(repo_root=REPO_ROOT, output=out, runner=runner)
    assert code == 0
    assert len(doc["steps"]) == len(LIFECYCLE_STEPS)
    assert all(step["ok"] for step in doc["steps"])
    assert calls[0][:4] == [str(REPO_ROOT / "openlabs"), "--json", "--non-interactive", "lab"]


def test_command_failure_partial_evidence() -> None:
    def runner(argv: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        _ = cwd, timeout
        if "setup" in argv:
            return _completed(1, "", "setup failed")
        return _completed(0, json.dumps(OK_ENVELOPE))

    with mock.patch.object(
        tier1_mod,
        "_cleanup",
        return_value={"ok": True, "detail": "ok", "seconds": 0.0, "steps": []},
    ):
        out = _temp_json("failure-evidence.json")
        code, doc = run_tier1_lifecycle(repo_root=REPO_ROOT, output=out, runner=runner)
    assert code != 0
    assert doc["steps"][0]["ok"] is False
    assert out.is_file()
    json.loads(out.read_text(encoding="utf-8"))


def test_malformed_json_from_cli() -> None:
    record = run_openlabs_step(
        [str(REPO_ROOT / "openlabs"), "--json", "--non-interactive", "lab", "status", "duck-cross"],
        step_name="lab_status",
        cwd=REPO_ROOT,
        runner=lambda argv, cwd, timeout: _completed(0, "not-json", ""),
    )
    assert record["ok"] is False
    assert "not valid JSON" in record["detail"]


def test_invalid_envelope_recorded() -> None:
    bad = {"version": "wrong", "command": "lab", "ok": True, "exit_code": 0, "dry_run": False, "data": {}, "diagnostics": []}
    record = run_openlabs_step(
        [str(REPO_ROOT / "openlabs"), "--json", "--non-interactive", "lab", "list"],
        step_name="lab_list",
        cwd=REPO_ROOT,
        runner=lambda argv, cwd, timeout: _completed(0, json.dumps(bad), ""),
    )
    assert record["ok"] is False
    assert record.get("envelope_errors")


def test_secret_redaction_in_artifact() -> None:
    secret = "duck{abcdefghijklmnopqrstuvwxyz}"
    path = _temp_json("redact-out.json")
    write_bounded_json(
        path,
        {"version": "openlabs.evidence.v1", "steps": [{"detail": secret}]},
        max_bytes=64 * 1024,
    )
    text = path.read_text(encoding="utf-8")
    assert not FLAG_PLAINTEXT_RE.search(text)
    assert_no_plaintext_secrets(path)


def test_size_limit_truncation() -> None:
    huge = {"version": "openlabs.evidence.v1", "steps": [{"stdout": "x" * 500_000}]}
    path = _temp_json("truncate-out.json")
    write_bounded_json(path, huge, max_bytes=4096)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("truncated") is True
    assert path.stat().st_size <= 4096 + 64


def test_cleanup_after_failure() -> None:
    cleanup_called = {"value": False}

    def fake_cleanup(ctx):  # noqa: ANN001
        _ = ctx
        cleanup_called["value"] = True
        return {"ok": True, "detail": "cleanup ok", "seconds": 0.0, "steps": []}

    def runner(argv: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        _ = cwd, timeout
        return _completed(1, "", "fail")

    with mock.patch.object(tier1_mod, "_cleanup", side_effect=fake_cleanup):
        code, doc = run_tier1_lifecycle(repo_root=REPO_ROOT, output=None, runner=runner)
    assert code != 0
    assert cleanup_called["value"]
    assert doc["cleanup"]["ok"] is True


def test_missing_executable_structured() -> None:
    def runner(argv: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        _ = argv, cwd, timeout
        raise FileNotFoundError("openlabs")

    record = run_openlabs_step(
        [str(REPO_ROOT / "openlabs"), "--json", "--non-interactive", "lab", "setup", "duck-cross"],
        step_name="lab_setup",
        cwd=REPO_ROOT,
        runner=runner,
    )
    assert record["diagnostic_key"] == "environment.docker.client_missing"


def test_timeout_structured() -> None:
    def runner(argv: list[str], *, cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
        _ = argv, cwd, timeout
        raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)

    record = run_openlabs_step(
        [str(REPO_ROOT / "openlabs"), "--json", "--non-interactive", "lab", "setup", "duck-cross"],
        step_name="lab_setup",
        cwd=REPO_ROOT,
        runner=runner,
    )
    assert record["exit_code"] == 124


def test_bound_prove_wrapper() -> None:
    raw = _temp_json("raw-prove.json")
    dest = _temp_json("bounded-prove.json")
    raw.write_text(json.dumps({"lab": "duck-cross", "steps": []}) + "\n", encoding="utf-8")
    bound_file(raw, dest)
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["meta"]["redacted"] is True


def test_valid_envelope_in_success_step() -> None:
    record = run_openlabs_step(
        [str(REPO_ROOT / "openlabs"), "--json", "--non-interactive", "lab", "status", "duck-cross"],
        step_name="lab_status",
        cwd=REPO_ROOT,
        runner=lambda argv, cwd, timeout: _completed(0, json.dumps(OK_ENVELOPE), ""),
    )
    assert record["ok"] is True
    errors = validate_envelope(record["envelope"], path="test.json")
    assert not errors


def main() -> int:
    tests = [
        test_success_sequence_all_steps,
        test_command_failure_partial_evidence,
        test_malformed_json_from_cli,
        test_invalid_envelope_recorded,
        test_secret_redaction_in_artifact,
        test_size_limit_truncation,
        test_cleanup_after_failure,
        test_missing_executable_structured,
        test_timeout_structured,
        test_bound_prove_wrapper,
        test_valid_envelope_in_success_step,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"tier1 lifecycle tests: failed {failures}", file=sys.stderr)
        return 1
    print(f"tier1 lifecycle tests: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
