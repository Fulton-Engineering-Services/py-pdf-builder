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

"""Integration test: embedding a raster image via ``make_image_block``.

Builds a full ``build_doc`` report whose story includes an embedded PNG, then
asserts the output PDF actually contains an image XObject using ``pypdf``.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.platypus import Paragraph

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
from fes_pdf_builder.blocks import make_image_block


def _make_chart_png(out: Path) -> Path:
    """Render a small branded bar chart to ``out`` and return its path."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(4, 2))
    ax.bar(["A", "B", "C"], [3, 7, 5], color="#2563EB")
    fig.savefig(out, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def test_build_doc_embeds_image(tmp_path: Path) -> None:
    chart_path = _make_chart_png(tmp_path / "chart.png")

    def story(styles: dict, state: HeaderState, p: Palette, lo: Layout) -> list:
        s: list = []
        s.extend(cover_pages(styles, brand_line="FES TEST", title_lines=["Image Test"], layout=lo))
        s.extend(preamble_break())
        s.append(ChapterAnchor("doc_root", "Report", state=state, level=0))
        s.append(ChapterAnchor("ch1", "Images", state=state, level=1))
        s.append(Paragraph("The figure below is embedded as a raster image.", styles["body"]))
        s.append(make_image_block(chart_path, caption="Figure 1 — Sample KPI chart", layout=lo))
        return s

    out = build_doc(
        ReportContext(
            out_path=tmp_path / "image-report.pdf",
            title="Image Report",
            subject="Integration test",
            author="Fulton Engineering Services LLC",
            creator="fes-pdf-builder test suite",
        ),
        story,
    )
    assert out.exists()

    from pypdf import PdfReader

    reader = PdfReader(out)
    image_counts = [len(page.images) for page in reader.pages]
    assert sum(image_counts) >= 1, f"expected at least one embedded image, got {image_counts}"
