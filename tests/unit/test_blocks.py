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

"""Unit tests for :mod:`fes_pdf_builder.blocks`."""

from __future__ import annotations

import pytest

from fes_pdf_builder.blocks import (
    SEVERITY_HEX,
    VerdictLike,
    interpretation_box,
    make_code_block,
    make_kv_table,
    make_md_table,
    make_sidebar,
    make_simple_table,
    see_also_block,
    severity_color_hex,
)
from fes_pdf_builder.styles import make_styles

# ─── Severity helpers ─────────────────────────────────────────────────────────


def test_severity_color_hex_known_levels() -> None:
    assert severity_color_hex("ok") == SEVERITY_HEX["ok"]
    assert severity_color_hex("warn") == SEVERITY_HEX["warn"]
    assert severity_color_hex("alert") == SEVERITY_HEX["alert"]
    assert severity_color_hex("info") == SEVERITY_HEX["info"]


def test_severity_color_hex_unknown_falls_back_to_slate() -> None:
    assert severity_color_hex("unknown") == "#475569"


def test_severity_color_hex_case_insensitive() -> None:
    assert severity_color_hex("OK") == severity_color_hex("ok")
    assert severity_color_hex("WARN") == severity_color_hex("warn")


# ─── VerdictLike protocol ─────────────────────────────────────────────────────


def test_verdict_like_protocol_satisfied_by_simple_class() -> None:
    class SimpleVerdict:
        label = "Acceptable"
        evidence = "p50 = 72 tok/s"
        severity = "ok"

    v = SimpleVerdict()
    assert isinstance(v, VerdictLike)


def test_verdict_like_protocol_not_satisfied_without_severity() -> None:
    class Incomplete:
        label = "x"
        evidence = "y"
        # missing severity

    assert not isinstance(Incomplete(), VerdictLike)


# ─── make_sidebar ─────────────────────────────────────────────────────────────


def test_make_sidebar_returns_table() -> None:
    styles = make_styles()
    from reportlab.platypus import Paragraph

    items = [Paragraph("Content item.", styles["sidebar_body"])]
    t = make_sidebar("My Sidebar", items, styles)
    assert t.__class__.__name__ == "Table"


def test_make_sidebar_custom_prefix() -> None:
    styles = make_styles()
    from reportlab.platypus import Paragraph

    items = [Paragraph("Info.", styles["sidebar_body"])]
    t = make_sidebar("Info", items, styles, title_prefix="▸  NOTE")
    # Inspect the title paragraph text; ReportLab may normalize whitespace
    first_row = t._cellvalues[0][0]  # type: ignore[attr-defined]
    text = first_row.text
    assert "NOTE" in text
    assert "INFO" in text


# ─── make_code_block ──────────────────────────────────────────────────────────


def test_make_code_block_returns_table() -> None:
    styles = make_styles()
    t = make_code_block("x = 1 + 2\nprint(x)", "python", styles)
    assert t.__class__.__name__ == "Table"


def test_make_code_block_truncates_long_lines() -> None:
    styles = make_styles()
    long_line = "x" * 200
    # Should not raise
    t = make_code_block(long_line, "", styles)
    assert t is not None


# ─── make_md_table ────────────────────────────────────────────────────────────


def test_make_md_table_returns_table_for_valid_rows() -> None:
    styles = make_styles()
    rows = [["Name", "Value"], ["Alpha", "1.0"], ["Beta", "2.5"]]
    t = make_md_table(rows, styles)
    assert t is not None
    assert t.__class__.__name__ == "Table"


def test_make_md_table_returns_none_for_empty() -> None:
    styles = make_styles()
    assert make_md_table([], styles) is None


# ─── make_simple_table ────────────────────────────────────────────────────────


def test_make_simple_table_returns_table() -> None:
    rows = [["Key", "Value"], ["alpha", "1"], ["beta", "2"]]
    t = make_simple_table(rows)
    assert t is not None


def test_make_simple_table_no_header() -> None:
    rows = [["alpha", "1"], ["beta", "2"]]
    t = make_simple_table(rows, has_header=False)
    assert t is not None


# ─── make_kv_table ────────────────────────────────────────────────────────────


def test_make_kv_table_two_column() -> None:
    pairs = [("Name", "Gemma"), ("Params", "4B")]
    t = make_kv_table(pairs)
    assert t is not None


def test_make_kv_table_three_column() -> None:
    pairs = [("GPU", "A100", "80 GiB VRAM"), ("vCPU", "96", "AMD EPYC")]
    t = make_kv_table(pairs)
    assert t is not None


def test_make_kv_table_returns_none_for_empty() -> None:
    assert make_kv_table([]) is None


# ─── interpretation_box ──────────────────────────────────────────────────────


def test_interpretation_box_accepts_verdict_like() -> None:
    class MyVerdict:
        label = "Excellent"
        evidence = "p95 latency < 2s"
        severity = "ok"

    box = interpretation_box(MyVerdict())
    assert box.__class__.__name__ == "KeepTogether"


def test_interpretation_box_handles_all_severities() -> None:
    class V:
        label = "x"
        evidence = "y"
        severity: str

    for sev in ("ok", "info", "warn", "alert"):
        V.severity = sev
        box = interpretation_box(V())
        assert box is not None


# ─── see_also_block ───────────────────────────────────────────────────────────


def test_see_also_block_returns_none_for_empty() -> None:
    assert see_also_block([]) is None


def test_see_also_block_returns_keep_together_for_pointers() -> None:
    block = see_also_block(["Chapter 3 — KV Cache", "Appendix B — Benchmarks"])
    assert block is not None
    assert block.__class__.__name__ == "KeepTogether"


# ─── VerdictLike not a type that blocks import without data deps ───────────────


def test_blocks_importable_without_data_layer() -> None:
    """importing blocks must not trigger any data.* import."""
    import sys

    data_modules = [k for k in sys.modules if k.startswith("fes_pdf_builder.data")]
    assert data_modules == [], f"unexpected data imports: {data_modules}"


@pytest.mark.parametrize(
    "sev,expected_start",
    [
        ("ok", "#16"),
        ("info", "#1D"),
        ("warn", "#D9"),
        ("alert", "#B9"),
    ],
)
def test_severity_hex_values(sev: str, expected_start: str) -> None:
    assert severity_color_hex(sev).upper().startswith(expected_start.upper())
