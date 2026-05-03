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

"""Integration smoke test: full build_doc round-trip writes a valid non-empty PDF."""

from __future__ import annotations

from pathlib import Path

from reportlab.platypus import Paragraph, Spacer

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


def _simple_story(styles: dict, state: HeaderState, p: Palette, lo: Layout) -> list:
    story = []
    story.extend(
        cover_pages(
            styles,
            brand_line="FES TEST SUITE",
            title_lines=["Smoke Test Report"],
            subtitle_lines=["Integration test"],
            date_line="April 2026",
            layout=lo,
        )
    )
    story.extend(preamble_break())
    # A level-0 anchor is required by ReportLab before any level-1 entries.
    story.append(ChapterAnchor("doc_root", "Report", state=state, level=0))
    story.append(ChapterAnchor("ch_intro", "Introduction", state=state, level=1))
    story.append(Paragraph("This is the introduction chapter.", styles["body"]))
    story.append(Spacer(1, 12))
    story.append(ChapterAnchor("ch_methods", "Methods", state=state, level=1))
    story.append(Paragraph("This chapter covers methods.", styles["body"]))
    return story


def test_build_doc_writes_pdf(tmp_path: Path) -> None:
    out = build_doc(
        ReportContext(
            out_path=tmp_path / "smoke.pdf",
            title="Smoke Test",
            subject="Integration test",
            author="Fulton Engineering Services LLC",
            creator="fes-pdf-builder test suite",
        ),
        _simple_story,
    )
    assert out.exists(), f"PDF not created at {out}"
    assert out.stat().st_size > 1024, "PDF is suspiciously small"


def test_build_doc_output_is_pdf_bytes(tmp_path: Path) -> None:
    out = build_doc(
        ReportContext(
            out_path=tmp_path / "bytes.pdf",
            title="Bytes Test",
            subject="Test",
            author="ACME",
            creator="test",
        ),
        _simple_story,
    )
    header = out.read_bytes()[:4]
    assert header == b"%PDF", f"Expected PDF header, got {header!r}"


def test_build_doc_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "deeply" / "nested" / "report.pdf"
    out = build_doc(
        ReportContext(
            out_path=nested,
            title="Nested",
            subject="Test",
            author="Test",
            creator="Test",
        ),
        _simple_story,
    )
    assert out.exists()


def test_build_doc_palette_override(tmp_path: Path) -> None:
    from reportlab.lib.colors import HexColor

    custom_palette = Palette(navy=HexColor("#003366"))
    out = build_doc(
        ReportContext(
            out_path=tmp_path / "palette.pdf",
            title="Custom Palette",
            subject="Test",
            author="FES",
            creator="test",
        ),
        _simple_story,
        palette=custom_palette,
    )
    assert out.exists()


def test_build_doc_with_part_divider(tmp_path: Path) -> None:
    from reportlab.platypus import NextPageTemplate, PageBreak, Paragraph

    from fes_pdf_builder import part_divider

    def story_with_part(styles: dict, state: HeaderState, p: Palette, lo: Layout) -> list:
        story = []
        story.extend(cover_pages(styles, brand_line="FES", title_lines=["Parts Test"], layout=lo))
        story.extend(preamble_break())
        story.extend(
            part_divider(
                styles,
                label="PART I",
                title="First Part",
                description="The first part of the report.",
                state=state,
                anchor="part_i",
                outline_title="Part I — First Part",
                layout=lo,
            )
        )
        story.extend([NextPageTemplate("main"), PageBreak()])
        story.append(ChapterAnchor("ch1", "Chapter 1", state=state, level=1))
        story.append(Paragraph("Body text.", styles["body"]))
        return story

    out = build_doc(
        ReportContext(
            out_path=tmp_path / "parts.pdf",
            title="Parts Test",
            subject="Test",
            author="FES",
            creator="test",
        ),
        story_with_part,
    )
    assert out.exists()
    assert out.stat().st_size > 1024
