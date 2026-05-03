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

"""Unit tests for :mod:`fes_pdf_builder.diagrams.math`."""

from __future__ import annotations

import pytest

from fes_pdf_builder.diagrams.math import make_math_block, render_latex_png
from fes_pdf_builder.styles import make_styles


def test_make_math_block_returns_flowable_with_matplotlib() -> None:
    pytest.importorskip("matplotlib")
    styles = make_styles()
    block = make_math_block(r"\frac{a}{b} + \alpha", styles)
    assert block is not None


def test_make_math_block_returns_fallback_without_matplotlib(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When render_latex_png returns None (e.g. matplotlib unavailable),
    make_math_block should fall back to a text block."""
    import fes_pdf_builder.diagrams.math as math_mod

    monkeypatch.setattr(math_mod, "render_latex_png", lambda *a, **kw: None)
    styles = make_styles()
    block = make_math_block(r"\frac{a}{b}", styles)
    assert block.__class__.__name__ in ("Paragraph", "Table")


def test_render_latex_png_returns_buffer_and_size() -> None:
    pytest.importorskip("matplotlib")
    result = render_latex_png(r"\frac{a}{b}")
    assert result is not None
    buf, w, h = result
    assert w > 0
    assert h > 0
    data = buf.getvalue()
    assert data.startswith(b"\x89PNG")


def test_render_latex_png_returns_none_for_empty() -> None:
    result = render_latex_png("")
    assert result is None
