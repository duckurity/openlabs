"""Shared lab catalog inventory helpers for validate.py and score_lab.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_VERSION = "openlabs.inventory.v1"
STATUS_SELECTIONS = frozenset({"all", "supported", "experimental"})
STATUSES = frozenset({"experimental", "supported"})

# Exit codes (documented contract)
EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_USAGE = 2
EXIT_CATALOG = 3


@dataclass
class LabRecord:
    path: str
    name: str
    status: str
    ok: bool
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "status": self.status,
            "ok": self.ok,
            "errors": list(self.errors),
        }


def lab_status(lab: Path) -> str:
    from openlabs_contract import load_lab_metadata

    result = load_lab_metadata(lab / "lab.yml")
    if result.record is None:
        return "invalid"
    raw = result.record.status.strip()
    if raw in STATUSES:
        return raw
    return "invalid"


def lab_name(lab: Path) -> str:
    from openlabs_contract import load_lab_metadata

    result = load_lab_metadata(lab / "lab.yml")
    if result.record is None:
        return lab.name
    name = result.record.name.strip()
    return name or lab.name


def in_selection(status: str, selection: str) -> bool:
    if selection == "all":
        return True
    return status == selection


def build_inventory_report(
    records: list[LabRecord],
    *,
    selection: str,
    uncatalogued: list[Path],
    tool: str,
    catalog: dict[str, int] | None = None,
) -> dict[str, Any]:
    if catalog is None:
        supported = [r for r in records if r.status == "supported"]
        experimental = [r for r in records if r.status == "experimental"]
        invalid = [r for r in records if r.status not in STATUSES]
        catalog = {
            "supported_count": len(supported),
            "experimental_count": len(experimental),
            "invalid_status_count": len(invalid),
        }

    blocking = [r for r in records if not r.ok and r.status != "experimental"]
    advisory = [r for r in records if not r.ok and r.status == "experimental"]

    return {
        "version": REPORT_VERSION,
        "tool": tool,
        "selection": selection,
        "catalog": catalog,
        "uncatalogued": [p.relative_to(REPO_ROOT).as_posix() for p in uncatalogued],
        "results": [r.to_dict() for r in records if in_selection(r.status, selection)],
        "blocking": [r.to_dict() for r in blocking],
        "advisory": [r.to_dict() for r in advisory],
    }


def exit_code_for_report(report: dict[str, Any]) -> int:
    if report["catalog"]["supported_count"] == 0:
        return EXIT_CATALOG
    if report["blocking"]:
        return EXIT_BLOCKING
    return EXIT_OK


def format_terminal_summary(report: dict[str, Any]) -> str:
    lines: list[str] = []
    blocking = report["blocking"]
    advisory = report["advisory"]
    if blocking:
        lines.append("blocking failures (supported):")
        for item in blocking:
            lines.append(f"  {item['path']}:")
            for error in item["errors"]:
                lines.append(f"    - {error}")
    else:
        lines.append("blocking failures (supported): none")

    if advisory:
        lines.append("advisory findings (experimental):")
        for item in advisory:
            lines.append(f"  {item['path']}:")
            for error in item["errors"]:
                lines.append(f"    - {error}")
    else:
        lines.append("advisory findings (experimental): none")

    uncatalogued = report["uncatalogued"]
    if uncatalogued:
        lines.append(
            f"uncatalogued directories ({len(uncatalogued)}; not in public catalog):"
        )
        for path in uncatalogued:
            lines.append(f"  {path}")

    cat = report["catalog"]
    lines.append(
        "catalog: "
        f"{cat['supported_count']} supported, "
        f"{cat['experimental_count']} experimental"
    )
    return "\n".join(lines)


def format_github_step_summary(report: dict[str, Any]) -> str:
    lines = [
        "## Lab inventory",
        "",
        f"- Report version: `{report['version']}`",
        f"- Tool: `{report['tool']}`",
        f"- Selection: `{report['selection']}`",
        "",
        "### Blocking (supported)",
    ]
    if report["blocking"]:
        for item in report["blocking"]:
            lines.append(f"- `{item['path']}`: {'; '.join(item['errors'])}")
    else:
        lines.append("- none")

    lines.extend(["", "### Advisory (experimental)"])
    if report["advisory"]:
        for item in report["advisory"]:
            lines.append(f"- `{item['path']}`: {'; '.join(item['errors'])}")
    else:
        lines.append("- none")

    if report["uncatalogued"]:
        lines.extend(["", "### Uncatalogued"])
        for path in report["uncatalogued"]:
            lines.append(f"- `{path}`")

    return "\n".join(lines) + "\n"


def discover_catalog() -> tuple[list[Path], list[Path]]:
    from validate import discover_labs, discover_uncatalogued_dirs

    return discover_labs(), discover_uncatalogued_dirs()


def catalog_counts(labs: list[Path]) -> dict[str, int]:
    supported = experimental = invalid = 0
    for lab in labs:
        status = lab_status(lab)
        if status == "supported":
            supported += 1
        elif status == "experimental":
            experimental += 1
        else:
            invalid += 1
    return {
        "supported_count": supported,
        "experimental_count": experimental,
        "invalid_status_count": invalid,
    }
