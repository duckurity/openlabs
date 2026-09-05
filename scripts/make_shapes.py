#!/usr/bin/env python3
"""Generate one hash-seeded dither gradient per lab into public/shapes/.

Each lab gets a unique Bayer-ordered gradient derived from sha256 of its
flag_hash (a hash of a hash reveals nothing). Ink field resolving to
Ember at the sweep peak, on transparent ground, built for the
DitheredObject renderer, which extrudes alpha contours and applies
its own dither at render time.

Deterministic: same lab.yml produces same SVG bytes. No network.

Usage:
    python3 scripts/make_shapes.py
    python3 scripts/make_shapes.py --check
"""

from __future__ import annotations

import hashlib
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABS = ROOT / "labs"
OUT = ROOT / "public" / "shapes"

SIZE = 256
INK = "#1E1E1E"
EMBER = "#FF3616"

BAYER_4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def dither_dots(
    seed: int,
    w: float,
    h: float,
    cell: float = 16.0,
    stops: tuple[tuple[float, str, float], ...] = ((0.0, INK, 1.0), (0.82, EMBER, 1.0)),
    x0: float = 0.0,
    y0: float = 0.0,
) -> str:
    """Bayer-ordered gradient dots. Deterministic per seed.

    A linear sweep picks direction at random; each cell fires when the
    sweep value beats the Bayer threshold. Stops map sweep ranges to
    (fill, opacity); cells below the first stop stay empty.
    """
    rng = random.Random(seed)
    angle = rng.choice([0, 45, 90, 135, 180, 225, 270, 315]) * math.pi / 180
    dx, dy = math.cos(angle), math.sin(angle)
    corners = [(x0, y0), (x0 + w, y0), (x0, y0 + h), (x0 + w, y0 + h)]
    projs = [x * dx + y * dy for x, y in corners]
    lo, span = min(projs), max(projs) - min(projs) or 1.0
    parts: list[str] = []
    row = 0
    y = y0
    while y < y0 + h:
        col = 0
        x = x0
        while x < x0 + w:
            t = ((x + cell / 2) * dx + (y + cell / 2) * dy - lo) / span
            threshold = (BAYER_4[row % 4][col % 4] + 0.5) / 16.0
            if t > threshold:
                fill, op = stops[0][1], stops[0][2]
                for min_t, f, o in stops:
                    if t >= min_t:
                        fill, op = f, o
                if op > 0:
                    op_str = f' opacity="{op:g}"' if op < 1 else ""
                    parts.append(
                        f'<rect x="{x:g}" y="{y:g}" width="{cell:g}" '
                        f'height="{cell:g}" fill="{fill}"{op_str}/>'
                    )
            x += cell
            col += 1
        y += cell
        row += 1
    return "\n".join(parts)


def seed_for(flag_hash: str, name: str) -> int:
    return int.from_bytes(
        hashlib.sha256(f"{flag_hash}:{name}".encode("utf-8")).digest()[:8],
        "big",
    )


def compose(seed: int) -> str:
    """Seeded dither gradient on a 16px grid: Ink field resolving to
    Ember at the sweep peak. Transparent ground for the 3D extruder."""
    return dither_dots(seed, SIZE, SIZE)


def render(name: str, flag_hash: str) -> bytes:
    shapes = compose(seed_for(flag_hash, name))
    svg = (
        f'<svg width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" '
        f'preserveAspectRatio="xMidYMid slice" '
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
