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

"""Text helpers: XML-escape, inline-markdown formatter, LaTeX cleanup, math.

Public functions:

* :func:`esc` — XML-escape ``&``, ``<``, ``>`` for safe ReportLab paragraph
  content.
* :func:`fmt` — apply inline-markdown formatting (``**bold**``, ``_italic_``,
  ``` `code` ```, ``\\(math\\)`` placeholders, link-text extraction) and
  return a ReportLab-safe XML string.  Accepts an optional ``link_color``
  override (default: FES brand blue ``#2563EB``).
* :func:`safe_para` — :class:`Paragraph` constructor with a graceful
  fallback when the XML parser rejects markup we couldn't predict.
* :func:`clean_latex` — collapse a LaTeX expression to readable plain text
  (used as a fallback when matplotlib mathtext can't parse a formula).
* :func:`format_inline_math` — turn ``\\(...\\)`` inline math into ReportLab
  paragraph XML with ``<sub>`` / ``<super>`` tags.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from reportlab.platypus import Paragraph

__all__ = ["clean_latex", "esc", "fmt", "format_inline_math", "safe_para"]


# Default brand-blue link colour (matches ``branding.default_palette().blue``).
# Hard-coded here so :func:`fmt` stays a pure ``str -> str`` function with no
# palette dependency unless an override is explicitly passed.
_DEFAULT_LINK_COLOR = "#2563EB"


def esc(text: str) -> str:
    """XML-escape ``&``, ``<``, ``>``."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(
    text: str,
    *,
    link_resolver: Callable[[str], str | None] | None = None,
    link_color: str | None = None,
) -> str:
    """Apply inline markdown formatting and return ReportLab-safe XML markup.

    Processing order:
      0. Extract ``\\(...\\)`` inline math spans BEFORE XML-escaping so LaTeX
         backslashes/braces never reach the XML layer.
      0b. Extract bare ``<https://...>`` URLs BEFORE XML-escaping so the
          angle brackets survive (otherwise ``esc`` rewrites them to
          ``&lt;``/``&gt;`` and the bare-URL regex never matches).
      1. XML-escape the remaining text.
      2. Protect backtick code spans with placeholders.
      3. Apply bold / bold-italic / italic markdown rules.
      4. Convert ``[text](url)`` markdown links to styled, clickable
         ``<a href="url">…</a>`` anchors. The display text already carries
         any bold/italic markup applied in step 3.
      5. Restore math, code, and bare-URL placeholders (bare URLs become
         the same kind of styled anchor).

    Args:
        text: Inline-markdown source string.
        link_resolver: Optional callable consulted for every ``[text](url)``
            link. When it returns a non-empty PDF anchor key, the link is
            rendered as an internal navigation anchor (brand-blue, no
            underline) targeting ``#<key>``. Returning ``None`` falls
            through to the default behaviour (scheme URLs become external
            anchors; everything else is stripped to display text). The
            resolver is responsible for parsing the URL it receives —
            relative paths, ``#fragment``-only forms, and absolute
            schemes are all delivered verbatim.
        link_color: Hex colour string for hyperlinks (e.g. ``"#2563EB"``).
            Defaults to the FES brand blue.
    """
    _link_color = link_color or _DEFAULT_LINK_COLOR
    _math_spans: list[str] = []

    def _save_math(m: re.Match[str]) -> str:
        idx = len(_math_spans)
        _math_spans.append(format_inline_math(m.group(0)))
        return f"\x00M{idx}\x00"

    text = re.sub(r"\\\(.+?\\\)", _save_math, text, flags=re.DOTALL)

    # 0b. Extract bare-URL form ``<https://...>`` BEFORE escaping. The
    # angle brackets must be literal ``<`` ``>`` for the regex to match;
    # ``esc`` (next step) rewrites them to ``&lt;``/``&gt;``.
    _bare_url_spans: list[str] = []

    def _save_bare(m: re.Match[str]) -> str:
        idx = len(_bare_url_spans)
        _bare_url_spans.append(m.group(1))
        return f"\x00U{idx}\x00"

    text = re.sub(r"<(https?://[^>]+)>", _save_bare, text)

    text = esc(text)

    _code_spans: list[str] = []

    def _save_code(m: re.Match[str]) -> str:
        idx = len(_code_spans)
        _code_spans.append(f'<font name="Courier">{m.group(1)}</font>')
        return f"\x00C{idx}\x00"

    text = re.sub(r"`([^`]+?)`", _save_code, text)

    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*\n]{1,100}?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<![a-zA-Z0-9_])_([^_\n]{1,80}?)_(?![a-zA-Z0-9_])", r"<i>\1</i>", text)

    # Markdown links ``[text](url)`` become styled clickable anchors when
    # the URL has an absolute scheme (``http://``, ``https://``,
    # ``mailto:``, ``ftp://``, ...). Schema-less / anchor-only forms
    # (``#section-id``, ``./relative/path``) are stripped down to display
    # text instead — ReportLab would otherwise treat ``#xxx`` as an
    # internal PDF bookmark and fail at save time when the destination
    # doesn't exist.
    #
    # When a ``link_resolver`` is supplied, it gets first refusal: if it
    # returns a non-empty key, render an INTERNAL anchor (no underline)
    # targeting ``#<key>``.
    def _render_link(m: re.Match[str]) -> str:
        url: str = m.group(2).strip()
        display: str = m.group(1)
        if link_resolver is not None:
            key = link_resolver(url)
            if key:
                return f'<a href="#{key}"><font color="{_link_color}">{display}</font></a>'
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", url):
            return f'<a href="{url}"><font color="{_link_color}"><u>{display}</u></font></a>'
        return display

    text = re.sub(r"\[([^\]]+)\]\(([^\)]*)\)", _render_link, text)

    for idx, cs in enumerate(_code_spans):
        text = text.replace(f"\x00C{idx}\x00", cs)
    for idx, ms in enumerate(_math_spans):
        text = text.replace(f"\x00M{idx}\x00", ms)
    for idx, url in enumerate(_bare_url_spans):
        safe_url = esc(url)
        text = text.replace(
            f"\x00U{idx}\x00",
            f'<a href="{safe_url}"><font color="{_link_color}"><u>{safe_url}</u></font></a>',
        )
    return text


def safe_para(text: str, style: object) -> Paragraph:
    """Construct a :class:`Paragraph` with a fallback for malformed XML."""
    try:
        return Paragraph(text, style)
    except Exception:
        cleaned = re.sub(r"<[^>]+>", "", text)
        try:
            return Paragraph(esc(cleaned), style)
        except Exception:
            return Paragraph("[formatting error]", style)


def clean_latex(text: str) -> str:
    """Convert LaTeX math notation to readable plain text.

    Used as a fallback when matplotlib mathtext can't parse a formula.
    Best-effort: not all LaTeX features round-trip; the goal is
    ``"\\frac{a}{b}"`` → ``"(a / b)"`` rather than literal backslashes.
    """
    text = text.strip()
    # Remove display math delimiters
    text = re.sub(r"\\\[|\\\]", "", text)
    # Fractions
    text = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1 / \2)", text)
    # Text command
    text = re.sub(r"\\text\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\mathbf\{([^}]*)\}", r"\1", text)
    # Subscript / superscript braces
    text = re.sub(r"_\{([^}]*)\}", r"_\1", text)
    text = re.sub(r"\^\{([^}]*)\}", r"^\1", text)
    # Greek
    for g, u in [
        ("\\theta", "θ"),
        ("\\alpha", "α"),
        ("\\beta", "β"),
        ("\\gamma", "γ"),
        ("\\delta", "δ"),
        ("\\epsilon", "ε"),
        ("\\lambda", "λ"),
        ("\\mu", "μ"),
        ("\\nu", "ν"),
        ("\\sigma", "σ"),
        ("\\tau", "τ"),
        ("\\phi", "φ"),
        ("\\omega", "ω"),
        ("\\Sigma", "Σ"),
        ("\\Pi", "Π"),
        ("\\Delta", "Δ"),
    ]:
        text = text.replace(g, u)
    # Operators
    for k, v in [
        ("\\sum", "Σ"),
        ("\\prod", "Π"),
        ("\\exp", "exp"),
        ("\\log", "log"),
        ("\\ln", "ln"),
        ("\\max", "max"),
        ("\\min", "min"),
        ("\\arg", "arg"),
        ("\\times", "×"),
        ("\\cdot", "·"),
        ("\\mid", "|"),
        ("\\leq", "≤"),
        ("\\geq", "≥"),
        ("\\approx", "≈"),
        ("\\neq", "≠"),
        ("\\infty", "∞"),
        ("\\sqrt", "√"),
        ("\\rightarrow", "→"),
        ("\\leftarrow", "←"),
        ("\\Rightarrow", "⇒"),
        ("\\in", "∈"),
        ("\\notin", "∉"),
        ("\\partial", "∂"),
        ("\\nabla", "∇"),
    ]:
        text = text.replace(k, v)
    # Remove spacing/grouping commands
    text = re.sub(r"\\[,;! ]", " ", text)
    text = re.sub(r"\\left|\\right", "", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    # Clean up braces
    text = text.replace("{", "").replace("}", "")
    # Collapse whitespace
    text = re.sub(r" {2,}", " ", text).strip()
    return text


_GREEK_TABLE: list[tuple[str, str]] = [
    ("\\theta", "θ"),
    ("\\alpha", "α"),
    ("\\beta", "β"),
    ("\\gamma", "γ"),
    ("\\delta", "δ"),
    ("\\epsilon", "ε"),
    ("\\varepsilon", "ε"),
    ("\\zeta", "ζ"),
    ("\\eta", "η"),
    ("\\iota", "ι"),
    ("\\kappa", "κ"),
    ("\\lambda", "λ"),
    ("\\mu", "μ"),
    ("\\nu", "ν"),
    ("\\xi", "ξ"),
    ("\\pi", "π"),
    ("\\rho", "ρ"),
    ("\\sigma", "σ"),
    ("\\tau", "τ"),
    ("\\upsilon", "υ"),
    ("\\phi", "φ"),
    ("\\varphi", "φ"),
    ("\\chi", "χ"),
    ("\\psi", "ψ"),
    ("\\omega", "ω"),
    ("\\Gamma", "Γ"),
    ("\\Delta", "Δ"),
    ("\\Theta", "Θ"),
    ("\\Lambda", "Λ"),
    ("\\Xi", "Ξ"),
    ("\\Pi", "Π"),
    ("\\Sigma", "Σ"),
    ("\\Upsilon", "Υ"),
    ("\\Phi", "Φ"),
    ("\\Psi", "Ψ"),
    ("\\Omega", "Ω"),
]

_OPERATOR_TABLE: list[tuple[str, str]] = [
    ("\\sum", "Σ"),
    ("\\prod", "Π"),
    ("\\exp", "exp"),
    ("\\log", "log"),
    ("\\ln", "ln"),
    ("\\max", "max"),
    ("\\min", "min"),
    ("\\arg", "arg"),
    ("\\times", "×"),
    ("\\cdot", "·"),
    ("\\mid", "|"),
    ("\\leq", "≤"),
    ("\\geq", "≥"),
    ("\\approx", "≈"),
    ("\\neq", "≠"),
    ("\\infty", "∞"),
    ("\\sqrt", "√"),
    ("\\rightarrow", "→"),
    ("\\leftarrow", "←"),
    ("\\Rightarrow", "⇒"),
    ("\\in", "∈"),
    ("\\notin", "∉"),
    ("\\partial", "∂"),
    ("\\nabla", "∇"),
]


def format_inline_math(raw: str) -> str:
    r"""Convert a ``\(...\)`` inline-math span to ReportLab paragraph XML.

    Emits ``<sub>`` and ``<super>`` tags so subscripted expressions like
    ``p_θ``, ``x_i``, and ``x_{<i}`` render with proper typographic
    subscripting rather than flat text.

    Pipeline:
      1. Greek / operator symbol substitution (longest-match first)
      2. ``\\frac``, ``\\text``, ``\\mathrm`` structural transforms
      3. Remaining backslash command removal
      4. Extract ``_{...}``/``^{...}`` and ``_x``/``^x`` into byte-safe placeholders
      5. XML-escape body (placeholders use ``\\x01`` — not an XML special char)
      6. Restore placeholders as ``<sub>``/``<super>`` tags with escaped content
      7. Wrap in italic Courier
    """
    inner = re.sub(r"^\\\(|\\\)$", "", raw).strip()

    # Longest-match first avoids prefix collisions (e.g. \phi before \p)
    for k, v in sorted(_GREEK_TABLE, key=lambda x: -len(x[0])):
        inner = inner.replace(k, v)
    for k, v in sorted(_OPERATOR_TABLE, key=lambda x: -len(x[0])):
        inner = inner.replace(k, v)

    # Structural transforms
    inner = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1 / \2)", inner)
    inner = re.sub(r"\\(?:text|mathrm|mathbf|mathit|operatorname)\{([^}]*)\}", r"\1", inner)
    inner = re.sub(r"\\[,;!: ]", " ", inner)
    inner = re.sub(r"\\(?:left|right|bigl|bigr|Bigl|Bigr)", "", inner)
    inner = re.sub(r"\\[a-zA-Z]+", "", inner)

    # Sub/super extraction: byte-safe placeholders BEFORE XML-escaping so
    # brace content (including '<' in x_{<i}) never corrupts the XML parser.
    _spans: list[tuple[str, str]] = []

    def _save(tag: str, content: str) -> str:
        idx = len(_spans)
        _spans.append((tag, content))
        return f"\x01S{idx}\x01"

    # Braced forms first (handles multi-char and special chars like <i)
    inner = re.sub(r"_\{([^}]*)\}", lambda m: _save("sub", m.group(1)), inner)
    inner = re.sub(r"\^\{([^}]*)\}", lambda m: _save("super", m.group(1)), inner)

    # Single-char forms: letter, digit, or Greek/math Unicode codepoint
    _SC = r"[a-zA-Z0-9\u0370-\u03FF\u2200-\u22FF]"
    inner = re.sub(rf"_({_SC})", lambda m: _save("sub", m.group(1)), inner)
    inner = re.sub(rf"\^({_SC})", lambda m: _save("super", m.group(1)), inner)

    # Clean up stray braces and whitespace
    inner = inner.replace("{", "").replace("}", "")
    inner = re.sub(r" {2,}", " ", inner).strip()

    # XML-escape body
    inner = inner.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Restore sub/super tags with escaped content
    for idx, (tag, content) in enumerate(_spans):
        safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        inner = inner.replace(f"\x01S{idx}\x01", f"<{tag}>{safe}</{tag}>")

    return f'<i><font name="Courier">{inner}</font></i>'
