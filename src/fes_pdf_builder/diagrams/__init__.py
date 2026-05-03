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

"""Optional diagram + math renderers.

Three opt-in renderers live here:

* :mod:`reporting.diagrams.mermaid` — renders Mermaid ``flowchart`` /
  ``graph`` blocks via GraphViz. Requires the ``dot`` binary on PATH at
  render time; otherwise falls back to a structured text-description box.
* :mod:`reporting.diagrams.sequence` — renders Mermaid ``sequenceDiagram``
  blocks via matplotlib (pure-Python port of the original
  ``tmp/render_sequence.mjs`` Node.js + cairosvg pipeline). Falls back to
  ``None`` when matplotlib is unavailable, in which case
  :func:`make_diagram_box` falls back to a structured text-description box.
* :mod:`reporting.diagrams.math` — renders LaTeX math via matplotlib's
  mathtext engine; falls back to :func:`reporting.text.clean_latex` plain
  text when matplotlib can't parse the expression.
"""

from __future__ import annotations

from .math import make_math_block, render_latex_png
from .mermaid import (
    has_graphviz,
    make_diagram_box,
    mermaid_to_dot,
    render_mermaid_png,
)
from .sequence import parse_sequence, render_sequence_png

__all__ = [
    "has_graphviz",
    "make_diagram_box",
    "make_math_block",
    "mermaid_to_dot",
    "parse_sequence",
    "render_latex_png",
    "render_mermaid_png",
    "render_sequence_png",
]
