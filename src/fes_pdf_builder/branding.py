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

"""Brand palette + page geometry for Fulton Engineering Services LLC reports.

Two dataclasses are exposed:

* :class:`Palette` — every named brand colour, as ReportLab :class:`Color`
  instances (so they can be passed directly to ``setFillColor``,
  ``ParagraphStyle(textColor=...)``, etc.).
* :class:`Layout`  — page size, margins, and reserved header/footer bands.
  Page-template painters and frame builders read these values so the report
  driver can pass a different layout (e.g. landscape, A4) without forking
  the rest of the package.

The :func:`default_palette` and :func:`default_layout` helpers return the
canonical FES values; reports may construct their own ``Palette`` /
``Layout`` instances to override individual fields.
"""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

__all__ = ["Layout", "Palette", "default_layout", "default_palette"]


@dataclass(frozen=True)
class Palette:
    """Branded colour palette.

    All values are :class:`reportlab.lib.colors.Color` instances.

    * ``navy``         → primary brand fill (covers, headers, table headings)
    * ``blue``         → primary accent (links, sidebar borders, accents)
    * ``blue_light``   → ~10% accent fill (sidebar borders / outlines)
    * ``blue_xlight``  → ~5% accent fill (sidebar backgrounds)
    * ``slate``        → secondary text / dividers
    * ``slate_light`` → table zebra rows, math block backgrounds
    * ``slate_mid``   → table grids, borders
    * ``code_bg``      → dark code-block background
    * ``code_fg``      → light code-block foreground
    * ``amber_light`` / ``amber`` → sequence-diagram notes (legacy; kept for
      forward-compatibility even though the sequence renderer was not
      extracted)
    * ``text_dark`` / ``text_mid`` → primary/secondary body copy
    * ``white`` / ``black`` → convenience constants
    """

    navy: colors.Color = colors.HexColor("#1B2A4A")
    blue: colors.Color = colors.HexColor("#2563EB")
    blue_light: colors.Color = colors.HexColor("#DBEAFE")
    blue_xlight: colors.Color = colors.HexColor("#EFF6FF")
    slate: colors.Color = colors.HexColor("#475569")
    slate_light: colors.Color = colors.HexColor("#F1F5F9")
    slate_mid: colors.Color = colors.HexColor("#CBD5E1")
    code_bg: colors.Color = colors.HexColor("#475569")  # slate for bg
    code_fg: colors.Color = colors.white  # white fg
    amber_light: colors.Color = colors.HexColor("#FFFBEB")
    amber: colors.Color = colors.HexColor("#D97706")
    text_dark: colors.Color = colors.HexColor("#0F172A")
    text_mid: colors.Color = colors.HexColor("#334155")
    cover_brand_blue: colors.Color = colors.HexColor("#93C5FD")
    cover_sub_blue: colors.Color = colors.HexColor("#BFDBFE")
    accent_blue_dark: colors.Color = colors.HexColor("#1D4ED8")
    white: colors.Color = colors.white
    black: colors.Color = colors.black


@dataclass(frozen=True)
class Layout:
    """Page geometry.

    All values are in PDF points (1/72 inch).

    Attributes:
        page_width: Page width in points.
        page_height: Page height in points.
        margin: Uniform left/right/top/bottom margin in points.
        header_height: Reserved height above the body frame for the running
            header (separator line + chapter / brand text).
        footer_height: Reserved height below the body frame for the running
            footer (separator line + document title + page number).
    """

    page_width: float = letter[0]  # 612 pts
    page_height: float = letter[1]  # 792 pts
    margin: float = 0.6 * inch
    # ``header_height`` reserves a small gap between the running-header
    # line (drawn at ~y=733 pts, just below the top margin) and the top
    # of the body frame. The 8-pt header text sits above the line and
    # only needs a few points of breathing room below the line, so we
    # default to 0.05 inch (~3.6 pts).
    header_height: float = 0.05 * inch
    footer_height: float = 0.35 * inch

    @property
    def frame_width(self) -> float:
        """Width of the body frame (page width minus left+right margins)."""
        return self.page_width - 2 * self.margin

    @property
    def main_frame_height(self) -> float:
        """Height of the main-template body frame (page minus margins, header, footer)."""
        return self.page_height - 2 * self.margin - self.header_height - self.footer_height

    @property
    def cover_frame_height(self) -> float:
        """Height of the cover/part-template body frame (margins only)."""
        return self.page_height - 2 * self.margin


def default_palette() -> Palette:
    """Return the canonical Fulton Engineering Services palette."""
    return Palette()


def default_layout() -> Layout:
    """Return the canonical letter-size, 0.9-inch-margin layout."""
    return Layout()
