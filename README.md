# fes-pdf-builder

An open-source PDF report toolkit (Apache 2.0) from Fulton Engineering Services LLC.

Provides a complete **ReportLab + matplotlib chassis** for building branded PDF deliverables from Python scripts: palette, styles, flowables, page templates, a markdown → flowable parser, chart helpers, and optional Mermaid / math diagram renderers.

---

## Install

This package is not yet published to PyPI. Install directly from GitHub using a tagged release.

### Via `git+https` (source install — builds on the consumer side)

```bash
# Core only (ReportLab)
pip install "fes-pdf-builder @ git+https://github.com/Fulton-Engineering-Services/py-pdf-builder@v0.1.0"

# With chart support (matplotlib)
pip install "fes-pdf-builder[charts] @ git+https://github.com/Fulton-Engineering-Services/py-pdf-builder@v0.1.0"

# With diagram support
pip install "fes-pdf-builder[diagrams] @ git+https://github.com/Fulton-Engineering-Services/py-pdf-builder@v0.1.0"

# Everything
pip install "fes-pdf-builder[all] @ git+https://github.com/Fulton-Engineering-Services/py-pdf-builder@v0.1.0"
```

### Via pre-built wheel (faster — no build step)

Each GitHub Release has a `.whl` attached. Install it directly:

```bash
pip install "https://github.com/Fulton-Engineering-Services/py-pdf-builder/releases/download/v0.1.0/fes_pdf_builder-0.1.0-py3-none-any.whl"
```

### In `pyproject.toml` (uv / pip)

```toml
dependencies = [
    # Tagged source install (recommended):
    "fes-pdf-builder @ git+https://github.com/Fulton-Engineering-Services/py-pdf-builder@v0.1.0",
    # Or pin to the pre-built wheel from a Release (faster CI):
    # "fes-pdf-builder @ https://github.com/Fulton-Engineering-Services/py-pdf-builder/releases/download/v0.1.0/fes_pdf_builder-0.1.0-py3-none-any.whl",
]
```

For full Mermaid `flowchart` / `graph` rendering you also need the `dot` binary:

```bash
brew install graphviz          # macOS
apt-get install -y graphviz    # Debian / Ubuntu
```

Without `dot`, Mermaid blocks fall back to a structured-text description box — no exception is raised.

---

## Quickstart

### Minimal report — `build_doc`

```python
from pathlib import Path
from reportlab.platypus import Paragraph

from fes_pdf_builder import (
    build_doc, ReportContext,
    ChapterAnchor, HeaderState, Layout, Palette,
    cover_pages, preamble_break,
)

def my_story(styles, state: HeaderState, palette: Palette, layout: Layout):
    story = []
    story.extend(cover_pages(styles,
                              brand_line="ACME CORP",
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
```

### Markdown-driven report — `build_single_markdown_pdf`

```python
from pathlib import Path
from fes_pdf_builder.reports.single_markdown import SingleMdConfig, build_single_markdown_pdf

build_single_markdown_pdf(
    SingleMdConfig(
        out_path=Path("output.pdf"),
        source_path=Path("docs/my-doc.md"),
        doc_title="My Document",
        doc_subject="Reference",
        doc_author="ACME Corp",
        doc_creator="my-pipeline",
        brand_line="ACME CORP",
        title_lines=["My Document"],
        subtitle_lines=["v1.0"],
        cover_footer_line="Confidential",   # optional
    )
)
```

Each `## Heading` in the markdown file becomes its own chapter, complete with running header, TOC link, and PDF outline entry.

---

## API Overview

| Module | Key exports |
|---|---|
| `fes_pdf_builder.branding` | `Palette`, `Layout`, `default_palette()`, `default_layout()` |
| `fes_pdf_builder.styles` | `make_styles(palette)` → `dict[str, ParagraphStyle]` |
| `fes_pdf_builder.flowables` | `ChapterAnchor`, `FigureAnchor`, `BookmarkAnchor`, `HeaderState` |
| `fes_pdf_builder.page_templates` | `PageContext`, `make_page_templates()` |
| `fes_pdf_builder.text` | `esc()`, `fmt()`, `safe_para()`, `clean_latex()` |
| `fes_pdf_builder.blocks` | `make_sidebar()`, `make_code_block()`, `make_md_table()`, `make_kv_table()`, `interpretation_box()`, `make_image()`, `make_image_block()` |
| `fes_pdf_builder.toc` | `FigureRegistry`, `TocEntry`, `TocPart`, `toc_pages()`, `anchor_key()` |
| `fes_pdf_builder.markdown` | `parse_section_lines()`, `parse_md_file()`, `split_md_by_h2()`, `MarkdownConfig` |
| `fes_pdf_builder.charts` | `bar_chart()`, `grouped_bar_chart()`, `line_chart()`, `heatmap()`, `gantt_chart()`, `multi_panel_timeline()` |
| `fes_pdf_builder.diagrams.mermaid` | `make_diagram_box()`, `has_graphviz()` |
| `fes_pdf_builder.diagrams.sequence` | `parse_sequence()`, `render_sequence_png()` |
| `fes_pdf_builder.diagrams.math` | `make_math_block()`, `render_latex_png()` |
| `fes_pdf_builder.reports.base` | `build_doc()`, `ReportContext`, `cover_pages()`, `part_divider()`, `concept_overview()` |
| `fes_pdf_builder.reports.single_markdown` | `build_single_markdown_pdf()`, `SingleMdConfig` |

All of the above are also re-exported from the top-level `fes_pdf_builder` namespace.

---

## Branding override recipe

```python
from reportlab.lib.colors import HexColor
from fes_pdf_builder.branding import Layout, Palette
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

my_palette = Palette(
    navy=HexColor("#003366"),
    blue=HexColor("#0055AA"),
)
my_layout = Layout(
    page_width=A4[0],
    page_height=A4[1],
    margin=0.75 * inch,
)

build_doc(context, story_builder, palette=my_palette, layout=my_layout)
```

---

## Examples

| File | Description |
|---|---|
| [`examples/minimal_report.py`](examples/minimal_report.py) | `build_doc` + cover + TOC + two chapters |
| [`examples/single_markdown_report.py`](examples/single_markdown_report.py) | `build_single_markdown_pdf` from `tests/fixtures/sample.md` |
| [`examples/charts_and_diagrams.py`](examples/charts_and_diagrams.py) | Bar, line, heatmap, Gantt + Mermaid flowchart in one PDF |

Run any example:

```bash
uv run python examples/minimal_report.py
# → examples/output/minimal-report.pdf
```

---

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full developer workflow.

```bash
uv sync --group dev
uv run pytest
uv run ruff check src tests examples
uv run mypy src tests
```

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Copyright 2026 Fulton Engineering Services LLC.
