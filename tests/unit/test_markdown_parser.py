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

"""Unit tests for :mod:`fes_pdf_builder.markdown`."""

from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.platypus import Paragraph

from fes_pdf_builder.markdown import (
    MarkdownConfig,
    MdH2Section,
    parse_section_lines,
    slugify_heading,
    split_md_by_h2,
)
from fes_pdf_builder.styles import make_styles


def test_slugify_heading_basic() -> None:
    assert slugify_heading("## How it Works") == "how-it-works"


def test_slugify_heading_strips_backticks() -> None:
    assert slugify_heading("`llama.cpp` loading") == "llamacpp-loading"


def test_slugify_heading_collapses_special_chars() -> None:
    slug = slugify_heading("A: B & C — D")
    assert " " not in slug
    assert slug  # non-empty


def test_markdown_config_sidebar_title_default_is_generic() -> None:
    cfg = MarkdownConfig()
    assert cfg.sidebar_title == "Sidebar"


def test_markdown_config_sidebar_title_override() -> None:
    cfg = MarkdownConfig(sidebar_title="My Custom Sidebar")
    assert cfg.sidebar_title == "My Custom Sidebar"


def test_parse_section_lines_produces_body_paragraphs() -> None:
    styles = make_styles()
    lines = ["This is a paragraph.", "", "This is a second paragraph."]
    flowables = parse_section_lines(lines, styles)
    # Both paragraphs should produce Paragraph flowables
    names = [f.__class__.__name__ for f in flowables]
    assert names.count("Paragraph") >= 2


def test_parse_section_lines_handles_bullet_lists() -> None:
    styles = make_styles()
    lines = ["- Item one", "- Item two", "- Item three"]
    flowables = parse_section_lines(lines, styles)
    texts = [
        f.text if hasattr(f, "text") else ""
        for f in flowables
        if f.__class__.__name__ == "Paragraph"
    ]
    full = " ".join(texts)
    assert "Item one" in full
    assert "Item two" in full


def test_parse_section_lines_handles_h2_heading() -> None:
    styles = make_styles()
    lines = ["## Section Title", "Body text."]
    flowables = parse_section_lines(lines, styles)
    assert any(f.__class__.__name__ == "Paragraph" for f in flowables)


def test_parse_section_lines_emits_bookmark_for_heading_in_chapter() -> None:
    styles = make_styles()
    lines = ["## My Heading", "Body text."]
    flowables = parse_section_lines(lines, styles, chapter_anchor="ch1")
    anchor_types = {f.__class__.__name__ for f in flowables}
    assert "BookmarkAnchor" in anchor_types


def test_parse_section_lines_code_fence() -> None:
    styles = make_styles()
    lines = ["```python", "x = 1 + 2", "```"]
    flowables = parse_section_lines(lines, styles)
    # Should produce a Table (the code block wrapper)
    assert any(f.__class__.__name__ == "Table" for f in flowables)


def test_split_md_by_h2_basic(tmp_path: Path) -> None:
    md = tmp_path / "doc.md"
    md.write_text(
        "# Document Title\n\nLead paragraph.\n\n"
        "## Section One\n\nBody one.\n\n## Section Two\n\nBody two.\n",
        encoding="utf-8",
    )
    h1, lead, sections = split_md_by_h2(md)
    assert h1 == "Document Title"
    assert any("Lead paragraph" in ln for ln in lead)
    assert len(sections) == 2
    assert sections[0].title == "Section One"
    assert sections[1].title == "Section Two"
    assert sections[0].anchor_slug == "section-one"


def test_split_md_by_h2_no_h2(tmp_path: Path) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Title\n\nJust a lead.\n", encoding="utf-8")
    h1, _lead, sections = split_md_by_h2(md)
    assert h1 == "Title"
    assert sections == []


def test_md_h2_section_anchor_slug_is_derived() -> None:
    sec = MdH2Section(
        title="My Section",
        raw_title="My Section",
        lines=[],
        anchor_slug=slugify_heading("My Section"),
    )
    assert sec.anchor_slug == "my-section"


@pytest.mark.parametrize(
    "heading,expected",
    [
        ("Simple Title", "simple-title"),
        ("Title with: Colon & Special Chars!", "title-with-colon-special-chars"),
        ("KV Cache", "kv-cache"),
        ("A  B", "a-b"),  # double space collapsed
    ],
)
def test_slugify_heading_parametrized(heading: str, expected: str) -> None:
    assert slugify_heading(heading) == expected


def test_parse_md_file_full_chapter(tmp_path: Path) -> None:
    from fes_pdf_builder.flowables import HeaderState
    from fes_pdf_builder.markdown import MarkdownConfig, parse_md_file

    md = tmp_path / "chapter.md"
    md.write_text(
        "# My Chapter\n\nLead prose for the chapter.\n\n"
        "## Section One\n\nBody text.\n\n"
        "- bullet one\n- bullet two\n\n"
        "## How it shows up in this repo\n\nSidebar content.\n\n"
        "## Further reading\n\n1. Reference one\n2. Reference two\n",
        encoding="utf-8",
    )
    styles = make_styles()
    state = HeaderState()
    flowables = parse_md_file(
        md,
        styles,
        chapter_label="Chapter 1",
        chapter_title="My Chapter",
        state=state,
        config=MarkdownConfig(),
        anchor="my_chapter",
    )
    assert len(flowables) > 0
    names = {f.__class__.__name__ for f in flowables}
    assert "Paragraph" in names


def test_parse_md_file_no_sidebar(tmp_path: Path) -> None:
    from fes_pdf_builder.flowables import HeaderState
    from fes_pdf_builder.markdown import MarkdownConfig, parse_md_file

    md = tmp_path / "chapter.md"
    md.write_text(
        "# Title\n\nBody without sidebar.\n\n## Section\n\nContent.\n",
        encoding="utf-8",
    )
    styles = make_styles()
    state = HeaderState()
    # Pass config with regexes disabled → no sidebar folding
    cfg = MarkdownConfig(sidebar_heading_re=None, further_reading_heading_re=None)
    flowables = parse_md_file(
        md, styles, chapter_label="Ch", chapter_title="Title", state=state, config=cfg
    )
    assert len(flowables) > 0


def test_parse_section_lines_math_block(tmp_path: Path) -> None:
    styles = make_styles()
    lines = [
        r"\[",
        r"\frac{a}{b} = c",
        r"\]",
        "Regular paragraph.",
    ]
    flowables = parse_section_lines(lines, styles, math_renderer=None)
    # Without math_renderer, math block is silently skipped; paragraph emits
    assert any(f.__class__.__name__ == "Paragraph" for f in flowables)


def test_parse_section_lines_hr_rule() -> None:
    styles = make_styles()
    lines = ["Text before.", "---", "Text after."]
    flowables = parse_section_lines(lines, styles)
    names = [f.__class__.__name__ for f in flowables]
    assert "HRFlowable" in names


def test_parse_section_lines_numbered_list() -> None:
    styles = make_styles()
    lines = ["1. First item", "2. Second item", "3. Third item"]
    flowables = parse_section_lines(lines, styles)
    texts = [
        f.text if hasattr(f, "text") else ""
        for f in flowables
        if f.__class__.__name__ == "Paragraph"
    ]
    full = " ".join(texts)
    assert "First item" in full


def test_parse_section_lines_markdown_table() -> None:
    styles = make_styles()
    lines = [
        "| Name | Value |",
        "| --- | --- |",
        "| alpha | 1.0 |",
        "| beta | 2.0 |",
    ]
    flowables = parse_section_lines(lines, styles)
    assert any(f.__class__.__name__ == "Table" for f in flowables)


def test_parse_section_lines_latex_mode_dollar_display_block() -> None:
    styles = make_styles()
    lines = ["$$", "a^2 + b^2 = c^2", "$$", "Regular paragraph."]
    seen: list[str] = []

    def math_renderer(text: str, _styles: dict) -> object:
        seen.append(text)
        return Paragraph(text, styles["body"])

    flowables = parse_section_lines(lines, styles, math_renderer=math_renderer, math_mode="latex")
    assert seen == ["a^2 + b^2 = c^2"]
    assert any(f.__class__.__name__ == "Paragraph" for f in flowables)


def test_parse_section_lines_latex_mode_single_line_display() -> None:
    styles = make_styles()
    lines = ["$$x = y$$", "Prose after."]
    seen: list[str] = []

    def math_renderer(text: str, _styles: dict) -> object:
        seen.append(text)
        return Paragraph(text, styles["body"])

    parse_section_lines(lines, styles, math_renderer=math_renderer, math_mode="latex")
    assert seen == ["x = y"]


def test_parse_section_lines_latex_mode_bracket_block_captures_trailing() -> None:
    styles = make_styles()
    lines = [r"\[ \frac{a}{b} = c \]", "Prose after."]
    seen: list[str] = []

    def math_renderer(text: str, _styles: dict) -> object:
        seen.append(text)
        return Paragraph(text, styles["body"])

    parse_section_lines(lines, styles, math_renderer=math_renderer, math_mode="latex")
    assert seen == [r"\frac{a}{b} = c"]


def test_parse_section_lines_legacy_mode_ignores_dollar_blocks() -> None:
    styles = make_styles()
    lines = ["$$", "a^2 + b^2 = c^2", "$$"]
    seen: list[str] = []

    def math_renderer(text: str, _styles: dict) -> object:
        seen.append(text)
        return Paragraph(text, styles["body"])

    parse_section_lines(lines, styles, math_renderer=math_renderer)
    assert seen == []


def test_parse_section_lines_latex_mode_math_in_sidebar_suppressed() -> None:
    styles = make_styles()
    lines = ["$$", "a + b", "$$"]
    seen: list[str] = []

    def math_renderer(text: str, _styles: dict) -> object:
        seen.append(text)
        return Paragraph(text, styles["body"])

    parse_section_lines(
        lines, styles, math_renderer=math_renderer, math_mode="latex", is_sidebar=True
    )
    assert seen == []
