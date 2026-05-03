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

"""Unit tests for :mod:`fes_pdf_builder.charts`."""

from __future__ import annotations

from fes_pdf_builder.charts import (
    bar_chart,
    gantt_chart,
    grouped_bar_chart,
    heatmap,
    line_chart,
    multi_panel_timeline,
    register_chart_anchor,
)
from fes_pdf_builder.toc import FigureRegistry


def test_bar_chart_returns_flowable() -> None:
    f = bar_chart(["a", "b", "c"], [1.0, 2.0, 3.0], title="Test")
    assert f is not None


def test_grouped_bar_chart_returns_flowable() -> None:
    f = grouped_bar_chart(
        groups=["g4dn", "g5", "g6"],
        series={"q4q4": [10, 20, 30], "q8q8": [12, 22, 32]},
        title="Tokens/sec",
        ylabel="tok/s",
    )
    assert f is not None


def test_line_chart_returns_flowable() -> None:
    f = line_chart(
        x=[2048, 8192, 32768],
        series={"decode": [100, 80, 40], "prefill": [5000, 4500, 3800]},
        title="vs depth",
        log_x=True,
    )
    assert f is not None


def test_heatmap_returns_flowable() -> None:
    rows = ["g4dn.xlarge", "g5.xlarge"]
    cols = ["gemma4-e2b", "gemma4-e4b"]
    matrix: list[list[float | None]] = [[100.0, 80.0], [None, 75.5]]
    f = heatmap(rows, cols, matrix, title="decode tok/s", cmap_name="Blues")
    assert f is not None


def test_gantt_chart_returns_flowable() -> None:
    phases = [
        {"name": "build", "status": "SUCCESS", "elapsed_s": 120.0},
        {"name": "bench", "status": "SUCCESS", "elapsed_s": 3600.0},
        {"name": "niah", "status": "SKIPPED", "elapsed_s": 0.0},
    ]
    f = gantt_chart(phases, title="Phase timing")
    assert f is not None


def test_multi_panel_timeline_returns_flowable() -> None:
    x = [0.0, 1.0, 2.0, 3.0]
    panels = [
        {"label": "GPU util %", "y": [10.0, 80.0, 90.0, 20.0]},
        {"label": "VRAM MiB", "y": [1000.0, 15000.0, 15000.0, 1000.0]},
    ]
    f = multi_panel_timeline(x, panels, title="GPU telemetry")
    assert f is not None


def test_register_chart_anchor_advances_registry() -> None:
    figs = FigureRegistry()
    anchor = register_chart_anchor(
        figs, chapter_title="Chapter 1", chart_type="Bar chart", title="decode tok/s"
    )
    assert len(figs) == 1
    assert figs.entries[0].fig_key == "fig_001"
    assert anchor.__class__.__name__ == "FigureAnchor"
