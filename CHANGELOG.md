# Changelog

All notable changes to `fes-pdf-builder` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.0] — 2026-04-29

### Added

- Initial release.
- `branding` — `Palette` + `Layout` dataclasses with FES defaults.
- `styles` — `make_styles(palette)` factory producing ~30 named `ParagraphStyle` objects.
- `flowables` — `ChapterAnchor`, `FigureAnchor`, `BookmarkAnchor`, `HeaderState`.
- `page_templates` — `PageContext`, `make_page_templates`, cover/main/part painters.
- `text` — `esc`, `fmt` (inline-markdown → ReportLab XML), `safe_para`, `clean_latex`,
  `format_inline_math`. `fmt` now accepts an optional `link_color` override.
- `blocks` — `make_sidebar`, `make_code_block`, `make_md_table`, `make_kv_table`,
  `make_simple_table`, `see_also_block`, `interpretation_box` (uses local
  `VerdictLike` protocol; no data-layer coupling).
- `toc` — `FigureRegistry`, `FigureEntry`, `TocEntry`, `TocPart`, `toc_pages`, `anchor_key`.
- `markdown` — `MarkdownConfig`, `parse_section_lines`, `parse_md_file`, `split_md_by_h2`,
  `slugify_heading`, `MdH2Section`. `MarkdownConfig.sidebar_title` default
  genericized to `"Sidebar"`.
- `charts` — `bar_chart`, `grouped_bar_chart`, `line_chart`, `heatmap`, `gantt_chart`,
  `multi_panel_timeline`, `register_chart_anchor`. Requires `[charts]` extra.
- `diagrams.math` — `make_math_block`, `render_latex_png`.
- `diagrams.mermaid` — `make_diagram_box`, `render_mermaid_png`, `mermaid_to_dot`,
  `has_graphviz`. Requires `dot` on PATH for full rendering; falls back to
  structured-text box otherwise.
- `diagrams.sequence` — `parse_sequence`, `render_sequence_png`. Requires `[diagrams]`.
- `reports.base` — `build_doc`, `ReportContext`, `cover_pages`, `preamble_break`,
  `part_divider`, `concept_overview`. `ReportContext.author` and `.creator` are
  now required (no vendor-specific defaults).
- `reports.single_markdown` — `build_single_markdown_pdf`, `SingleMdConfig`. New
  `cover_footer_line` field replaces the hard-coded confidentiality string.
- Curated public API via top-level `fes_pdf_builder.__init__`.
- Full test suite: 11 unit-test modules + 4 integration-test modules.
- 3 runnable examples under `examples/`.
- GitHub Actions CI matrix (Python 3.10 – 3.13).

[0.1.0]: https://github.com/Fulton-Engineering-Services/py-pdf-builder/releases/tag/v0.1.0
