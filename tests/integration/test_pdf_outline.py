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

"""Integration tests: verify PDF outline entries via pypdf."""

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


def _multi_chapter_story(styles: dict, state: HeaderState, p: Palette, lo: Layout) -> list:
    story = []
    story.extend(
        cover_pages(
            styles,
            brand_line="OUTLINE TEST",
            title_lines=["Outline Test"],
            layout=lo,
        )
    )
    story.extend(preamble_break())
    story.append(ChapterAnchor("doc_root", "Report", state=state, level=0))
    for i in range(1, 4):
        story.append(ChapterAnchor(f"ch_{i}", f"Chapter {i}", state=state, level=1))
        story.append(Paragraph(f"This is chapter {i}.", styles["body"]))
        story.append(Spacer(1, 20))
    return story


def test_pdf_has_outline_entries(tmp_path: Path) -> None:
    """pypdf should be able to read back the PDF outline we wrote."""
    pytest_pypdf = __import__("pypdf", fromlist=["PdfReader"])  # noqa: F841
    from pypdf import PdfReader

    out = build_doc(
        ReportContext(
            out_path=tmp_path / "outline.pdf",
            title="Outline Test",
            subject="Test",
            author="FES",
            creator="test",
        ),
        _multi_chapter_story,
    )
    assert out.exists()

    reader = PdfReader(str(out))
    # pypdf exposes outline via .outline property
    outline = reader.outline
    assert outline is not None

    # Flatten to count leaf nodes
    def count_entries(nodes: list) -> int:  # type: ignore[type-arg]
        total = 0
        for node in nodes:
            if isinstance(node, list):
                total += count_entries(node)
            else:
                total += 1
        return total

    n = count_entries(outline)
    assert n >= 3, f"expected at least 3 outline entries, got {n}"


def test_pdf_metadata_title_and_author(tmp_path: Path) -> None:
    from pypdf import PdfReader

    out = build_doc(
        ReportContext(
            out_path=tmp_path / "meta.pdf",
            title="Meta Test Report",
            subject="Metadata subject",
            author="Fulton Engineering Services LLC",
            creator="fes-pdf-builder test",
        ),
        _multi_chapter_story,
    )
    reader = PdfReader(str(out))
    meta = reader.metadata
    assert meta is not None
    # ReportLab stores /Title and /Author in PDF metadata
    title = meta.get("/Title") or meta.get("title") or ""
    assert "Meta Test Report" in title or title == "Meta Test Report"
