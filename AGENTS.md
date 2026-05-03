# AGENTS.md — Cursor / AI agent guidance for fes-pdf-builder

## Project summary

`fes-pdf-builder` is an open-source Python library (Apache 2.0) by Fulton Engineering
Services LLC. It provides a ReportLab + matplotlib chassis for building
branded PDF reports: palette, styles, flowables, page templates, markdown
parser, charts, and diagram renderers. It has no domain-specific knowledge
of benchmarks, hardware registries, or model specs — those live in consuming
projects.

## Directory conventions

- `src/fes_pdf_builder/` — all library code; use relative imports (`.branding`,
  `..toc`, etc.).
- `tests/unit/` — fast, pure-Python tests; no disk I/O beyond `tmp_path`.
- `tests/integration/` — tests that write real PDFs; always use `tmp_path`.
- `tests/fixtures/` — static `.md` files used by integration tests.
- `examples/` — runnable demo scripts; must be self-contained.

## Coding standards

- Python ≥ 3.10; use `X | Y` unions, `match`, PEP 695 syntax only from 3.12.
- All public symbols have docstrings.
- Type-annotate everything; `mypy --strict` must pass.
- Ruff `line-length = 100`, double quotes, LF endings.
- No `print()` in library code; use `logging` if status is needed.
- Copyright header on every `.py` file:

```python
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
```

## Dependency rules

- Core runtime dep: `reportlab>=4.0,<5.0` only.
- `matplotlib` is optional; guard with `_try_matplotlib()` pattern.
- `graphviz` (`dot`) is a system binary, not a Python dep; use `shutil.which`.
- `pypdf` is a **dev-only** dep (PDF assertion in tests).

## Test requirements

- New public functions need at least one unit test.
- PDF-writing tests belong in `tests/integration/` and must use `tmp_path`.
- Coverage gate is 85%; don't skip lines without a `# pragma: no cover` comment
  and a justification in the PR description.
