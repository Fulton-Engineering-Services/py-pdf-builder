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

"""Mermaid ``flowchart`` / ``graph`` → GraphViz → PNG → ReportLab flowable.

The figure registry is passed in explicitly rather than read from module-level globals.

The entire pipeline is best-effort: if the diagram type is not a Mermaid
flowchart, or if the ``dot`` binary is not on PATH, or if it returns a
non-zero exit code, :func:`make_diagram_box` falls back to a structured
text box that lists the diagram's labelled nodes. This means a report
that uses :func:`make_diagram_box` STILL builds successfully on a machine
without GraphViz installed — it just renders fewer diagrams.

Public surface:

* :func:`mermaid_to_dot` — pure-Python Mermaid → DOT translator.
* :func:`render_mermaid_png` — invoke ``dot`` and return ``(BytesIO, w, h)``.
* :func:`make_diagram_box` — full builder: registers a :class:`FigureAnchor`,
  emits a PNG-rendered diagram (or text-fallback box).
* :func:`has_graphviz` — boolean check used by reports to skip diagrams
  cleanly when ``dot`` is unavailable.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from io import BytesIO

from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, Table, TableStyle

from ..branding import Layout, Palette, default_layout, default_palette
from ..flowables import FigureAnchor
from ..text import esc, fmt
from ..toc import FigureRegistry

__all__ = [
    "has_graphviz",
    "make_diagram_box",
    "mermaid_to_dot",
    "render_mermaid_png",
]


def has_graphviz() -> bool:
    """Return ``True`` iff the ``dot`` binary is on PATH."""
    return shutil.which("dot") is not None


# ─── Mermaid → DOT ───────────────────────────────────────────────────────────


def mermaid_to_dot(mermaid_text: str) -> str | None:
    """Convert a Mermaid flowchart/graph block to GraphViz DOT source.

    Handles: flowchart TB/LR/RL/BT, graph TB/LR, subgraphs, node shapes
    (box, diamond, ellipse), edge labels (``-->|label|``), and chained
    edges (``A --> B --> C``). Multi-line quoted labels are joined with
    ``\\n`` before parsing.

    Returns ``None`` for unsupported diagram types (sequenceDiagram, gantt,
    classDiagram, etc.) so the caller can fall back to the text-description
    box.
    """
    text = mermaid_text.strip()
    lines = text.split("\n")
    first = lines[0].strip().lower()

    if not (first.startswith("flowchart") or first.startswith("graph")):
        return None

    # Direction
    rankdir = "LR"
    for tok, val in [("tb", "TB"), ("td", "TB"), ("lr", "LR"), ("rl", "RL"), ("bt", "BT")]:
        if tok in first:
            rankdir = val
            break

    # Pre-process: join multi-line quoted labels.
    joined: list[str] = []
    buf = ""
    depth = 0
    for line in lines[1:]:
        for ch in line:
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth = max(0, depth - 1)
            buf += ch
        if depth > 0:
            buf += "\\n"
        else:
            joined.append(buf)
            buf = ""
    if buf.strip():
        joined.append(buf)

    def _clean(s: str) -> str:
        s = s.strip().strip('"').strip("'")
        s = s.replace('"', '\\"')
        s = re.sub(r"\s{2,}", " ", s)
        return s

    def _extract_nodes(line: str) -> list[tuple[str, str, str]]:
        found: list[tuple[str, str, str]] = []
        seen: set = set()
        for m in re.finditer(r'(\w+)\["([^"]*)"\]', line):
            found.append((m.group(1), m.group(2), "box"))
            seen.add(m.group(1))
        for m in re.finditer(r'(\w+)\[([^\]"\']+)\]', line):
            if m.group(1) not in seen:
                found.append((m.group(1), m.group(2).strip(), "box"))
                seen.add(m.group(1))
        for m in re.finditer(r"(\w+)\{([^}]+)\}", line):
            found.append((m.group(1), m.group(2).strip(), "diamond"))
        for m in re.finditer(r"(\w+)\(\(([^)]+)\)\)", line):
            found.append((m.group(1), m.group(2).strip(), "ellipse"))
        return found

    nodes: dict = {}
    edges: list[tuple[str, str, str]] = []
    subgraphs: list[tuple[str, str, list[str]]] = []
    cur_sg = False
    cur_sg_id = ""
    cur_sg_lbl = ""
    cur_sg_nds: list[str] = []

    for raw in joined:
        s = raw.strip()
        if not s or s.startswith("%"):
            continue

        m = re.match(r"subgraph\s+(\w+)\s*(?:\[\"?([^\"\]]*)\"?\])?", s, re.I)
        if m:
            cur_sg_id = m.group(1)
            cur_sg_lbl = m.group(2) or cur_sg_id
            cur_sg_nds = []
            cur_sg = True
            continue
        if s.lower() == "end":
            if cur_sg:
                subgraphs.append((cur_sg_id, cur_sg_lbl, cur_sg_nds[:]))
            cur_sg = False
            continue

        for nid, nlbl, nshp in _extract_nodes(s):
            if nid not in nodes:
                nodes[nid] = {"label": nlbl, "shape": nshp}
            if cur_sg and nid not in cur_sg_nds:
                cur_sg_nds.append(nid)

        if re.search(r"--[>-]|==>|-.->|-->", s):
            parts = re.split(r"(--[>-]*|==>|-\.->)", s)
            node_seq: list[str] = []
            elabels: list[str] = []
            for p in parts:
                if re.match(r"^(--[>-]*|==>|-\.->)$", p.strip()):
                    elabels.append("")
                    continue
                lm = re.match(r"\s*\|([^|]*)\|\s*(.*)", p)
                if lm:
                    if elabels:
                        elabels[-1] = lm.group(1).strip()
                    p = lm.group(2)
                nm = re.match(r"\s*(\w+)", p)
                if nm:
                    nid = nm.group(1)
                    node_seq.append(nid)
                    for did, dlbl, dshp in _extract_nodes(p):
                        if did not in nodes:
                            nodes[did] = {"label": dlbl, "shape": dshp}
                    if nid not in nodes:
                        nodes[nid] = {"label": nid, "shape": "box"}
                    if cur_sg and nid not in cur_sg_nds:
                        cur_sg_nds.append(nid)
            for k in range(len(node_seq) - 1):
                el = elabels[k] if k < len(elabels) else ""
                edges.append((node_seq[k], node_seq[k + 1], el))

    dot: list[str] = [
        "digraph G {",
        f"    rankdir={rankdir};",
        '    graph [fontname="Helvetica" bgcolor="white" pad="0.4" nodesep="0.4" ranksep="0.5"];',
        '    node  [shape=box style="filled,rounded" fillcolor="#EFF6FF" '
        'color="#1B2A4A" fontname="Helvetica" fontsize=9 margin="0.15,0.08"];',
        '    edge  [fontname="Helvetica" fontsize=8 color="#475569" arrowsize=0.7];',
        "",
    ]

    sg_all: set = set()
    for sg_id, sg_lbl, sg_nds in subgraphs:
        sg_all |= set(sg_nds)
        dot += [
            f"    subgraph cluster_{sg_id} {{",
            f'        label="{_clean(sg_lbl)}";',
            '        style="filled,rounded";',
            '        fillcolor="#F8FAFC";',
            '        color="#CBD5E1";',
            '        fontname="Helvetica"; fontsize=9;',
        ]
        for nid in sg_nds:
            if nid in nodes:
                info = nodes[nid]
                lbl = _clean(info["label"])
                shp = info.get("shape", "box")
                shp_attr = f" shape={shp}" if shp != "box" else ""
                dot.append(f'        {nid} [label="{lbl}"{shp_attr}];')
        dot.append("    }")

    for nid, info in nodes.items():
        if nid not in sg_all:
            lbl = _clean(info["label"])
            shp = info.get("shape", "box")
            shp_attr = f" shape={shp}" if shp != "box" else ""
            dot.append(f'    {nid} [label="{lbl}"{shp_attr}];')

    dot.append("")
    for fr, to, lbl in edges:
        lbl = _clean(lbl)
        el = f' [label="{lbl}"]' if lbl else ""
        dot.append(f"    {fr} -> {to}{el};")
    dot.append("}")
    return "\n".join(dot)


# ─── PNG render ──────────────────────────────────────────────────────────────


def render_mermaid_png(
    mermaid_text: str,
    *,
    layout: Layout | None = None,
) -> tuple[BytesIO, float, float] | None:
    """Render a Mermaid flowchart to PNG via GraphViz ``dot``.

    Returns ``(BytesIO, width_pts, height_pts)`` scaled to fit inside the
    body frame, or ``None`` if the diagram type is unsupported, ``dot`` is
    missing, or the subprocess fails.
    """
    layout = layout or default_layout()

    dot_src = mermaid_to_dot(mermaid_text)
    if dot_src is None:
        return None
    if not has_graphviz():
        return None

    try:
        result = subprocess.run(
            ["dot", "-Tpng", "-Gdpi=150"],
            input=dot_src.encode("utf-8"),
            capture_output=True,
            timeout=20,
        )
        if result.returncode != 0 or not result.stdout:
            return None

        buf = BytesIO(result.stdout)
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
        return None


# ─── Diagram box ─────────────────────────────────────────────────────────────


def make_diagram_box(
    mermaid_text: str,
    styles: dict,
    *,
    figures: FigureRegistry,
    chapter_title: str,
    diagram_hint: str = "",
    title: str = "",
    layout: Layout | None = None,
    palette: Palette | None = None,
) -> list:
    """Render a Mermaid diagram block.

    Returns a list ``[FigureAnchor, flowable]`` so callers must use
    ``flowables.extend(...)`` rather than ``.append(...)``.

    Args:
        mermaid_text: Raw Mermaid source (without the ```` ```mermaid ```` fences).
        styles: Style dict from :func:`reporting.styles.make_styles`.
        figures: Registry to add a new entry to.
        chapter_title: Display name used in the TOC's Figures section.
        diagram_hint: Free-text caption shown in the fallback box.
        title: Optional per-figure caption appended after the type in
            the TOC's Figures section (``"Figure N \u00b7 Type \u00b7 Title"``).
        layout: Page geometry.
        palette: Brand palette.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()

    first_line = mermaid_text.strip().split("\n")[0].strip().lower()
    if first_line.startswith("flowchart") or first_line.startswith("graph"):
        dtype = "Flowchart"
    elif "sequence" in first_line:
        dtype = "Sequence Diagram"
    elif "gantt" in first_line:
        dtype = "Gantt Chart"
    else:
        dtype = "Diagram"

    fig_key = figures.register(
        chapter_title=chapter_title,
        diagram_type=dtype,
        title=title,
    )
    anchor = FigureAnchor(fig_key)

    result: tuple[BytesIO, float, float] | None = None
    if first_line.startswith("flowchart") or first_line.startswith("graph"):
        result = render_mermaid_png(mermaid_text, layout=layout)
    elif "sequence" in first_line:
        from .sequence import render_sequence_png

        result = render_sequence_png(
            mermaid_text,
            layout=layout,
            palette=palette,
        )

    if result:
        buf, w_pts, h_pts = result
        img = RLImage(buf, width=w_pts, height=h_pts)
        t = Table([[img]], colWidths=[layout.frame_width])
        t.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("BOX", (0, 0), (-1, -1), 0.5, palette.slate_mid),
                ]
            )
        )
        return [anchor, t]

    # ── Fallback text box ────────────────────────────────────────────────
    lines = [ln.strip() for ln in mermaid_text.split("\n") if ln.strip()]
    inner: list = [Paragraph(f"[ {dtype} ]", styles["diagram_hdr"])]
    if diagram_hint:
        inner.append(Paragraph(fmt(diagram_hint), styles["diagram_body"]))

    labels: list[str] = []
    for ln in lines[1:]:
        for f in re.findall(r'["\'"]([^"\'""]{4,60})["\'""]', ln):
            clean = re.sub(r"\\n", " ", f).strip()
            if clean not in labels:
                labels.append(clean)
        for f in re.findall(r"\[([^\]]{4,50})\]", ln):
            if f not in labels:
                labels.append(f.strip())
    if labels:
        snippet = " → ".join(labels[:6])
        if len(labels) > 6:
            snippet += f" … (+{len(labels) - 6} nodes)"
        inner.append(Paragraph(esc(snippet), styles["diagram_body"]))

    t = Table([[inner]], colWidths=[layout.frame_width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette.slate_light),
                ("BOX", (0, 0), (-1, -1), 0.5, palette.slate_mid),
                ("LINEBEFORE", (0, 0), (0, -1), 2, palette.slate),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return [anchor, t]
