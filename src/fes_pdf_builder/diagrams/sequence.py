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

"""Mermaid ``sequenceDiagram`` → matplotlib PNG → ReportLab flowable.

Pure-Python port of :mod:`tmp.render_sequence.mjs`. Replaces the original
Node.js + cairosvg pipeline with a self-contained matplotlib renderer that
takes the same scaling envelope as :func:`render_mermaid_png` and returns
``(BytesIO, w_pts, h_pts)``.

The parser handles:

* ``participant Foo`` and ``participant Foo as "Long Label"`` (and the
  ``actor`` synonym).
* Message arrows: ``->>`` ``-->>`` ``->`` ``-x`` ``--x`` ``--`` (the
  ``--`` prefix produces a dashed arrow).
* ``note over Foo,Bar : text``, ``note right of Foo : text``,
  ``note left of Foo : text``.
* Block constructs: ``loop`` / ``alt`` / ``opt`` / ``par`` / ``critical``
  / ``break`` with optional ``"label"``, ``else "..."`` mid-block, and
  ``end`` close.
* ``autonumber`` is silently ignored (no message numbering yet).
* ``activate`` / ``deactivate`` / ``rect`` / ``links`` are ignored.

The renderer mirrors the JS layout: a two-pass Y-extent computation
followed by a Z-ordered draw — block backgrounds first, lifelines next,
participant boxes, then per-step content (arrows, notes, else dividers),
then the bottom participant boxes. The final image is scaled to fit
inside the body frame (`max_w = layout.frame_width - 12`,
`max_h = layout.main_frame_height - 40`) using the same ``min(...)``
clamp `render_mermaid_png` applies.

Public surface:

* :func:`parse_sequence` — pure parser returning ``(parts, steps)``.
* :func:`render_sequence_png` — matplotlib renderer returning
  ``(BytesIO, w_pts, h_pts)`` or ``None`` if matplotlib isn't available
  or the diagram is empty.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from reportlab.lib.utils import ImageReader

from ..branding import Layout, Palette, default_layout, default_palette

__all__ = [
    "Participant",
    "Step",
    "parse_sequence",
    "render_sequence_png",
]


# ─── Data shapes ─────────────────────────────────────────────────────────────


@dataclass
class Participant:
    """One ``participant`` / ``actor`` declaration."""

    pid: str
    label: str


@dataclass
class Step:
    """One step in the sequence (message, note, or block boundary).

    Fields are typed loosely (``Any``) so a single dataclass can carry the
    union of message/note/block payloads without a class hierarchy.
    """

    kind: str  # "msg" | "note" | "block_open" | "block_else" | "block_close"
    payload: dict[str, Any] = field(default_factory=dict)


# ─── Parser ──────────────────────────────────────────────────────────────────


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _clean_text(s: str) -> str:
    """Strip quotes, normalize <br/>, collapse whitespace."""
    s = _strip_quotes(s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.IGNORECASE)
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def parse_sequence(text: str) -> tuple[list[Participant], list[Step]]:
    """Parse a Mermaid ``sequenceDiagram`` block into participants + steps.

    Returns ``([], [])`` for empty/unparseable input — callers should
    treat that as a signal to fall back to a text box.
    """
    lines = [ln.strip() for ln in text.strip().split("\n")]
    lines = [ln for ln in lines if ln]

    parts: list[Participant] = []
    steps: list[Step] = []
    seen: dict[str, int] = {}

    def _ensure(pid: str) -> None:
        if pid not in seen:
            seen[pid] = len(parts)
            parts.append(Participant(pid=pid, label=pid))

    for line in lines:
        lo = line.lower()
        if lo.startswith("sequencediagram") or lo == "autonumber":
            continue

        # ``participant Foo as "Long Label"`` / ``actor Foo as "Long Label"``
        m = re.match(
            r'^(?:participant|actor)\s+(\w+)\s+as\s+"?([^"]+)"?\s*$',
            line,
            re.IGNORECASE,
        )
        if m:
            pid, label = m.group(1), _clean_text(m.group(2))
            if pid in seen:
                parts[seen[pid]].label = label
            else:
                seen[pid] = len(parts)
                parts.append(Participant(pid=pid, label=label))
            continue

        # ``participant Foo`` / ``actor Foo``
        m = re.match(r"^(?:participant|actor)\s+(\w+)\s*$", line, re.IGNORECASE)
        if m:
            _ensure(m.group(1))
            continue

        # Messages: arrow forms ``->>`` ``-->>`` ``->`` ``-x`` ``--x``
        m = re.match(r"^(\w+)\s*(-->>?|--[xX]|->>|->|-[xX])\s*(\w+)\s*:\s*(.+)$", line)
        if m:
            frm, arrow, to, msg = m.group(1), m.group(2), m.group(3), m.group(4)
            _ensure(frm)
            _ensure(to)
            steps.append(
                Step(
                    kind="msg",
                    payload={
                        "from": frm,
                        "to": to,
                        "text": _clean_text(msg),
                        "dashed": arrow.startswith("--"),
                        "is_cross": arrow.endswith("x") or arrow.endswith("X"),
                    },
                )
            )
            continue

        # Notes: ``note over Foo,Bar : text`` / ``note right of Foo : text``
        m = re.match(
            r"^note\s+(?:over|right of|left of)\s+([\w ,]+)\s*:\s*(.+)$",
            line,
            re.IGNORECASE,
        )
        if m:
            pids = [p for p in re.split(r"[\s,]+", m.group(1)) if p]
            for p in pids:
                _ensure(p)
            steps.append(
                Step(
                    kind="note",
                    payload={"pids": pids, "text": _clean_text(m.group(2))},
                )
            )
            continue

        # Block open: ``loop "label"`` / ``alt "..."`` / ``opt`` / ...
        m = re.match(
            r'^(loop|alt|opt|par|critical|break)\s*"?([^"]*)"?\s*$',
            line,
            re.IGNORECASE,
        )
        if m:
            steps.append(
                Step(
                    kind="block_open",
                    payload={
                        "block_kind": m.group(1).lower(),
                        "label": _clean_text(m.group(2)),
                    },
                )
            )
            continue

        # ``else "label"``
        m = re.match(r'^else\s*"?([^"]*)"?\s*$', line, re.IGNORECASE)
        if m:
            steps.append(
                Step(
                    kind="block_else",
                    payload={"label": _clean_text(m.group(1))},
                )
            )
            continue

        # ``end``
        if lo == "end":
            steps.append(Step(kind="block_close", payload={}))
            continue

        # ``activate`` / ``deactivate`` / ``rect`` / ``links`` — ignored

    return parts, steps


# ─── Renderer ────────────────────────────────────────────────────────────────


# Layout constants in matplotlib data units (also pixels at 1× scaling).
# Tuned to match the original render_sequence.mjs proportions.
_FONT_FAMILY = "DejaVu Sans"
_PART_LABEL_FONT_SZ = 10
_MSG_LABEL_FONT_SZ = 9
_NOTE_FONT_SZ = 8.5
_BLOCK_TAG_FONT_SZ = 7.5
_CHAR_W = 6.2
_PART_H = 30
_PART_PAD = 14
_COL_GAP = 160
_L_MARGIN = 30
_T_MARGIN = 18
_NOTE_WRAP_CHARS = 26


def _wrap_chars(text: str, max_chars: int) -> list[str]:
    """Word-wrap ``text`` to lines of approximately ``max_chars``."""
    if not text:
        return [""]
    out: list[str] = []
    for chunk in textwrap.wrap(
        text, width=max_chars, break_long_words=False, break_on_hyphens=False
    ):
        out.append(chunk)
    return out or [""]


def _step_height(step: Step, msg_wrap: int) -> float:
    """Mirror render_sequence.mjs:stepH() — Y-extent estimation per step."""
    if step.kind == "msg":
        n = len(_wrap_chars(step.payload.get("text", ""), msg_wrap))
        return max(40.0, n * 12 + 28)
    if step.kind == "note":
        n = len(_wrap_chars(step.payload.get("text", ""), _NOTE_WRAP_CHARS))
        return max(34.0, n * 13 + 14)
    return 20.0


def render_sequence_png(
    mermaid_text: str,
    *,
    layout: Layout | None = None,
    palette: Palette | None = None,
) -> tuple[BytesIO, float, float] | None:
    """Render a Mermaid sequence diagram to PNG.

    Returns ``(BytesIO, width_pts, height_pts)`` scaled to fit inside the
    body frame, or ``None`` if matplotlib is unavailable, the parser
    extracted nothing, or rendering raised.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()

    parts, steps = parse_sequence(mermaid_text)
    if not parts and not steps:
        return None

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
    except Exception:
        return None

    # ── Brand colours ────────────────────────────────────────────────────
    def _hx(c) -> str:
        r = int(c.red * 255)
        g = int(c.green * 255)
        b = int(c.blue * 255)
        return f"#{r:02X}{g:02X}{b:02X}"

    navy_hex = _hx(palette.navy)
    blue_hex = _hx(palette.blue)
    blue_dark_hex = _hx(palette.accent_blue_dark)
    blue_xlight_hex = _hx(palette.blue_xlight)
    cover_brand_blue_hex = _hx(palette.cover_brand_blue)
    slate_mid_hex = _hx(palette.slate_mid)
    text_mid_hex = _hx(palette.text_mid)
    amber_light_hex = _hx(palette.amber_light)
    amber_hex = _hx(palette.amber)

    # ── Pass 1: layout participants horizontally ─────────────────────────
    if not parts:
        # Notes-only or blocks-only — synthesize a single phantom participant.
        parts = [Participant(pid="_anon", label="participant")]

    box_widths = [max(len(p.label) * _CHAR_W + _PART_PAD * 2, 72) for p in parts]
    centres: list[float] = []
    cx = _L_MARGIN
    for i, _ in enumerate(parts):
        cx += box_widths[i] / 2
        centres.append(cx)
        cx += _COL_GAP

    svg_w = centres[-1] + box_widths[-1] / 2 + _L_MARGIN if centres else 300.0
    pid_idx = {p.pid: i for i, p in enumerate(parts)}

    # ── Pass 2: compute per-step heights and absolute Y positions ────────
    msg_wrap = max(14, int((_COL_GAP - 10) / _CHAR_W))
    heights = [_step_height(s, msg_wrap) for s in steps]
    total_content_h = float(sum(heights))

    ll_top = _T_MARGIN + _PART_H
    ll_bot = ll_top + total_content_h + 12
    svg_h = ll_bot + _PART_H + _T_MARGIN

    y_pos: list[float] = []
    y = ll_top + 4
    for h in heights:
        y_pos.append(y)
        y += h

    # ── Pass 3: resolve block (loop/alt/...) Y extents ───────────────────
    block_rects: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    for si, s in enumerate(steps):
        if s.kind == "block_open":
            stack.append(
                {
                    "y": y_pos[si],
                    "kind": s.payload.get("block_kind", "loop"),
                    "label": s.payload.get("label", ""),
                }
            )
        elif s.kind == "block_close" and stack:
            blk = stack.pop()
            block_rects.append(
                {
                    "y_start": blk["y"],
                    "y_end": y_pos[si] + heights[si],
                    "kind": blk["kind"],
                    "label": blk["label"],
                }
            )

    # ── Render with matplotlib ───────────────────────────────────────────
    # We treat the layout as a top-down Y axis (Y=0 at the top, Y grows
    # downward) and convert to matplotlib's bottom-up axis at draw time
    # via ``svg_h - y``. fig sized so 1 data-unit ≈ 1 pixel at 150 DPI.
    try:
        fig_w_in = svg_w / 100.0  # ~ "natural" inches at 100 dpi feel
        fig_h_in = svg_h / 100.0
        fig, ax = plt.subplots(figsize=(fig_w_in, fig_h_in))
        ax.set_xlim(0, svg_w)
        ax.set_ylim(0, svg_h)
        ax.invert_yaxis()
        ax.set_axis_off()
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        # Block backgrounds (drawn first so everything else sits on top).
        for blk in block_rects:
            bh = blk["y_end"] - blk["y_start"]
            ax.add_patch(
                mpatches.FancyBboxPatch(
                    (_L_MARGIN / 2, blk["y_start"]),
                    svg_w - _L_MARGIN,
                    bh,
                    boxstyle="round,pad=0,rounding_size=3",
                    linewidth=0.8,
                    edgecolor=cover_brand_blue_hex,
                    facecolor=blue_xlight_hex,
                    linestyle=(0, (5, 3)),
                )
            )
            tag = (blk["kind"] or "loop").upper()[:6]
            ax.add_patch(
                mpatches.Rectangle(
                    (_L_MARGIN / 2, blk["y_start"]),
                    40,
                    13,
                    linewidth=0,
                    facecolor=blue_hex,
                )
            )
            ax.text(
                _L_MARGIN / 2 + 4,
                blk["y_start"] + 9,
                tag,
                fontsize=_BLOCK_TAG_FONT_SZ,
                fontweight="bold",
                color="white",
                family=_FONT_FAMILY,
                va="center",
            )
            if blk["label"]:
                ax.text(
                    _L_MARGIN / 2 + 46,
                    blk["y_start"] + 9,
                    f"[{blk['label']}]",
                    fontsize=_BLOCK_TAG_FONT_SZ,
                    color=blue_dark_hex,
                    family=_FONT_FAMILY,
                    va="center",
                )

        # Lifelines (dashed slate down the centre of each participant).
        for i, _ in enumerate(parts):
            ax.plot(
                [centres[i], centres[i]],
                [ll_top, ll_bot],
                linewidth=1.5,
                color=slate_mid_hex,
                linestyle=(0, (5, 4)),
            )

        # Top participant boxes.
        for i, p in enumerate(parts):
            bx = centres[i] - box_widths[i] / 2
            ax.add_patch(
                mpatches.FancyBboxPatch(
                    (bx, _T_MARGIN),
                    box_widths[i],
                    _PART_H,
                    boxstyle="round,pad=0,rounding_size=4",
                    linewidth=0,
                    facecolor=navy_hex,
                )
            )
            ax.text(
                centres[i],
                _T_MARGIN + _PART_H / 2,
                p.label,
                fontsize=_PART_LABEL_FONT_SZ,
                fontweight="bold",
                color="white",
                family=_FONT_FAMILY,
                ha="center",
                va="center",
            )

        # Per-step content (arrows / notes / else dividers).
        for si, s in enumerate(steps):
            y0 = y_pos[si]
            h = heights[si]

            if s.kind == "msg":
                fi = pid_idx.get(s.payload.get("from", ""), 0)
                ti = pid_idx.get(s.payload.get("to", ""), 0)
                x1 = centres[fi] if fi < len(centres) else centres[0]
                x2 = centres[ti] if ti < len(centres) else centres[0]
                is_self = fi == ti
                ay = y0 + h - 14
                lines = _wrap_chars(s.payload.get("text", ""), msg_wrap)
                ty = ay - len(lines) * 12 - 3
                tx = x1 + 30 if is_self else (x1 + x2) / 2
                for li, ltext in enumerate(lines):
                    ax.text(
                        tx,
                        ty + li * 12,
                        ltext,
                        fontsize=_MSG_LABEL_FONT_SZ,
                        color=text_mid_hex,
                        family=_FONT_FAMILY,
                        ha="center",
                        va="center",
                    )
                arrow_kwargs = dict(
                    arrowstyle="-|>",
                    mutation_scale=12,
                    linewidth=1.5,
                    color=navy_hex,
                )
                if s.payload.get("dashed"):
                    arrow_kwargs["linestyle"] = (0, (5, 3))
                if is_self:
                    rx = x1 + 38
                    ax.plot(
                        [x1, rx, rx, x1],
                        [ay - 7, ay - 7, ay + 7, ay + 7],
                        linewidth=1.5,
                        color=navy_hex,
                        linestyle=(0, (5, 3)) if s.payload.get("dashed") else "-",
                    )
                    ax.annotate(
                        "",
                        xy=(x1, ay + 7),
                        xytext=(x1 + 8, ay + 7),
                        arrowprops=dict(
                            arrowstyle="-|>",
                            mutation_scale=12,
                            linewidth=1.5,
                            color=navy_hex,
                        ),
                    )
                else:
                    ax.annotate(
                        "",
                        xy=(x2, ay),
                        xytext=(x1, ay),
                        arrowprops=arrow_kwargs,
                    )

            elif s.kind == "note":
                pids = s.payload.get("pids") or []
                idxs = [pid_idx[p] for p in pids if p in pid_idx]
                if not idxs:
                    idxs = [0]
                min_c = min(centres[i] for i in idxs)
                max_c = max(centres[i] for i in idxs)
                lines = _wrap_chars(s.payload.get("text", ""), _NOTE_WRAP_CHARS)
                nw = max(
                    max_c - min_c + 50,
                    max((len(ln) * _CHAR_W for ln in lines), default=0) + 24,
                    90,
                )
                nx = (min_c + max_c) / 2 - nw / 2
                ny = y0 + 2
                nh = max(28, len(lines) * 13 + 10)
                ax.add_patch(
                    mpatches.FancyBboxPatch(
                        (nx, ny),
                        nw,
                        nh,
                        boxstyle="round,pad=0,rounding_size=3",
                        linewidth=1,
                        edgecolor=amber_hex,
                        facecolor=amber_light_hex,
                    )
                )
                for li, ltext in enumerate(lines):
                    ax.text(
                        nx + nw / 2,
                        ny + 9 + li * 13,
                        ltext,
                        fontsize=_NOTE_FONT_SZ,
                        fontstyle="italic",
                        color="#92400E",  # amber-900; harmonizes with palette.amber
                        family=_FONT_FAMILY,
                        ha="center",
                        va="center",
                    )

            elif s.kind == "block_else":
                ax.plot(
                    [_L_MARGIN / 2, svg_w - _L_MARGIN / 2],
                    [y0 + h / 2, y0 + h / 2],
                    linewidth=0.7,
                    color=blue_hex,
                    linestyle=(0, (4, 3)),
                )
                if s.payload.get("label"):
                    ax.text(
                        _L_MARGIN / 2 + 4,
                        y0 + h / 2,
                        f"[{s.payload['label']}]",
                        fontsize=_BLOCK_TAG_FONT_SZ,
                        color=blue_dark_hex,
                        family=_FONT_FAMILY,
                        va="center",
                    )

        # Bottom participant boxes (mirror the top so each lifeline reads
        # cleanly even on long diagrams).
        for i, p in enumerate(parts):
            bx = centres[i] - box_widths[i] / 2
            ax.add_patch(
                mpatches.FancyBboxPatch(
                    (bx, ll_bot),
                    box_widths[i],
                    _PART_H,
                    boxstyle="round,pad=0,rounding_size=4",
                    linewidth=0,
                    facecolor=navy_hex,
                )
            )
            ax.text(
                centres[i],
                ll_bot + _PART_H / 2,
                p.label,
                fontsize=_PART_LABEL_FONT_SZ,
                fontweight="bold",
                color="white",
                family=_FONT_FAMILY,
                ha="center",
                va="center",
            )

        buf = BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=150,
            bbox_inches="tight",
            pad_inches=0.06,
            facecolor="white",
        )
        plt.close(fig)
        buf.seek(0)

        ir = ImageReader(buf)
        w_px, h_px = ir.getSize()
        w_pts = w_px * 72.0 / 150
        h_pts = h_px * 72.0 / 150

        max_w = layout.frame_width - 12
        max_h = layout.main_frame_height - 40
        scale = min(
            max_w / w_pts if w_pts > max_w else 1.0,
            max_h / h_pts if h_pts > max_h else 1.0,
        )
        w_pts *= scale
        h_pts *= scale

        buf.seek(0)
        return buf, w_pts, h_pts

    except Exception:
        try:
            import matplotlib.pyplot as plt

            plt.close("all")
        except Exception:
            pass
        return None
