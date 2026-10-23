#!/usr/bin/env python3
"""Tests for catalog discovery and lab selection (M2-04)."""

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
from openlabs_cli.lab_discovery import (  # noqa: E402
    LabSelectionError,
    ResolvedLab,
    discover_catalog_labs,
    list_catalog,
    resolve_lab,
)


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


FIXTURE_FLAG_HASH = "1001444936d1ac7055a213bde05726f86f482f72555d2e6bb8dde40cbabbeb06"


def _write_lab(root: Path, track: str, name: str, *, status: str, slug: str | None = None) -> Path:
    lab = root / "labs" / track / name
    lab.mkdir(parents=True, exist_ok=True)
    slug = slug or name
    (lab / "lab.yml").write_text(
        "\n".join(
            [
                "contract_version: 1",
                f"name: {slug}",
                f"track: {track}",
                "difficulty: easy",
                "description: fixture lab",
                f"flag_hash: {FIXTURE_FLAG_HASH}",
                f"status: {status}",
                "techniques: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (lab / "README.md").write_text("# fixture\n", encoding="utf-8")
    (lab / "docker-compose.yml").write_text(
        "services:\n  web:\n    ports:\n      - \"127.0.0.1:9001:9001\"\n",
        encoding="utf-8",
    )
    return lab


def _mini_repo(tmp: Path) -> Path:
    (tmp / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
    (tmp / "scripts").mkdir()
    (tmp / "scripts" / "validate.py").write_text("", encoding="utf-8")
    (tmp / "labs").mkdir()
    return tmp


def test_list_json_baseline_counts() -> None:
    code, out, _err = _run(["--json", "lab", "list"])
    assert code == 0
    payload = _json(out, label="list.json")
    assert payload["data"]["action"] == "list"
    assert payload["data"]["counts"] == {"supported": 1, "experimental": 19}
    supported = payload["data"]["supported"]
    assert len(supported) == 1
    assert supported[0]["slug"] == "duck-cross"
    assert supported[0]["lifecycle_eligible"] is True
    assert supported[0]["port"] == 8377
    paths = {item["path"] for item in payload["data"]["experimental"]}
    assert not any("duckmarket" in path for path in paths)


def test_list_human_sections() -> None:
    code, out, err = _run(["lab", "list"])
    assert code == 0
    assert err == ""
    assert "supported (1):" in out
    assert "experimental (19):" in out
    assert "duck-cross" in out


def test_resolve_slug_and_path() -> None:
    resolved = resolve_lab(REPO_ROOT, "duck-cross")
    assert isinstance(resolved, ResolvedLab)
    assert resolved.entry["slug"] == "duck-cross"
    by_path = resolve_lab(REPO_ROOT, "labs/web/duck-cross")
    assert isinstance(by_path, ResolvedLab)
    assert by_path.entry["slug"] == "duck-cross"


def test_resolve_rejects_uncatalogued_and_escape() -> None:
    result = resolve_lab(REPO_ROOT, "labs/web/duckmarket")
    assert isinstance(result, LabSelectionError)
    assert "not catalogued" in result.message

    with tempfile.TemporaryDirectory() as tmp:
        root = _mini_repo(Path(tmp))
        _write_lab(root, "web", "good", status="supported")
        outside = Path(tmp) / "outside_repo"
        outside.mkdir()
        link = root / "labs" / "web" / "escape"
        link.symlink_to(outside, target_is_directory=True)
        escaped = resolve_lab(root, "labs/web/escape")
        assert isinstance(escaped, LabSelectionError)
        assert "escapes catalog root" in escaped.message


def test_fixture_catalog_independent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _mini_repo(Path(tmp))
        _write_lab(root, "web", "alpha", status="supported", slug="alpha")
        lab = _write_lab(root, "web", "beta", status="experimental", slug="beta")
        compose = lab / "docker-compose.yml"
        compose.write_text(
            compose.read_text(encoding="utf-8")
            + "    container_name: beta-fixed\n",
            encoding="utf-8",
        )
        payload = list_catalog(root)
        assert payload["counts"] == {"supported": 1, "experimental": 1}
        assert payload["experimental"][0]["blockers"] == ["container_name"]
        assert payload["supported"][0]["lifecycle_eligible"] is True
        assert len(discover_catalog_labs(root)) == 2


def test_container_name_blockers_without_docker() -> None:
    payload = list_catalog(REPO_ROOT)
    blocked = [item for item in payload["experimental"] if item["blockers"]]
    assert blocked
    assert all("container_name" in item["blockers"] for item in blocked)


def main() -> int:
    tests = [
        test_list_json_baseline_counts,
        test_list_human_sections,
        test_resolve_slug_and_path,
        test_resolve_rejects_uncatalogued_and_escape,
        test_fixture_catalog_independent,
        test_container_name_blockers_without_docker,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL {test.__name__}: {exc}", file=sys.stderr)
    if failures:
        print(f"openlabs lab discovery: failed {failures} tests", file=sys.stderr)
        return 1
    print(f"openlabs lab discovery: passed {len(tests)} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
