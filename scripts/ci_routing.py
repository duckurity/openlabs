"""Compute labs workflow job scope from changed paths (mirrors labs.yml detect-changes)."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "labs.yml"

FILTER_BLOCK_RE = re.compile(
    r"^\s+filters:\s*\|\s*\n((?:^\s+[^\n]+\n)+?)(?=^\s+- id: scope)",
    re.MULTILINE,
)


def _parse_filters_block(body: str) -> dict[str, tuple[str, ...]]:
    filters: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        head = re.match(r"^            (\w+):\s*$", line)
        if head:
            current = head.group(1)
            filters.setdefault(current, [])
            continue
        item = re.match(r"^              - '([^']+)'\s*$", line)
        if item and current:
            filters[current].append(item.group(1))
    return {name: tuple(patterns) for name, patterns in filters.items()}


def load_path_filters(workflow_text: str | None = None) -> dict[str, tuple[str, ...]]:
    text = workflow_text if workflow_text is not None else WORKFLOW.read_text(encoding="utf-8")
    block = FILTER_BLOCK_RE.search(text)
    if not block:
        raise ValueError("labs.yml: could not find paths-filter filters block")
    filters = _parse_filters_block(block.group(1))
    required = {
        "labs",
        "lab_scripts",
        "workflow",
        "security_scripts",
        "reference",
        "content",
        "pdf",
        "compose",
    }
    missing = required - filters.keys()
    if missing:
        raise ValueError(f"labs.yml: missing filters {sorted(missing)}")
    for name, patterns in filters.items():
        if not patterns:
            raise ValueError(f"labs.yml: filter {name} has no patterns")
    return filters


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    parts: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i : i + 1] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i : i + 1] == "?":
            parts.append("[^/]")
            i += 1
        else:
            j = i
            while j < len(pattern) and pattern[j] not in "*?":
                j += 1
            parts.append(re.escape(pattern[i:j]))
            i = j
    return re.compile("^" + "".join(parts) + "$")


def path_matches_pattern(path: str, pattern: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    if pattern.endswith("/**"):
        prefix = pattern[: -len("/**")]
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True
        return False
    return _glob_to_regex(pattern).fullmatch(normalized) is not None


def match_filters(
    changed_files: list[str],
    filters: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, bool]:
    groups = filters if filters is not None else load_path_filters()
    result: dict[str, bool] = {}
    for name, patterns in groups.items():
        hit = False
        for path in changed_files:
            for pattern in patterns:
                if path_matches_pattern(path, pattern):
                    hit = True
                    break
            if hit:
                break
        result[name] = hit
    return result


def bool_or(*values: bool) -> bool:
    return any(values)


def compute_pull_request_scope(
    *,
    actor: str,
    changed_files: list[str],
    filters: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, bool]:
    if actor == "dependabot[bot]":
        return {
            f"run_{key}": True
            for key in ("validate", "compose", "reference", "security", "content", "pdf")
        }

    matched = match_filters(changed_files, filters)
    labs = matched["labs"]
    lab_scripts = matched["lab_scripts"]
    workflow = matched["workflow"]
    security_scripts = matched["security_scripts"]
    reference = matched["reference"]
    content = matched["content"]
    pdf = matched["pdf"]
    compose = matched["compose"]

    return {
        "run_validate": bool_or(labs, lab_scripts, workflow),
        "run_compose": bool_or(labs, compose, workflow),
        "run_reference": bool_or(reference, workflow),
        "run_security": bool_or(labs, security_scripts, workflow),
        "run_content": bool_or(content, workflow),
        "run_pdf": bool_or(pdf, workflow),
    }


def labs_workflow_permissions_read_only(workflow_text: str | None = None) -> bool:
    text = workflow_text if workflow_text is not None else WORKFLOW.read_text(encoding="utf-8")
    if re.search(r"^permissions:\s*\n\s+contents:\s*read\s*$", text, re.MULTILINE):
        return True
    return "contents: read" in text and "contents: write" not in text
