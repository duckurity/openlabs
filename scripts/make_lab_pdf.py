#!/usr/bin/env python3
"""Generate a branded PDF challenge sheet for an openlabs lab.

The generator is a template engine, not a prose writer. It reads lab.yml
(metadata) and README.md (the player brief), then fills the design owned by
templates/labsheet.cls into fixed slots: masthead metadata, the difficulty
meter, the verify command, and the README's ## sections as body headings.
All wording, flags, and structure come from the lab author; nothing is
synthesised. The plaintext flag never enters the sheet — only agnostic
brief text does.

Usage:
    python3 scripts/make_lab_pdf.py labs/web/duck-cross
    python3 scripts/make_lab_pdf.py labs/web/duck-cross --out /tmp/duck.pdf
    python3 scripts/make_lab_pdf.py labs/web/duck-cross --keep
    python3 scripts/make_lab_pdf.py --all                 # every lab
    python3 scripts/make_lab_pdf.py --all --strict        # + fail on layout gaps

Zero dependencies beyond the standard library and two external binaries:

    xelatex         LaTeX engine (TeX Live)
    rsvg-convert    librsvg, converts the brand SVGs to PNG for inclusion

    --strict  fails on any overfull/underfull box. CI uses it, so a layout
              whose boxes overflow their measure cannot merge.

Exit codes: 0 on success, 1 on any error.

The output PDF lands next to the lab by default (LAB.pdf in the lab
directory), or wherever --out points.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "templates"
ASSETS = REPO_ROOT / ".github" / "assets"
FONTS = ASSETS / "fonts"
BADGES = ASSETS / "badges"

REQUIRED_KEYS = ("name", "track", "difficulty", "description")
DIFFICULTIES = ("easy", "medium", "hard", "insane")
TRACKS = ("web", "binary", "crypto", "network", "osint")

# Characters that must be escaped before reaching LaTeX inline text.
LATEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Characters the listings package actually treats as special inside a code
# block. Everything the escaper maps that is NOT here (_, ^, ~, &, $, #) is a
# literal character to listings and must be passed through untouched, so
# double-escaping can never mangle user code.
LISTING_SPECIALS = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "%": r"\%"}


def die(msg: str, code: int = 1) -> None:
    print(f"{Path(sys.argv[0]).name}: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_flat_yaml(text: str) -> dict[str, str]:
    """Parse a flat key: value mapping. Ignores comments and blank lines."""
    data: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    return data


def load_meta(lab: Path) -> dict[str, str]:
    meta_path = lab / "lab.yml"
    if not meta_path.is_file():
        die(f"missing lab.yml in {lab}")
    return parse_flat_yaml(meta_path.read_text(encoding="utf-8"))


def escape_latex_inline(text: str) -> str:
    """Escape special characters for a run of inline LaTeX text."""
    return "".join(LATEX_SPECIALS.get(ch, ch) for ch in text)


def escape_latex_listing(text: str) -> str:
    """Escape only the characters listings treats specially in a code block.

    Underscores, carets, tildes, and the like are literal to listings, so the
    inline table's wider escaping would corrupt real user code. Keeping the
    two escapers separate is what makes the code cards render verbatim.
    """
    return "".join(LISTING_SPECIALS.get(ch, ch) for ch in text)


def render_inline(text: str) -> str:
    """Convert a markdown paragraph to LaTeX. Backtick spans become \texttt
    (Geist Mono); everything else is escaped. The paragraph is left free to
    reflow; only the markdown emphasis is resolved here."""
    out: list[str] = []
    for i, part in enumerate(text.split("`")):
        if i % 2 == 0:
            out.append(escape_latex_inline(part))
        else:
            out.append(f"\\texttt{{{escape_latex_inline(part)}}}")
    return "".join(out)


def render_paragraph(text: str) -> str:
    """Escape a single paragraph for the body, preserving natural line wrap."""
    return render_inline(text)


def split_sections(readme: str) -> list[tuple[str, str]]:
    """Split a README into (heading, body) pairs on markdown ## headings."""
    lines = readme.splitlines()
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current: list[str] = []

    def flush(force: bool = False) -> None:
        nonlocal current_title, current
        if current_title is not None and (current or force):
            sections.append((current_title, "\n".join(current).strip()))
        current = []

    for line in lines:
        m = re.match(r"^#{2,5}\s+(.*)$", line)
        if m:
            flush()
            current_title = m.group(1).strip()
        else:
            if current_title is not None:
                current.append(line)
    flush(force=True)
    return sections


def find_port(readme: str) -> str:
    """Extract the documented host port from a README if present."""
    m = re.search(r"(?i)localhost[:]\s*(\d{2,5})", readme)
    if m:
        return m.group(1)
    m = re.search(r"(?i)[:](\d{2,5})(?![\d])", readme)
    return m.group(1) if m else ""


def emit_runs(runs: list[tuple[str, str]]) -> list[str]:
    """Convert a mixed list of ('text', ...) and ('code', ...) runs into
    LaTeX source. text runs become escaped paragraphs; code runs become
    listing blocks with the stored index resolved at call site."""
    out: list[str] = []
    for kind, data in runs:
        if kind == "code":
            lines = [escape_latex_listing(line) for line in data.splitlines()]
            out.append("\\begin{lstlisting}")
            out.extend(f"    {line}" if line else "" for line in lines)
            out.append("\\end{lstlisting}")
        else:
            # Blank lines separate paragraphs; consecutive lines join into one
            # reflowing paragraph. Body text stays natural looking with the
            # class's pitched paragraph rhythm.
            para: list[str] = []
            for raw in data.split("\n"):
                line = raw.strip()
                if not line:
                    if para:
                        out.append(render_paragraph(" ".join(para)))
                        out.append("\\par\\vspace{1.8mm}")
                        para = []
                    continue
                para.append(line)
            if para:
                out.append(render_paragraph(" ".join(para)))
    return out


def parse_runs(section_body: str) -> list[tuple[str, str]]:
    """Split a section body into ordered ('text', ...) and ('code', ...)
    runs, preserving blank-line paragraphs and fenced code blocks."""
    runs: list[tuple[str, str]] = []
    buf: list[str] = []
    i = 0
    lines = section_body.splitlines()
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            if buf:
                runs.append(("text", "\n".join(buf)))
                buf = []
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # closing fence
            runs.append(("code", "\n".join(code)))
        else:
            buf.append(line)
            i += 1
    if buf:
        runs.append(("text", "\n".join(buf)))
    return runs


def humanize(slug: str) -> str:
    """Turn duck-cross into Duck Cross."""
    return " ".join(word.capitalize() for word in slug.split("-"))


def difficulty_rank(diff: str) -> int:
    return DIFFICULTIES.index(diff) + 1


def build_main_tex(meta: dict[str, str], sections: list[tuple[str, str]],
                   port: str, assetpath: Path) -> str:
    name = meta["name"]
    display = humanize(name)
    rank = difficulty_rank(meta["difficulty"])
    diff_upper = meta["difficulty"].upper()
    track_upper = meta["track"].upper()
    tex: list[str] = []
    tex.append("\\documentclass{labsheet}")
    tex.append(f"\\newcommand{{\\labname}}{{{name}}}")
    tex.append(f"\\newcommand{{\\assetpath}}{{{assetpath.as_posix()}/}}")
    # Load the vendored brand fonts after \assetpath is known.
    tex.append("\\newcommand{\\fontpath}{\\assetpath fonts/}")
    tex.append("\\newfontfamily{\\displayfont}{Funnel Display}["
               "Path=\\fontpath, Extension=.otf, "
               "UprightFont=FunnelDisplay-Regular, "
               "BoldFont=FunnelDisplay-Bold]")
    tex.append("\\setmainfont{Geist}[Path=\\fontpath, Extension=.otf, "
               "UprightFont=Geist-Regular, BoldFont=Geist-Bold]")
    tex.append("\\newfontfamily{\\monofont}{Geist Mono}[Path=\\fontpath, "
               "Extension=.otf, "
               "UprightFont=GeistMono-Regular, BoldFont=GeistMono-Bold]")
    tex.append("\\setmonofont{Geist Mono}[Path=\\fontpath, Extension=.otf, "
               "UprightFont=GeistMono-Regular, BoldFont=GeistMono-Bold]")
    tex.append("\\begin{document}")

    # Masthead, laid out on the class's pitched vertical beat. Read order:
    # eyebrow, title, lead, then the stat grid and the single data graph
    # (difficulty meter), then the verify command as the one tactile affordance.
    # Ember appears exactly twice: the difficulty value and the meter fill.
    tex.append("\\eyebrow{Challenge sheet}")
    tex.append("\\vspace{1.8mm}\\\\")
    tex.append(f"\\noindent\\labtitle{{{escape_latex_inline(display)}}}")
    tex.append("\\vspace{0.8mm}\\\\")
    tex.append(f"\\lead{{{escape_latex_inline(meta['description'])}}}")
    # Stat grid: four cells, split by the class gutter so they fill the measure.
    tx = escape_latex_inline
    tex.append("\\bsmall")
    tex.append(
        f"\\metric[ember]{{Difficulty}}{{{tx(diff_upper)}}}"
        f"\\hspace{{\\mdimsep}}"
        f"\\metric{{Track}}{{{tx(track_upper)}}}"
        f"\\hspace{{\\mdimsep}}"
        f"\\metric{{Host port}}{{{tx(port)}}}"
        f"\\hspace{{\\mdimsep}}"
        f"\\metric{{Lab id}}{{{tx(name)}}}"
    )
    # The meter is the one data graph: active rank fills Ember.
    tex.append("\\bbase")
    tex.append(f"\\noindent\\difficultybar{{{rank}}}")
    # Verify command: warm chip with a prompt marker, the one action offered.
    tex.append("\\bsmall")
    tex.append(f"\\begingroup\\eyebrow{{Verify the solve}}\\par\\vspace{{1.6mm}}\\endgroup")
    tex.append(f"\\noindent\\cmdbox{{python3 ../scripts/check.py {escape_latex_listing(name)}}}")
    tex.append("\\bdouble")
    tex.append("\\noindent\\hairline")
    tex.append("\\bdouble")

    for title, body in sections:
        tex.append(f"\\section*{{{escape_latex_inline(title)}}}")
        tex.extend(emit_runs(parse_runs(body)))

    tex.append("\\end{document}")
    return "\n".join(tex) + "\n"


def compile_pdf(workdir: Path, tex_name: str, out_pdf: Path, strict: bool = False) -> list[str]:
    """Compile a .tex to PDF with XeLaTeX. Returns the log lines.

    Raises (via die) if XeLaTeX fails or no PDF is produced. When strict is
    true the procedure also fails on any overfull/underfull box, so CI can
    reject layouts whose boxes overflow their measure even though the build
    "succeeds". These warnings are the print analogue of a layout bug.
    """
    if not shutil.which("xelatex"):
        die("xelatex is required (TeX Live); install it first")
    log_path = workdir / (Path(tex_name).stem + ".log")
    proc = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
         "-output-directory", str(workdir), tex_name],
        cwd=workdir, capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        tail = "\n".join(proc.stdout.splitlines()[-40:])
        die(f"xelatex failed:\n{tail}\n{proc.stderr[-2000:]}")
    built = workdir / (Path(tex_name).stem + ".pdf")
    if not built.is_file():
        die("xelatex finished but produced no PDF")
    log_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if strict:
        bad = [ln for ln in log_lines if "Overfull" in ln or "Underfull" in ln]
        if bad:
            die(f"layout warnings in {tex_name}:\n" + "\n".join(bad[:12]))
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, out_pdf)
    return log_lines


def convert_svg_to_png(src: Path, dst: Path, width: int) -> None:
    """Render an SVG to a PNG at the requested pixel width using rsvg-convert."""
    if not shutil.which("rsvg-convert"):
        die("rsvg-convert is required (librsvg); install it first")
    subprocess.run(
        ["rsvg-convert", "-w", str(width), "-o", str(dst), str(src)],
        check=True, capture_output=True, timeout=120,
    )
    if not dst.is_file():
        die(f"rsvg-convert produced no output for {src.name}")


def stage_assets(workdir: Path) -> None:
    """Copy fonts and render the light SVG assets to PNG in the staging dir,
    mirroring the layout the class expects under \assetpath."""
    staged_fonts = workdir / "fonts"
    staged_fonts.mkdir(parents=True, exist_ok=True)
    for f in FONTS.glob("*.otf"):
        shutil.copy2(f, staged_fonts / f.name)
    convert_svg_to_png(ASSETS / "mark-cross-light.svg",
                       workdir / "mark-cross-light.png", width=26)
    convert_svg_to_png(ASSETS / "logo-openlabs-light.svg",
                       workdir / "logo-openlabs-light.png", width=760)


def build_lab(lab: Path, out: Path | None, keep: bool, strict: bool) -> Path:
    """Stage and compile one lab's PDF. Returns the output path."""
    meta = load_meta(lab)
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        die(f"lab.yml missing keys: {', '.join(missing)}")
    if meta["difficulty"] not in DIFFICULTIES:
        die(f"unknown difficulty: {meta['difficulty']}")
    if meta["track"] not in TRACKS:
        die(f"unknown track: {meta['track']}")

    readme_path = lab / "README.md"
    if not readme_path.is_file():
        die(f"missing README.md in {lab}")
    readme = readme_path.read_text(encoding="utf-8")

    port = find_port(readme)
    sections = split_sections(readme)

    workdir = Path(tempfile.mkdtemp(prefix="labsheet-"))
    try:
        stage_assets(workdir)
        with (workdir / "labsheet.cls").open("w", encoding="utf-8") as fh:
            fh.write((TEMPLATES / "labsheet.cls").read_text(encoding="utf-8"))
        tex = build_main_tex(meta, sections, port, workdir)
        (workdir / "Labsheet.tex").write_text(tex, encoding="utf-8")

        default_out = lab / f"{meta['name']}.pdf"
        if out is not None:
            out_pdf = out.resolve()
        else:
            out_pdf = default_out.resolve()
        compile_pdf(workdir, "Labsheet.tex", out_pdf, strict=strict)
        return out_pdf
    finally:
        if not keep:
            shutil.rmtree(workdir, ignore_errors=True)


def discover_labs(root: Path = REPO_ROOT / "labs") -> list[Path]:
    """Walk labs/<track>/<lab>/ and return every dir containing a lab.yml."""
    found: list[Path] = []
    if not root.is_dir():
        return found
    for track in sorted(p for p in root.iterdir() if p.is_dir()):
        if track.name == "_template":
            continue
        for lab in sorted(p for p in track.iterdir() if p.is_dir()):
            if (lab / "lab.yml").is_file():
                found.append(lab)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lab", nargs="?",
                    help="path to a lab directory; omit with --all to build every lab")
    ap.add_argument("--all", action="store_true",
                    help="build a PDF for every lab in the repo")
    ap.add_argument("--out", help="output PDF path (default <lab>/<name>.pdf)")
    ap.add_argument("--keep", action="store_true",
                    help="keep the staging directory instead of deleting it")
    ap.add_argument("--strict", action="store_true",
                    help="fail on any overfull/underfull layout warning")
    args = ap.parse_args()

    if args.all:
        labs = discover_labs()
        if not labs:
            die("--all found no labs")
        for lab in labs:
            out_pdf = build_lab(lab, None, args.keep, args.strict)
            print(f"wrote {out_pdf}")
        return 0

    if not args.lab:
        ap.error("path to a lab is required unless --all is given")
    lab = Path(args.lab).resolve()
    if not lab.is_dir():
        die(f"not a directory: {args.lab}")

    out_pdf = build_lab(lab, Path(args.out) if args.out else None,
                        args.keep, args.strict)
    print(f"wrote {out_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
