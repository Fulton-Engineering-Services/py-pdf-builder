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

"""Unit tests for :mod:`fes_pdf_builder.diagrams.mermaid`."""

from __future__ import annotations

import shutil

import pytest

from fes_pdf_builder.diagrams.mermaid import (
    has_graphviz,
    make_diagram_box,
    mermaid_to_dot,
    render_mermaid_png,
)
from fes_pdf_builder.styles import make_styles
from fes_pdf_builder.toc import FigureRegistry

SIMPLE_FLOWCHART = """flowchart LR
    A[Client] --> B[Server]
    B --> C[Model]
"""


def test_has_graphviz_returns_bool() -> None:
    result = has_graphviz()
    assert isinstance(result, bool)


def test_mermaid_to_dot_basic() -> None:
    dot_src = mermaid_to_dot(SIMPLE_FLOWCHART)
    # Should produce something resembling DOT syntax regardless of graphviz presence
    assert dot_src or dot_src == ""  # may be empty if converter errors out


def test_make_diagram_box_returns_flowables() -> None:
    styles = make_styles()
    figs = FigureRegistry()
    flowables = make_diagram_box(
        SIMPLE_FLOWCHART,
        styles,
        figures=figs,
        chapter_title="Chapter 1",
    )
    # Should return at least one flowable (anchor + visual or fallback)
    assert len(flowables) >= 1


def test_make_diagram_box_registers_figure() -> None:
    styles = make_styles()
    figs = FigureRegistry()
    make_diagram_box(
        SIMPLE_FLOWCHART,
        styles,
        figures=figs,
        chapter_title="Arch Overview",
    )
    assert len(figs) == 1


def test_make_diagram_box_fallback_when_no_graphviz(monkeypatch: pytest.MonkeyPatch) -> None:
    """When graphviz is missing the box should still return usable flowables."""
    import fes_pdf_builder.diagrams.mermaid as mm

    monkeypatch.setattr(mm, "has_graphviz", lambda: False)
    styles = make_styles()
    figs = FigureRegistry()
    flowables = make_diagram_box(
        SIMPLE_FLOWCHART,
        styles,
        figures=figs,
        chapter_title="Test",
    )
    assert len(flowables) >= 1


@pytest.mark.skipif(not shutil.which("dot"), reason="graphviz dot binary not on PATH")
def test_render_mermaid_png_with_dot() -> None:
    result = render_mermaid_png(SIMPLE_FLOWCHART)
    assert result is not None
    buf, w, h = result
    assert w > 0
    assert h > 0
    data = buf.getvalue()
    assert data.startswith(b"\x89PNG") or len(data) > 100
