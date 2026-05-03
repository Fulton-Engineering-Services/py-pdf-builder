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

"""Table-of-contents factory + figure registry.

Reports build a :class:`FigureRegistry`,
emit anchors via :class:`FigureAnchor`, and pass the registry to
:func:`toc_pages` to produce a clickable index.

Public surface:

* :class:`FigureRegistry` — accumulates ``(fig_key, chapter, dtype)`` triples.
* :func:`toc_pages` — given a list of TOC entries (and optionally a
  registry), builds the flowables for the contents page(s).
* :func:`anchor_key` — derive a PDF-safe anchor key from a markdown
  filename.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from reportlab.platypus import HRFlowable, PageBreak, Paragraph, Spacer

from .branding import Palette, default_palette
from .flowables import ChapterAnchor, HeaderState
from .text import esc

__all__ = [
    "FigureEntry",
    "FigureRegistry",
    "TocEntry",
    "TocPart",
    "anchor_key",
    "toc_pages",
]


# ─── Data shapes ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FigureEntry:
    """One row in the TOC's "Figures & Diagrams" section."""

    fig_key: str
    chapter_title: str
    diagram_type: str  # e.g. "Flowchart", "Heatmap", "Bar Chart"
    title: str = ""  # per-figure caption rendered after the type


@dataclass
class FigureRegistry:
    """Mutable list of :class:`FigureEntry` items.

    Reports register figures here as they emit them; :func:`toc_pages`
    iterates the registry in registration order to build the figures
    section. The registry also exposes :meth:`next_key` so renderers can
    request a stable ``fig_NNN`` key.
    """

    entries: list[FigureEntry] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def next_key(self) -> str:
        """Return ``fig_001``, ``fig_002``, ... incrementally."""
        return f"fig_{len(self.entries) + 1:03d}"

    def register(
        self,
        *,
        chapter_title: str,
        diagram_type: str,
        title: str = "",
    ) -> str:
        """Register and return a new key in one call.

        Args:
            chapter_title: Chapter heading the figure belongs to (used to
                group rows in the Figures section).
            diagram_type: Short type label (``"Bar chart"``, ``"Heatmap"``,
                ``"Flowchart"`` …) shown after the figure number.
            title: Optional per-figure caption appended after the type
                (``"Figure N \u00b7 Type \u00b7 Title"``). Empty string
                falls back to the legacy two-part label.
        """
        key = self.next_key()
        self.entries.append(
            FigureEntry(
                fig_key=key,
                chapter_title=chapter_title,
                diagram_type=diagram_type,
                title=title,
            )
        )
        return key


@dataclass(frozen=True)
class TocEntry:
    """One leaf line in the TOC.

    Attributes:
        label: Display text (already inline-formatted; pass plain text and
            :func:`toc_pages` will :func:`esc` it).
        anchor: PDF destination key (matches the :class:`ChapterAnchor`'s
            ``key``).
        deep: ``True`` to render with the italicized "deep dive" style
            (used for appendices).
    """

    label: str
    anchor: str
    deep: bool = False


@dataclass(frozen=True)
class TocPart:
    """A grouped section of TOC entries.

    Attributes:
        heading: Bold-uppercase heading rendered above the entries (e.g.
            ``"PART I — PRIMERS"`` or ``"GROUP A — SMALL MODELS"``).
        anchor: Optional PDF destination key the heading should link to
            (e.g. the part-divider page). ``None`` to render an unlinked
            heading.
        entries: Ordered list of :class:`TocEntry` items inside this part.
    """

    heading: str
    anchor: str | None
    entries: Sequence[TocEntry]


# ─── Builders ─────────────────────────────────────────────────────────────────


def anchor_key(name: str) -> str:
    """Derive a PDF-safe anchor key from a markdown filename or arbitrary id.

    Strips ``.md`` and replaces ``-`` with ``_``. Safe to call on already-clean ids.
    """
    return name.replace("-", "_").replace(".md", "")


def toc_pages(
    parts: Sequence[TocPart],
    styles: dict,
    *,
    state: HeaderState,
    title: str = "Contents",
    figures: FigureRegistry | None = None,
    palette: Palette | None = None,
    page_break_first: bool = True,
) -> list:
    """Build a clickable Table of Contents.

    Args:
        parts: Ordered list of :class:`TocPart`s.
        styles: Style dict from :func:`reporting.styles.make_styles`.
        state: Shared :class:`HeaderState` (so the TOC's own
            :class:`ChapterAnchor` updates the running header).
        title: Top-of-page heading (default ``"Contents"``).
        figures: Optional figure registry. When provided, a "Figures &
            Diagrams" section is appended grouped by chapter title.
        palette: Brand palette (used only for the link colour).
        page_break_first: Emit a ``PageBreak`` before the TOC body. Set to
            ``False`` if the caller already inserted one.

    Returns:
        A list of flowables ready to extend the story.
    """
    palette = palette or default_palette()

    items: list = []
    if page_break_first:
        items.append(PageBreak())
    items.extend(
        [
            ChapterAnchor("sec_toc", title, state=state, level=0),
            Paragraph(title, styles["toc_h"]),
            Spacer(1, 4),
            HRFlowable(
                width="100%",
                thickness=1,
                color=palette.slate_mid,
                spaceBefore=0,
                spaceAfter=12,
            ),
        ]
    )

    blue = (
        f"#{int(palette.blue.red * 255):02X}"
        f"{int(palette.blue.green * 255):02X}"
        f"{int(palette.blue.blue * 255):02X}"
    )
    navy = (
        f"#{int(palette.navy.red * 255):02X}"
        f"{int(palette.navy.green * 255):02X}"
        f"{int(palette.navy.blue * 255):02X}"
    )

    for pi, part in enumerate(parts):
        if pi > 0:
            items.append(Spacer(1, 12))
        if part.anchor:
            heading_html = (
                f'<a href="#{esc(part.anchor)}"><font color="{navy}">{esc(part.heading)}</font></a>'
            )
        else:
            heading_html = f'<font color="{navy}">{esc(part.heading)}</font>'
        items.append(Paragraph(heading_html, styles["toc_part"]))

        for entry in part.entries:
            link_html = (
                f'<a href="#{esc(entry.anchor)}"><font color="{blue}">{esc(entry.label)}</font></a>'
            )
            style = styles["toc_deep"] if entry.deep else styles["toc_entry"]
            items.append(Paragraph(link_html, style))

    if figures is not None and len(figures) > 0:
        items.extend(
            [
                Spacer(1, 16),
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=palette.slate_mid,
                    spaceBefore=0,
                    spaceAfter=10,
                ),
                Paragraph(
                    f'<font color="{navy}">FIGURES &amp; DIAGRAMS</font>',
                    styles["toc_part"],
                ),
            ]
        )
        current_chap = None
        for fig_num, fig_entry in enumerate(figures.entries, 1):
            if fig_entry.chapter_title != current_chap:
                items.append(Paragraph(esc(fig_entry.chapter_title), styles["toc_fig_chap"]))
                current_chap = fig_entry.chapter_title
            label_parts = [f"Figure {fig_num}", fig_entry.diagram_type]
            if fig_entry.title:
                label_parts.append(fig_entry.title)
            label = " \u00b7 ".join(label_parts)
            key = esc(fig_entry.fig_key)
            link = f'<a href="#{key}"><font color="{blue}">{esc(label)}</font></a>'
            items.append(Paragraph(link, styles["toc_fig_entry"]))

    return items


def _flatten_for_doctests(parts: Iterable[TocPart]) -> tuple[int, int]:  # pragma: no cover
    """Quick sanity helper used by tests."""
    total = 0
    n_parts = 0
    for p in parts:
        n_parts += 1
        total += len(p.entries)
    return n_parts, total
