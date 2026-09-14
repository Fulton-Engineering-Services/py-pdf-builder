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

"""Integration test: LaTeX math mode through :func:`build_single_markdown_pdf`."""

from __future__ import annotations

from pathlib import Path

import pytest

from fes_pdf_builder.reports.single_markdown import SingleMdConfig, build_single_markdown_pdf

FIXTURES = Path(__file__).parent.parent / "fixtures"


MATH_FIXTURE = """\
# Math Fixture

Lead paragraph with inline math $x_i$ and money $5 and $10.

## Equations

The log-likelihood is:

\\[
\\ell(\\theta) = \\sum_{i=1}^{n} \\log f(y_i \\mid x_i, \\theta)
\\]

with overdispersion $\\hat{c}^{2}$ and code:

```r
pred <- exp(coef(fit)[1]) * v$W
```

Done.
"""


def _write_fixture(tmp_path: Path) -> Path:
    src = tmp_path / "math-fixture.md"
    src.write_text(MATH_FIXTURE, encoding="utf-8")
    return src


def test_build_single_markdown_latex_mode_writes_pdf(tmp_path: Path) -> None:
    pytest.importorskip("ziamath")
    pytest.importorskip("svglib")
    out = build_single_markdown_pdf(
        SingleMdConfig(
            out_path=tmp_path / "math-latex.pdf",
            source_path=_write_fixture(tmp_path),
            doc_title="Math Fixture",
            doc_subject="Test",
            doc_author="FES Test Suite",
            doc_creator="fes-pdf-builder tests",
            brand_line="FULTON ENGINEERING SERVICES LLC",
            title_lines=["Math Fixture"],
            subtitle_lines=["Integration test"],
            math_mode="latex",
        )
    )
    assert out.exists()
    assert out.stat().st_size > 2048


def test_build_single_markdown_legacy_mode_unchanged(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    out = build_single_markdown_pdf(
        SingleMdConfig(
            out_path=tmp_path / "math-legacy.pdf",
            source_path=_write_fixture(tmp_path),
            doc_title="Math Fixture",
            doc_subject="Test",
            doc_author="FES Test Suite",
            doc_creator="fes-pdf-builder tests",
            brand_line="FULTON ENGINEERING SERVICES LLC",
            title_lines=["Math Fixture"],
            subtitle_lines=["Integration test"],
            math_mode="legacy",
        )
    )
    assert out.exists()
    assert out.stat().st_size > 2048
