#!/usr/bin/env python3
"""Generate one hash-seeded vector shape per lab into public/shapes/.

Each lab gets a unique geometric composition derived from sha256 of its
flag_hash (a hash of a hash reveals nothing). Ink shapes with one Ember
accent on transparent ground, built for the DitheredObject renderer,
which extrudes alpha contours and applies the dither at render time.

Deterministic: same lab.yml produces same SVG bytes. No network.

Usage:
    python3 scripts/make_shapes.py
    python3 scripts/make_shapes.py --check
"""

from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABS = ROOT / "labs"
OUT = ROOT / "public" / "shapes"

SIZE = 256
INK = "#1E1E1E"
EMBER = "#FF3616"


def seed_for(flag_hash: str, name: str) -> int:
    return int.from_bytes(
        hashlib.sha256(f"{flag_hash}:{name}".encode("utf-8")).digest()[:8],
        "big",
    )


def compose(seed: int) -> str:
    """Seeded geometric composition: rotated squares, bars, one Ember cell."""
    rng = random.Random(seed)
    parts: list[str] = []
    cells = rng.randint(3, 6)
    for _ in range(cells):
        size = rng.choice([32, 48, 64, 96])
        x = rng.randint(0, (SIZE - size) // 16) * 16
        y = rng.randint(0, (SIZE - size) // 16) * 16
        angle = rng.choice([0, 0, 0, 15, 30, 45])
        if angle:
            cx, cy = x + size / 2, y + size / 2
            parts.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" '
                f'fill="{INK}" transform="rotate({angle} {cx:g} {cy:g})"/>'
            )
        else:
            parts.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{INK}"/>'
            )
    ax = rng.randint(0, (SIZE - 32) // 16) * 16
    ay = rng.randint(0, (SIZE - 32) // 16) * 16
    parts.append(
        f'<rect x="{ax}" y="{ay}" width="32" height="32" fill="{EMBER}"/>'
    )
    return "\n".join(parts)


def render(name: str, flag_hash: str) -> bytes:
    shapes = compose(seed_for(flag_hash, name))
    svg = (
        f'<svg width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" '
        f'fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        f"{shapes}\n</svg>\n"
    )
    return svg.encode("utf-8")


def read_flag_hash(lab_yml: Path) -> str | None:
    for line in lab_yml.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "flag_hash":
            return value.strip()
    return None


def build() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    built: list[str] = []
    for lab_yml in sorted(LABS.glob("*/*/lab.yml")):
        if "_template" in lab_yml.parts:
            continue
        flag_hash = read_flag_hash(lab_yml)
        if not flag_hash:
            print(f"make_shapes: {lab_yml.parent.name} has no flag_hash, skipped")
            continue
        out = OUT / f"{lab_yml.parent.name}.svg"
        svg = render(lab_yml.parent.name, flag_hash)
        if not out.is_file() or out.read_bytes() != svg:
            out.write_bytes(svg)
        built.append(out.name)
    for existing in OUT.glob("*.svg"):
        if existing.name not in built:
            existing.unlink()
    return built


def main() -> int:
    if "--check" in sys.argv:
        before = {p.name: p.read_bytes() for p in OUT.glob("*.svg")} if OUT.is_dir() else {}
        built = build()
        after = {p.name: p.read_bytes() for p in OUT.glob("*.svg")}
        if before != after:
            print(f"shapes out of date, rebuilt: {', '.join(built)}")
            return 1
        print(f"shapes up to date ({len(built)} files)")
        return 0
    built = build()
    print(f"rendered {len(built)} shapes: {', '.join(built)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
