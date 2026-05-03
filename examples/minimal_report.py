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

"""Minimal example: build_doc + cover + two chapters.

Run from the repo root:

    uv run python examples/minimal_report.py
    # Writes: examples/output/minimal-report.pdf
"""

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
from fes_pdf_builder.toc import TocEntry, TocPart, toc_pages


def build_story(styles: dict, state: HeaderState, palette: Palette, layout: Layout) -> list:
    story: list = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.extend(
        cover_pages(
            styles,
            brand_line="FULTON ENGINEERING SERVICES LLC",
            title_lines=["Example Report", "v0.1.0"],
            subtitle_lines=["A minimal fes-pdf-builder demonstration"],
            author_line="J. Patrick Fulton",
            date_line="April 2026",
            layout=layout,
        )
    )
    story.extend(preamble_break())

    # ── TOC ───────────────────────────────────────────────────────────────────
    parts = [
        TocPart(
            heading="CONTENTS",
            anchor=None,
            entries=[
                TocEntry(label="01  ·  Introduction", anchor="ch_intro"),
                TocEntry(label="02  ·  Conclusion", anchor="ch_conclusion"),
            ],
        )
    ]
    story.extend(toc_pages(parts, styles, state=state, palette=palette))

    # ── Chapter 1 ─────────────────────────────────────────────────────────────
    from reportlab.platypus import HRFlowable, NextPageTemplate, PageBreak

    story.extend([NextPageTemplate("main"), PageBreak()])
    story.append(ChapterAnchor("ch_intro", "Introduction", state=state, level=1))
    story.append(Paragraph("CHAPTER 1 OF 2", styles["chap_label"]))
    story.append(Paragraph("Introduction", styles["chap_title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=palette.blue, spaceBefore=2, spaceAfter=10)
    )
    story.append(
        Paragraph(
            "Welcome to the minimal example of <b>fes-pdf-builder</b>. "
            "This library provides a chassis for branded PDF reports using "
            "ReportLab and optional matplotlib charts.",
            styles["body"],
        )
    )
    story.append(Spacer(1, 12))
    story.append(Paragraph("## Key features", styles["h2"]))
    story.append(
        Paragraph(
            "• Configurable palette and page layout via frozen dataclasses.",
            styles["bullet"],
        )
    )
    story.append(Paragraph("• Markdown → flowable parser.", styles["bullet"]))
    story.append(
        Paragraph("• Optional chart renderers (bar, line, heatmap, Gantt).", styles["bullet"])
    )
    story.append(Paragraph("• Optional Mermaid and sequence-diagram renderers.", styles["bullet"]))

    # ── Chapter 2 ─────────────────────────────────────────────────────────────
    story.extend([NextPageTemplate("main"), PageBreak()])
    story.append(ChapterAnchor("ch_conclusion", "Conclusion", state=state, level=1))
    story.append(Paragraph("CHAPTER 2 OF 2", styles["chap_label"]))
    story.append(Paragraph("Conclusion", styles["chap_title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=palette.blue, spaceBefore=2, spaceAfter=10)
    )
    story.append(
        Paragraph(
            "The fes-pdf-builder library simplifies the creation of reproducible, "
            "branded PDF deliverables from Python scripts.",
            styles["body"],
        )
    )

    return story


if __name__ == "__main__":
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)

    out = build_doc(
        ReportContext(
            out_path=out_dir / "minimal-report.pdf",
            title="Example Report v0.1.0",
            subject="fes-pdf-builder minimal example",
            author="Fulton Engineering Services LLC",
            creator="fes-pdf-builder examples",
        ),
        build_story,
    )
    print(out)
