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

"""Example: build a PDF from a single markdown file.

Renders the sample fixture from tests/fixtures/sample.md using
:func:`build_single_markdown_pdf`. Each H2 section becomes a chapter.

Run from the repo root:

    uv run python examples/single_markdown_report.py
    # Writes: examples/output/sample-report.pdf
"""

from __future__ import annotations

from pathlib import Path

from fes_pdf_builder.reports.single_markdown import SingleMdConfig, build_single_markdown_pdf

if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent
    source = repo_root / "tests" / "fixtures" / "sample.md"
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)

    out = build_single_markdown_pdf(
        SingleMdConfig(
            out_path=out_dir / "sample-report.pdf",
            source_path=source,
            doc_title="Sample Report",
            doc_subject="fes-pdf-builder single-markdown example",
            doc_author="Fulton Engineering Services LLC",
            doc_creator="fes-pdf-builder examples",
            brand_line="FULTON ENGINEERING SERVICES LLC",
            title_lines=["Sample Report"],
            subtitle_lines=["Rendered from sample.md"],
            cover_footer_line="For demonstration purposes",
        )
    )
    print(out)
