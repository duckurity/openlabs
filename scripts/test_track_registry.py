#!/usr/bin/env python3
"""Check track registry shape and consumer parity."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import contract_schema  # noqa: E402
import make_lab_pdf  # noqa: E402
import openlabs_contract  # noqa: E402
from tracks import TRACK_DEFINITIONS, TRACK_SLUGS, TRACK_SLUG_SET  # noqa: E402
from validate_issue_forms import extract_dropdown_options  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "contracts" / "lab.schema.json"
SITE_TRACKS_PATH = REPO_ROOT / "lib" / "tracks.ts"
LAB_IDEA_PATH = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "lab-idea.yml"
SITE_TRACKS_RE = re.compile(
    r"export const TRACKS\s*=\s*\[(?P<body>.*?)\]\s*as const",
    re.DOTALL,
)


def run_registry_shape() -> int:
    if len(TRACK_DEFINITIONS) != len(TRACK_SLUG_SET):
        print("track registry: duplicate slugs", file=sys.stderr)
        return 1
    if not all(track.label.strip() and track.focus.strip() for track in TRACK_DEFINITIONS):
        print("track registry: labels and focus text must be non-empty", file=sys.stderr)
        return 1
    print(f"track registry: ok ({len(TRACK_DEFINITIONS)} tracks)")
    return 0


def run_schema_parity() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_tracks = tuple(schema["properties"]["track"]["enum"])
    if schema_tracks != TRACK_SLUGS:
        print(
            f"track registry: schema enum {schema_tracks!r} does not match {TRACK_SLUGS!r}",
            file=sys.stderr,
        )
        return 1
    print("track registry: JSON Schema aligned")
    return 0


def run_python_parity() -> int:
    set_consumers = {
        "contract_schema.TRACKS": contract_schema.TRACKS,
        "openlabs_contract.TRACKS": openlabs_contract.TRACKS,
    }
    failures = 0
    for name, tracks in set_consumers.items():
        if frozenset(tracks) == TRACK_SLUG_SET:
            continue
        failures += 1
        print(f"track registry: {name} does not match the registry", file=sys.stderr)
    if tuple(make_lab_pdf.TRACKS) != TRACK_SLUGS:
        failures += 1
        print("track registry: make_lab_pdf.TRACKS order does not match", file=sys.stderr)
    if failures:
        return 1
    print("track registry: Python consumers aligned")
    return 0


def run_site_parity() -> int:
    text = SITE_TRACKS_PATH.read_text(encoding="utf-8")
    match = SITE_TRACKS_RE.search(text)
    if match is None:
        print("track registry: lib/tracks.ts has no TRACKS tuple", file=sys.stderr)
        return 1
    site_tracks = tuple(re.findall(r"'([a-z0-9]+(?:-[a-z0-9]+)*)'", match.group("body")))
    if site_tracks != TRACK_SLUGS:
        print(
            f"track registry: site tuple {site_tracks!r} does not match {TRACK_SLUGS!r}",
            file=sys.stderr,
        )
        return 1
    print("track registry: site enum aligned")
    return 0


def run_issue_form_parity() -> int:
    options = extract_dropdown_options(LAB_IDEA_PATH, "track")
    if options != TRACK_SLUGS:
        print(
            f"track registry: lab idea options {options!r} do not match {TRACK_SLUGS!r}",
            file=sys.stderr,
        )
        return 1
    print("track registry: lab idea form aligned")
    return 0


def run_issue_form_option_parser() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="openlabs-form-opts-") as temp:
        root = Path(temp)

        quoted = root / "quoted.yml"
        quoted.write_text(
            "\n".join(
                (
                    "body:",
                    "  - type: dropdown",
                    "    id: track",
                    "    attributes:",
                    "      label: Track",
                    "      options:",
                    '        - "web"',
                    "        - 'binary'",
                    "        - crypto",
                    "        - network",
                    "        - osint",
                    '        - "forensics"',
                    "        - misc",
                    "",
                )
            ),
            encoding="utf-8",
        )
        try:
            quoted_options = extract_dropdown_options(quoted, "track")
        except ValueError as exc:
            failures += 1
            print(f"track registry: quoted options rejected: {exc}", file=sys.stderr)
        else:
            if quoted_options != TRACK_SLUGS:
                failures += 1
                print(
                    "track registry: quoted options "
                    f"{quoted_options!r} do not match {TRACK_SLUGS!r}",
                    file=sys.stderr,
                )

        sneaky = root / "sneaky.yml"
        sneaky.write_text(
            "\n".join(
                (
                    "body:",
                    "  - type: dropdown",
                    "    id: track",
                    "    attributes:",
                    "      label: Track",
                    "      options:",
                    "        - web",
                    "        - binary",
                    "        - crypto",
                    "        - network",
                    "        - osint",
                    "        - forensics",
                    "        - misc",
                    '        - "general"',
                    "",
                )
            ),
            encoding="utf-8",
        )
        try:
            sneaky_options = extract_dropdown_options(sneaky, "track")
        except ValueError as exc:
            failures += 1
            print(
                f"track registry: quoted general option should parse, got: {exc}",
                file=sys.stderr,
            )
        else:
            if sneaky_options == TRACK_SLUGS:
                failures += 1
                print(
                    "track registry: quoted general option was silently truncated",
                    file=sys.stderr,
                )
            elif sneaky_options != TRACK_SLUGS + ("general",):
                failures += 1
                print(
                    "track registry: unexpected sneaky options "
                    f"{sneaky_options!r}",
                    file=sys.stderr,
                )

        broken = root / "broken.yml"
        broken.write_text(
            "\n".join(
                (
                    "body:",
                    "  - type: dropdown",
                    "    id: track",
                    "    attributes:",
                    "      label: Track",
                    "      options:",
                    "        - web",
                    "        - [not-a-scalar]",
                    "",
                )
            ),
            encoding="utf-8",
        )
        try:
            extract_dropdown_options(broken, "track")
        except ValueError as exc:
            if "unrecognized dropdown option line" not in str(exc):
                failures += 1
                print(
                    f"track registry: broken options raised wrong error: {exc}",
                    file=sys.stderr,
                )
        else:
            failures += 1
            print(
                "track registry: broken option line was accepted",
                file=sys.stderr,
            )

    if failures:
        return 1
    print("track registry: issue form option parser hardened")
    return 0


def run_new_track_context() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="openlabs-tracks-") as temp:
        root = Path(temp)
        for track in ("forensics", "misc"):
            lab_dir = root / track / f"{track}-fixture"
            lab_dir.mkdir(parents=True)
            (lab_dir / "lab.yml").write_text(
                "\n".join(
                    (
                        "contract_version: 1",
                        f"name: {track}-fixture",
                        f"track: {track}",
                        "difficulty: medium",
                        "description: Track registry context fixture.",
                        f"flag_hash: {'0' * 64}",
                        "status: experimental",
                        "techniques: []",
                        "",
                    )
                ),
                encoding="utf-8",
            )
            errors = openlabs_contract.collect_metadata_errors(lab_dir)
            if errors:
                failures += 1
                print(f"track registry: {track} context failed: {errors}", file=sys.stderr)
    if failures:
        return 1
    print("track registry: new track context accepted")
    return 0


def main() -> int:
    steps = (
        run_registry_shape,
        run_schema_parity,
        run_python_parity,
        run_site_parity,
        run_issue_form_parity,
        run_issue_form_option_parser,
        run_new_track_context,
    )
    for step in steps:
        if step() != 0:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
