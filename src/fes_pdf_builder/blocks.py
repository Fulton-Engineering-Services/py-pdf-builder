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

"""Reusable visual blocks: sidebar, code, math, markdown table, simple table.

Parametrized on a :class:`Layout` so non-letter-size reports work without a
fork. Every helper returns a single ReportLab flowable that can be appended
to a story.

Public functions:

* :func:`make_sidebar` — blue-left-bordered "Practical Application" box.
* :func:`make_code_block` — dark-background code block with optional
  language label.
* :func:`make_image` — embed a raster image (PNG/JPEG/…) as a ReportLab
  flowable, scaling to preserve aspect ratio.
* :func:`make_image_block` — centered, boxed image block with an optional
  caption row.
* :func:`make_md_table` — header-row + zebra-striped data table from
  pre-split markdown rows.
* :func:`make_simple_table` — one-cell-per-cell key/value or comparison
  table for spec-renderers.
* :func:`make_kv_table` — two- or three-column key/value table.
* :func:`interpretation_box` — severity-coloured verdict callout.
* :func:`see_also_block` — italic "See also" cross-chapter footer.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from io import BytesIO
from os import PathLike, fspath
from pathlib import Path
from typing import Protocol, runtime_checkable

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from .branding import Layout, Palette, default_layout, default_palette
from .text import esc, fmt

__all__ = [
    "SEVERITY_HEX",
    "VerdictLike",
    "interpretation_box",
    "make_code_block",
    "make_image",
    "make_image_block",
    "make_kv_table",
    "make_md_table",
    "make_sidebar",
    "make_simple_table",
    "see_also_block",
    "severity_color_hex",
]


# ─── VerdictLike protocol ────────────────────────────────────────────────────


@runtime_checkable
class VerdictLike(Protocol):
    """Structural protocol for objects accepted by :func:`interpretation_box`.

    Any object with ``label``, ``evidence``, and ``severity`` attributes
    satisfies this protocol. The canonical implementation is
    ``reporting.data.interpretation.Verdict`` in the consuming project, but
    the library itself carries no data-layer dependency.
    """

    @property
    def label(self) -> str: ...

    @property
    def evidence(self) -> str: ...

    @property
    def severity(self) -> str: ...


# ─── Verdict severity palette ────────────────────────────────────────────────

# Hex strings for the four severity levels. Aligned with the status
# palette used elsewhere so the report uses one visual vocabulary for both
# phase statuses and verdict severities.
SEVERITY_HEX = {
    "ok": "#16A34A",  # green-600
    "info": "#1D4ED8",  # blue-700
    "warn": "#D97706",  # amber-600
    "alert": "#B91C1C",  # red-700
}


def severity_color_hex(severity: str) -> str:
    """Look up a hex string for a verdict severity, with a slate fallback."""
    return SEVERITY_HEX.get(str(severity).lower(), "#475569")


# ─── Sidebar ─────────────────────────────────────────────────────────────────


def make_sidebar(
    title_text: str,
    content_items: Iterable,
    styles: dict,
    *,
    layout: Layout | None = None,
    palette: Palette | None = None,
    title_prefix: str = "▸  PRACTICAL APPLICATION",
) -> Table:
    """Blue-left-bordered sidebar — multi-row so ReportLab can split across pages.

    Args:
        title_text: Sidebar title (will be uppercased and prefixed).
        content_items: Iterable of pre-built flowables (Paragraphs, Tables, …)
            to stack inside the sidebar body.
        styles: Style dict from :func:`fes_pdf_builder.styles.make_styles`.
        layout: Page geometry; defaults to :func:`default_layout`.
        palette: Brand palette; defaults to :func:`default_palette`.
        title_prefix: Override the default "PRACTICAL APPLICATION" lead-in
            (e.g. ``"▸  RECOMMENDED RUNTIME"`` for spec-renderer sidebars).
    """
    layout = layout or default_layout()
    palette = palette or default_palette()

    title_para = Paragraph(
        f"{title_prefix} — {title_text.upper()}",
        styles["sidebar_title"],
    )
    rows: list[list] = [[title_para]]
    for item in content_items:
        rows.append([item])

    t = Table(rows, colWidths=[layout.frame_width], splitByRow=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette.blue_xlight),
                ("LINEBEFORE", (0, 0), (0, -1), 3, palette.blue),
                ("BOX", (0, 0), (-1, -1), 0.5, palette.blue_light),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (0, 0), 10),
                ("BOTTOMPADDING", (0, 0), (0, 0), 6),
                ("BOTTOMPADDING", (0, -1), (0, -1), 10),
            ]
        )
    )
    return t


# ─── Code block ──────────────────────────────────────────────────────────────


def make_code_block(
    code_text: str,
    lang: str,
    styles: dict,
    *,
    layout: Layout | None = None,
    palette: Palette | None = None,
    max_lines_per_chunk: int = 8,
) -> Table:
    """Dark-background code block using ``<br/>`` line breaks.

    Long inputs are split into multiple ~``max_lines_per_chunk``-line
    paragraphs (one per row of the wrapping :class:`Table`) so that
    ReportLab can split the block across pages without raising a
    ``LayoutError``.

    Args:
        code_text: Raw source text.
        lang: Optional language label (rendered uppercased above the block).
            Empty string suppresses the label.
        styles: Style dict from :func:`fes_pdf_builder.styles.make_styles`.
        layout: Page geometry.
        palette: Brand palette.
        max_lines_per_chunk: Maximum number of source lines per paragraph chunk.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()

    raw_lines = code_text.split("\n")
    formatted: list[str] = []
    for ln in raw_lines:
        if len(ln) > 110:
            ln = ln[:107] + "..."
        stripped = ln.lstrip(" ")
        n_spaces = len(ln) - len(stripped)
        formatted.append("&nbsp;" * n_spaces + esc(stripped))

    rows: list[list] = []
    if lang:
        rows.append([Paragraph(lang.upper(), styles["code_label"])])

    for start in range(0, len(formatted), max_lines_per_chunk):
        chunk = formatted[start : start + max_lines_per_chunk]
        br_text = "<br/>".join(chunk) if chunk else ""
        try:
            chunk_para = Paragraph(br_text, styles["code"])
        except Exception:
            chunk_para = Paragraph(
                esc("\n".join(raw_lines[start : start + max_lines_per_chunk])), styles["code"]
            )
        rows.append([chunk_para])

    if not rows:
        rows = [[Paragraph("", styles["code"])]]

    t = Table(rows, colWidths=[layout.frame_width], splitByRow=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette.code_bg),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, palette.slate),
            ]
        )
    )
    return t


# ─── Markdown table ──────────────────────────────────────────────────────────


def make_md_table(
    rows: Sequence[Sequence[str]],
    styles: dict,
    *,
    layout: Layout | None = None,
    palette: Palette | None = None,
) -> Table | None:
    """Convert markdown table rows into a ReportLab table.

    The first row becomes the header. Cells are passed through
    :func:`fes_pdf_builder.text.fmt` so inline markdown survives.
    """
    if not rows:
        return None
    layout = layout or default_layout()
    palette = palette or default_palette()

    col_count = max(len(r) for r in rows)
    col_w = layout.frame_width / col_count

    th_style = ParagraphStyle(
        "th",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=palette.white,
    )
    td_style = ParagraphStyle(
        "td",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=palette.text_dark,
    )

    data: list[list[Paragraph]] = []
    for ri, row in enumerate(rows):
        padded = list(row) + [""] * (col_count - len(row))
        cell_style = th_style if ri == 0 else td_style
        data.append([Paragraph(fmt(c.strip()), cell_style) for c in padded])

    t = Table(data, colWidths=[col_w] * col_count)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette.navy),
                ("BACKGROUND", (0, 1), (-1, -1), palette.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [palette.white, palette.slate_light]),
                ("GRID", (0, 0), (-1, -1), 0.5, palette.slate_mid),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    return t


def make_simple_table(
    rows: Sequence[Sequence[str]],
    *,
    has_header: bool = True,
    col_widths: Sequence[float] | None = None,
    styles: dict | None = None,
    layout: Layout | None = None,
    palette: Palette | None = None,
    escape_cells: bool = True,
) -> Table | None:
    """Plain-text version of :func:`make_md_table` for data-driven reports.

    Behaves identically to :func:`make_md_table` but skips ``fmt()`` so
    callers can pass already-formatted strings (or plain numbers).

    Args:
        rows: List of row tuples (first row is the header iff ``has_header``).
        has_header: Treat the first row as a header (navy background, white text).
        col_widths: Optional explicit column widths in points. Defaults to
            equal-width columns summing to ``layout.frame_width``.
        escape_cells: When ``True`` (default), each cell value is XML-escaped
            via :func:`esc` so plain strings render literally. Set to
            ``False`` when callers have already built ReportLab-safe
            markup (e.g. ``<a href="#anchor">…</a>`` internal-PDF links
            or ``<font color="…">…</font>`` colored spans) and want it
            passed through verbatim. Header cells are still escaped.
    """
    if not rows:
        return None
    layout = layout or default_layout()
    palette = palette or default_palette()

    col_count = max(len(r) for r in rows)
    if col_widths is None:
        col_widths = [layout.frame_width / col_count] * col_count

    th_style = ParagraphStyle(
        "th_simple",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=palette.white,
    )
    td_style = ParagraphStyle(
        "td_simple",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=palette.text_dark,
    )

    data: list[list[Paragraph]] = []
    for ri, row in enumerate(rows):
        padded = list(row) + [""] * (col_count - len(row))
        is_header_row = has_header and ri == 0
        cell_style = th_style if is_header_row else td_style
        cells: list[Paragraph] = []
        for c in padded:
            text = str(c)
            if escape_cells or is_header_row:
                text = esc(text)
            cells.append(Paragraph(text, cell_style))
        data.append(cells)

    style_cmds: list = [
        ("GRID", (0, 0), (-1, -1), 0.5, palette.slate_mid),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if has_header:
        style_cmds.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette.navy),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [palette.white, palette.slate_light]),
            ]
        )
    else:
        style_cmds.append(
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [palette.white, palette.slate_light])
        )

    t = Table(list(data), colWidths=list(col_widths))
    t.setStyle(TableStyle(style_cmds))
    return t


def make_kv_table(
    pairs: Sequence[tuple[str, str] | tuple[str, str, str]],
    *,
    label_width_ratio: float = 0.32,
    value_width_ratio: float | None = None,
    has_context_column: bool | None = None,
    show_header: bool | None = None,
    layout: Layout | None = None,
    palette: Palette | None = None,
) -> Table | None:
    """Two- or three-column key/value table with bold labels and zebra rows.

    The ``pairs`` argument accepts either:

    * 2-tuples ``(label, value)`` — classic 2-column layout (default
      32 / 68 split, no header row).
    * 3-tuples ``(label, value, context)`` — 3-column layout with a
      bold "Field / Value / Context" navy header row.

    When ``has_context_column`` is ``None`` (the default), it is
    auto-detected: any 3-tuple in ``pairs`` switches the table to
    3-column mode.

    Args:
        pairs: Iterable of 2- or 3-tuples; mixing is allowed.
        label_width_ratio: Fraction of the frame width allocated to the label column.
        value_width_ratio: Fraction allocated to the value column.
        has_context_column: Force 2- or 3-column mode. ``None`` to auto-detect.
        show_header: Render a navy "Field / Value / Context" header row.
    """
    if not pairs:
        return None
    layout = layout or default_layout()
    palette = palette or default_palette()

    normalized: list[tuple[str, str, str]] = []
    for row in pairs:
        if len(row) == 2:
            k, v = row
            normalized.append((str(k), str(v), ""))
        elif len(row) == 3:
            k, v, c = row
            normalized.append((str(k), str(v), str(c)))
        else:  # pragma: no cover
            raise ValueError(f"make_kv_table rows must be 2- or 3-tuples; got {row!r}")

    if has_context_column is None:
        has_context_column = any(c for _, _, c in normalized)
    if show_header is None:
        show_header = has_context_column

    total = layout.frame_width
    if has_context_column:
        if value_width_ratio is None:
            value_width_ratio = 0.30
        ctx_ratio = max(0.0, 1.0 - label_width_ratio - value_width_ratio)
        col_widths = [
            total * label_width_ratio,
            total * value_width_ratio,
            total * ctx_ratio,
        ]
    else:
        if value_width_ratio is None:
            value_width_ratio = 1 - label_width_ratio
        col_widths = [total * label_width_ratio, total * value_width_ratio]

    label_style = ParagraphStyle(
        "kv_label",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=palette.navy,
    )
    value_style = ParagraphStyle(
        "kv_value",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=palette.text_dark,
    )
    ctx_style = ParagraphStyle(
        "kv_context",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=palette.text_mid,
    )
    th_style = ParagraphStyle(
        "kv_th",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=palette.white,
    )

    data: list[list[Paragraph]] = []
    if show_header:
        if has_context_column:
            data.append(
                [
                    Paragraph("Field", th_style),
                    Paragraph("Value", th_style),
                    Paragraph("Context", th_style),
                ]
            )
        else:
            data.append(
                [
                    Paragraph("Field", th_style),
                    Paragraph("Value", th_style),
                ]
            )

    for k, v, c in normalized:
        cells = [
            Paragraph(esc(k), label_style),
            Paragraph(esc(v), value_style),
        ]
        if has_context_column:
            cells.append(Paragraph(fmt(c) if c else "", ctx_style))
        data.append(cells)

    style_cmds: list = [
        ("GRID", (0, 0), (-1, -1), 0.25, palette.slate_mid),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if show_header:
        style_cmds.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette.navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [palette.white, palette.slate_light]),
            ]
        )
    else:
        style_cmds.append(
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [palette.white, palette.slate_light])
        )

    t = Table(data, colWidths=col_widths, splitByRow=1, repeatRows=1 if show_header else 0)
    t.setStyle(TableStyle(style_cmds))
    return t


# ─── Verdict / see-also callouts ─────────────────────────────────────────────


def interpretation_box(
    verdict: VerdictLike,
    *,
    layout: Layout | None = None,
    palette: Palette | None = None,
    styles: dict | None = None,
    spacer_before: int = 6,
) -> KeepTogether:
    """Render a "verdict + evidence" callout box.

    Visually distinct from both the yellow failure callout and the blue
    "Practical Application" sidebar:

    * Slate-light background.
    * Severity-coloured 3-point left border (green / blue / amber / red).
    * First line: bold uppercase ``"VERDICT — {label}"``.
    * Second line: italic evidence with the supporting numbers explicit.

    The whole box is wrapped in :class:`KeepTogether` so the verdict and
    its evidence can never be split across a page boundary.

    Accepts any object satisfying the :class:`VerdictLike` protocol
    (``label``, ``evidence``, ``severity`` attributes).
    """
    layout = layout or default_layout()
    palette = palette or default_palette()
    del styles  # accepted for forward-compat; not used here

    from reportlab.lib.colors import HexColor

    border = HexColor(severity_color_hex(getattr(verdict, "severity", "info")))

    label_style = ParagraphStyle(
        "verdict_label",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=palette.text_dark,
        spaceBefore=0,
        spaceAfter=2,
    )
    evidence_style = ParagraphStyle(
        "verdict_evidence",
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12.5,
        textColor=palette.text_mid,
        spaceBefore=0,
        spaceAfter=0,
    )

    label_html = f"VERDICT &mdash; {getattr(verdict, 'label', '')}"
    evidence_html = getattr(verdict, "evidence", "") or ""
    inner = [
        Paragraph(label_html, label_style),
        Paragraph(evidence_html, evidence_style),
    ]
    box = Table([[inner]], colWidths=[layout.frame_width])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette.slate_light),
                ("LINEBEFORE", (0, 0), (0, -1), 3, border),
                ("BOX", (0, 0), (-1, -1), 0.4, palette.slate_mid),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    items: list = []
    if spacer_before:
        items.append(Spacer(1, spacer_before))
    items.append(box)
    return KeepTogether(items)


def see_also_block(
    pointers: Sequence[str],
    *,
    palette: Palette | None = None,
    styles: dict | None = None,
    spacer_before: int = 8,
) -> KeepTogether | None:
    """Render a small italic "See also:" footer for cross-chapter pointers."""
    if not pointers:
        return None
    palette = palette or default_palette()
    del styles  # accepted for forward-compat; not used here

    italic = ParagraphStyle(
        "see_also",
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=palette.slate,
        spaceBefore=0,
        spaceAfter=0,
    )
    items: list = [Spacer(1, spacer_before)]
    items.append(Paragraph("<b>See also:</b>", italic))
    for p in pointers:
        items.append(Paragraph(f"&bull; {p}", italic))
    return KeepTogether(items)


# ─── Image embedding ──────────────────────────────────────────────────────────


def _sniff_svg(image: str | PathLike[str] | bytes | BytesIO) -> bool:
    """Return ``True`` if ``image`` looks like an SVG document."""
    if isinstance(image, (str, PathLike)):
        return Path(fspath(image)).suffix.lower() in (".svg", ".svgz")
    head = image if isinstance(image, bytes) else _peek(image)
    stripped = head[:2048].lstrip()
    return stripped.startswith(b"<svg") or (stripped.startswith(b"<?xml") and b"<svg" in stripped)


def _peek(stream: BytesIO) -> bytes:
    """Read up to 2 KiB from a binary stream without moving its position."""
    pos = stream.tell()
    try:
        return stream.read(2048)
    finally:
        stream.seek(pos)


def _natural_size_pts(reader: ImageReader, w_px: float, h_px: float) -> tuple[float, float]:
    """Return an image's natural ``(width, height)`` in points, honouring DPI."""
    try:
        dpi_x, dpi_y = reader.getDPI()
    except Exception:  # pragma: no cover - format-dependent attribute absence
        dpi_x = dpi_y = 72.0
    dpi_x = dpi_x or 72.0
    dpi_y = dpi_y or 72.0
    return w_px * 72.0 / dpi_x, h_px * 72.0 / dpi_y


def _svg_to_png(image: str | PathLike[str] | bytes | BytesIO) -> BytesIO:  # pragma: no cover
    """Rasterize an SVG to PNG bytes using the optional ``svglib`` dependency.

    This conversion path is only exercised when ``svglib`` is installed; the
    project's default dependency set does not include it, so the happy path
    is marked ``no cover`` and the missing-dependency branch is tested
    instead.
    """
    try:
        from reportlab.graphics import renderPM
        from svglib.svglib import svg2rlg
    except ImportError as exc:
        raise ValueError(
            "SVG images are not natively supported by ReportLab. Install the "
            "optional 'svglib' package (pip install svglib) or rasterize the "
            "image to PNG/JPEG before embedding."
        ) from exc

    if isinstance(image, bytes):
        source: str | BytesIO = BytesIO(image)
    elif isinstance(image, (str, PathLike)):
        source = fspath(image)
    else:
        image.seek(0)
        source = image

    try:
        drawing = svg2rlg(source)
        if drawing is None:
            raise ValueError("svglib could not parse the SVG document.")
        buf = BytesIO()
        renderPM.drawToFile(drawing, buf, fmt="PNG", dpi=150)
        buf.seek(0)
        return buf
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Failed to rasterize SVG: {exc}") from exc


def _raster_image(
    image: str | PathLike[str] | bytes | BytesIO,
    *,
    width_pts: float | None,
    height_pts: float | None,
    max_width_pts: float | None,
    max_height_pts: float | None,
    layout: Layout,
) -> RLImage:
    """Render a raster image (PNG/JPEG/…) into a sized ReportLab flowable."""
    source: str | BytesIO = BytesIO(image) if isinstance(image, bytes) else image
    if isinstance(source, (str, PathLike)):
        source = fspath(source)
    else:
        source.seek(0)

    reader = ImageReader(source)
    w_px, h_px = reader.getSize()
    nat_w, nat_h = _natural_size_pts(reader, float(w_px), float(h_px))

    if width_pts is not None and height_pts is not None:
        w = float(width_pts)
        h = float(height_pts)
    elif width_pts is not None:
        w = float(width_pts)
        h = w * h_px / w_px
    elif height_pts is not None:
        h = float(height_pts)
        w = h * w_px / h_px
    else:
        w, h = nat_w, nat_h

    max_w = max_width_pts if max_width_pts is not None else layout.frame_width
    if w > max_w:
        scale = max_w / w
        w *= scale
        h *= scale
    if max_height_pts is not None and h > max_height_pts:
        scale = max_height_pts / h
        w *= scale
        h *= scale

    if not isinstance(source, str):
        source.seek(0)
    return RLImage(source, width=w, height=h)


def make_image(
    image: str | PathLike[str] | bytes | BytesIO,
    *,
    width_pts: float | None = None,
    height_pts: float | None = None,
    max_width_pts: float | None = None,
    max_height_pts: float | None = None,
    layout: Layout | None = None,
) -> RLImage:
    """Embed an image (PNG/JPEG/…, or SVG via optional svglib) as a flowable.

    The image's aspect ratio is preserved unless both ``width_pts`` and
    ``height_pts`` are supplied (which forces an exact size and may distort
    the image). Pass only one dimension to fix it and derive the other from
    the image's pixel ratio; pass neither to render at the natural size
    (honouring any embedded DPI), then scale down — if necessary — to fit
    ``max_width_pts`` (default: the body frame width).

    Args:
        image: Image source — a filesystem path (``str`` / ``PathLike``),
            raw ``bytes``, or a ``BytesIO`` buffer.
        width_pts: Fixed display width in points (height derived).
        height_pts: Fixed display height in points (width derived).
        max_width_pts: Maximum width; over-sized images are scaled down.
            Defaults to ``layout.frame_width``.
        max_height_pts: Optional maximum height; over-tall images are
            scaled down proportionally.
        layout: Page geometry; defaults to :func:`default_layout`.

    Returns:
        A :class:`reportlab.platypus.Image` flowable ready to append to a
        story.
    """
    layout = layout or default_layout()
    if _sniff_svg(image):
        png = _svg_to_png(image)
        return _raster_image(  # pragma: no cover — SVG path needs svglib
            png,
            width_pts=width_pts,
            height_pts=height_pts,
            max_width_pts=max_width_pts,
            max_height_pts=max_height_pts,
            layout=layout,
        )
    return _raster_image(
        image,
        width_pts=width_pts,
        height_pts=height_pts,
        max_width_pts=max_width_pts,
        max_height_pts=max_height_pts,
        layout=layout,
    )


def make_image_block(
    image: str | PathLike[str] | bytes | BytesIO,
    *,
    caption: str = "",
    width_pts: float | None = None,
    height_pts: float | None = None,
    max_width_pts: float | None = None,
    max_height_pts: float | None = None,
    layout: Layout | None = None,
    palette: Palette | None = None,
) -> Table:
    """Centered, boxed image block with an optional caption row.

    Wraps :func:`make_image` in a single-column :class:`Table` so the image
    is centered in the body frame and — when ``caption`` is given — followed
    by a small centered caption. The thin slate border matches the diagram
    and math block styling.

    Args:
        image: Image source (see :func:`make_image`).
        caption: Optional plain-text caption rendered beneath the image.
        width_pts / height_pts / max_width_pts / max_height_pts: Sizing
            controls forwarded to :func:`make_image`.
        layout: Page geometry; defaults to :func:`default_layout`.
        palette: Brand palette; defaults to :func:`default_palette`.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()

    img = make_image(
        image,
        width_pts=width_pts,
        height_pts=height_pts,
        max_width_pts=max_width_pts,
        max_height_pts=max_height_pts,
        layout=layout,
    )
    rows: list[list] = [[img]]
    if caption:
        caption_style = ParagraphStyle(
            "figure_caption",
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=11,
            textColor=palette.slate,
            alignment=TA_CENTER,
            spaceBefore=6,
        )
        rows.append([Paragraph(esc(caption), caption_style)])

    t = Table(rows, colWidths=[layout.frame_width])
    t.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 0.5, palette.slate_mid),
            ]
        )
    )
    return t
