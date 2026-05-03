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

"""Integration smoke test for :func:`build_single_markdown_pdf`."""

from __future__ import annotations

from pathlib import Path

from fes_pdf_builder.reports.single_markdown import SingleMdConfig, build_single_markdown_pdf

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_build_single_markdown_writes_pdf(tmp_path: Path) -> None:
    out = build_single_markdown_pdf(
        SingleMdConfig(
            out_path=tmp_path / "sample.pdf",
            source_path=FIXTURES / "sample.md",
            doc_title="Sample Report",
            doc_subject="Test",
            doc_author="FES Test Suite",
            doc_creator="fes-pdf-builder tests",
            brand_line="FULTON ENGINEERING SERVICES LLC",
            title_lines=["Sample Report"],
            subtitle_lines=["Integration test"],
        )
    )
    assert out.exists()
    assert out.stat().st_size > 2048


def test_build_single_markdown_is_pdf_bytes(tmp_path: Path) -> None:
    out = build_single_markdown_pdf(
        SingleMdConfig(
            out_path=tmp_path / "check.pdf",
            source_path=FIXTURES / "minimal.md",
            doc_title="Minimal",
            doc_subject="Test",
            doc_author="FES",
            doc_creator="test",
            brand_line="FES",
            title_lines=["Minimal"],
            subtitle_lines=[],
        )
    )
    assert out.read_bytes()[:4] == b"%PDF"


def test_build_single_markdown_with_cover_footer_line(tmp_path: Path) -> None:
    out = build_single_markdown_pdf(
        SingleMdConfig(
            out_path=tmp_path / "confidential.pdf",
            source_path=FIXTURES / "minimal.md",
            doc_title="Confidential",
            doc_subject="Test",
            doc_author="FES",
            doc_creator="test",
            brand_line="FES",
            title_lines=["Confidential Report"],
            subtitle_lines=[],
            cover_footer_line="Confidential — Internal Use",
        )
    )
    assert out.exists()
    assert out.stat().st_size > 1024


def test_build_single_markdown_empty_cover_footer_line(tmp_path: Path) -> None:
    out = build_single_markdown_pdf(
        SingleMdConfig(
            out_path=tmp_path / "no_footer.pdf",
            source_path=FIXTURES / "minimal.md",
            doc_title="No Footer",
            doc_subject="Test",
            doc_author="FES",
            doc_creator="test",
            brand_line="FES",
            title_lines=["No Footer"],
            subtitle_lines=[],
            cover_footer_line="",  # should not crash
        )
    )
    assert out.exists()
