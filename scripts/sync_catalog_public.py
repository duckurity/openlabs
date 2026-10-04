#!/usr/bin/env python3
"""Regenerate public catalog counts and listings from lab.yml metadata.

Single entry point for README, wiki, site index, badge inputs, and JSON
evidence. Uncatalogued directories stay out of public totals.

    python3 scripts/sync_catalog_public.py --write
    python3 scripts/sync_catalog_public.py --check

Exit codes:
    0  ok
    1  stale generated output (--check)
    2  usage error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
GENERATED_DIR = SCRIPTS / "generated"
JSON_PATH = GENERATED_DIR / "catalog-public.json"
GENERATOR = "scripts/sync_catalog_public.py"

sys.path.insert(0, str(SCRIPTS))

from catalog_public import build_public_catalog  # noqa: E402

MARKER_START = "<!-- catalog-public:start -->"
MARKER_END = "<!-- catalog-public:end -->"
SITE_INDEX_MARKER_START = "{/* catalog-public:start */}"
SITE_INDEX_MARKER_END = "{/* catalog-public:end */}"
MARKER_BADGES_START = "<!-- catalog-public:badges-start -->"
MARKER_BADGES_END = "<!-- catalog-public:badges-end -->"


def badge_asset_version(stem: str, *, variant: str) -> str:
    path = REPO_ROOT / ".github/assets/badges" / f"{stem}-{variant}.svg"
    if not path.is_file():
        return "00000000"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]

CHIP_RE = re.compile(
    r'<picture><source media="\(prefers-color-scheme: dark\)" '
    r'srcset="\.github/assets/badges/chip-(easy|medium|hard|insane)-dark\.svg\?v=[0-9a-f]+">'
    r'<img src="\.github/assets/badges/chip-\1-light\.svg\?v=[0-9a-f]+" '
    r'alt="([A-Z]+)" height="18"></picture>'
)


def load_chip_snippets(readme: Path) -> dict[str, str]:
    text = readme.read_text(encoding="utf-8")
    chips: dict[str, str] = {}
    for match in CHIP_RE.finditer(text):
        chips[match.group(1)] = match.group(0)
    if len(chips) < 4:
        raise ValueError("README missing difficulty chip picture snippets")
    return chips


def difficulty_chip(chips: dict[str, str], difficulty: str) -> str:
    key = difficulty.strip().lower()
    if key not in chips:
        return f"`{key}`"
    return chips[key]


def replace_block(text: str, start: str, end: str, body: str) -> str:
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL,
    )
    block = f"{start}\n{body}\n{end}"
    if not pattern.search(text):
        raise ValueError(f"missing marker block {start} … {end}")
    return pattern.sub(block, text, count=1)


def render_table_rows(
    labs: list[dict], chips: dict[str, str], *, show_status: bool
) -> str:
    lines = []
    for lab in labs:
        diff = difficulty_chip(chips, lab["difficulty"])
        if show_status:
            lines.append(
                f"| [`{lab['name']}`]({lab['path']}) | `{lab['status']}` "
                f"| `{lab['track']}` | {diff} | {lab['description']} |"
            )
        else:
            lines.append(
                f"| [`{lab['name']}`]({lab['path']}) | `{lab['track']}` "
                f"| {diff} | {lab['description']} |"
            )
    return "\n".join(lines)


def render_readme_body(catalog: dict, chips: dict[str, str]) -> str:
    supported = catalog["supported_count"]
    experimental = catalog["experimental_count"]
    header = (
        f"<sub>{supported} supported · {experimental} experimental</sub>\n\n"
        "<div align=\"center\">\n\n"
        "**Supported** labs have documented L0–L6 evidence on file. "
        f"**{experimental} experimental** labs are runnable but not promoted. "
        "Experimental entries are not guaranteed supported.\n\n"
    )
    if catalog["supported"]:
        header += (
            "| Lab | Track | Difficulty | Description |\n"
            "|:---:|:---:|:---:|:---|\n"
            + render_table_rows(catalog["supported"], chips, show_status=False)
            + "\n\n"
        )
    if catalog["experimental"]:
        header += (
            "### Experimental\n\n"
            "| Lab | Status | Track | Difficulty | Description |\n"
            "|:---:|:---:|:---:|:---:|:---|\n"
            + render_table_rows(catalog["experimental"], chips, show_status=True)
            + "\n\n"
        )
    header += (
        "Uncatalogued directories are omitted from public totals. "
        "Maintainers track them in the "
        "[lab triage inventory](https://github.com/Duckurity/openlabs/wiki/Lab-Triage-Inventory).\n\n"
        "</div>"
    )
    return header


def render_badge_block(catalog: dict) -> str:
    supported = catalog["supported_count"]
    experimental = catalog["experimental_count"]
    sup_dark = badge_asset_version("labs-supported", variant="dark")
    sup_light = badge_asset_version("labs-supported", variant="light")
    exp_dark = badge_asset_version("labs-experimental", variant="dark")
    exp_light = badge_asset_version("labs-experimental", variant="light")
    return (
        f'  <picture><source media="(prefers-color-scheme: dark)" '
        f'srcset=".github/assets/badges/labs-supported-dark.svg?v={sup_dark}">'
        f'<img src=".github/assets/badges/labs-supported-light.svg?v={sup_light}" '
        f'alt="labs: {supported} supported" height="20"></picture>\n'
        f'  <picture><source media="(prefers-color-scheme: dark)" '
        f'srcset=".github/assets/badges/labs-experimental-dark.svg?v={exp_dark}">'
        f'<img src=".github/assets/badges/labs-experimental-light.svg?v={exp_light}" '
        f'alt="labs: {experimental} experimental" height="20"></picture>'
    )


def render_wiki_badge_block(catalog: dict) -> str:
    supported = catalog["supported_count"]
    experimental = catalog["experimental_count"]
    base = "https://raw.githubusercontent.com/Duckurity/openlabs/main/.github/assets/badges"
    sup_dark = badge_asset_version("labs-supported", variant="dark")
    sup_light = badge_asset_version("labs-supported", variant="light")
    exp_dark = badge_asset_version("labs-experimental", variant="dark")
    exp_light = badge_asset_version("labs-experimental", variant="light")
    return (
        f"  <picture>\n"
        f'    <source media="(prefers-color-scheme: dark)" '
        f'srcset="{base}/labs-supported-dark.svg?v={sup_dark}">\n'
        f'    <img src="{base}/labs-supported-light.svg?v={sup_light}" '
        f'alt="labs: {supported} supported" height="20">\n'
        f"  </picture>\n"
        f"  <picture>\n"
        f'    <source media="(prefers-color-scheme: dark)" '
        f'srcset="{base}/labs-experimental-dark.svg?v={exp_dark}">\n'
        f'    <img src="{base}/labs-experimental-light.svg?v={exp_light}" '
        f'alt="labs: {experimental} experimental" height="20">\n'
        f"  </picture>"
    )


def render_site_index_body(catalog: dict) -> str:
    supported = catalog["supported_count"]
    experimental = catalog["experimental_count"]
    maint = catalog["maintainer"]["uncatalogued_count"]
    return (
        f"The public catalog lists **{supported} supported** and "
        f"**{experimental} experimental** labs with valid `lab.yml` metadata. "
        f"Experimental labs are runnable but not promoted. "
        f"{maint} uncatalogued directories are maintainer-only and excluded "
        "from these totals.\n"
    )


def json_document(catalog: dict) -> str:
    payload = {
        "generator": GENERATOR,
        **catalog,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def patch_readme(catalog: dict, chips: dict[str, str]) -> None:
    path = REPO_ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    text = replace_block(
        text, MARKER_START, MARKER_END, render_readme_body(catalog, chips)
    )
    badge_inner = render_badge_block(catalog)
    text = replace_block(text, MARKER_BADGES_START, MARKER_BADGES_END, badge_inner)
    text = re.sub(
        r"## Labs <sub>\d+ live</sub>",
        "## Labs",
        text,
        count=1,
    )
    text = text.replace('href="#labs-1-live"', 'href="#labs-catalog"')
    if 'id="labs-catalog"' not in text:
        text = text.replace("## Labs\n", '## Labs <span id="labs-catalog"></span>\n', 1)
    path.write_text(text, encoding="utf-8")


def patch_wiki_home(catalog: dict) -> None:
    path = REPO_ROOT / "wiki" / "Home.md"
    text = path.read_text(encoding="utf-8")
    body = (
        f"Catalog totals: **{catalog['supported_count']} supported**, "
        f"**{catalog['experimental_count']} experimental**. "
        "Experimental labs are not guaranteed supported. "
        "See [[Lab catalog status](Lab-Catalog-Status)] and "
        "[[Lab triage inventory](Lab-Triage-Inventory)]."
    )
    if MARKER_START not in text:
        text = text.rstrip() + f"\n\n{MARKER_START}\n{body}\n{MARKER_END}\n"
    else:
        text = replace_block(text, MARKER_START, MARKER_END, body)
    if MARKER_BADGES_START in text:
        text = replace_block(
            text,
            MARKER_BADGES_START,
            MARKER_BADGES_END,
            render_wiki_badge_block(catalog),
        )
    path.write_text(text, encoding="utf-8")


def patch_site_index(catalog: dict) -> None:
    path = REPO_ROOT / "content" / "labs" / "index.mdx"
    text = path.read_text(encoding="utf-8")
    # MDX cannot parse HTML comment markers in page bodies.
    text = text.replace(MARKER_START, SITE_INDEX_MARKER_START).replace(
        MARKER_END, SITE_INDEX_MARKER_END
    )
    start = SITE_INDEX_MARKER_START
    end = SITE_INDEX_MARKER_END
    if start not in text:
        insert = (
            f"\n{start}\n"
            f"{render_site_index_body(catalog)}\n"
            f"{end}\n\n"
        )
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError("content/labs/index.mdx missing frontmatter")
        text = parts[0] + "---" + parts[1] + "---" + insert + parts[2].lstrip("\n")
    else:
        text = replace_block(
            text, start, end, render_site_index_body(catalog)
        )
    path.write_text(text, encoding="utf-8")


def write_json(catalog: dict) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json_document(catalog), encoding="utf-8")


def expected_outputs(catalog: dict, chips: dict[str, str]) -> dict[str, str]:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    return {
        "json": json_document(catalog),
        "readme_block": render_readme_body(catalog, chips),
        "readme_badges": render_badge_block(catalog),
        "site_index": render_site_index_body(catalog),
        "wiki_block": (
            f"Catalog totals: **{catalog['supported_count']} supported**, "
            f"**{catalog['experimental_count']} experimental**. "
            "Experimental labs are not guaranteed supported. "
            "See [[Lab catalog status](Lab-Catalog-Status)] and "
            "[[Lab triage inventory](Lab-Triage-Inventory)]."
        ),
    }


def check_stale() -> list[str]:
    readme_path = REPO_ROOT / "README.md"
    chips = load_chip_snippets(readme_path)
    catalog = build_public_catalog()
    errors: list[str] = []
    expected = expected_outputs(catalog, chips)

    if not JSON_PATH.is_file():
        errors.append(f"missing {JSON_PATH.relative_to(REPO_ROOT)}")
    elif JSON_PATH.read_text(encoding="utf-8") != expected["json"]:
        errors.append(f"stale {JSON_PATH.relative_to(REPO_ROOT)}")

    readme = readme_path.read_text(encoding="utf-8")
    if expected["readme_block"] not in readme:
        errors.append("stale README catalog-public block")
    if expected["readme_badges"] not in readme:
        errors.append("stale README catalog-public badge block")

    index = (REPO_ROOT / "content" / "labs" / "index.mdx").read_text(encoding="utf-8")
    if expected["site_index"] not in index:
        errors.append("stale content/labs/index.mdx catalog block")

    home = (REPO_ROOT / "wiki" / "Home.md").read_text(encoding="utf-8")
    if MARKER_START in home and expected["wiki_block"] not in home:
        errors.append("stale wiki/Home.md catalog-public block")

    return errors


def write_all() -> None:
    readme_path = REPO_ROOT / "README.md"
    chips = load_chip_snippets(readme_path)
    catalog = build_public_catalog()
    write_json(catalog)
    patch_readme(catalog, chips)
    if (REPO_ROOT / "wiki" / "Home.md").is_file():
        patch_wiki_home(catalog)
    patch_site_index(catalog)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="regenerate outputs")
    group.add_argument("--check", action="store_true", help="fail if outputs are stale")
    args = parser.parse_args()

    if args.write:
        write_all()
        catalog = build_public_catalog()
        print(
            f"catalog: {catalog['supported_count']} supported, "
            f"{catalog['experimental_count']} experimental "
            f"({catalog['maintainer']['uncatalogued_count']} uncatalogued omitted)"
        )
        return 0

    errors = check_stale()
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print("run: python3 scripts/sync_catalog_public.py --write", file=sys.stderr)
        return 1
    print("catalog public outputs up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
