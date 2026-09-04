#!/usr/bin/env python3
"""Render per-page social cards (1200x630 PNG) into public/og/.

Reads title/eyebrow text from content/**/*.mdx frontmatter (only pages
carrying ogImage), draws Funnel Display/Geist Mono glyph outlines with
fonttools, converts with rsvg-convert. Deterministic: same input bytes
produce same output bytes. No network, no timestamps.

Requires: fonttools (requirements-dev.txt), rsvg-convert.

Usage:
    python3 scripts/make_og_images.py
    python3 scripts/make_og_images.py --check
"""

from __future__ import annotations

import hashlib
import random
import re
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "public" / "og"
FONTS = ROOT / ".github" / "assets" / "fonts"

W, H = 1200, 630
INK = "#1E1E1E"
WARM = "#F2F2F0"
MUTED = "#A8A29E"
EMBER = "#FF3616"

DISPLAY = FONTS / "FunnelDisplay-Bold.otf"
MONO = FONTS / "GeistMono-Regular.otf"


def die(message: str) -> "NoReturn":
    from typing import NoReturn

    print(f"make_og_images: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(font_path: Path) -> tuple[TTFont, dict, float]:
    if not font_path.is_file():
        die(f"missing font: {font_path}")
    font = TTFont(str(font_path))
    cmap = font.getBestCmap()
    upem = float(font["head"].unitsPerEm)
    return font, cmap, upem


def text_path(
    font: TTFont, cmap: dict, upem: float, size: float, text: str, x: float, baseline: float
) -> tuple[str, float]:
    gs = font.getGlyphSet()
    scale = size / upem
    parts: list[str] = []
    for ch in text:
        if ch == " ":
            x += 0.30 * size
            continue
        gname = cmap.get(ord(ch))
        if gname is None:
            die(f"character not in font: {ch!r} (U+{ord(ch):04X})")
        pen = SVGPathPen(gs)
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x, baseline))
        gs[gname].draw(tpen)
        d = pen.getCommands()
        if d:
            parts.append(d)
        x += gs[gname].width * scale
    return " ".join(parts), x


def text_width(font: TTFont, cmap: dict, upem: float, size: float, text: str) -> float:
    gs = font.getGlyphSet()
    scale = size / upem
    w = 0.0
    for ch in text:
        if ch == " ":
            w += 0.30 * size
            continue
        gname = cmap.get(ord(ch))
        if gname is None:
            die(f"character not in font: {ch!r} (U+{ord(ch):04X})")
        w += gs[gname].width * scale
    return w


def fit_size(font: TTFont, cmap: dict, upem: float, text: str, start: float, limit: float, floor: float = 40.0) -> float:
    size = start
    while size > floor and text_width(font, cmap, upem, size, text) > limit:
        size -= 4.0
    return size


MARK = [(0, 80, WARM), (160, 80, WARM), (80, 0, WARM), (80, 160, WARM), (0, 0, EMBER)]

BAYER_4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def dither_field(seed: int) -> str:
    """Ordered-dither texture for the right third. Seeded per page,
    Ember monochrome, faint enough to sit behind type."""
    rng = random.Random(seed)
    cx = rng.uniform(880.0, 1080.0)
    cy = rng.uniform(150.0, 480.0)
    max_r = rng.uniform(280.0, 420.0)
    cell = 10.0
    parts: list[str] = []
    y = 0.0
    row = 0
    while y < H:
        x = 760.0
        col = 0
        while x < W:
            dx, dy = x + cell / 2 - cx, y + cell / 2 - cy
            falloff = max(0.0, 1.0 - (dx * dx + dy * dy) ** 0.5 / max_r)
            threshold = (BAYER_4[row % 4][col % 4] + 0.5) / 16.0
            if falloff > threshold + 0.35:
                parts.append(
                    f'  <rect x="{x:g}" y="{y:g}" width="{cell:g}" '
                    f'height="{cell:g}" fill="{EMBER}" opacity="0.10"/>'
                )
            x += cell
            col += 1
        y += cell
        row += 1
    return "\n".join(parts)


def hash_shapes(seed: int) -> str:
    """Two outlined rotated squares, seeded per page, hairline Warm."""
    rng = random.Random(seed ^ 0x9E3779B9)
    parts: list[str] = []
    for _ in range(2):
        size = rng.uniform(120.0, 220.0)
        x = rng.uniform(820.0, 1120.0 - size)
        y = rng.uniform(60.0, 570.0 - size)
        angle = rng.uniform(0.0, 90.0)
        cx, cy = x + size / 2, y + size / 2
        parts.append(
            f'  <rect x="{x:g}" y="{y:g}" width="{size:g}" height="{size:g}" '
            f'fill="none" stroke="{WARM}" stroke-width="2" opacity="0.12" '
            f'transform="rotate({angle:g} {cx:g} {cy:g})"/>'
        )
    return "\n".join(parts)


def render(title: str, eyebrow: str, slug: str) -> bytes:
    display, dcmap, dupem = load(DISPLAY)
    mono, mcmap, mupem = load(MONO)

    seed = int.from_bytes(hashlib.sha256(slug.encode("utf-8")).digest()[:8], "big")
    max_w = W - 420.0
    title_size = fit_size(display, dcmap, dupem, title, 88.0, max_w)
    title_d, _ = text_path(display, dcmap, dupem, title_size, title, 340.0, 360.0)
    eye_d, _ = text_path(mono, mcmap, mupem, 28.0, eyebrow, 342.0, 270.0)

    mark = "\n".join(
        f'  <rect x="{96 + x}" y="{235 + y}" width="80" height="80" fill="{fill}"/>'
        for x, y, fill in MARK
    )
    svg = (
        f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        f'  <rect width="{W}" height="{H}" fill="{INK}"/>\n'
        f"{dither_field(seed)}\n"
        f"{hash_shapes(seed)}\n"
        f"{mark}\n"
        f'  <path d="{eye_d}" fill="{EMBER}"/>\n'
        f'  <path d="{title_d}" fill="{WARM}"/>\n'
        f"</svg>\n"
    )
    proc = subprocess.run(
        ["rsvg-convert", "-w", str(W), "-h", str(H)],
        input=svg.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        die(f"rsvg-convert failed: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def frontmatter(path: Path) -> dict[str, str]:
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    data: dict[str, str] = {}
    if not match:
        return data
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip().strip("\"'")
    return data


def eyebrow_for(meta: dict[str, str], path: Path) -> str:
    kind = meta.get("type", "guide")
    if kind == "lab":
        return f"{meta.get('track', 'lab')} · {meta.get('difficulty', '')}".strip(" ·")
    if kind == "technique":
        return "Technique"
    return "Guide"


def collect() -> list[tuple[str, str, str, str]]:
    """(filename, slug, title, eyebrow) for every page carrying ogImage."""
    pages: list[tuple[str, str, str, str]] = []
    for path in sorted(CONTENT.rglob("*.mdx")):
        meta = frontmatter(path)
        og = meta.get("ogImage", "")
        if not og.startswith("/og/") or not og.endswith(".png"):
            continue
        title = meta.get("title")
        if not title:
            die(f"{path}: ogImage without title")
        slug = og.removeprefix("/og/").removesuffix(".png")
        pages.append((og.removeprefix("/og/"), slug, title, eyebrow_for(meta, path)))
    return pages


def build() -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    built: list[str] = []
    for filename, slug, title, eyebrow in collect():
        out = OUT / filename
        png = render(title, eyebrow, slug)
        if not out.is_file() or out.read_bytes() != png:
            out.write_bytes(png)
        built.append(filename)
    # Remove stale cards, keep the directory placeholder.
    for existing in OUT.glob("*.png"):
        if existing.name not in built:
            existing.unlink()
    return built


def main() -> int:
    if "--check" in sys.argv:
        before = {p.name: p.read_bytes() for p in OUT.glob("*.png")} if OUT.is_dir() else {}
        built = build()
        after = {p.name: p.read_bytes() for p in OUT.glob("*.png")}
        if before != after:
            print(f"og images out of date, rebuilt: {', '.join(built)}")
            return 1
        print(f"og images up to date ({len(built)} cards)")
        return 0
    built = build()
    print(f"rendered {len(built)} cards: {', '.join(built)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
