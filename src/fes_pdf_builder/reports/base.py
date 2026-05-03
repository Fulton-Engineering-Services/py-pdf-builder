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

"""Shared report driver.

Every per-report module ends in a one-line call to :func:`build_doc`,
which:

1. Constructs a fresh :class:`HeaderState` (so multiple builds in the same
   process don't share running-header text).
2. Wires the three brand page templates from :mod:`fes_pdf_builder.page_templates`.
3. Calls the supplied ``story_builder`` callback to assemble flowables.
4. Drops the PDF on disk via :class:`reportlab.platypus.BaseDocTemplate.build`.

It also re-exports the :func:`cover_pages`, :func:`preamble_break`, and
:func:`part_divider` factory helpers.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from reportlab.platypus import (
    BaseDocTemplate,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
)

from ..branding import Layout, Palette, default_layout, default_palette
from ..flowables import ChapterAnchor, HeaderState
from ..page_templates import PageContext, make_page_templates
from ..styles import make_styles
from ..text import esc

__all__ = [
    "ReportContext",
    "build_doc",
    "concept_overview",
    "cover_pages",
    "part_divider",
    "preamble_break",
]


# ─── Driver ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReportContext:
    """Aggregated input for :func:`build_doc`.

    Attributes:
        out_path: Output PDF path.
        title: Document title (used for the PDF metadata + footer text).
        subject: PDF metadata "subject" field.
        author: PDF metadata "author" / running-header brand text.
            Required — no default. Pass your organization name.
        creator: PDF metadata "creator" field.
            Required — no default. Pass your tool/team identifier.
    """

    out_path: Path
    title: str
    subject: str
    author: str
    creator: str


def build_doc(
    context: ReportContext,
    story_builder: Callable[[dict, HeaderState, Palette, Layout], list],
    *,
    palette: Palette | None = None,
    layout: Layout | None = None,
) -> Path:
    """Build a PDF using the shared chassis.

    The ``story_builder`` callback is the only per-report code: it receives
    a fresh styles dict, header state, palette, and layout, and returns a
    list of flowables. The driver wires templates and writes the PDF.

    Args:
        context: Static document metadata.
        story_builder: Callable that returns the report's flowables.
        palette: Brand palette override.
        layout: Page geometry override.

    Returns:
        Resolved path to the written PDF.
    """
    palette = palette or default_palette()
    layout = layout or default_layout()
    styles = make_styles(palette)
    state = HeaderState()

    out_path = Path(context.out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(out_path),
        pagesize=(layout.page_width, layout.page_height),
        leftMargin=layout.margin,
        rightMargin=layout.margin,
        topMargin=layout.margin,
        bottomMargin=layout.margin,
        title=context.title,
        author=context.author,
        subject=context.subject,
        creator=context.creator,
    )

    year = datetime.date.today().year
    page_ctx = PageContext(
        brand_text=context.author,
        document_title=context.title,
        copyright_line=f"\u00a9 {year} {context.author}",
    )
    doc.addPageTemplates(
        make_page_templates(
            context=page_ctx,
            state=state,
            palette=palette,
            layout=layout,
        )
    )

    story = story_builder(styles, state, palette, layout)
    doc.build(story)

    return out_path


# ─── Cover / part-divider factories ──────────────────────────────────────────


def cover_pages(
    styles: dict,
    *,
    brand_line: str,
    title_lines: list[str],
    subtitle_lines: list[str] | None = None,
    author_line: str | None = None,
    date_line: str = "",
    layout: Layout | None = None,
) -> list:
    """Build the cover-page flowables (front cover only).

    ReportLab's first page already uses the first registered template
    (``cover``), so callers should NOT prepend a :class:`NextPageTemplate`;
    the cover sits naturally on page 1, and the caller switches to
    ``"main"`` for page 2 (typically via :func:`preamble_break`).

    Args:
        brand_line: Small all-caps label at top of cover (e.g. organisation name).
        title_lines: Cover title, one string per line.
        subtitle_lines: Optional subtitle, one string per line.
        author_line: Optional author attribution rendered between the
            subtitle and date lines. The ``"Author - "`` prefix is added
            automatically.
        date_line: Optional date string at the bottom of the cover.
        layout: Page geometry override.
    """
    layout = layout or default_layout()
    flowables: list = [
        Spacer(1, layout.page_height * 0.22),
        Paragraph(esc(brand_line), styles["cover_brand"]),
        Spacer(1, 10),
        Paragraph(
            "<br/>".join(esc(line) for line in title_lines),
            styles["cover_title"],
        ),
        Spacer(1, 16),
    ]
    if subtitle_lines:
        flowables.append(
            Paragraph(
                "<br/>".join(esc(line) for line in subtitle_lines),
                styles["cover_sub"],
            )
        )
        flowables.append(Spacer(1, 18))
    if author_line:
        flowables.append(
            Paragraph(
                f"Author - {esc(author_line)}",
                styles["cover_author"],
            )
        )
        flowables.append(Spacer(1, 14))
    elif subtitle_lines:
        flowables.append(Spacer(1, 10))
    if date_line:
        flowables.append(Paragraph(esc(date_line), styles["cover_date"]))
    return flowables


def preamble_break() -> list:
    """Return the standard "switch to main template, advance one page" flowables."""
    return [NextPageTemplate("main"), PageBreak()]


def part_divider(
    styles: dict,
    *,
    label: str,
    title: str,
    description: str,
    state: HeaderState,
    anchor: str,
    outline_title: str,
    layout: Layout | None = None,
) -> list:
    """Full-bleed navy part-divider page.

    The caller is responsible for issuing the trailing
    ``NextPageTemplate('main')`` + ``PageBreak`` so the next chapter lands
    on the body template.
    """
    layout = layout or default_layout()
    return [
        NextPageTemplate("part"),
        PageBreak(),
        ChapterAnchor(anchor, outline_title, state=state, level=0),
        Spacer(1, layout.page_height * 0.25),
        Paragraph(esc(label), styles["part_label"]),
        Spacer(1, 8),
        Paragraph(esc(title), styles["part_title"]),
        Spacer(1, 16),
        Paragraph(esc(description), styles["part_desc"]),
    ]


def concept_overview(
    styles: dict,
    *,
    label: str,
    title: str,
    state: HeaderState,
    anchor: str,
    body: Iterable,
    outline_title: str | None = None,
    palette: Palette | None = None,
    layout: Layout | None = None,
) -> list:
    """Body-template "Concept Overview" preamble section.

    Unlike :func:`part_divider`, this stays on the ``main`` body template
    so the overview can flow across multiple pages and carry inline
    tables, summary matrices, and prose. The ``ChapterAnchor`` registers
    a top-level (``level=0``) PDF outline entry and a bookmark target so
    callers can cross-link from the TOC and from chapter prose with
    ``<a href="#{anchor}">``.

    Args:
        styles: Style dict from :func:`fes_pdf_builder.styles.make_styles`.
        label: Small all-caps label rendered above the title.
        title: Section title.
        state: Shared :class:`HeaderState` so the running header updates.
        anchor: PDF destination key for the overview's bookmark target.
        body: Iterable of pre-built flowables.
        outline_title: Optional override for the PDF outline / running-header
            text. Defaults to ``title`` when not supplied.
        palette: Brand palette (used for the accent rule under the title).
        layout: Page geometry override.

    Returns:
        A list of flowables ready to extend the story.
    """
    palette = palette or default_palette()
    layout = layout or default_layout()
    flowables: list = [
        NextPageTemplate("main"),
        PageBreak(),
        ChapterAnchor(
            anchor,
            outline_title or title,
            state=state,
            level=0,
        ),
        Paragraph(esc(label), styles["chap_label"]),
        Paragraph(esc(title), styles["chap_title"]),
        HRFlowable(
            width="100%",
            thickness=2,
            color=palette.blue,
            spaceBefore=2,
            spaceAfter=10,
        ),
    ]
    flowables.extend(body)
    return flowables
