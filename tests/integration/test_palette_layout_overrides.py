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

"""Integration tests: palette and layout overrides round-trip through build_doc."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

from fes_pdf_builder import (
    ChapterAnchor,
    HeaderState,
    Layout,
    Palette,
    ReportContext,
    build_doc,
    cover_pages,
    preamble_break,
)


def _minimal_story(styles: dict, state: HeaderState, p: Palette, lo: Layout) -> list:
    story = []
    story.extend(
        cover_pages(
            styles,
            brand_line="TEST",
            title_lines=["Override Test"],
            layout=lo,
        )
    )
    story.extend(preamble_break())
    story.append(ChapterAnchor("doc_root", "Report", state=state, level=0))
    story.append(ChapterAnchor("ch1", "Chapter One", state=state, level=1))
    return story


def test_custom_navy_palette_produces_pdf(tmp_path: Path) -> None:
    palette = Palette(navy=HexColor("#003366"), blue=HexColor("#0055AA"))
    out = build_doc(
        ReportContext(
            out_path=tmp_path / "custom_palette.pdf",
            title="Custom Palette",
            subject="Test",
            author="FES",
            creator="test",
        ),
        _minimal_story,
        palette=palette,
    )
    assert out.exists()
    assert out.stat().st_size > 1024


def test_a4_layout_produces_pdf(tmp_path: Path) -> None:
    a4 = Layout(page_width=A4[0], page_height=A4[1], margin=0.75 * inch)
    out = build_doc(
        ReportContext(
            out_path=tmp_path / "a4.pdf",
            title="A4 Layout",
            subject="Test",
            author="FES",
            creator="test",
        ),
        _minimal_story,
        layout=a4,
    )
    assert out.exists()
    assert out.stat().st_size > 1024


def test_narrow_margin_layout(tmp_path: Path) -> None:
    narrow = Layout(margin=0.3 * inch)
    out = build_doc(
        ReportContext(
            out_path=tmp_path / "narrow.pdf",
            title="Narrow Margin",
            subject="Test",
            author="FES",
            creator="test",
        ),
        _minimal_story,
        layout=narrow,
    )
    assert out.exists()
