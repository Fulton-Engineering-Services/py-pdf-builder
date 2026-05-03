# Contributing to fes-pdf-builder

`fes-pdf-builder` is open source under the Apache License 2.0.
Contributions are welcome — bug reports, fixes, and new features alike.

By submitting a pull request you agree that your contribution is made under
the same Apache 2.0 license as the project (inbound = outbound).

---

## Development environment

Requires [uv](https://docs.astral.sh/uv/) ≥ 0.4.

```bash
# Clone and enter the repo
git clone git@github.com:Fulton-Engineering-Services/py-pdf-builder.git
cd py-pdf-builder

# Install all dev dependencies (including matplotlib + pypdf for tests)
uv sync --group dev

# Optional: install the graphviz binary for mermaid happy-path tests
brew install graphviz          # macOS
# apt-get install -y graphviz  # Debian / Ubuntu
```

---

## Running the checks

```bash
# Lint
uv run ruff check src tests examples

# Format check (CI gate)
uv run ruff format --check src tests examples

# Auto-format
uv run ruff format src tests examples

# Type-check
uv run mypy src tests

# Tests + coverage
uv run pytest

# Build the wheel locally
uv build
```

All five commands must pass before a PR is merged.

---

## Pre-commit hooks

```bash
uv run pre-commit install
# Run manually against all files
uv run pre-commit run --all-files
```

---

## Project layout

```
src/fes_pdf_builder/     # library source
tests/unit/              # pure-Python unit tests
tests/integration/       # PDF-writing integration tests
tests/fixtures/          # static .md files used by tests
examples/                # runnable demo scripts
```

---

## Releases

Releases are managed automatically via [release-please](https://github.com/googleapis/release-please).

- Use conventional commit titles on your PRs: `feat:`, `fix:`, `docs:`, `chore:`, etc.
- `feat!:` or a `BREAKING CHANGE:` footer triggers a minor bump while the project is in `0.x`.
- Every merge to `main` that carries new conventional commits causes release-please to open
  (or update) a release PR that bumps `pyproject.toml`'s `version` and updates `CHANGELOG.md`.
- Merging the release PR creates the git tag and GitHub Release automatically.
- A wheel (`.whl`) and source distribution (`.tar.gz`) are built and attached to every Release.
