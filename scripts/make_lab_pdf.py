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
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "templates"
ASSETS = REPO_ROOT / ".github" / "assets"
FONTS = ASSETS / "fonts"
BADGES = ASSETS / "badges"

REQUIRED_KEYS = ("name", "track", "difficulty", "description")
DIFFICULTIES = ("easy", "medium", "hard", "insane")
TRACKS = ("web", "binary", "crypto", "network", "osint")
COMPOSE_NAMES = (
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
)

META_KEY_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?:\s*(?P<value>.*))?$")
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})[ \t]+(?P<title>.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})(?:[^`]*)$")
UNORDERED_LIST_RE = re.compile(r"^\s*[-*+]\s+(?P<text>.+)$")
ORDERED_LIST_RE = re.compile(r"^\s*\d+[.)]\s+(?P<text>.+)$")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(?P<text>.*)$")
DETAILS_OPEN_RE = re.compile(r"^\s*<details(?:\s+[^>]*)?>", re.IGNORECASE)
DETAILS_CLOSE_RE = re.compile(r"</details>\s*$", re.IGNORECASE)
SUMMARY_RE = re.compile(r"<summary(?:\s+[^>]*)?>(?P<text>.*?)</summary>", re.IGNORECASE)
PARAGRAPH_HTML_RE = re.compile(r"^\s*<p(?:\s+[^>]*)?>(?P<text>.*?)</p>\s*$", re.IGNORECASE)
BYLINE_RE = re.compile(r"<strong>\s*(Created by\s+[^<]+)\s*</strong>", re.IGNORECASE)
SHORT_PORT_RE = re.compile(r"^\s*-\s*(?P<value>[^#]+?)(?:\s+#.*)?$")
IP_PORT_RE = re.compile(r"^(?:(?:\d{1,3}\.){3}\d{1,3}:)?(?P<published>\d{1,5}):\d{1,5}(?:/(?:tcp|udp))?$")
ENV_DEFAULT_PORT_RE = re.compile(
    r"^\$\{[A-Za-z_][A-Za-z0-9_]*:-(?P<published>\d{1,5})\}:\d{1,5}(?:/(?:tcp|udp))?$"
)
INLINE_TOKEN_RE = re.compile(
    r"(?P<code>`(?P<code_text>[^`\n]+)`)"
    r"|(?P<link>\[(?P<link_label>[^\]\n]+)\]\((?P<link_target>[^()\s]+)\))"
    r"|(?P<strong>(?:\*\*(?P<strong_star>[^*\n]+)\*\*|__(?P<strong_under>[^_\n]+)__))"
    r"|(?P<em>(?:\*(?P<em_star>[^*\n]+)\*|_(?P<em_under>[^_\n]+)_))"
)


class MetadataError(ValueError):
    """Raised when a lab.yml file is outside this dependency-free contract."""


class MarkdownError(ValueError):
    """Raised when a README uses unsupported or malformed Markdown."""


@dataclass(frozen=True)
class MarkdownNode:
    """A line-aware Markdown block used by the LaTeX renderer."""

    kind: str
    line: int
    text: str = ""
    level: int = 0
    items: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    children: tuple["MarkdownNode", ...] = ()

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


def strip_inline_comment(value: str) -> str:
    """Remove an unquoted YAML comment while retaining literal ``#`` values."""
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote == '"' and char == "\\" and not escaped:
            escaped = True
            continue
        if char in "\"'" and not escaped:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        elif char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        escaped = False
    return value.rstrip()


def parse_yaml_scalar(value: str, line_number: int) -> str:
    """Read a scalar used by the flat lab.yml contract."""
    value = strip_inline_comment(value).strip()
    if not value:
        return ""
    if value[0] not in "\"'":
        return value
    quote = value[0]
    if len(value) < 2 or value[-1] != quote:
        raise MetadataError(f"line {line_number}: unterminated quoted value")
    if quote == "'":
        return value[1:-1].replace("''", "'")
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise MetadataError(f"line {line_number}: invalid double-quoted value") from exc


def fold_yaml_block(lines: list[str]) -> str:
    """Fold the simple ``>`` block scalar form accepted by this parser."""
    folded: list[str] = []
    for line in lines:
        if not line:
            if folded and folded[-1] != "\n":
                folded.append("\n")
            continue
        if folded and folded[-1] != "\n":
            folded.append(" ")
        folded.append(line)
    return "".join(folded)


def parse_flat_yaml(text: str) -> dict[str, str]:
    """Parse supported flat metadata and reject ambiguous YAML with a line number."""
    data: dict[str, str] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        line_number = index + 1
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        match = META_KEY_RE.match(raw)
        if not match or match.group("indent"):
            raise MetadataError(f"line {line_number}: expected an unindented key: value mapping")
        key = match.group("key")
        if key in data:
            raise MetadataError(f"line {line_number}: duplicate key `{key}`")

        value = strip_inline_comment(match.group("value") or "").strip()
        if not value and index + 1 < len(lines) and re.match(r"^\s+-\s+\S", lines[index + 1]):
            items: list[str] = []
            index += 1
            while index < len(lines):
                item = re.match(r"^\s+-\s+(?P<value>.+?)\s*$", lines[index])
                if item is None:
                    break
                items.append(parse_yaml_scalar(item.group("value"), index + 1))
                index += 1
            data[key] = "[" + ", ".join(items) + "]"
            continue
        if value not in {"|", ">"}:
            data[key] = parse_yaml_scalar(value, line_number)
            index += 1
            continue

        style = value
        index += 1
        block: list[str] = []
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and not candidate[0].isspace():
                break
            block.append(candidate.lstrip() if candidate.strip() else "")
            index += 1
        if not block:
            raise MetadataError(f"line {line_number}: block scalar has no content")
        data[key] = "\n".join(block) if style == "|" else fold_yaml_block(block)
    return data


def load_meta(lab: Path) -> dict[str, str]:
    meta_path = lab / "lab.yml"
    if not meta_path.is_file():
        die(f"missing lab.yml in {lab}")
    try:
        return parse_flat_yaml(meta_path.read_text(encoding="utf-8"))
    except (MetadataError, OSError, UnicodeDecodeError) as exc:
        die(f"invalid {meta_path}: {exc}")


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


def normalize_inline_html(text: str, line_number: int) -> str:
    """Accept the small inline HTML subset common in existing lab READMEs."""
    parts = text.split("`")
    for index in range(0, len(parts), 2):
        part = parts[index]
        part = re.sub(r"<strong>(.*?)</strong>", r"**\1**", part, flags=re.IGNORECASE)
        part = re.sub(r"<(?:em|i)>(.*?)</(?:em|i)>", r"*\1*", part, flags=re.IGNORECASE)
        part = re.sub(r"<sub>(.*?)</sub>", r"\1", part, flags=re.IGNORECASE)
        part = re.sub(r"<br\s*/?>", " ", part, flags=re.IGNORECASE)
        if re.search(r"</?[A-Za-z][^>]*>", part):
            raise MarkdownError(f"line {line_number}: unsupported inline HTML")
        parts[index] = html.unescape(part)
    return "`".join(parts)


def render_inline_code(text: str) -> str:
    """Render inline code verbatim while allowing a line break at separators."""
    escaped = escape_latex_inline(text)
    escaped = escaped.replace("/", r"/\allowbreak{}")
    escaped = escaped.replace("-", r"-\allowbreak{}")
    escaped = escaped.replace(r"\_", r"\_\allowbreak{}")
    return r"\allowbreak{} ".join(rf"\texttt{{{part}}}" for part in escaped.split(" "))


def render_inline(text: str, line_number: int) -> str:
    """Render the supported inline Markdown without allowing raw syntax through."""
    text = normalize_inline_html(text, line_number)
    text = re.sub(
        r"(?P<fence>`{2,})(?P<content>[^\n]*?)(?P=fence)",
        lambda match: f"`{match.group('content')}`",
        text,
    )
    if text.count("`") % 2:
        raise MarkdownError(f"line {line_number}: unclosed inline code span")

    out: list[str] = []
    cursor = 0
    for match in INLINE_TOKEN_RE.finditer(text):
        out.append(escape_latex_inline(text[cursor:match.start()]))
        if match.group("code"):
            out.append(render_inline_code(match.group("code_text")))
        elif match.group("link"):
            # A print sheet keeps the human-readable label. URLs already
            # included in the label remain visible without relying on a PDF
            # hyperlink package or leaking Markdown syntax into the output.
            out.append(render_inline(match.group("link_label"), line_number))
        elif match.group("strong"):
            content = match.group("strong_star") or match.group("strong_under") or ""
            out.append(f"\\textbf{{{render_inline(content, line_number)}}}")
        else:
            content = match.group("em_star") or match.group("em_under") or ""
            out.append(f"\\emph{{{render_inline(content, line_number)}}}")
        cursor = match.end()
    out.append(escape_latex_inline(text[cursor:]))
    return "".join(out)


def split_table_row(line: str) -> tuple[str, ...]:
    """Split a simple GFM table row into cells."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return tuple(cell.strip() for cell in stripped.split("|"))


def is_table_divider(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def is_rule(line: str) -> bool:
    return bool(re.fullmatch(r"\s{0,3}(?:[-*_]\s*){3,}", line))


def is_block_start(lines: list[str], index: int) -> bool:
    line = lines[index]
    if not line.strip():
        return True
    if (HEADING_RE.match(line) or FENCE_RE.match(line) or is_rule(line)
            or UNORDERED_LIST_RE.match(line) or ORDERED_LIST_RE.match(line)
            or BLOCKQUOTE_RE.match(line) or DETAILS_OPEN_RE.match(line)
            or PARAGRAPH_HTML_RE.match(line)):
        return True
    return "|" in line and index + 1 < len(lines) and is_table_divider(lines[index + 1])


def parse_details(lines: list[str], index: int, first_line: int) -> tuple[MarkdownNode, int]:
    """Parse an HTML details block into a visible print callout."""
    fragments = [DETAILS_OPEN_RE.sub("", lines[index], count=1)]
    cursor = index + 1
    closed = False
    while cursor < len(lines):
        fragment = lines[cursor]
        close = DETAILS_CLOSE_RE.search(fragment)
        if close:
            fragments.append(fragment[:close.start()])
            if fragment[close.end():].strip():
                raise MarkdownError(f"line {first_line + cursor}: content after </details> is unsupported")
            closed = True
            cursor += 1
            break
        fragments.append(fragment)
        cursor += 1
    if not closed:
        raise MarkdownError(f"line {first_line + index}: unclosed <details> block")

    content = "\n".join(fragments)
    summary = SUMMARY_RE.search(content)
    if summary is None:
        raise MarkdownError(f"line {first_line + index}: <details> needs a <summary>")
    before_summary = content[:summary.start()].strip()
    if before_summary:
        raise MarkdownError(f"line {first_line + index}: unexpected text before <summary>")
    title = normalize_inline_html(summary.group("text").strip(), first_line + index)
    body = content[summary.end():].strip("\n")
    children = parse_markdown_blocks(body.splitlines(), first_line + index + 1) if body else []
    return MarkdownNode("details", first_line + index, text=title, children=tuple(children)), cursor


def parse_markdown_blocks(lines: list[str], first_line: int = 1) -> list[MarkdownNode]:
    """Parse the documented README subset into a line-aware block tree."""
    nodes: list[MarkdownNode] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        line_number = first_line + index
        if not line.strip():
            index += 1
            continue

        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group("fence")
            code: list[str] = []
            index += 1
            while index < len(lines):
                closing = re.match(rf"^\s*{re.escape(marker[0])}{{{len(marker)},}}\s*$", lines[index])
                if closing:
                    break
                code.append(lines[index])
                index += 1
            if index == len(lines):
                raise MarkdownError(f"line {line_number}: unclosed fenced code block")
            nodes.append(MarkdownNode("code", line_number, text="\n".join(code)))
            index += 1
            continue

        if DETAILS_OPEN_RE.match(line):
            node, index = parse_details(lines, index, first_line)
            nodes.append(node)
            continue

        heading = HEADING_RE.match(line)
        if heading:
            nodes.append(MarkdownNode(
                "heading", line_number, text=heading.group("title").strip(),
                level=len(heading.group("marks")),
            ))
            index += 1
            continue

        if is_rule(line):
            nodes.append(MarkdownNode("rule", line_number))
            index += 1
            continue

        quote = BLOCKQUOTE_RE.match(line)
        if quote:
            quoted: list[str] = []
            while index < len(lines):
                current = BLOCKQUOTE_RE.match(lines[index])
                if not current:
                    break
                quoted.append(current.group("text"))
                index += 1
            nodes.append(MarkdownNode("quote", line_number, text=" ".join(quoted).strip()))
            continue

        if "|" in line and index + 1 < len(lines) and is_table_divider(lines[index + 1]):
            rows = [split_table_row(line)]
            column_count = len(rows[0])
            index += 2
            while index < len(lines) and lines[index].strip() and "|" in lines[index]:
                row = split_table_row(lines[index])
                if len(row) != column_count:
                    raise MarkdownError(f"line {first_line + index}: table has {len(row)} cells; expected {column_count}")
                rows.append(row)
                index += 1
            nodes.append(MarkdownNode("table", line_number, rows=tuple(rows)))
            continue

        list_match = UNORDERED_LIST_RE.match(line) or ORDERED_LIST_RE.match(line)
        if list_match:
            ordered = ORDERED_LIST_RE.match(line) is not None
            matcher = ORDERED_LIST_RE if ordered else UNORDERED_LIST_RE
            items: list[str] = []
            while index < len(lines):
                current = matcher.match(lines[index])
                if current:
                    items.append(current.group("text").strip())
                    index += 1
                    continue
                if lines[index].startswith((" ", "\t")) and lines[index].strip() and items:
                    items[-1] += " " + lines[index].strip()
                    index += 1
                    continue
                break
            nodes.append(MarkdownNode("ordered_list" if ordered else "list", line_number, items=tuple(items)))
            continue

        html_paragraph = PARAGRAPH_HTML_RE.match(line)
        if html_paragraph:
            nodes.append(MarkdownNode(
                "paragraph", line_number,
                text=normalize_inline_html(html_paragraph.group("text").strip(), line_number),
            ))
            index += 1
            continue

        if line.lstrip().startswith("<"):
            raise MarkdownError(f"line {line_number}: unsupported HTML block")

        paragraph: list[str] = [line.strip()]
        index += 1
        while index < len(lines) and not is_block_start(lines, index):
            paragraph.append(lines[index].strip())
            index += 1
        nodes.append(MarkdownNode("paragraph", line_number, text=" ".join(paragraph)))
    return nodes


def parse_markdown(readme: str) -> tuple[list[MarkdownNode], str]:
    """Return the printable README body and an optional authored byline."""
    lines = readme.splitlines()
    byline_match = BYLINE_RE.search(readme)
    byline = html.unescape(byline_match.group(1).strip()) if byline_match else ""

    start = next(
        (index for index, line in enumerate(lines)
         if (match := HEADING_RE.match(line)) and len(match.group("marks")) == 2),
        None,
    )
    if start is None:
        start = next((index for index, line in enumerate(lines) if HEADING_RE.match(line)), None)
    if start is None:
        raise MarkdownError("README has no Markdown heading")
    return parse_markdown_blocks(lines[start:], start + 1), byline


def compose_path(lab: Path) -> Path | None:
    """Find the compose file used to expose a lab to the host."""
    return next((lab / name for name in COMPOSE_NAMES if (lab / name).is_file()), None)


def published_port(value: str) -> str | None:
    """Return a published port from the common short Compose port forms."""
    value = value.strip().strip("\"'")
    env_default = ENV_DEFAULT_PORT_RE.fullmatch(value)
    if env_default:
        return env_default.group("published")
    numeric = IP_PORT_RE.fullmatch(value)
    return numeric.group("published") if numeric else None


def find_host_ports(lab: Path) -> str:
    """Read published host ports from Compose, never from arbitrary README text."""
    path = compose_path(lab)
    if path is None:
        return "Not published"

    ports: list[str] = []
    ports_indent: int | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if match := re.match(r"^(?P<indent>\s*)ports:\s*(?P<inline>\[.*\])?\s*(?:#.*)?$", raw):
            ports_indent = len(match.group("indent"))
            inline = match.group("inline")
            if inline:
                for value in re.findall(r"[\"']([^\"']+)[\"']", inline):
                    if port := published_port(value):
                        ports.append(port)
                ports_indent = None
            continue
        if ports_indent is None:
            continue
        indent = len(raw) - len(raw.lstrip())
        if raw.strip() and indent <= ports_indent:
            ports_indent = None
            continue
        entry = SHORT_PORT_RE.match(raw)
        if entry and (port := published_port(entry.group("value"))):
            ports.append(port)

    unique = list(dict.fromkeys(ports))
    return ", ".join(unique) if unique else "Not published"


def emit_node(node: MarkdownNode) -> list[str]:
    """Render one Markdown AST node into the class's supported LaTeX blocks."""
    if node.kind == "heading":
        command = "section" if node.level <= 2 else "subsection" if node.level == 3 else "subsubsection"
        return [f"\\{command}*{{{render_inline(node.text, node.line)}}}"]
    if node.kind == "paragraph":
        return [render_inline(node.text, node.line), "\\par\\vspace{1.8mm}"]
    if node.kind == "code":
        escaped = [escape_latex_listing(line) for line in node.text.splitlines()]
        return ["\\begin{lstlisting}", *[f"    {line}" if line else "" for line in escaped], "\\end{lstlisting}"]
    if node.kind in {"list", "ordered_list"}:
        environment = "enumerate" if node.kind == "ordered_list" else "itemize"
        out = [f"\\begin{{{environment}}}", "\\setlength{\\itemsep}{1.0mm}"]
        out.extend(f"\\item {render_inline(item, node.line)}" for item in node.items)
        out.append(f"\\end{{{environment}}}")
        return out
    if node.kind == "quote":
        return ["\\begin{quote}\\color{soft}", render_inline(node.text, node.line), "\\end{quote}"]
    if node.kind == "rule":
        return ["\\bsmall", "\\noindent\\hairline", "\\bsmall"]
    if node.kind == "table":
        columns = len(node.rows[0])
        width = rf">{{\raggedright\arraybackslash}}p{{\dimexpr(\textwidth-{2 * columns}\tabcolsep)/{columns}\relax}}"
        spec = "@{}" + width * columns + "@{}"
        out = [
            "\\begin{tcolorbox}[enhanced,breakable,colback=warm,colframe=warm,boxrule=0pt,arc=0pt,left=1.4mm,right=1.4mm,top=1.2mm,bottom=1.2mm]",
            "{\\small\\renewcommand{\\arraystretch}{1.2}",
            f"\\begin{{tabular}}{{{spec}}}",
            " & ".join(f"\\textbf{{{render_inline(cell, node.line)}}}" for cell in node.rows[0]) + r" \\\\ \hline",
        ]
        for row in node.rows[1:]:
            out.append(" & ".join(render_inline(cell, node.line) for cell in row) + " \\\\")
        out.extend(["\\end{tabular}", "}", "\\end{tcolorbox}"])
        return out
    if node.kind == "details":
        out = [
            "\\begin{tcolorbox}[enhanced,breakable,colback=warm,colframe=haire,boxrule=0.4pt,arc=0pt,left=1.4mm,right=1.4mm,top=1.2mm,bottom=1.2mm,title={" + render_inline(node.text, node.line) + "}]",
        ]
        for child in node.children:
            out.extend(emit_node(child))
        out.append("\\end{tcolorbox}")
        return out
    raise MarkdownError(f"line {node.line}: unsupported Markdown node {node.kind!r}")


def humanize(slug: str) -> str:
    """Turn duck-cross into Duck Cross."""
    return " ".join(word.capitalize() for word in slug.split("-"))


def render_metric_value(value: str) -> str:
    """Keep a long metadata value on one balanced masthead metric line."""
    escaped = escape_latex_inline(value)
    if len(value) > 14:
        return rf"{{\fontsize{{7.5}}{{9}}\selectfont {escaped}}}"
    return escaped


def render_lab_id(slug: str) -> str:
    """Render a slug for the constrained masthead Lab ID cell."""
    return render_metric_value(slug)


def difficulty_rank(diff: str) -> int:
    return DIFFICULTIES.index(diff) + 1


def build_main_tex(meta: dict[str, str], nodes: list[MarkdownNode],
                   port: str, assetpath: Path, byline: str = "") -> str:
    name = meta["name"]
    display = humanize(name)
    lab_id = render_lab_id(name)
    host_ports = render_metric_value(port)
    rank = difficulty_rank(meta["difficulty"])
    diff_upper = meta["difficulty"].upper()
    track_upper = meta["track"].upper()
    tex: list[str] = []
    tex.append("\\documentclass{labsheet}")
    tex.append(f"\\newcommand{{\\labname}}{{{escape_latex_inline(name)}}}")
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
    if byline:
        tex.append("\\vspace{1.2mm}\\\\")
        tex.append(
            f"\\noindent{{\\fontsize{{8.5}}{{11}}\\selectfont\\color{{dim}}"
            f"{render_inline(byline, 0)}}}"
        )
    # Stat grid: four cells, split by the class gutter so they fill the measure.
    tx = escape_latex_inline
    tex.append("\\bsmall")
    tex.append(
        f"\\metric[ember]{{Difficulty}}{{{tx(diff_upper)}}}"
        f"\\hspace{{\\mdimsep}}"
        f"\\metric{{Track}}{{{tx(track_upper)}}}"
        f"\\hspace{{\\mdimsep}}"
        f"\\metric{{Host port}}{{{host_ports}}}"
        f"\\hspace{{\\mdimsep}}"
        f"\\metric{{Lab id}}{{{lab_id}}}"
    )
    # The meter is the one data graph: active rank fills Ember.
    tex.append("\\bbase")
    tex.append(f"\\noindent\\difficultybar{{{rank}}}")
    # Verify command: warm chip with a prompt marker, the one action offered.
    tex.append("\\bsmall")
    tex.append(f"\\begingroup\\eyebrow{{Verify the solve}}\\par\\vspace{{1.6mm}}\\endgroup")
    tex.append(f"\\noindent\\cmdbox{{python3 ../scripts/check.py {escape_latex_inline(name)}}}")
    tex.append("\\bdouble")
    tex.append("\\noindent\\hairline")
    tex.append("\\bdouble")

    for node in nodes:
        tex.extend(emit_node(node))

    tex.append("\\end{document}")
    return "\n".join(tex) + "\n"


def compile_pdf(workdir: Path, tex_name: str, out_pdf: Path, strict: bool = False,
                label: str = "") -> list[str]:
    """Compile a .tex to PDF with XeLaTeX. Returns the log lines.

    Raises (via die) if XeLaTeX fails or no PDF is produced. When strict is
    true the procedure also fails on any overfull/underfull box, so CI can
    reject layouts whose boxes overflow their measure even though the build
    "succeeds". These warnings are the print analogue of a layout bug.
    """
    if not shutil.which("xelatex"):
        die("xelatex is required (TeX Live); install it first")
    log_path = workdir / (Path(tex_name).stem + ".log")
    try:
        proc = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
             "-output-directory", str(workdir), tex_name],
            cwd=workdir, capture_output=True, text=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        die(f"xelatex timed out after 300 seconds for {tex_name}")
    except OSError as exc:
        die(f"could not run xelatex: {exc}")
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
            context = f" for {label}" if label else ""
            die(f"layout warnings{context}:\n" + "\n".join(bad[:12]))
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(
        prefix=f".{out_pdf.stem}-", suffix=".pdf", dir=out_pdf.parent,
    )
    os.close(descriptor)
    tmp_out = Path(tmp_name)
    try:
        shutil.copy2(built, tmp_out)
        os.replace(tmp_out, out_pdf)
    finally:
        tmp_out.unlink(missing_ok=True)
    return log_lines


def convert_svg_to_png(src: Path, dst: Path, width: int) -> None:
    """Render an SVG to a PNG at the requested pixel width using rsvg-convert."""
    if not shutil.which("rsvg-convert"):
        die("rsvg-convert is required (librsvg); install it first")
    try:
        subprocess.run(
            ["rsvg-convert", "-w", str(width), "-o", str(dst), str(src)],
            check=True, capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        die(f"rsvg-convert timed out after 120 seconds for {src.name}")
    except subprocess.CalledProcessError as exc:
        die(f"rsvg-convert failed for {src.name}: {exc.stderr.strip()}")
    except OSError as exc:
        die(f"could not run rsvg-convert: {exc}")
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

    try:
        nodes, byline = parse_markdown(readme)
    except MarkdownError as exc:
        die(f"invalid README.md in {lab}: {exc}")
    port = find_host_ports(lab)

    workdir = Path(tempfile.mkdtemp(prefix="labsheet-"))
    try:
        stage_assets(workdir)
        with (workdir / "labsheet.cls").open("w", encoding="utf-8") as fh:
            fh.write((TEMPLATES / "labsheet.cls").read_text(encoding="utf-8"))
        tex = build_main_tex(meta, nodes, port, workdir, byline=byline)
        (workdir / "Labsheet.tex").write_text(tex, encoding="utf-8")

        default_out = lab / f"{meta['name']}.pdf"
        if out is not None:
            out_pdf = out.resolve()
        else:
            out_pdf = default_out.resolve()
        compile_pdf(workdir, "Labsheet.tex", out_pdf, strict=strict, label=str(lab))
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


def main(argv: Sequence[str] | None = None) -> int:
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
    args = ap.parse_args(argv)

    if args.all and args.out:
        ap.error("--out cannot be used with --all; each lab has its own output path")

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
