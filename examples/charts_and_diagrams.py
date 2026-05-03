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

"""Example: bar chart, line chart, heatmap, Gantt, and Mermaid diagram in one PDF.

Requires the [charts] / [diagrams] optional extras:

    uv run pip install -e ".[all]"

Run from the repo root:

    uv run python examples/charts_and_diagrams.py
    # Writes: examples/output/charts-and-diagrams.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.platypus import HRFlowable, NextPageTemplate, PageBreak, Paragraph, Spacer

from fes_pdf_builder import (
    ChapterAnchor,
    FigureRegistry,
    HeaderState,
    Layout,
    Palette,
    ReportContext,
    build_doc,
    cover_pages,
    preamble_break,
)
from fes_pdf_builder.charts import (
    bar_chart,
    gantt_chart,
    grouped_bar_chart,
    heatmap,
    line_chart,
    register_chart_anchor,
)
from fes_pdf_builder.diagrams.mermaid import make_diagram_box
from fes_pdf_builder.toc import TocEntry, TocPart, toc_pages

MERMAID_FLOW = """flowchart LR
    Client[Caller] --> Builder[PDF Builder]
    Builder --> ReportLab
    Builder --> Matplotlib
    ReportLab --> PDF[(PDF output)]
    Matplotlib --> PDF
"""


def build_story(styles: dict, state: HeaderState, palette: Palette, layout: Layout) -> list:
    story: list = []
    figures = FigureRegistry()

    # Cover
    story.extend(
        cover_pages(
            styles,
            brand_line="FULTON ENGINEERING SERVICES LLC",
            title_lines=["Charts & Diagrams Demo"],
            subtitle_lines=["fes-pdf-builder · matplotlib + Mermaid"],
            date_line="April 2026",
            layout=layout,
        )
    )
    story.extend(preamble_break())

    # TOC
    story.extend(
        toc_pages(
            [
                TocPart(
                    heading="CONTENTS",
                    anchor=None,
                    entries=[
                        TocEntry(label="01  ·  Bar Charts", anchor="ch_bar"),
                        TocEntry(label="02  ·  Line Chart", anchor="ch_line"),
                        TocEntry(label="03  ·  Heatmap", anchor="ch_heatmap"),
                        TocEntry(label="04  ·  Gantt Chart", anchor="ch_gantt"),
                        TocEntry(label="05  ·  Mermaid Diagram", anchor="ch_mermaid"),
                    ],
                )
            ],
            styles,
            state=state,
            figures=figures,
            palette=palette,
        )
    )

    # Chapter 1: Bar charts
    story.extend([NextPageTemplate("main"), PageBreak()])
    story.append(ChapterAnchor("ch_bar", "Bar Charts", state=state, level=1))
    story.append(Paragraph("CHAPTER 1 OF 5", styles["chap_label"]))
    story.append(Paragraph("Bar Charts", styles["chap_title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=palette.blue, spaceBefore=2, spaceAfter=10)
    )
    story.append(Paragraph("Single-series bar chart:", styles["h3"]))
    story.append(register_chart_anchor(figures, chapter_title="Bar Charts", chart_type="Bar chart"))
    story.append(
        bar_chart(
            ["q4q4", "q4q8", "q8q8", "f16f16"],
            [72.4, 68.1, 55.9, 45.2],
            title="Decode throughput by KV level (tok/s)",
            ylabel="tok/s",
            palette=palette,
            layout=layout,
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("Grouped bar chart:", styles["h3"]))
    story.append(
        register_chart_anchor(figures, chapter_title="Bar Charts", chart_type="Grouped bar chart")
    )
    story.append(
        grouped_bar_chart(
            groups=["g4dn.xlarge", "g5.xlarge", "g6e.xlarge"],
            series={
                "q4q4": [38.1, 72.4, 155.3],
                "q8q8": [28.5, 55.9, 121.7],
            },
            title="Decode throughput by instance (tok/s)",
            ylabel="tok/s",
            palette=palette,
            layout=layout,
        )
    )

    # Chapter 2: Line chart
    story.extend([NextPageTemplate("main"), PageBreak()])
    story.append(ChapterAnchor("ch_line", "Line Chart", state=state, level=1))
    story.append(Paragraph("CHAPTER 2 OF 5", styles["chap_label"]))
    story.append(Paragraph("Line Chart", styles["chap_title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=palette.blue, spaceBefore=2, spaceAfter=10)
    )
    story.append(
        register_chart_anchor(figures, chapter_title="Line Chart", chart_type="Line chart")
    )
    story.append(
        line_chart(
            x=[2048, 8192, 32768, 65536, 131072],
            series={
                "decode (q4q4)": [72.4, 64.1, 55.3, 48.2, 40.1],
                "decode (q8q8)": [55.9, 50.2, 43.8, 37.1, 30.5],
            },
            title="Throughput vs context length",
            xlabel="context tokens",
            ylabel="tok/s",
            log_x=True,
            x_tick_labels=["2K", "8K", "32K", "64K", "128K"],
            palette=palette,
            layout=layout,
        )
    )

    # Chapter 3: Heatmap
    story.extend([NextPageTemplate("main"), PageBreak()])
    story.append(ChapterAnchor("ch_heatmap", "Heatmap", state=state, level=1))
    story.append(Paragraph("CHAPTER 3 OF 5", styles["chap_label"]))
    story.append(Paragraph("Heatmap", styles["chap_title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=palette.blue, spaceBefore=2, spaceAfter=10)
    )
    story.append(register_chart_anchor(figures, chapter_title="Heatmap", chart_type="Heatmap"))
    story.append(
        heatmap(
            rows=["g4dn.xlarge", "g5.xlarge", "g6e.xlarge"],
            cols=["gemma4-2b", "gemma4-4b", "gemma4-12b"],
            matrix=[[None, 95.2, 72.4], [88.1, 155.3, 95.1], [None, None, 200.4]],
            title="Decode tok/s — instance × model",
            cmap_name="Blues",
            palette=palette,
            layout=layout,
        )
    )

    # Chapter 4: Gantt
    story.extend([NextPageTemplate("main"), PageBreak()])
    story.append(ChapterAnchor("ch_gantt", "Gantt Chart", state=state, level=1))
    story.append(Paragraph("CHAPTER 4 OF 5", styles["chap_label"]))
    story.append(Paragraph("Gantt Chart", styles["chap_title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=palette.blue, spaceBefore=2, spaceAfter=10)
    )
    story.append(
        register_chart_anchor(figures, chapter_title="Gantt Chart", chart_type="Phase Gantt")
    )
    story.append(
        gantt_chart(
            [
                {"name": "setup", "status": "SUCCESS", "elapsed_s": 45.0},
                {"name": "build", "status": "SUCCESS", "elapsed_s": 320.0},
                {"name": "bench_standard", "status": "SUCCESS", "elapsed_s": 1800.0},
                {"name": "perplexity", "status": "PARTIAL", "elapsed_s": 7200.0},
                {"name": "coding", "status": "SUCCESS", "elapsed_s": 900.0},
            ],
            title="Phase timing",
            palette=palette,
            layout=layout,
        )
    )

    # Chapter 5: Mermaid
    story.extend([NextPageTemplate("main"), PageBreak()])
    story.append(ChapterAnchor("ch_mermaid", "Mermaid Diagram", state=state, level=1))
    story.append(Paragraph("CHAPTER 5 OF 5", styles["chap_label"]))
    story.append(Paragraph("Mermaid Diagram", styles["chap_title"]))
    story.append(
        HRFlowable(width="100%", thickness=2, color=palette.blue, spaceBefore=2, spaceAfter=10)
    )
    story.extend(
        make_diagram_box(
            MERMAID_FLOW,
            styles,
            figures=figures,
            chapter_title="Mermaid Diagram",
            title="Library architecture",
            palette=palette,
            layout=layout,
        )
    )

    return story


if __name__ == "__main__":
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)

    out = build_doc(
        ReportContext(
            out_path=out_dir / "charts-and-diagrams.pdf",
            title="Charts & Diagrams Demo",
            subject="fes-pdf-builder charts and diagrams example",
            author="Fulton Engineering Services LLC",
            creator="fes-pdf-builder examples",
        ),
        build_story,
    )
    print(out)
