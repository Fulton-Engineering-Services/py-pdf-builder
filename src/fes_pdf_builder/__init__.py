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

"""fes-pdf-builder — Branded PDF report toolkit (ReportLab + matplotlib chassis).

This package provides a layered, palette-driven chassis for building
branded PDF deliverables with ReportLab. It has no domain-specific
knowledge — all business-level content (benchmark data, hardware registries,
etc.) lives in the consuming project.

Layered architecture::

    branding ── styles ── flowables ── page_templates
        │           │          │             │
        ├──────── text ────────┴── blocks ── toc ── markdown
        │
        ├── diagrams.{math, mermaid, sequence}   (opt: matplotlib / dot)
        ├── charts                                (opt: matplotlib)
        └── reports.{base, single_markdown}

Quickstart::

    from pathlib import Path
    from fes_pdf_builder import (
        build_doc, ReportContext, cover_pages, preamble_break,
        default_palette, default_layout, make_styles,
        ChapterAnchor, HeaderState,
    )
    from reportlab.platypus import Paragraph, PageBreak, NextPageTemplate

    def my_story(styles, state, palette, layout):
        story = []
        story.extend(cover_pages(styles, brand_line="ACME Corp",
                                  title_lines=["My Report"]))
        story.extend(preamble_break())
        story.append(ChapterAnchor("ch1", "Introduction", state=state, level=1))
        story.append(Paragraph("Hello, world!", styles["body"]))
        return story

    build_doc(
        ReportContext(
            out_path=Path("my-report.pdf"),
            title="My Report",
            subject="Demo",
            author="ACME Corp",
            creator="my-tool v1.0",
        ),
        my_story,
    )
"""

from __future__ import annotations

# ── Branding ──────────────────────────────────────────────────────────────────
from .branding import Layout, Palette, default_layout, default_palette

# ── Flowables ─────────────────────────────────────────────────────────────────
from .flowables import BookmarkAnchor, ChapterAnchor, FigureAnchor, HeaderState

# ── Reports ───────────────────────────────────────────────────────────────────
from .reports.base import (
    ReportContext,
    build_doc,
    concept_overview,
    cover_pages,
    part_divider,
    preamble_break,
)
from .reports.single_markdown import SingleMdConfig, build_single_markdown_pdf

# ── Styles ────────────────────────────────────────────────────────────────────
from .styles import make_styles

# ── Text ──────────────────────────────────────────────────────────────────────
from .text import clean_latex, esc, fmt, format_inline_math, safe_para

# ── TOC ───────────────────────────────────────────────────────────────────────
from .toc import FigureRegistry, TocEntry, TocPart, anchor_key, toc_pages

__all__ = [
    "BookmarkAnchor",
    "ChapterAnchor",
    "FigureAnchor",
    "FigureRegistry",
    "HeaderState",
    "Layout",
    "Palette",
    "ReportContext",
    "SingleMdConfig",
    "TocEntry",
    "TocPart",
    "anchor_key",
    "build_doc",
    "build_single_markdown_pdf",
    "clean_latex",
    "concept_overview",
    "cover_pages",
    "default_layout",
    "default_palette",
    "esc",
    "fmt",
    "format_inline_math",
    "make_styles",
    "part_divider",
    "preamble_break",
    "safe_para",
    "toc_pages",
]
