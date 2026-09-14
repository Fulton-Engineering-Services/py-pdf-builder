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

"""High-fidelity LaTeX math rendering (optional ``[math]`` extra).

Display equations are rendered as vector graphics: ziamath (pure-Python
LaTeX → MathML → SVG, glyphs drawn as SVG paths so no font embedding is
needed) → svglib → a ReportLab :class:`~reportlab.graphics.shapes.Drawing`.
If ziamath/svglib are unavailable or cannot parse an expression, the
pipeline degrades gracefully: matplotlib mathtext PNG (see
:mod:`fes_pdf_builder.diagrams.math`), then the plain-text
:func:`fes_pdf_builder.text.clean_latex` representation. A single bad
formula never aborts a build.

Inline equations (``$...$`` / ``\\(...\\)`` spans inside a paragraph) are
rendered as small transparent PNGs via matplotlib mathtext, cropped to the
expression's ink and embedded as base64 data-URI ``<img>`` tags with a
numeric ``valign`` that baseline-aligns each formula with the surrounding
text.

Requires the ``[math]`` extra (``pip install fes-pdf-builder[math]``) for
the vector path; the matplotlib PNG path needs the ``[charts]``/``[diagrams]``
extra. When neither is installed, callers should fall back to plain text.

Public surface:

* :func:`render_latex_drawing` — ziamath → ``(Drawing, w_pts, h_pts)`` or None.
* :func:`render_inline_math_png` — mathtext → ``(png_bytes, w_pts, h_pts)`` or None.
* :func:`make_math_block_latex` — slate-bordered display block, vector-first.
* :func:`make_inline_math_img` — ``<img>`` XML tag for inline math, or None.
"""

from __future__ import annotations

import base64
import re
from io import BytesIO

from reportlab.graphics.shapes import Drawing
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, Table, TableStyle

from ..branding import Layout, Palette, default_layout, default_palette
from .math import render_latex_png

__all__ = [
    "make_inline_math_img",
    "make_math_block_latex",
    "render_inline_math_png",
    "render_latex_drawing",
]

# SVG user units are 96-dpi CSS pixels; ReportLab points are 72-dpi.
_SVG_PX_TO_PT = 72.0 / 96.0


def render_latex_drawing(
    latex_text: str,
    *,
    fontsize: int = 14,
    layout: Layout | None = None,
) -> tuple[Drawing, float, float] | None:
    """Render a LaTeX expression as a vector ReportLab Drawing via ziamath.

    Args:
        latex_text: LaTeX math source (``\\[...\\]`` / ``$$...$$`` wrappers
            are tolerated and stripped).
        fontsize: Base font size in points for the rendered expression.
        layout: Page layout for the max-width clamp; defaults to the brand
            layout when omitted.

    Returns:
        ``(drawing, width_pts, height_pts)`` on success, or ``None`` when
        ziamath/svglib are unavailable or cannot parse the expression.
    """
    layout = layout or default_layout()
    raw = latex_text.strip()
    raw = re.sub(r"^\\\[|\\\]$", "", raw).strip()
    raw = re.sub(r"^\$\$|\$\$$", "", raw).strip()
    if not raw:
        return None

    try:
        import ziamath
    except Exception:
        return None

    try:
        from svglib.svglib import svg2rlg
    except Exception:
        return None

    # Glyphs as <path> elements: svglib does not fully support SVG 2.0
    # <symbol>/<use> indirection. Plain paths are larger but always render.
    ziamath.config.svg2 = False

    try:
        eq = ziamath.Latex(raw, size=fontsize)
        svg_str = eq.svg()
        drawing = svg2rlg(BytesIO(svg_str.encode("utf-8")))
        if drawing is None:
            return None

        scale = _SVG_PX_TO_PT
        drawing.scale(scale, scale)
        drawing.width *= scale
        drawing.height *= scale

        max_w = layout.frame_width - 32
        if drawing.width > max_w > 0:
            fit = max_w / drawing.width
            drawing.scale(fit, fit)
            drawing.width *= fit
            drawing.height *= fit

        return drawing, drawing.width, drawing.height

    except Exception:
        return None


def render_inline_math_png(
    latex_text: str,
    *,
    fontsize: int = 10,
    dpi: int = 300,
) -> tuple[bytes, float, float, float] | None:
    """Render an inline LaTeX span as a tight transparent PNG (matplotlib).

    The image is cropped to the expression's ink (plus a 0.72 pt pad), so
    its width tracks the content instead of being a fixed-width rectangle,
    and it sits on the text baseline when the caller passes the returned
    descent to ReportLab as a numeric ``valign``.

    Args:
        latex_text: LaTeX math source; ``$...$``, ``\\(...\\)`` and
            ``\\[...\\]`` wrappers are tolerated and stripped.
        fontsize: Base mathtext font size in points; defaults to the 10 pt body size.
        dpi: Output resolution. 300 dpi keeps the raster crisp in print.

    Returns:
        ``(png_bytes, width_pts, height_pts, descent_pts)`` on success, or
        ``None`` when matplotlib is unavailable or cannot parse the
        expression. ``descent_pts`` is the distance from the bottom of the
        image to the math baseline (including the padding).
    """
    raw = latex_text.strip()
    raw = re.sub(r"^\\\[|\\\]$", "", raw).strip()
    raw = re.sub(r"^\\\(|\\\)$", "", raw).strip()
    raw = re.sub(r"^\$\$|\$\$$", "", raw).strip()
    raw = re.sub(r"^\$|\$$", "", raw).strip()
    if not raw:
        return None
    expr = raw if raw.startswith("$") else f"${raw}$"

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import mathtext
        from matplotlib.font_manager import FontProperties
    except Exception:
        return None

    try:
        prop = FontProperties(size=fontsize)
        # Parse at 72 dpi so the reported metrics are already in points;
        # ``depth`` is the ink descent below the baseline.
        _w, _h, depth_pts, _glyphs, _rects = mathtext.MathTextParser("path").parse(
            expr, dpi=72, prop=prop
        )

        # Figure-level text artist (no axes) so ``bbox_inches="tight"``
        # crops to the glyphs rather than to a fixed-width axes rectangle.
        fig = plt.figure(figsize=(0.5, 0.5))
        fig.patch.set_alpha(0)
        fig.text(
            0.0,
            0.0,
            expr,
            fontproperties=prop,
            color="#0F172A",
            ha="left",
            va="bottom",
        )
        pad_in = 0.01
        buf = BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=pad_in,
            transparent=True,
        )
        plt.close(fig)
        buf.seek(0)

        ir = ImageReader(buf)
        w_px, h_px = ir.getSize()
        w_pts = w_px * 72.0 / dpi
        h_pts = h_px * 72.0 / dpi
        buf.seek(0)
        descent_pts = depth_pts + pad_in * 72.0
        return buf.getvalue(), w_pts, h_pts, descent_pts

    except Exception:
        try:
            import matplotlib.pyplot as plt

            plt.close("all")
        except Exception:
            pass
        return None


def make_inline_math_img(latex_text: str, *, fontsize: int = 10) -> str | None:
    """Render an inline math span to a base64 data-URI ``<img>`` tag.

    The tag uses a negative numeric ``valign`` equal to the expression's
    descent, which ReportLab interprets as the image-bottom offset below
    the text baseline — giving per-expression baseline alignment without
    the fixed-width/centred look of a ``valign="middle"`` image.

    Returns ``None`` when the expression cannot be rendered, so callers can
    fall back to the Unicode-approximation path
    (:func:`fes_pdf_builder.text.format_inline_math`).
    """
    result = render_inline_math_png(latex_text, fontsize=fontsize)
    if result is None:
        return None
    png_bytes, w_pts, h_pts, descent_pts = result
    b64 = base64.b64encode(png_bytes).decode("ascii")
    uri = f"data:image/png;base64,{b64}"
    return (
        f'<img src="{uri}" width="{w_pts:.2f}" height="{h_pts:.2f}" valign="-{descent_pts:.2f}"/>'
    )


def make_math_block_latex(
    latex_text: str,
    styles: dict,
    *,
    layout: Layout | None = None,
    palette: Palette | None = None,
) -> Table:
    """Slate-bordered display-math block, vector-first.

    Rendering priority:

    1. ziamath vector :class:`Drawing` (crisp at any zoom, small file size)
    2. matplotlib mathtext PNG (``[charts]`` extra)
    3. ``clean_latex`` plain-text paragraph — the build never aborts on a
       single bad formula.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()

    inner: object
    valign = "MIDDLE"
    align = "CENTER"

    drawing = render_latex_drawing(latex_text, layout=layout)
    if drawing is not None:
        inner = drawing[0]
    else:
        result = render_latex_png(latex_text, layout=layout)
        if result:
            buf, w_pts, h_pts = result
            inner = RLImage(buf, width=w_pts, height=h_pts)
        else:
            from ..text import clean_latex, esc

            cleaned = clean_latex(latex_text)
            inner = Paragraph(esc(cleaned), styles["math"])
            valign = "TOP"
            align = "LEFT"

    t = Table([[inner]], colWidths=[layout.frame_width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette.slate_light),
                ("LINEBEFORE", (0, 0), (0, -1), 3, palette.slate),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("VALIGN", (0, 0), (-1, -1), valign),
                ("ALIGN", (0, 0), (-1, -1), align),
            ]
        )
    )
    return t
