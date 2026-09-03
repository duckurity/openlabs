#!/usr/bin/env python3
"""Generate brand badges and difficulty chips for openlabs.

Renders Funnel Display text as SVG paths, so the output never depends on
fonts at render time. Deterministic: same inputs, same bytes.

Requires the vendored fonts under `.github/assets/fonts/` and the
`fonttools` package (`pip install fonttools`). For reproducible CI,
pin fonttools in `requirements-dev.txt`.

Usage:
    python3 scripts/make_badges.py [--out DIR]
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

REPO_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = REPO_ROOT / ".github/assets/fonts"
BOLD = FONT_DIR / "FunnelDisplay-Bold.otf"
LABS_DIR = REPO_ROOT / "labs"

# brand tokens (single source of truth)
INK = "#1E1E1E"
WARM = "#F4F2F1"
CANVAS = "#1C1916"
EMBER = "#FF3616"

DARK = {"bg": CANVAS, "fg": WARM, "dim": WARM, "accent": EMBER}
LIGHT = {"bg": WARM, "fg": INK, "dim": INK, "accent": EMBER}

BADGE_H = 20
CHIP_H = 18
BADGE_FONT = 11.0
CHIP_FONT = 10.0
PAD_X = 7.0
GAP = 6.0
CHIP_TRACK = 1.0

GENERATOR = "scripts/make_badges.py"
GENERATED_AT = datetime.now(timezone.utc).isoformat(timespec="seconds")


def die(msg: str, code: int = 1) -> None:
    """Print to stderr and exit with non-zero status."""
    print(f"{Path(sys.argv[0]).name}: {msg}", file=sys.stderr)
    sys.exit(code)


def count_labs() -> int:
    """Count lab directories across tracks, mirroring validate.py rules."""
    if not LABS_DIR.is_dir():
        return 0
    n = 0
    for track in sorted(LABS_DIR.iterdir()):
        if not track.is_dir() or track.name.startswith((".", "_")):
            continue
        n += sum(
            1 for lab in track.iterdir()
            if lab.is_dir() and not lab.name.startswith((".", "_"))
        )
    return n


def load_font(path: Path) -> tuple[TTFont, dict, float]:
    if not path.is_file():
        die(f"missing font: {path.relative_to(REPO_ROOT)} "
            f"(vendor Funnel Display under .github/assets/fonts/)")
    try:
        font = TTFont(str(path))
    except Exception as exc:
        die(f"failed to load {path.name}: {exc}")
    return font, font.getBestCmap(), font["head"].unitsPerEm


def cap_height(font: TTFont, upem: float, size: float) -> float:
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    cmap = font.getBestCmap()
    if ord("H") not in cmap:
        die(f"{font['name'].getDebugName(1) or 'font'} has no 'H' glyph")
    gs[cmap[ord("H")]].draw(pen)
    if pen.bounds is None:
        die("could not measure cap height (no 'H' bounds)")
    return pen.bounds[3] * size / upem


def glyph_name(cmap: dict, ch: str) -> str:
    gname = cmap.get(ord(ch))
    if gname is None:
        die(f"character not in font: {ch!r} (U+{ord(ch):04X})")
    return gname


def run_path(font: TTFont, cmap: dict, upem: float, size: float,
             text: str, x: float, baseline: float, track: float = 0.0
             ) -> tuple[str, float]:
    """Return (svg path d, end x) for text drawn with y-flip at baseline."""
    gs = font.getGlyphSet()
    scale = size / upem
    parts: list[str] = []
    for ch in text:
        if ch == " ":
            x += 0.30 * size + track
            continue
        gname = glyph_name(cmap, ch)
        pen = SVGPathPen(gs)
        tpen = TransformPen(pen, (scale, 0, 0, -scale, x, baseline))
        gs[gname].draw(tpen)
        d = pen.getCommands()
        if d:
            parts.append(d)
        x += gs[gname].width * scale + track
    return " ".join(parts), x


def measure(font: TTFont, cmap: dict, upem: float, size: float,
            text: str, track: float = 0.0) -> float:
    gs = font.getGlyphSet()
    scale = size / upem
    w = 0.0
    for ch in text:
        if ch == " ":
            w += 0.30 * size + track
            continue
        glyph_name(cmap, ch)  # validate coverage
        w += gs[cmap[ord(ch)]].width * scale + track
    return max(0.0, w - (track if text.strip() else 0.0))


def svg(w: float, h: float, bg: str, runs: list[tuple[str, str, float]]) -> str:
    paths = "\n".join(
        f'  <path d="{d}" fill="{fill}"'
        f'{f" opacity=\"{op:g}\"" if op < 1 else ""}/>'
        for d, fill, op in runs
    )
    return (
        f'<svg width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}" '
        f'fill="none" xmlns="http://www.w3.org/2000/svg">\n'
        f'  <rect width="{w:g}" height="{h:g}" fill="{bg}"/>\n'
        f"{paths}\n</svg>\n"
    )


def compose(font: TTFont, cmap: dict, upem: float, size: float, h: float,
            runs_spec: list[tuple[str, str]], track: float, theme: dict
            ) -> str:
    """runs_spec: list of (text, style) with style in label|value|accent."""
    cap = cap_height(font, upem, size)
    baseline = round((h + cap) / 2, 2)
    widths = [measure(font, cmap, upem, size, t, track) for t, _ in runs_spec]
    total = PAD_X * 2 + sum(widths) + GAP * (len(runs_spec) - 1)
    x = PAD_X
    out = []
    for (text, style), w in zip(runs_spec, widths):
        d, end = run_path(font, cmap, upem, size, text, x, baseline, track)
        if style == "label":
            fill, op = theme["dim"], 0.62
        elif style == "accent":
            fill, op = theme["accent"], 1.0
        else:
            fill, op = theme["fg"], 1.0
        out.append((d, fill, op))
        x = end + GAP
    return svg(round(total, 2), h, theme["bg"], out)


def write_atomic(path: Path, content: str) -> None:
    """Write text atomically (write-temp + rename) with deterministic mode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    os.replace(tmp, path)
    # Enforce mode (replace preserves source mode)
    os.chmod(path, 0o644 & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)


def badge(font, cmap, upem, name: str, spec: list[tuple[str, str]],
          out: Path) -> list[Path]:
    written: list[Path] = []
    for suffix, theme in (("dark", DARK), ("light", LIGHT)):
        content = compose(font, cmap, upem, BADGE_FONT, BADGE_H, spec, 0.0, theme)
        path = out / f"{name}-{suffix}.svg"
        write_atomic(path, content)
        written.append(path)
    return written


def chip(font, cmap, upem, word: str, out: Path) -> list[Path]:
    written: list[Path] = []
    for suffix, theme in (("dark", DARK), ("light", LIGHT)):
        content = compose(font, cmap, upem, CHIP_FONT, CHIP_H,
                          [(word.upper(), "value")], CHIP_TRACK, theme)
        path = out / f"chip-{word}-{suffix}.svg"
        write_atomic(path, content)
        written.append(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / ".github/assets/badges",
                    help="output directory (default .github/assets/badges)")
    ap.add_argument("--no-manifest", action="store_true",
                    help="skip writing MANIFEST.json")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    bold = load_font(BOLD)

    n_labs = count_labs()
    badges = {
        "code-license": [("code", "label"), ("Apache-2.0", "value")],
        "content-license": [("content", "label"), ("CC-BY-4.0", "value")],
        "labs-count": [("labs", "label"), (str(n_labs), "accent"),
                       ("live", "value")],
        "docker": [("docker", "label"), ("compose v2", "value")],
        "checker": [("checker", "label"), ("python3", "value")],
    }
    written: list[Path] = []
    for name, spec in badges.items():
        written.extend(badge(*bold, name, spec, args.out))
    for word in ("easy", "medium", "hard", "insane"):
        written.extend(chip(*bold, word, args.out))

    if not args.no_manifest:
        import hashlib
        manifest = {
            "generator": GENERATOR,
            "generated_at": GENERATED_AT,
            "lab_count": n_labs,
            "files": [
                {
                    "name": p.name,
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:8],
                    "bytes": p.stat().st_size,
                }
                for p in sorted(written)
            ],
        }
        write_atomic(args.out / "MANIFEST.json",
                     json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    try:
        out_display = args.out.relative_to(REPO_ROOT)
    except ValueError:
        out_display = args.out
    print(f"{n_labs} lab{'s' if n_labs != 1 else ''}; "
          f"wrote {len(written)} svgs to {out_display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
