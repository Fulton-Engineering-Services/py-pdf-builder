# Copyright 2026 Fulton Engineering Services LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Markdown → ReportLab flowable parser (optional narrative-appendix layer).

The sidebar / further-reading H2 headings are
injectable via :class:`MarkdownConfig` so each report (or spec-renderer)
can decide whether to fold ``## How it shows up in this repo`` into a
sidebar (as the primer did) or simply render it inline.

This module is OPTIONAL — none of the four data-driven reports needs it
to build. It is here so reports can include narrative appendices
(``Methodology``, ``Glossary``, ``Reading Guide``, …) authored as ``.md``
files without losing the brand chassis.

Public surface:

* :class:`MarkdownConfig` — knobs for sidebar/further-reading heading
  matching, plus a switch for the "Practical Application" sidebar prefix.
* :func:`parse_section_lines` — convert a list of markdown source lines
  into flowables.
* :func:`parse_md_file` — read a ``.md`` file from disk and return a full
  chapter (header + lead + body + sidebar + further-reading flowables).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.platypus import HRFlowable, Paragraph, Spacer

from .blocks import make_code_block, make_md_table, make_sidebar
from .branding import Palette, default_palette
from .flowables import BookmarkAnchor, ChapterAnchor, HeaderState
from .text import esc, fmt, safe_para
from .toc import FigureRegistry

__all__ = [
    "MarkdownConfig",
    "MdH2Section",
    "parse_md_file",
    "parse_section_lines",
    "slugify_heading",
    "split_md_by_h2",
]


# ─── Configuration ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MarkdownConfig:
    """Per-call tunables for the markdown parser.

    Defaults:

    * ``sidebar_heading_re`` matches ``## How it shows up in this repo``
      and folds the section into a "Practical Application" sidebar.
    * ``further_reading_heading_re`` matches ``## Further reading`` and
      folds the section into a numbered list.

    Reports that want plain inline rendering can pass an instance with
    both regexes set to ``None``.
    """

    sidebar_heading_re: re.Pattern[str] | None = re.compile(
        r"^## How it shows up in this repo", re.IGNORECASE
    )
    further_reading_heading_re: re.Pattern[str] | None = re.compile(
        r"^## Further reading", re.IGNORECASE
    )
    sidebar_title: str = "Sidebar"
    sidebar_prefix: str = "▸  PRACTICAL APPLICATION"


# ─── Helpers (private) ───────────────────────────────────────────────────────


def _heading_to_title(raw: str) -> str:
    """Strip inline markdown markers from a heading so it reads naturally
    in the figure TOC.

    Headings frequently contain backticks (``"## How `llama.cpp` loads ..."``)
    and occasional bold / italic emphasis. The figure-TOC label is rendered
    as plain XML-escaped text, so any leftover markdown syntax shows up
    literally. This helper unwraps the four common inline markers without
    depending on the full :func:`reporting.text.fmt` pipeline (which would
    return XML markup we'd then have to unescape).
    """
    out = raw.strip()
    out = re.sub(r"`([^`]+)`", r"\1", out)
    out = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", out)
    out = re.sub(r"\*\*(.+?)\*\*", r"\1", out)
    out = re.sub(r"__(.+?)__", r"\1", out)
    out = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)", r"\1", out)
    out = re.sub(r"(?<![a-zA-Z0-9_])_([^_\n]+?)_(?![a-zA-Z0-9_])", r"\1", out)
    return out


def slugify_heading(raw: str) -> str:
    """Convert a heading to a GitHub-flavoured-markdown style slug.

    Used to produce the trailing component of a heading-level PDF anchor
    key (``<chapter_anchor>__<slug>``). The rules mirror what GitHub
    applies to ``#fragment`` references in rendered markdown: strip
    inline markup, lowercase, drop everything outside ``[a-z0-9 -]``,
    convert whitespace to hyphens, and collapse runs.

    The resulting slug is intentionally lossy and stable — two headings
    with the same prose content collide on purpose, matching the source
    markdown's behaviour. Callers who need uniqueness across an entire
    document should pair the slug with a chapter prefix.
    """
    out = _heading_to_title(raw).lower()
    out = re.sub(r"[^a-z0-9\s-]", "", out)
    out = re.sub(r"\s+", "-", out).strip("-")
    out = re.sub(r"-{2,}", "-", out)
    return out


# ─── Markdown grammar regexes (private) ──────────────────────────────────────


_H1_RE = re.compile(r"^# (.+)$")
_H2_RE = re.compile(r"^## (.+)$")
_H3_RE = re.compile(r"^### (.+)$")
_H4_RE = re.compile(r"^#### (.+)$")
_FENCE_RE = re.compile(r"^```(\w*)$")
_FENCE_CLOSE = re.compile(r"^```\s*$")
_HR_RE = re.compile(r"^[-*_]{3,}\s*$")
_BULLET_RE = re.compile(r"^([-*+]|\d+\.) (.+)$")
_INDENT_BULLET = re.compile(r"^  ([-*+]) (.+)$")
_TABLE_ROW = re.compile(r"^\|(.+)\|$")
_TABLE_SEP = re.compile(r"^\|[\s\-:|]+\|$")
_MATH_OPEN = re.compile(r"^\\\[$")
_MATH_CLOSE = re.compile(r"^\\\]$")


# ─── Section parser ──────────────────────────────────────────────────────────


def parse_section_lines(
    lines: Sequence[str],
    styles: dict,
    *,
    is_sidebar: bool = False,
    figures: FigureRegistry | None = None,
    chapter_title_for_figures: str = "",
    diagram_renderer: Callable[..., list] | None = None,
    math_renderer: Callable[[str, dict], object] | None = None,
    palette: Palette | None = None,
    chapter_anchor: str = "",
    link_resolver: Callable[[str], str | None] | None = None,
) -> list:
    """Parse a list of markdown source lines into a list of flowables.

    Args:
        lines: Raw lines to parse (no trailing newlines required).
        styles: Style dict from :func:`reporting.styles.make_styles`.
        is_sidebar: When ``True``, suppress block-level constructs that
            don't belong inside a sidebar (headings, math, tables) and use
            sidebar-specific paragraph styles.
        figures: Optional :class:`FigureRegistry` for diagram registration.
            Required when ``diagram_renderer`` is provided.
        chapter_title_for_figures: Display name passed to the diagram
            renderer for the TOC's Figures section.
        diagram_renderer: Optional callable
            ``(mermaid_text, styles, *, title="") -> list[Flowable]``. Use
            :func:`reporting.diagrams.mermaid.make_diagram_box` (curried
            with the registry/chapter title/etc.) here. The parser passes
            the most recent ``##``/``###``/``####`` heading text as
            ``title=`` so the figure's TOC entry reads
            ``Figure N \u00b7 Type \u00b7 <heading>``.
        math_renderer: Optional callable
            ``(latex_text, styles) -> Flowable``. Use
            :func:`reporting.diagrams.math.make_math_block` here.
        palette: Brand palette (only used by the HR rule colour).
        chapter_anchor: PDF anchor key of the surrounding chapter
            (e.g. ``"kv_cache"``). When non-empty (and not in sidebar
            mode) every H2/H3/H4 emits a :class:`BookmarkAnchor` whose
            key is ``"<chapter_anchor>__<slugify_heading(text)>"``, so
            cross-references like ``[X](#some-heading)`` and
            ``[X](kv-cache.md#some-heading)`` resolve to the right
            destination at render time.
        link_resolver: Optional callable forwarded to every :func:`fmt`
            call. Lets the caller turn ``[text](relative.md)`` and
            ``[text](#fragment)`` markdown links into clickable
            internal PDF anchors. See :func:`reporting.text.fmt` for
            the contract.
    """
    palette = palette or default_palette()
    flowables: list = []
    para_lines: list[str] = []
    bullet_items: list[tuple[int, str]] = []
    in_numbered = False
    last_heading: str = ""
    seen_heading_keys: set[str] = set()

    def emit_heading_anchor(raw_heading: str) -> None:
        """Append a :class:`BookmarkAnchor` for an H2/H3/H4 if one is warranted.

        Skipped inside sidebars (where headings are also suppressed),
        when no ``chapter_anchor`` was supplied, or when the slug
        collapses to empty. Duplicate slugs within the same chapter are
        de-duplicated to avoid two headings binding to the same PDF
        destination key — first occurrence wins, matching how viewers
        typically handle ambiguous ``#fragment`` references.
        """
        if is_sidebar or not chapter_anchor:
            return
        slug = slugify_heading(raw_heading)
        if not slug:
            return
        key = f"{chapter_anchor}__{slug}"
        if key in seen_heading_keys:
            return
        seen_heading_keys.add(key)
        flowables.append(BookmarkAnchor(key))

    def flush_para() -> None:
        if para_lines:
            text = " ".join(para_lines).strip()
            if text:
                st = styles["sidebar_body"] if is_sidebar else styles["body"]
                flowables.append(safe_para(fmt(text, link_resolver=link_resolver), st))
            para_lines.clear()

    def flush_bullets() -> None:
        if bullet_items:
            for indent, btext in bullet_items:
                marker = "•" if not in_numbered else "·"
                if is_sidebar:
                    st = styles["sidebar_bullet"]
                elif indent > 0:
                    st = styles["bullet2"]
                else:
                    st = styles["bullet"]
                flowables.append(
                    safe_para(
                        f"{marker}  {fmt(btext, link_resolver=link_resolver)}",
                        st,
                    )
                )
            bullet_items.clear()

    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.rstrip()

        if _HR_RE.match(line):
            flush_para()
            flush_bullets()
            if not is_sidebar:
                flowables.append(
                    HRFlowable(
                        width="100%",
                        thickness=0.5,
                        color=palette.slate_mid,
                        spaceBefore=6,
                        spaceAfter=6,
                    )
                )
            i += 1
            continue

        if m := _H2_RE.match(line):
            flush_para()
            flush_bullets()
            if not is_sidebar:
                emit_heading_anchor(m.group(1))
                flowables.append(
                    safe_para(
                        fmt(m.group(1), link_resolver=link_resolver),
                        styles["h2"],
                    )
                )
                last_heading = _heading_to_title(m.group(1))
            i += 1
            continue

        if m := _H3_RE.match(line):
            flush_para()
            flush_bullets()
            if not is_sidebar:
                emit_heading_anchor(m.group(1))
                flowables.append(
                    safe_para(
                        fmt(m.group(1), link_resolver=link_resolver),
                        styles["h3"],
                    )
                )
                last_heading = _heading_to_title(m.group(1))
            i += 1
            continue

        if m := _H4_RE.match(line):
            flush_para()
            flush_bullets()
            if not is_sidebar:
                emit_heading_anchor(m.group(1))
                flowables.append(
                    safe_para(
                        fmt(m.group(1), link_resolver=link_resolver),
                        styles["h4"],
                    )
                )
                last_heading = _heading_to_title(m.group(1))
            i += 1
            continue

        # Math display block \[ ... \]
        if _MATH_OPEN.match(line):
            flush_para()
            flush_bullets()
            math_lines: list[str] = []
            i += 1
            while i < n and not _MATH_CLOSE.match(lines[i].rstrip()):
                math_lines.append(lines[i])
                i += 1
            if not is_sidebar and math_renderer is not None:
                flowables.append(math_renderer("\n".join(math_lines), styles))
            i += 1
            continue

        # Code fence
        if m := _FENCE_RE.match(line):
            flush_para()
            flush_bullets()
            lang = m.group(1).lower()
            code_lines: list[str] = []
            i += 1
            while i < n and not (
                _FENCE_CLOSE.match(lines[i].rstrip()) or lines[i].strip() == "```"
            ):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            if lang == "mermaid" and diagram_renderer is not None:
                flowables.extend(diagram_renderer(code_text, styles, title=last_heading))
            elif code_text.strip():
                flowables.append(make_code_block(code_text, lang, styles))
            i += 1
            continue

        # Markdown table
        if _TABLE_ROW.match(line) and i + 1 < n and _TABLE_SEP.match(lines[i + 1].strip()):
            flush_para()
            flush_bullets()
            rows: list[list[str]] = []
            hdr_parts = [c.strip() for c in line.strip("|").split("|")]
            rows.append(hdr_parts)
            i += 2
            while i < n and _TABLE_ROW.match(lines[i].rstrip()):
                parts = [c.strip() for c in lines[i].strip("|").split("|")]
                rows.append(parts)
                i += 1
            if not is_sidebar:
                tbl = make_md_table(rows, styles)
                if tbl:
                    flowables.append(Spacer(1, 4))
                    flowables.append(tbl)
                    flowables.append(Spacer(1, 4))
            continue

        # Bullet / numbered list
        if m := _BULLET_RE.match(line):
            flush_para()
            marker = m.group(1)
            in_numbered = bool(re.match(r"\d+\.", marker))
            btext = m.group(2)
            bullet_items.append((0, btext))
            i += 1
            while i < n:
                next_raw = lines[i]
                if m2 := _INDENT_BULLET.match(next_raw):
                    bullet_items.append((1, m2.group(2)))
                    i += 1
                elif re.match(r"^  \S", next_raw) and bullet_items:
                    idx, prev = bullet_items[-1]
                    bullet_items[-1] = (idx, prev + " " + next_raw.strip())
                    i += 1
                elif m3 := _BULLET_RE.match(next_raw):
                    in_numbered = bool(re.match(r"\d+\.", m3.group(1)))
                    bullet_items.append((0, m3.group(2)))
                    i += 1
                else:
                    break
            flush_bullets()
            continue

        if m := _INDENT_BULLET.match(line):
            flush_para()
            bullet_items.append((1, m.group(2)))
            i += 1
            continue

        if not line.strip():
            flush_para()
            flush_bullets()
            i += 1
            continue

        if _H1_RE.match(line):
            # H1 is consumed as the chapter title; the body never repeats it.
            flush_para()
            flush_bullets()
            i += 1
            continue

        para_lines.append(line.strip())
        i += 1

    flush_para()
    flush_bullets()
    return flowables


# ─── File-level driver ──────────────────────────────────────────────────────


def parse_md_file(
    filepath: Path,
    styles: dict,
    *,
    chapter_label: str,
    chapter_title: str,
    state: HeaderState,
    config: MarkdownConfig | None = None,
    anchor: str = "",
    outline_level: int = 1,
    figures: FigureRegistry | None = None,
    diagram_renderer: Callable[[str, dict], list] | None = None,
    math_renderer: Callable[[str, dict], object] | None = None,
    palette: Palette | None = None,
    link_resolver: Callable[[str], str | None] | None = None,
) -> list:
    """Parse a full markdown file into a chapter's worth of flowables.

    Produces a standard chapter shape:

    1. :class:`ChapterAnchor` (registers TOC destination + outline entry)
    2. Chapter label + title + accent rule + lead paragraph
    3. Body content (parsed via :func:`parse_section_lines`)
    4. Optional sidebar (folded from the configured sidebar heading)
    5. Optional Further Reading numbered list

    The chapter's resolved ``anchor`` (or ``filepath.stem`` if blank)
    is also passed down to :func:`parse_section_lines` as
    ``chapter_anchor`` so every H2/H3/H4 emits a
    :class:`BookmarkAnchor` whose key is
    ``"<chapter_anchor>__<slugify_heading(text)>"`` — the destination
    for ``[X](#fragment)`` and ``[X](other.md#fragment)``
    cross-references resolved by ``link_resolver``.
    """
    config = config or MarkdownConfig()
    palette = palette or default_palette()
    chapter_anchor = anchor or filepath.stem

    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    normal_lines: list[str] = []
    sidebar_lines: list[str] = []
    fr_lines: list[str] = []
    mode = "normal"

    for line in lines:
        stripped = line.rstrip()
        if config.sidebar_heading_re is not None and config.sidebar_heading_re.match(stripped):
            mode = "sidebar"
            continue
        if (
            config.further_reading_heading_re is not None
            and config.further_reading_heading_re.match(stripped)
        ):
            mode = "fr"
            continue
        if _H2_RE.match(stripped) and mode in ("sidebar", "fr"):
            mode = "normal"
        if mode == "normal":
            normal_lines.append(line)
        elif mode == "sidebar":
            sidebar_lines.append(line)
        elif mode == "fr":
            fr_lines.append(line)

    lead_text = ""
    body_start = 0
    clean = [ln.rstrip() for ln in normal_lines]
    for idx, ln in enumerate(clean):
        if ln.startswith("# "):
            body_start = idx + 1
            continue
        if (
            body_start > 0
            and ln.strip()
            and not ln.startswith("#")
            and not ln.startswith("```")
            and not ln.startswith("---")
        ):
            lead_lines: list[str] = []
            j = idx
            while j < len(clean) and clean[j].strip() and not clean[j].startswith("#"):
                lead_lines.append(clean[j])
                j += 1
            lead_text = " ".join(lead_lines)
            body_start = j
            break

    flowables: list = [
        ChapterAnchor(chapter_anchor, chapter_title, state=state, level=outline_level),
        Paragraph(esc(chapter_label), styles["chap_label"]),
        Paragraph(esc(chapter_title), styles["chap_title"]),
        HRFlowable(
            width="100%",
            thickness=2,
            color=palette.blue,
            spaceBefore=2,
            spaceAfter=10,
        ),
    ]
    if lead_text.strip():
        flowables.append(
            Paragraph(
                fmt(lead_text, link_resolver=link_resolver),
                styles["chap_lead"],
            )
        )

    body_lines = normal_lines[body_start:]
    flowables.extend(
        parse_section_lines(
            body_lines,
            styles,
            figures=figures,
            chapter_title_for_figures=chapter_title,
            diagram_renderer=diagram_renderer,
            math_renderer=math_renderer,
            palette=palette,
            chapter_anchor=chapter_anchor,
            link_resolver=link_resolver,
        )
    )

    if sidebar_lines:
        sb_flowables = parse_section_lines(
            sidebar_lines,
            styles,
            is_sidebar=True,
            figures=figures,
            chapter_title_for_figures=chapter_title,
            diagram_renderer=diagram_renderer,
            math_renderer=math_renderer,
            palette=palette,
            chapter_anchor=chapter_anchor,
            link_resolver=link_resolver,
        )
        if sb_flowables:
            flowables.append(Spacer(1, 10))
            flowables.append(
                make_sidebar(
                    config.sidebar_title,
                    sb_flowables,
                    styles,
                    title_prefix=config.sidebar_prefix,
                    palette=palette,
                )
            )

    if fr_lines:
        flowables.append(Paragraph("Further Reading", styles["fr_title"]))
        items: list[str] = []
        current: str | None = None
        for ln in fr_lines:
            ln = ln.rstrip()
            if not ln.strip():
                continue
            if m := re.match(r"^\d+\. (.+)$", ln):
                if current is not None:
                    items.append(current)
                current = m.group(1)
            elif current is not None and re.match(r"^\s+", ln):
                current += " " + ln.strip()
            elif ln.startswith("- ") or ln.startswith("* "):
                if current is not None:
                    items.append(current)
                current = ln[2:].strip()
        if current:
            items.append(current)
        for idx, item in enumerate(items, 1):
            flowables.append(
                Paragraph(
                    f"{idx}.  {fmt(item, link_resolver=link_resolver)}",
                    styles["fr_item"],
                )
            )

    return flowables


# ─── H2-section splitter ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class MdH2Section:
    """One H2-delimited section of a markdown document.

    Attributes:
        title: Display title (inline markers stripped via
            :func:`_heading_to_title`).
        raw_title: Original H2 text after stripping the ``## `` prefix.
        lines: Body lines that follow the H2 heading, up to (but not
            including) the next H2 or end-of-file.
        anchor_slug: URL / PDF anchor slug derived from ``raw_title``
            via :func:`slugify_heading`.
    """

    title: str
    raw_title: str
    lines: list[str] = field(default_factory=list)
    anchor_slug: str = ""


def split_md_by_h2(
    filepath: Path,
) -> tuple[str, list[str], list[MdH2Section]]:
    """Split a markdown file into its H1 title, lead prose, and H2 sections.

    Reads ``filepath`` and returns a 3-tuple:

    * ``h1_title`` — the text of the first ``# Heading`` line (or ``""``
      if none is found).
    * ``lead_lines`` — raw lines between the H1 and the first H2 (or all
      lines when there are no H2 headings).
    * ``sections`` — one :class:`MdH2Section` per ``## Heading`` found in
      the document, in source order.  Each section's ``lines`` list
      contains the raw body lines that follow the heading up to (but not
      including) the next ``## Heading`` or end-of-file.

    The function preserves every line as-is (no stripping beyond what is
    needed to detect heading markers) so that
    :func:`parse_section_lines` can process the body lines without loss.
    """
    text = filepath.read_text(encoding="utf-8")
    raw_lines: list[str] = text.split("\n")

    h1_title: str = ""
    lead_lines: list[str] = []
    sections: list[MdH2Section] = []

    # State: "pre_h1" → "lead" (after H1 seen) → "section" (inside an H2)
    state = "pre_h1"
    current_raw_title: str = ""
    current_body: list[str] = []

    for line in raw_lines:
        stripped = line.rstrip()

        # H1 — capture title, switch to lead collection
        if m := _H1_RE.match(stripped):
            if state == "pre_h1":
                h1_title = _heading_to_title(m.group(1))
                state = "lead"
            # Extra H1s fall through to the active bucket.
            elif state == "lead":
                lead_lines.append(line)
            else:
                current_body.append(line)
            continue

        # H2 — start a new section; flush the previous one if any
        if m := _H2_RE.match(stripped):
            if state == "section":
                sections.append(
                    MdH2Section(
                        title=_heading_to_title(current_raw_title),
                        raw_title=current_raw_title,
                        lines=current_body,
                        anchor_slug=slugify_heading(current_raw_title),
                    )
                )
            current_raw_title = m.group(1)
            current_body = []
            state = "section"
            continue

        # Body line — route to the active bucket
        if state == "pre_h1":
            pass  # lines before the H1 are discarded
        elif state == "lead":
            lead_lines.append(line)
        else:
            current_body.append(line)

    # Flush the last open section
    if state == "section":
        sections.append(
            MdH2Section(
                title=_heading_to_title(current_raw_title),
                raw_title=current_raw_title,
                lines=current_body,
                anchor_slug=slugify_heading(current_raw_title),
            )
        )

    return h1_title, lead_lines, sections
