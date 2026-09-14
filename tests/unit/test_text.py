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

"""Unit tests for :mod:`fes_pdf_builder.text`."""

from __future__ import annotations

import pytest

from fes_pdf_builder.styles import make_styles
from fes_pdf_builder.text import clean_latex, esc, fmt, format_inline_math, safe_para


def test_esc_handles_xml_special_chars() -> None:
    assert esc("<a>&b") == "&lt;a&gt;&amp;b"


def test_fmt_bold_italic_and_code() -> None:
    out = fmt("**bold** _italic_ `Q4_K_M`")
    assert "<b>bold</b>" in out
    assert "<i>italic</i>" in out
    assert "Q4_K_M" in out  # underscore inside identifier should not become italic


def test_fmt_inline_math_emits_subscript() -> None:
    out = fmt(r"PPL is \(p_\theta(x_i)\) tied to the model.")
    # The math span should be wrapped in italic Courier with a <sub> tag
    assert "<sub>" in out
    assert "Courier" in out


def test_safe_para_falls_back_on_bad_xml() -> None:
    styles = make_styles()
    p = safe_para("<<<not-xml>>>", styles["body"])
    # Falls back to a plain Paragraph; assert it's a ReportLab object
    assert p.__class__.__name__ == "Paragraph"


def test_clean_latex_collapses_frac_and_greek() -> None:
    out = clean_latex(r"\frac{a}{b} + \alpha")
    assert "(a / b)" in out
    assert "α" in out


def test_format_inline_math_handles_braced_subscript() -> None:
    out = format_inline_math(r"\(x_{<i}\)")
    # The braced subscript content should survive XML escaping
    assert "<sub>" in out
    assert "&lt;i" in out


def test_fmt_link_resolver_renders_internal_anchor() -> None:
    """A resolver returning a key should produce a brand-blue, no-underline
    internal anchor pointing at ``#<key>``."""
    out = fmt(
        "See [KV cache](kv-cache.md) for the derivation.",
        link_resolver=lambda url: "kv_cache" if url == "kv-cache.md" else None,
    )
    assert 'href="#kv_cache"' in out
    assert "#2563EB" in out
    assert "<u>" not in out
    assert "KV cache" in out


def test_fmt_link_resolver_handles_in_file_fragment() -> None:
    """In-file ``[X](#fragment)`` references resolve through the resolver
    just like sibling-file links."""
    out = fmt(
        "Jump to [Why corpus choice matters](#why-corpus-choice-matters).",
        link_resolver=lambda url: (
            "perplexity__why-corpus-choice-matters" if url == "#why-corpus-choice-matters" else None
        ),
    )
    assert 'href="#perplexity__why-corpus-choice-matters"' in out
    assert "Why corpus choice matters" in out


def test_fmt_link_resolver_returning_none_falls_back_to_display_only() -> None:
    """When the resolver declines, schemeless links keep the legacy
    display-only behaviour (no anchor markup)."""
    out = fmt(
        "See [the matrix](../../../source-artifacts/poc-02.md) for sizes.",
        link_resolver=lambda url: None,
    )
    assert "the matrix" in out
    assert "href=" not in out
    assert "<a " not in out


def test_fmt_link_resolver_does_not_override_external_links() -> None:
    """External http(s) URLs should fall through to the existing
    underlined-anchor branch even when the resolver is supplied (and
    returns ``None`` for them)."""
    out = fmt(
        "Spec at [llama.cpp](https://github.com/ggml-org/llama.cpp).",
        link_resolver=lambda url: None,
    )
    assert 'href="https://github.com/ggml-org/llama.cpp"' in out
    assert "<u>" in out


def test_fmt_without_resolver_strips_relative_md_links() -> None:
    """Backwards compatibility: callers that don't pass a resolver get
    the legacy behaviour where relative ``.md`` targets are dropped to
    display text."""
    out = fmt("See [KV cache](kv-cache.md) for details.")
    assert "KV cache" in out
    assert "href=" not in out


def test_fmt_link_color_override() -> None:
    """``link_color`` kwarg overrides the default FES blue."""
    out = fmt(
        "See [docs](https://example.com).",
        link_color="#FF0000",
    )
    assert "#FF0000" in out
    assert "#2563EB" not in out


def test_fmt_bare_url_uses_link_color() -> None:
    """Bare ``<https://...>`` URLs honour the ``link_color`` override."""
    out = fmt("<https://example.com>", link_color="#AABBCC")
    assert "#AABBCC" in out


def test_fmt_latex_mode_renders_dollar_math_as_image() -> None:
    pytest.importorskip("matplotlib")
    out = fmt(r"variance scales as $\hat{c}^{2}$ per month.", math_mode="latex")
    assert "data:image/png;base64," in out
    assert 'valign="-' in out


def test_fmt_latex_mode_keeps_money_prose() -> None:
    out = fmt("costs $5 and $10 for the licence.", math_mode="latex")
    assert "data:image/png;base64," not in out
    assert "$5" in out


def test_fmt_latex_mode_protects_code_spans_from_math() -> None:
    out = fmt(r"`v$W^coef(x)[1]` and \(x_i\)", math_mode="latex")
    assert "Courier" in out
    assert "v$W^coef(x)[1]" in out


def test_fmt_latex_mode_falls_back_per_span(monkeypatch: pytest.MonkeyPatch) -> None:
    import fes_pdf_builder.diagrams.math_latex as ml

    monkeypatch.setattr(ml, "make_inline_math_img", lambda *a, **kw: None)
    out = fmt(r"\(p_\theta(x_i)\) tied.", math_mode="latex")
    # Falls back to the legacy Unicode approximation
    assert "<sub>" in out


def test_fmt_legacy_mode_ignores_dollar_math() -> None:
    out = fmt(r"variance scales as $\hat{c}^{2}$ per month.")
    assert "data:image/png;base64," not in out
