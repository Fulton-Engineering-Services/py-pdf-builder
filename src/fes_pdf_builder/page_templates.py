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

"""ReportLab page templates: cover, main, and part-divider.

Every report uses the same three-template chassis (cover, main, part-divider).

The :func:`make_page_templates` factory wires together:

* a full-bleed navy ``cover`` template (used for the front cover only),
* a ``main`` body template with running header + footer (used for every
  body page; the header reads from the :class:`HeaderState` updated by
  :class:`ChapterAnchor` instances),
* a ``part`` divider template (full-bleed navy with an accent bar) used
  for "Part I — Primers" / "Part II — Deep Dives" style separators.

Two callable painters are also exposed in case a caller wants to register
them with a hand-built :class:`reportlab.platypus.PageTemplate`:

* :func:`make_cover_painter` and :func:`make_part_painter` are simple
  ``onPage`` painters that paint the navy backdrop.
* :func:`make_main_painter` is intentionally an ``onPageEnd`` painter (NOT
  ``onPage``). The deferred-execution model is required so that
  :class:`ChapterAnchor.draw` has already updated the header state before
  the header text is painted on a new chapter's first page.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.platypus import Frame, PageTemplate

from .branding import Layout, Palette, default_layout, default_palette
from .flowables import HeaderState

__all__ = [
    "PageContext",
    "make_cover_painter",
    "make_main_painter",
    "make_page_templates",
    "make_part_painter",
]


@dataclass(frozen=True)
class PageContext:
    """Static metadata painted by the running header / footer.

    Attributes:
        brand_text: Left-side header text (e.g. "Fulton Engineering Services LLC").
        document_title: Left-side footer text (the report's full title).
        copyright_line: Optional second footer line (e.g. ``"\u00a9 2026 …"``)
            painted left-aligned below ``document_title``. Empty string skips
            the line entirely.
    """

    brand_text: str
    document_title: str
    copyright_line: str = ""


# ─── Painters ─────────────────────────────────────────────────────────────────


def make_cover_painter(
    *,
    palette: Palette,
    layout: Layout,
) -> Callable:
    """Return an ``onPage`` painter that fills the cover page with brand navy."""

    def _cover_page(canvas, _doc) -> None:
        canvas.saveState()
        canvas.setFillColor(palette.navy)
        canvas.rect(0, 0, layout.page_width, layout.page_height, fill=1, stroke=0)
        # Decorative accent bar at ~4% from bottom.
        canvas.setFillColor(palette.blue)
        canvas.rect(0, layout.page_height * 0.04, layout.page_width, 6, fill=1, stroke=0)
        canvas.setFillColor(palette.accent_blue_dark)
        canvas.rect(0, layout.page_height * 0.04 + 6, layout.page_width, 2, fill=1, stroke=0)
        canvas.restoreState()

    return _cover_page


def make_part_painter(
    *,
    palette: Palette,
    layout: Layout,
) -> Callable:
    """Return an ``onPage`` painter for full-bleed Part-divider pages."""

    def _part_page(canvas, _doc) -> None:
        canvas.saveState()
        canvas.setFillColor(palette.navy)
        canvas.rect(0, 0, layout.page_width, layout.page_height, fill=1, stroke=0)
        canvas.setFillColor(palette.blue)
        canvas.rect(0, layout.page_height * 0.04, layout.page_width, 4, fill=1, stroke=0)
        canvas.restoreState()

    return _part_page


def make_main_painter(
    *,
    palette: Palette,
    layout: Layout,
    context: PageContext,
    state: HeaderState,
) -> Callable:
    """Return an ``onPageEnd`` painter for the running header + footer.

    The painter MUST be registered as ``onPageEnd`` (not ``onPage``) so that
    every :class:`ChapterAnchor` on the page has already mutated ``state``
    before the header text is drawn.
    """

    def _main_page(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(palette.slate)
        canvas.setStrokeColor(palette.slate_mid)
        canvas.setLineWidth(0.5)

        # ── Header ────────────────────────────────────────────────────────
        y_header = layout.page_height - layout.margin + 6
        canvas.line(layout.margin, y_header, layout.page_width - layout.margin, y_header)
        canvas.drawString(layout.margin, y_header + 4, context.brand_text)
        header_right = (
            f"Chapter: {state.current}"
            if state.current_is_chapter and state.current
            else state.current
        )
        canvas.drawRightString(
            layout.page_width - layout.margin,
            y_header + 4,
            header_right,
        )

        # ── Footer ────────────────────────────────────────────────────────
        # Single line: "{document title} · {copyright}" left-aligned and the
        # page number right-aligned. The two strings used to live in
        # separate slots (left + centred) which silently overlapped when
        # the document title grew long; concatenating them makes the
        # collision impossible.
        y_footer = layout.margin - 6
        canvas.line(layout.margin, y_footer, layout.page_width - layout.margin, y_footer)
        if context.document_title and context.copyright_line:
            footer_left = f"{context.document_title}  \u00b7  {context.copyright_line}"
        else:
            footer_left = context.document_title or context.copyright_line
        canvas.drawString(layout.margin, y_footer - 12, footer_left)
        canvas.drawRightString(
            layout.page_width - layout.margin,
            y_footer - 12,
            str(doc.page),
        )

        canvas.restoreState()

    return _main_page


# ─── Templates ────────────────────────────────────────────────────────────────


def make_page_templates(
    *,
    context: PageContext,
    state: HeaderState,
    palette: Palette | None = None,
    layout: Layout | None = None,
) -> list[PageTemplate]:
    """Build the canonical three-template chassis used by every report.

    Args:
        context: Static brand + document text painted in the header / footer.
        state: Mutable header state shared with :class:`ChapterAnchor`s.
        palette: Brand palette; defaults to :func:`default_palette`.
        layout: Page geometry; defaults to :func:`default_layout`.

    Returns:
        A list of three :class:`PageTemplate` instances with ids
        ``cover`` / ``main`` / ``part``. Callers should pass them straight
        into :meth:`BaseDocTemplate.addPageTemplates`. The first template
        in the returned list is the default ReportLab uses for page 1 — so
        cover-first reports work without an explicit ``NextPageTemplate``.
    """
    palette = palette or default_palette()
    layout = layout or default_layout()

    frame_main = Frame(
        layout.margin,
        # The footer is painted at ``y = margin - 6`` (just below the
        # bottom margin), but the running header is painted at the very
        # top of the top margin. Since ``main_frame_height`` already
        # subtracts BOTH ``header_height`` and ``footer_height``, the
        # frame's y-origin must include ``footer_height`` so the reserved
        # footer band sits between the frame's bottom and the bottom
        # margin — not above the frame's top, where it would otherwise
        # double the whitespace gap below the running header.
        layout.margin + layout.footer_height,
        layout.frame_width,
        layout.main_frame_height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="main_frame",
    )
    frame_cover = Frame(
        layout.margin,
        layout.margin,
        layout.frame_width,
        layout.cover_frame_height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="cover_frame",
    )

    return [
        PageTemplate(
            id="cover",
            frames=[frame_cover],
            onPage=make_cover_painter(palette=palette, layout=layout),
        ),
        PageTemplate(
            id="main",
            frames=[frame_main],
            onPageEnd=make_main_painter(
                palette=palette,
                layout=layout,
                context=context,
                state=state,
            ),
        ),
        PageTemplate(
            id="part",
            frames=[frame_cover],
            onPage=make_part_painter(palette=palette, layout=layout),
        ),
    ]


def _suppress_unused_import_warning() -> colors.Color:  # pragma: no cover
    """Some linters warn about ``colors`` unless we touch it at module scope."""
    return colors.white
