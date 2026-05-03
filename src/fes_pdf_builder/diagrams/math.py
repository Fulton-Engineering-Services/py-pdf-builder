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

"""LaTeX display-math → matplotlib mathtext PNG → ReportLab flowable.

LaTeX-to-PNG renderer plus the slate-grey display block that wraps it. matplotlib is
the only dependency; if it raises while parsing, the helper falls back to
the plain-text :func:`reporting.text.clean_latex` representation so the
build never aborts on a single bad formula.

Public surface:

* :func:`render_latex_png` — return ``(BytesIO, w_pts, h_pts)`` or None.
* :func:`make_math_block`  — return a slate-bordered display block
  (image-or-text fallback).
"""

from __future__ import annotations

import re
from io import BytesIO

from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, Table, TableStyle

from ..branding import Layout, Palette, default_layout, default_palette
from ..text import clean_latex, esc

__all__ = ["make_math_block", "render_latex_png"]


def render_latex_png(
    latex_text: str,
    *,
    fontsize: int = 14,
    layout: Layout | None = None,
) -> tuple[BytesIO, float, float] | None:
    """Render a LaTeX expression as a transparent PNG via matplotlib mathtext.

    Returns ``(BytesIO_buffer, width_pts, height_pts)`` on success, or
    ``None`` if matplotlib cannot parse the expression. The buffer is
    rewound to position 0 before being returned.
    """
    layout = layout or default_layout()
    raw = latex_text.strip()
    raw = re.sub(r"^\\\[|\\\]$", "", raw).strip()
    expr = raw if raw.startswith("$") else f"${raw}$"

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    try:
        fig, ax = plt.subplots(figsize=(8, 1.4))
        fig.patch.set_facecolor("none")
        ax.set_axis_off()
        ax.patch.set_alpha(0)
        ax.text(
            0.5,
            0.5,
            expr,
            fontsize=fontsize,
            color="#0F172A",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

        buf = BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=150,
            bbox_inches="tight",
            pad_inches=0.08,
            transparent=True,
        )
        plt.close(fig)
        buf.seek(0)

        ir = ImageReader(buf)
        w_px, h_px = ir.getSize()
        w_pts = w_px * 72.0 / 150
        h_pts = h_px * 72.0 / 150
        buf.seek(0)

        max_w = layout.frame_width - 32
        if w_pts > max_w:
            scale = max_w / w_pts
            w_pts *= scale
            h_pts *= scale

        return buf, w_pts, h_pts

    except Exception:
        try:
            import matplotlib.pyplot as plt

            plt.close("all")
        except Exception:
            pass
        return None


def make_math_block(
    latex_text: str,
    styles: dict,
    *,
    layout: Layout | None = None,
    palette: Palette | None = None,
) -> Table:
    """Slate-bordered display-math block.

    Attempts to render ``latex_text`` as a matplotlib mathtext PNG. If that
    fails, falls back to the cleaned plain-text representation in a Courier
    paragraph so the build never aborts on a single bad formula.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()

    result = render_latex_png(latex_text, layout=layout)

    if result:
        buf, w_pts, h_pts = result
        inner = RLImage(buf, width=w_pts, height=h_pts)
        valign = "MIDDLE"
        align = "CENTER"
    else:
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
