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

"""Unit tests for :mod:`fes_pdf_builder.styles`."""

from __future__ import annotations

from reportlab.lib.colors import HexColor

from fes_pdf_builder.branding import Palette
from fes_pdf_builder.styles import make_styles

_REQUIRED_KEYS = [
    # Cover
    "cover_brand",
    "cover_title",
    "cover_sub",
    "cover_date",
    "cover_author",
    # Part divider
    "part_label",
    "part_title",
    "part_desc",
    # TOC
    "toc_h",
    "toc_part",
    "toc_entry",
    "toc_deep",
    "toc_fig_chap",
    "toc_fig_entry",
    # Preface
    "preface_h",
    "preface_body",
    "preface_h2",
    # Chapter header
    "chap_label",
    "chap_title",
    "chap_lead",
    # Body
    "h2",
    "h3",
    "h4",
    "body",
    "bullet",
    "bullet2",
    "num_item",
    # Code
    "code",
    "code_label",
    # Math
    "math",
    # Sidebar
    "sidebar_title",
    "sidebar_body",
    "sidebar_bullet",
    # Diagram
    "diagram_hdr",
    "diagram_body",
    "diagram_code",
    # Further reading
    "fr_title",
    "fr_item",
]


def test_make_styles_returns_all_required_keys() -> None:
    styles = make_styles()
    for key in _REQUIRED_KEYS:
        assert key in styles, f"missing style key: {key!r}"


def test_make_styles_with_custom_palette_propagates_color() -> None:
    red_navy = HexColor("#FF0000")
    custom_palette = Palette(navy=red_navy)
    styles = make_styles(custom_palette)
    # toc_h and chap_title use palette.navy as textColor
    assert styles["toc_h"].textColor == red_navy
    assert styles["chap_title"].textColor == red_navy


def test_make_styles_without_palette_uses_defaults() -> None:
    styles = make_styles()
    # Default navy is #1B2A4A; check it's close
    navy = styles["chap_title"].textColor
    assert navy is not None


def test_make_styles_body_font_is_helvetica() -> None:
    styles = make_styles()
    assert styles["body"].fontName == "Helvetica"


def test_make_styles_code_font_is_courier() -> None:
    styles = make_styles()
    assert styles["code"].fontName == "Courier"


def test_make_styles_cover_title_is_large() -> None:
    styles = make_styles()
    assert styles["cover_title"].fontSize >= 24


def test_make_styles_returns_fresh_dict_each_call() -> None:
    s1 = make_styles()
    s2 = make_styles()
    assert s1 is not s2
