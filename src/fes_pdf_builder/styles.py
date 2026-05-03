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

"""ParagraphStyle factory.

Every report reads styles from the dict returned by :func:`make_styles`.

The factory is parametrized on a :class:`Palette` (so reports can rebrand
without forking) and exposes one function:

* :func:`make_styles(palette)` returns a ``dict[str, ParagraphStyle]`` with
  ~30 keys covering covers, TOC, preface, chapter headers, body text, code
  blocks, sidebars, math, diagrams, and further-reading lists.

A small set of additional convenience styles (``th``, ``td``) are NOT in
this dict because :mod:`reporting.blocks` constructs them on-the-fly per
table; everything else is centralized here.
"""

from __future__ import annotations

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle

from .branding import Palette, default_palette

__all__ = ["make_styles"]


def make_styles(palette: Palette | None = None) -> dict[str, ParagraphStyle]:
    """Build the canonical style dictionary used by all reports.

    Args:
        palette: Brand palette. Defaults to :func:`default_palette`.

    Returns:
        Dict whose keys are the style names referenced throughout
        :mod:`reporting.blocks`, :mod:`reporting.toc`, :mod:`reporting.markdown`,
        and the per-report renderers. Adding a new key is fine; renaming an
        existing key is a breaking change.
    """
    p = palette or default_palette()
    s: dict[str, ParagraphStyle] = {}

    # ── Cover ─────────────────────────────────────────────────────────────
    s["cover_brand"] = ParagraphStyle(
        "cover_brand",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=p.cover_brand_blue,
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    s["cover_title"] = ParagraphStyle(
        "cover_title",
        fontName="Helvetica-Bold",
        fontSize=30,
        leading=38,
        textColor=p.white,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub",
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=p.cover_sub_blue,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    s["cover_date"] = ParagraphStyle(
        "cover_date",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=p.cover_brand_blue,
        alignment=TA_CENTER,
    )
    s["cover_author"] = ParagraphStyle(
        "cover_author",
        fontName="Helvetica-Oblique",
        fontSize=11,
        leading=15,
        textColor=p.cover_sub_blue,
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    # ── Part divider ──────────────────────────────────────────────────────
    s["part_label"] = ParagraphStyle(
        "part_label",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=p.cover_brand_blue,
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    s["part_title"] = ParagraphStyle(
        "part_title",
        fontName="Helvetica-Bold",
        fontSize=34,
        leading=42,
        textColor=p.white,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    s["part_desc"] = ParagraphStyle(
        "part_desc",
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=p.cover_sub_blue,
        alignment=TA_CENTER,
    )

    # ── ToC ───────────────────────────────────────────────────────────────
    s["toc_h"] = ParagraphStyle(
        "toc_h",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=p.navy,
        spaceBefore=0,
        spaceAfter=8,
        alignment=TA_CENTER,
    )
    s["toc_part"] = ParagraphStyle(
        "toc_part",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=p.navy,
        spaceBefore=0,
        spaceAfter=6,
    )
    s["toc_entry"] = ParagraphStyle(
        "toc_entry",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=p.text_mid,
        leftIndent=16,
        spaceAfter=3,
    )
    s["toc_deep"] = ParagraphStyle(
        "toc_deep",
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=14,
        textColor=p.text_mid,
        leftIndent=16,
        spaceAfter=3,
    )
    s["toc_fig_chap"] = ParagraphStyle(
        "toc_fig_chap",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=p.slate,
        leftIndent=0,
        spaceBefore=8,
        spaceAfter=2,
    )
    s["toc_fig_entry"] = ParagraphStyle(
        "toc_fig_entry",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=p.text_mid,
        leftIndent=16,
        spaceAfter=2,
    )

    # ── Preface ───────────────────────────────────────────────────────────
    s["preface_h"] = ParagraphStyle(
        "preface_h",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=p.navy,
        spaceBefore=0,
        spaceAfter=14,
        alignment=TA_CENTER,
    )
    s["preface_body"] = ParagraphStyle(
        "preface_body",
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        textColor=p.text_dark,
        alignment=TA_JUSTIFY,
        spaceBefore=6,
        spaceAfter=6,
    )
    s["preface_h2"] = ParagraphStyle(
        "preface_h2",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=18,
        textColor=p.navy,
        spaceBefore=14,
        spaceAfter=6,
    )

    # ── Chapter header ────────────────────────────────────────────────────
    s["chap_label"] = ParagraphStyle(
        "chap_label",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=p.blue,
        spaceBefore=0,
        spaceAfter=6,
    )
    s["chap_title"] = ParagraphStyle(
        "chap_title",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=p.navy,
        spaceBefore=0,
        spaceAfter=10,
    )
    s["chap_lead"] = ParagraphStyle(
        "chap_lead",
        fontName="Helvetica-Oblique",
        fontSize=11,
        leading=16,
        textColor=p.slate,
        spaceBefore=0,
        spaceAfter=14,
        alignment=TA_JUSTIFY,
    )

    # ── Body ──────────────────────────────────────────────────────────────
    s["h2"] = ParagraphStyle(
        "h2",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=20,
        textColor=p.navy,
        spaceBefore=8,
        spaceAfter=8,
    )
    s["h3"] = ParagraphStyle(
        "h3",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=p.text_mid,
        spaceBefore=8,
        spaceAfter=5,
    )
    s["h4"] = ParagraphStyle(
        "h4",
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=p.slate,
        spaceBefore=4,
        spaceAfter=4,
    )
    s["body"] = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=p.text_dark,
        alignment=TA_JUSTIFY,
        spaceBefore=4,
        spaceAfter=4,
    )
    s["bullet"] = ParagraphStyle(
        "bullet",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=p.text_dark,
        leftIndent=18,
        firstLineIndent=0,
        spaceBefore=2,
        spaceAfter=2,
    )
    s["bullet2"] = ParagraphStyle(
        "bullet2",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=p.text_mid,
        leftIndent=34,
        firstLineIndent=0,
        spaceBefore=1,
        spaceAfter=1,
    )
    s["num_item"] = ParagraphStyle(
        "num_item",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=p.text_dark,
        leftIndent=18,
        firstLineIndent=0,
        spaceBefore=2,
        spaceAfter=2,
    )

    # ── Code ──────────────────────────────────────────────────────────────
    s["code"] = ParagraphStyle(
        "code",
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=p.code_fg,
        backColor=p.code_bg,
        leftIndent=10,
        rightIndent=10,
        spaceBefore=6,
        spaceAfter=6,
        borderPad=8,
    )
    s["code_label"] = ParagraphStyle(
        "code_label",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=p.slate_light,
        spaceAfter=2,
    )

    # ── Math ──────────────────────────────────────────────────────────────
    s["math"] = ParagraphStyle(
        "math",
        fontName="Courier",
        fontSize=9,
        leading=13,
        textColor=p.text_dark,
        backColor=p.slate_light,
        leftIndent=20,
        rightIndent=20,
        spaceBefore=8,
        spaceAfter=8,
        borderPad=10,
        alignment=TA_LEFT,
    )

    # ── Sidebar (Practical Application) ──────────────────────────────────
    s["sidebar_title"] = ParagraphStyle(
        "sidebar_title",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=p.blue,
        spaceBefore=0,
        spaceAfter=5,
    )
    s["sidebar_body"] = ParagraphStyle(
        "sidebar_body",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=p.text_dark,
        spaceBefore=2,
        spaceAfter=2,
    )
    s["sidebar_bullet"] = ParagraphStyle(
        "sidebar_bullet",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=p.text_dark,
        leftIndent=14,
        spaceBefore=1,
        spaceAfter=1,
    )

    # ── Diagram box ──────────────────────────────────────────────────────
    s["diagram_hdr"] = ParagraphStyle(
        "diagram_hdr",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=p.slate,
        spaceBefore=0,
        spaceAfter=4,
    )
    s["diagram_body"] = ParagraphStyle(
        "diagram_body",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=p.text_mid,
        spaceBefore=2,
        spaceAfter=2,
    )
    s["diagram_code"] = ParagraphStyle(
        "diagram_code",
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=p.text_mid,
        spaceBefore=2,
        spaceAfter=2,
    )

    # ── Further reading ──────────────────────────────────────────────────
    s["fr_title"] = ParagraphStyle(
        "fr_title",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=p.navy,
        spaceBefore=18,
        spaceAfter=8,
    )
    s["fr_item"] = ParagraphStyle(
        "fr_item",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=p.text_dark,
        leftIndent=14,
        spaceBefore=2,
        spaceAfter=2,
    )

    return s
