"""Per-lab verification adapters for smoke (L4) and intended solve (L5)."""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

from check import flag_stage
from openlabs_contract import read_player_flag_hashes

FLAG_RE = re.compile(r"duck\{[a-z0-9_]{16,40}\}")


def has_supported_l5(slug: str) -> bool:
    return slug == "duck-cross"


def _http_get(base_url: str, path: str, *, timeout: float = 10.0) -> tuple[int, str]:
    request = urllib.request.Request(f"{base_url}{path}", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        return error.code, body
    except OSError:
        return 0, ""


def _entry_ready(base_url: str) -> bool:
    status, body = _http_get(base_url, "/")
    return status == 200 and "duck cross" in body.lower()


def smoke_l4(slug: str, base_url: str) -> tuple[bool, str]:
    if slug != "duck-cross":
        return False, "no L4 smoke adapter registered for this lab"
    if not _entry_ready(base_url):
        return False, "player entry page failed"
    status, body = _http_get(base_url, "/api/reports/1")
    if status != 200 or "mill lane" not in body.lower():
        return False, "public report workflow failed"
    return True, "entry page and public report API ok"


def setup_smoke_l4(slug: str, base_url: str) -> tuple[bool, str]:
    """Setup-time check: entry page plus one public API (no L5)."""
    if slug != "duck-cross":
        return False, "no setup smoke adapter registered for this lab"
    if not _entry_ready(base_url):
        return False, "player entry page failed"
    status, body = _http_get(base_url, "/api/reports/1")
    if status != 200 or "mill lane" not in body.lower():
        return False, "public report workflow failed"
    return True, "supported verification passed"


def intended_l5(slug: str, base_url: str, lab_dir: Path) -> tuple[bool, str]:
    if slug != "duck-cross":
        return False, "no L5 intended-solve adapter registered for this lab"
    status, body = _http_get(base_url, "/api/reports/6")
    if status != 200:
        return False, "restricted report not reachable"
    match = FLAG_RE.search(body)
    if not match:
        return False, "no flag in intended solve path"
    flag = match.group(0)
    for report_id in ("1", "2", "3", "4", "5"):
        _, public_body = _http_get(base_url, f"/api/reports/{report_id}")
        if FLAG_RE.search(public_body):
            return False, f"flag leaked in public report {report_id}"
    stage = flag_stage(flag, read_player_flag_hashes(lab_dir))
    if stage != "final":
        return False, "checker rejected intended flag"
    return True, "intended IDOR path verifies with check.py"
