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

"""Unit tests for :mod:`fes_pdf_builder.toc`."""

from __future__ import annotations

from fes_pdf_builder.flowables import HeaderState
from fes_pdf_builder.styles import make_styles
from fes_pdf_builder.toc import (
    FigureEntry,
    FigureRegistry,
    TocEntry,
    TocPart,
    anchor_key,
    toc_pages,
)


def test_figure_registry_next_key_increments() -> None:
    reg = FigureRegistry()
    assert reg.next_key() == "fig_001"
    reg.register(chapter_title="Chap 1", diagram_type="Bar chart")
    assert reg.next_key() == "fig_002"
    reg.register(chapter_title="Chap 1", diagram_type="Heatmap")
    assert reg.next_key() == "fig_003"


def test_figure_registry_len() -> None:
    reg = FigureRegistry()
    assert len(reg) == 0
    reg.register(chapter_title="Ch", diagram_type="Flowchart")
    assert len(reg) == 1


def test_figure_registry_register_returns_key() -> None:
    reg = FigureRegistry()
    key = reg.register(chapter_title="Ch", diagram_type="Line chart", title="throughput")
    assert key == "fig_001"
    assert reg.entries[0].title == "throughput"
    assert reg.entries[0].chapter_title == "Ch"


def test_anchor_key_replaces_hyphens() -> None:
    assert anchor_key("kv-cache") == "kv_cache"


def test_anchor_key_strips_md_extension() -> None:
    assert anchor_key("kv-cache.md") == "kv_cache"


def test_anchor_key_idempotent_on_clean_id() -> None:
    assert anchor_key("kv_cache") == "kv_cache"


def test_toc_pages_produces_flowables() -> None:
    styles = make_styles()
    state = HeaderState()
    parts = [
        TocPart(
            heading="PART I — CHAPTERS",
            anchor="part_i",
            entries=[
                TocEntry(label="Introduction", anchor="ch_intro"),
                TocEntry(label="Methods", anchor="ch_methods"),
            ],
        )
    ]
    flowables = toc_pages(parts, styles, state=state)
    assert len(flowables) > 0
    names = {f.__class__.__name__ for f in flowables}
    assert "Paragraph" in names


def test_toc_pages_includes_figures_section_when_registry_populated() -> None:
    styles = make_styles()
    state = HeaderState()
    figs = FigureRegistry()
    figs.register(chapter_title="Ch 1", diagram_type="Bar chart", title="tokens/sec")

    parts = [
        TocPart(
            heading="CONTENTS",
            anchor=None,
            entries=[TocEntry(label="Ch 1", anchor="ch1")],
        )
    ]
    flowables = toc_pages(parts, styles, state=state, figures=figs)
    texts = [
        f.text if hasattr(f, "text") else ""
        for f in flowables
        if f.__class__.__name__ == "Paragraph"
    ]
    full = " ".join(texts)
    assert "FIGURES" in full or "Bar chart" in full or "Figure 1" in full


def test_toc_pages_omits_figures_section_when_registry_empty() -> None:
    styles = make_styles()
    state = HeaderState()
    figs = FigureRegistry()
    parts = [TocPart(heading="CONTENTS", anchor=None, entries=[TocEntry(label="x", anchor="x")])]
    flowables = toc_pages(parts, styles, state=state, figures=figs)
    texts = [
        f.text if hasattr(f, "text") else ""
        for f in flowables
        if f.__class__.__name__ == "Paragraph"
    ]
    full = " ".join(texts)
    assert "FIGURES" not in full


def test_toc_entry_deep_flag() -> None:
    e = TocEntry(label="Appendix A", anchor="app_a", deep=True)
    assert e.deep is True


def test_figure_entry_dataclass() -> None:
    fe = FigureEntry(fig_key="fig_001", chapter_title="Ch 1", diagram_type="Heatmap", title="perf")
    assert fe.fig_key == "fig_001"
    assert fe.title == "perf"
