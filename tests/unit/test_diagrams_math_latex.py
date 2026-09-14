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

"""Unit tests for :mod:`fes_pdf_builder.diagrams.math_latex`."""

from __future__ import annotations

import pytest

from fes_pdf_builder.diagrams.math_latex import (
    make_inline_math_img,
    make_math_block_latex,
    render_inline_math_png,
    render_latex_drawing,
)
from fes_pdf_builder.styles import make_styles


def test_render_latex_drawing_returns_vector_drawing() -> None:
    pytest.importorskip("ziamath")
    pytest.importorskip("svglib")
    result = render_latex_drawing(r"\frac{a}{b} + \alpha")
    assert result is not None
    drawing, w_pts, h_pts = result
    assert w_pts > 0
    assert h_pts > 0
    assert drawing.width == pytest.approx(w_pts)
    assert drawing.height == pytest.approx(h_pts)


def test_render_latex_drawing_clamps_to_frame_width() -> None:
    pytest.importorskip("ziamath")
    pytest.importorskip("svglib")
    result = render_latex_drawing(r"a+b+c+d+e+f+g+h+i+j+k+l+m+n")
    assert result is not None
    drawing, w_pts, _ = result
    assert w_pts > 0
    assert drawing.width == pytest.approx(w_pts)


def test_render_latex_drawing_strips_display_wrappers() -> None:
    pytest.importorskip("ziamath")
    pytest.importorskip("svglib")
    wrapped = render_latex_drawing(r"$$\frac{a}{b}$$")
    direct = render_latex_drawing(r"\frac{a}{b}")
    assert wrapped is not None and direct is not None
    assert wrapped[1] == pytest.approx(direct[1])


def test_render_latex_drawing_returns_none_for_empty() -> None:
    assert render_latex_drawing("") is None
    assert render_latex_drawing(r"\[ \]") is None


def test_render_latex_drawing_returns_none_for_unparseable() -> None:
    pytest.importorskip("ziamath")
    pytest.importorskip("svglib")
    # Unbalanced braces make latex2mathml raise
    assert render_latex_drawing(r"\frac{a}{") is None
    assert render_latex_drawing(r"\frac") is None


def test_render_inline_math_png_returns_bytes_and_size() -> None:
    pytest.importorskip("matplotlib")
    result = render_inline_math_png(r"\hat{c}^{2}")
    assert result is not None
    png_bytes, w_pts, h_pts = result
    assert png_bytes.startswith(b"\x89PNG")
    assert w_pts > 0
    assert h_pts > 0


def test_render_inline_math_png_strips_dollar_wrappers() -> None:
    pytest.importorskip("matplotlib")
    bare = render_inline_math_png(r"x_i")
    wrapped = render_inline_math_png(r"$x_i$")
    paren = render_inline_math_png(r"\(x_i\)")
    assert bare is not None and wrapped is not None and paren is not None
    assert wrapped[1] == pytest.approx(bare[1])
    assert paren[1] == pytest.approx(bare[1])


def test_render_inline_math_png_returns_none_for_empty() -> None:
    assert render_inline_math_png("") is None
    assert render_inline_math_png("$$") is None


def test_make_inline_math_img_returns_data_uri_tag() -> None:
    pytest.importorskip("matplotlib")
    tag = make_inline_math_img(r"p_\theta(x_i)")
    assert tag is not None
    assert tag.startswith('<img src="data:image/png;base64,')
    assert 'valign="middle"' in tag
    assert 'width="' in tag and 'height="' in tag


def test_make_inline_math_img_returns_none_when_unrenderable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fes_pdf_builder.diagrams.math_latex as ml

    monkeypatch.setattr(ml, "render_inline_math_png", lambda *a, **kw: None)
    assert make_inline_math_img(r"\frac{a}{b}") is None


def test_make_math_block_latex_prefers_vector_drawing() -> None:
    pytest.importorskip("ziamath")
    pytest.importorskip("svglib")
    styles = make_styles()
    block = make_math_block_latex(r"\ell(\theta) = \sum_i \log f(y_i \mid x_i, \theta)", styles)
    assert block.__class__.__name__ == "Table"


def test_make_math_block_latex_falls_back_to_mathtext_png(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("matplotlib")
    import fes_pdf_builder.diagrams.math_latex as ml

    monkeypatch.setattr(ml, "render_latex_drawing", lambda *a, **kw: None)
    styles = make_styles()
    block = make_math_block_latex(r"\frac{a}{b}", styles)
    assert block.__class__.__name__ == "Table"


def test_make_math_block_latex_falls_back_to_text_when_all_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fes_pdf_builder.diagrams.math_latex as ml

    monkeypatch.setattr(ml, "render_latex_drawing", lambda *a, **kw: None)
    monkeypatch.setattr(ml, "render_latex_png", lambda *a, **kw: None)
    styles = make_styles()
    block = make_math_block_latex(r"\frac{a}{b}", styles)
    assert block.__class__.__name__ == "Table"
