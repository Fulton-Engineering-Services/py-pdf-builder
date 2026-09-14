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

"""Generic single-file markdown → per-H2-chapter PDF builder.

:func:`build_single_markdown_pdf` handles the two-pass pattern common to
branded document reports:

Pass 1 — parse every H2 section into flowable blocks (populates the
:class:`FigureRegistry` so every diagram appears in the Figures TOC).

Pass 2 — assemble cover, preface, TOC, and part blocks, then concatenate
everything in render order.

Each H2 section becomes its own chapter (``chapter_label = "Chapter N of
M"``, ``chapter_title = <H2 text>``, accent rule, mermaid diagrams inline).
The lead prose between the H1 and the first H2 is rendered as an unlabelled
preface section on the page immediately after the cover.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path

from reportlab.platypus import HRFlowable, NextPageTemplate, PageBreak, Paragraph, Spacer

from ..branding import Layout, Palette
from ..diagrams.math import make_math_block
from ..diagrams.mermaid import make_diagram_box
from ..flowables import BookmarkAnchor, ChapterAnchor, HeaderState
from ..markdown import parse_section_lines, split_md_by_h2
from ..text import esc
from ..toc import FigureRegistry, TocEntry, TocPart, toc_pages
from .base import ReportContext, build_doc, cover_pages, preamble_break

__all__ = ["SingleMdConfig", "build_single_markdown_pdf"]


@dataclass(frozen=True)
class SingleMdConfig:
    """Metadata and defaults for a single-markdown-file PDF.

    Attributes:
        out_path: Destination PDF path.
        source_path: Source ``.md`` file.
        doc_title: PDF metadata title and running footer.
        doc_subject: PDF metadata subject.
        doc_author: PDF metadata author and running header brand text.
        doc_creator: PDF metadata creator field.
        brand_line: Cover brand text (ALL CAPS, e.g. organisation name).
        title_lines: Cover title, one string per line.
        subtitle_lines: Cover subtitle, one string per line.
        reference_date: Date stamped on the cover; defaults to today.
        cover_footer_line: Optional text appended after the date on the
            cover (e.g. ``"Confidential — Internal Use"``). Empty string
            suppresses the extra text.
        math_mode: ``"legacy"`` (default) or ``"latex"``. Legacy renders
            ``\\[...\\]`` display blocks via matplotlib mathtext PNG and
            approximates ``\\(...\\)`` inline spans with Unicode glyphs.
            Latex mode renders display equations as vector graphics via
            ziamath (requires the ``[math]`` extra) and renders
            ``$...$``/``$$...$$``/``\\(...\\)`` inline spans as small
            images, with graceful per-formula fallbacks in both cases.
        palette: Brand palette override.
        layout: Page geometry override.
    """

    out_path: Path
    source_path: Path
    doc_title: str
    doc_subject: str
    doc_author: str
    doc_creator: str
    brand_line: str
    title_lines: list[str]
    subtitle_lines: list[str]
    reference_date: date_cls | None = None
    cover_footer_line: str = ""
    math_mode: str = "legacy"
    palette: Palette | None = None
    layout: Layout | None = None


def build_single_markdown_pdf(cfg: SingleMdConfig) -> Path:
    """Build a branded PDF from a single markdown source file.

    Each H2 heading becomes its own chapter (one chapter per section,
    labelled ``"Chapter N of M"``). The lead prose between the document's
    H1 and its first H2 is rendered as an unlabelled preface.

    Args:
        cfg: All required metadata and path information.

    Returns:
        Resolved :class:`Path` of the written PDF.
    """
    ref_date = cfg.reference_date or date_cls.today()
    source_path = Path(cfg.source_path)

    # Pre-flight: read and split the source document once.
    _h1_title, lead_lines, sections = split_md_by_h2(source_path)

    def story_builder(styles, state: HeaderState, p: Palette, lo: Layout) -> list:
        figures = FigureRegistry()

        # Mutable cell so the diagram renderer captures the *current* chapter
        # title at render time without requiring a full closure factory.
        current_title: list[str] = [""]

        def diagram_renderer(text: str, _styles: dict, *, title: str = "") -> list:
            return make_diagram_box(
                text,
                _styles,
                figures=figures,
                chapter_title=current_title[0] or cfg.doc_title,
                title=title,
                palette=p,
                layout=lo,
            )

        if cfg.math_mode == "latex":
            from ..diagrams.math_latex import make_math_block_latex

            def math_renderer(text: str, _styles: dict) -> object:
                return make_math_block_latex(text, _styles, layout=lo, palette=p)
        else:

            def math_renderer(text: str, _styles: dict) -> object:
                return make_math_block(text, _styles, layout=lo, palette=p)

        # ── Pass 1: parse all chapter bodies ─────────────────────────────
        # Done BEFORE assembling the TOC so the FigureRegistry is fully
        # populated when toc_pages() reads it.
        n_sections = len(sections)
        chapter_blocks: list[list] = []
        for i, sec in enumerate(sections, 1):
            current_title[0] = sec.title
            ch_anchor = f"sec__{sec.anchor_slug}"
            block: list = [NextPageTemplate("main"), PageBreak()]
            block.append(ChapterAnchor(ch_anchor, sec.title, state=state, level=1))
            block.append(Paragraph(esc(f"Chapter {i} of {n_sections}"), styles["chap_label"]))
            block.append(Paragraph(esc(sec.title), styles["chap_title"]))
            block.append(
                HRFlowable(
                    width="100%",
                    thickness=2,
                    color=p.blue,
                    spaceBefore=2,
                    spaceAfter=10,
                )
            )
            block.extend(
                parse_section_lines(
                    sec.lines,
                    styles,
                    figures=figures,
                    chapter_title_for_figures=sec.title,
                    diagram_renderer=diagram_renderer,
                    math_renderer=math_renderer,
                    palette=p,
                    chapter_anchor=ch_anchor,
                    math_mode=cfg.math_mode,
                )
            )
            chapter_blocks.append(block)

        # ── Pass 2: cover, preface, TOC ──────────────────────────────────
        story: list = []

        date_str = ref_date.strftime("%B %Y")
        date_line = f"{date_str}  ·  {cfg.cover_footer_line}" if cfg.cover_footer_line else date_str
        story.extend(
            cover_pages(
                styles,
                brand_line=cfg.brand_line,
                title_lines=cfg.title_lines,
                subtitle_lines=cfg.subtitle_lines,
                date_line=date_line,
                layout=lo,
            )
        )
        story.extend(preamble_break())

        # Preface — the lead paragraphs between H1 and the first H2.
        if lead_lines:
            current_title[0] = "Overview"
            preface_anchor = "sec__doc_overview"
            story.append(BookmarkAnchor(preface_anchor))
            story.extend(
                parse_section_lines(
                    lead_lines,
                    styles,
                    figures=figures,
                    chapter_title_for_figures="Overview",
                    diagram_renderer=diagram_renderer,
                    math_renderer=math_renderer,
                    palette=p,
                    chapter_anchor=preface_anchor,
                    math_mode=cfg.math_mode,
                )
            )
            story.append(Spacer(1, 10))

        # TOC — one entry per H2 section.
        toc_entries = [
            TocEntry(
                label=f"  {i:02d}  ·  {sec.title}",
                anchor=f"sec__{sec.anchor_slug}",
            )
            for i, sec in enumerate(sections, 1)
        ]
        toc_parts = [
            TocPart(
                heading="CONTENTS",
                anchor=None,
                entries=toc_entries,
            )
        ]
        story.extend(
            toc_pages(
                toc_parts,
                styles,
                state=state,
                figures=figures,
                palette=p,
            )
        )

        # ── Append chapter blocks ─────────────────────────────────────────
        for block in chapter_blocks:
            story.extend(block)

        return story

    return build_doc(
        ReportContext(
            out_path=cfg.out_path,
            title=cfg.doc_title,
            subject=cfg.doc_subject,
            author=cfg.doc_author,
            creator=cfg.doc_creator,
        ),
        story_builder,
        palette=cfg.palette,
        layout=cfg.layout,
    )
