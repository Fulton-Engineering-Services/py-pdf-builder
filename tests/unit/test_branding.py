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

"""Unit tests for :mod:`fes_pdf_builder.branding`."""

from __future__ import annotations

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

from fes_pdf_builder.branding import Layout, Palette, default_layout, default_palette


def test_default_palette_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    p = default_palette()
    with pytest.raises(FrozenInstanceError):
        p.navy = None  # type: ignore[misc]


def test_default_palette_has_fes_navy() -> None:
    p = default_palette()
    # hexval() returns a CSS hex string like '#1b2a4a'
    assert p.navy.hexval().lower().lstrip("0x") == "1b2a4a"


def test_default_palette_white_and_black() -> None:
    p = default_palette()
    assert p.white.red == 1.0
    assert p.black.red == 0.0


def test_default_layout_is_letter() -> None:
    lo = default_layout()
    assert lo.page_width == pytest.approx(letter[0])
    assert lo.page_height == pytest.approx(letter[1])


def test_default_layout_margin_is_0_6_inch() -> None:
    lo = default_layout()
    assert lo.margin == pytest.approx(0.6 * inch)


def test_layout_frame_width_excludes_margins() -> None:
    lo = Layout()
    expected = lo.page_width - 2 * lo.margin
    assert lo.frame_width == pytest.approx(expected)


def test_layout_main_frame_height() -> None:
    lo = Layout()
    expected = lo.page_height - 2 * lo.margin - lo.header_height - lo.footer_height
    assert lo.main_frame_height == pytest.approx(expected)


def test_layout_cover_frame_height() -> None:
    lo = Layout()
    expected = lo.page_height - 2 * lo.margin
    assert lo.cover_frame_height == pytest.approx(expected)


def test_palette_override_navy_color() -> None:
    from reportlab.lib.colors import HexColor

    custom = Palette(navy=HexColor("#123456"))
    assert custom.navy.hexval().lower().lstrip("0x") == "123456"
    # Other colours unchanged
    assert custom.blue == default_palette().blue


def test_layout_override_margin() -> None:
    custom = Layout(margin=1.0 * inch)
    assert custom.margin == pytest.approx(1.0 * inch)
    assert custom.frame_width == pytest.approx(custom.page_width - 2 * inch)


def test_two_default_palette_instances_are_equal() -> None:
    assert default_palette() == default_palette()


def test_two_default_layout_instances_are_equal() -> None:
    assert default_layout() == default_layout()
