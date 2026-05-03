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

"""Matplotlib chart helpers that return ReportLab :class:`Image` flowables.

The helpers below cover the chart shapes needed for structured PDF reports:

* :func:`bar_chart` — single-series bar (e.g. tokens/sec per kv level for
  one model on one instance).
* :func:`grouped_bar_chart` — multi-series bars
  (instance × kv-level / quantization comparison).
* :func:`line_chart` — multi-series line (throughput vs. context length).
* :func:`heatmap` — matrix view (instance × model fits/perf grid).

All helpers honour the brand palette, default to ``layout.frame_width``,
and return either an :class:`reportlab.platypus.Image` (when matplotlib is
available) or a small text-fallback :class:`reportlab.platypus.Paragraph`
(when it is not). This keeps reports importable on minimal environments.

Each chart is also paired with :func:`register_chart_anchor` for callers
that want a TOC "Figures" entry — it returns a
:class:`reporting.flowables.FigureAnchor` flowable that can be prepended
to the chart in the story.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from io import BytesIO

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph

from .branding import Layout, Palette, default_layout, default_palette
from .flowables import FigureAnchor
from .toc import FigureRegistry

__all__ = [
    "bar_chart",
    "gantt_chart",
    "grouped_bar_chart",
    "heatmap",
    "line_chart",
    "multi_panel_timeline",
    "register_chart_anchor",
]


# ─── Internals ────────────────────────────────────────────────────────────────


def _try_matplotlib() -> tuple[object, object] | None:
    """Return ``(plt, mpatches)`` if matplotlib imports successfully."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt

        return plt, mpatches
    except Exception:
        return None


def _fallback(message: str, *, palette: Palette) -> Paragraph:
    """Render a small italic note when matplotlib is unavailable."""
    style = ParagraphStyle(
        "chart_fallback",
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=12,
        textColor=palette.slate,
    )
    return Paragraph(f"[chart unavailable — {message}]", style)


def _hex(color) -> str:
    """Convert a ReportLab :class:`Color` to a ``#RRGGBB`` string for matplotlib."""
    return f"#{int(color.red * 255):02X}{int(color.green * 255):02X}{int(color.blue * 255):02X}"


def _figure_to_rl_image(
    fig,
    *,
    width_pts: float,
    layout: Layout,
) -> RLImage:
    """Render a matplotlib :class:`Figure` and wrap it in :class:`RLImage`."""
    buf = BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=150,
        bbox_inches="tight",
        pad_inches=0.15,
        facecolor="white",
    )
    import matplotlib.pyplot as plt

    plt.close(fig)
    buf.seek(0)

    from reportlab.lib.utils import ImageReader

    ir = ImageReader(buf)
    w_px, h_px = ir.getSize()
    w_pts = w_px * 72.0 / 150
    h_pts = h_px * 72.0 / 150

    target_w = min(width_pts, layout.frame_width)
    if w_pts > target_w:
        scale = target_w / w_pts
        w_pts *= scale
        h_pts *= scale

    buf.seek(0)
    return RLImage(buf, width=w_pts, height=h_pts)


# ─── Anchor helper ───────────────────────────────────────────────────────────


def register_chart_anchor(
    figures: FigureRegistry,
    *,
    chapter_title: str,
    chart_type: str,
    title: str = "",
) -> FigureAnchor:
    """Register a TOC entry for a chart and return its anchor flowable.

    Args:
        figures: Registry to extend.
        chapter_title: Display name for the figure's chapter group.
        chart_type: Short label rendered after the figure number
            (e.g. ``"Bar chart"``, ``"Heatmap"``, ``"Phase Gantt"``).
        title: Optional per-chart caption appended after the type.
    """
    key = figures.register(
        chapter_title=chapter_title,
        diagram_type=chart_type,
        title=title,
    )
    return FigureAnchor(key)


# ─── Charts ──────────────────────────────────────────────────────────────────


def bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    width_pts: float | None = None,
    figure_height_in: float = 3.5,
    fmt_fn: Callable[[float], str] = lambda v: f"{v:.1f}",
    layout: Layout | None = None,
    palette: Palette | None = None,
):
    """Single-series bar chart."""
    layout = layout or default_layout()
    palette = palette or default_palette()
    width_pts = width_pts or layout.frame_width

    mpl = _try_matplotlib()
    if mpl is None:
        return _fallback("matplotlib not installed", palette=palette)
    plt, _ = mpl

    fig, ax = plt.subplots(figsize=(width_pts / 72.0, figure_height_in))
    bar_color = _hex(palette.blue)
    text_color = _hex(palette.text_dark)
    grid_color = _hex(palette.slate_mid)

    bars = ax.bar(
        list(range(len(labels))), list(values), color=bar_color, edgecolor=text_color, linewidth=0.5
    )
    ax.set_xticks(list(range(len(labels))))
    ax.set_xticklabels(list(labels), rotation=30, ha="right", color=text_color, fontsize=9)
    if title:
        ax.set_title(title, color=_hex(palette.navy), fontsize=11, fontweight="bold", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=text_color, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=text_color, fontsize=9)
    ax.tick_params(axis="y", colors=text_color, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=grid_color, alpha=0.4, linestyle="--", linewidth=0.5)

    # Value labels on top of each bar
    for rect, v in zip(bars, values):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            rect.get_height(),
            fmt_fn(v),
            ha="center",
            va="bottom",
            fontsize=8,
            color=text_color,
        )

    return _figure_to_rl_image(fig, width_pts=width_pts, layout=layout)


def grouped_bar_chart(
    groups: Sequence[str],
    series: Mapping[str, Sequence[float]],
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    width_pts: float | None = None,
    figure_height_in: float = 3.8,
    layout: Layout | None = None,
    palette: Palette | None = None,
):
    """Grouped bar chart: one bar group per ``groups`` label, one bar per ``series`` key.

    Args:
        groups: Outer category labels (e.g. instance types).
        series: ``{series_name: [value_per_group]}`` dict (e.g. one entry
            per kv level). Every value list must have the same length as
            ``groups``.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()
    width_pts = width_pts or layout.frame_width

    mpl = _try_matplotlib()
    if mpl is None:
        return _fallback("matplotlib not installed", palette=palette)
    plt, _ = mpl

    fig, ax = plt.subplots(figsize=(width_pts / 72.0, figure_height_in))
    text_color = _hex(palette.text_dark)
    grid_color = _hex(palette.slate_mid)

    series_names = list(series.keys())
    n_series = len(series_names)
    n_groups = len(groups)
    if n_series == 0 or n_groups == 0:
        plt.close(fig)
        return _fallback("no data", palette=palette)

    # Brand-derived palette of up to 6 distinct accents.
    accent_colors = [
        _hex(palette.blue),
        _hex(palette.navy),
        _hex(palette.amber),
        _hex(palette.slate),
        _hex(palette.accent_blue_dark),
        _hex(palette.text_mid),
    ]

    width = 0.8 / n_series
    x_base = list(range(n_groups))
    for si, name in enumerate(series_names):
        offset = (si - (n_series - 1) / 2) * width
        xs = [x + offset for x in x_base]
        ys = list(series[name])
        ax.bar(
            xs,
            ys,
            width=width,
            label=name,
            color=accent_colors[si % len(accent_colors)],
            edgecolor=text_color,
            linewidth=0.4,
        )

    ax.set_xticks(x_base)
    ax.set_xticklabels(list(groups), rotation=30, ha="right", color=text_color, fontsize=9)
    if title:
        ax.set_title(title, color=_hex(palette.navy), fontsize=11, fontweight="bold", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=text_color, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=text_color, fontsize=9)
    ax.tick_params(axis="y", colors=text_color, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=grid_color, alpha=0.4, linestyle="--", linewidth=0.5)
    ax.legend(loc="best", fontsize=8, frameon=False)

    return _figure_to_rl_image(fig, width_pts=width_pts, layout=layout)


def line_chart(
    x: Sequence[float],
    series: Mapping[str, Sequence[float]],
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    log_x: bool = False,
    log_y: bool = False,
    x_tick_labels: Sequence[str] | None = None,
    annotate_points: bool = False,
    annotate_fmt: Callable[[float], str] = lambda v: f"{v:.0f}",
    width_pts: float | None = None,
    figure_height_in: float = 3.6,
    layout: Layout | None = None,
    palette: Palette | None = None,
):
    """Multi-series line chart.

    Args:
        x: Shared x-axis values.
        series: ``{label: y_values}``; each list must align with ``x``.
        log_x / log_y: Use log scale on the corresponding axis.
        x_tick_labels: Optional explicit labels for each ``x`` value
            (e.g. ``["8K", "32K", "64K", "128K", "256K"]`` for context
            sizes). When supplied, matplotlib's auto-generated log-axis
            decade labels are replaced with these — much easier to read
            than ``10⁴`` / ``10⁵``.
        annotate_points: When ``True``, label every data point with its
            y-value (formatted via ``annotate_fmt``).
        annotate_fmt: Formatter for the per-point labels. Default
            ``f"{v:.0f}"`` (no decimals).
    """
    layout = layout or default_layout()
    palette = palette or default_palette()
    width_pts = width_pts or layout.frame_width

    mpl = _try_matplotlib()
    if mpl is None:
        return _fallback("matplotlib not installed", palette=palette)
    plt, _ = mpl

    fig, ax = plt.subplots(figsize=(width_pts / 72.0, figure_height_in))
    text_color = _hex(palette.text_dark)
    grid_color = _hex(palette.slate_mid)

    accent_colors = [
        _hex(palette.blue),
        _hex(palette.amber),
        _hex(palette.navy),
        _hex(palette.slate),
        _hex(palette.accent_blue_dark),
        _hex(palette.text_mid),
    ]
    markers = ["o", "s", "D", "^", "v", ">", "<", "P", "X"]

    x_list = list(x)
    series_items = list(series.items())
    for si, (name, ys) in enumerate(series_items):
        ax.plot(
            x_list,
            list(ys),
            label=name,
            color=accent_colors[si % len(accent_colors)],
            marker=markers[si % len(markers)],
            markersize=5,
            linewidth=1.5,
        )

    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")

    # Explicit x-axis tick labels (e.g. "8K", "32K", ...) — must come
    # AFTER set_xscale, otherwise matplotlib's log-locator clobbers our
    # ticks.
    if x_tick_labels is not None and len(x_tick_labels) == len(x_list):
        ax.set_xticks(x_list)
        ax.set_xticklabels(list(x_tick_labels), rotation=0, fontsize=9, color=text_color)
        # Remove the minor "decade" ticks that matplotlib adds in log scale
        # so they don't clutter the axis under our explicit major ticks.
        ax.minorticks_off()

    if title:
        ax.set_title(title, color=_hex(palette.navy), fontsize=11, fontweight="bold", pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, color=text_color, fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=text_color, fontsize=9)
    ax.tick_params(axis="both", colors=text_color, labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(color=grid_color, alpha=0.4, linestyle="--", linewidth=0.5)
    ax.legend(loc="best", fontsize=8, frameon=False)

    # Per-point value labels.
    if annotate_points:
        for si, (_, ys) in enumerate(series_items):
            color = accent_colors[si % len(accent_colors)]
            for xv, yv in zip(x_list, ys):
                # Skip NaN / non-finite values.
                if yv != yv or yv in (float("inf"), float("-inf")):
                    continue
                ax.annotate(
                    annotate_fmt(yv),
                    xy=(xv, yv),
                    xytext=(0, 7),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=7.5,
                    color=color,
                )

    return _figure_to_rl_image(fig, width_pts=width_pts, layout=layout)


def heatmap(
    rows: Sequence[str],
    cols: Sequence[str],
    matrix: Sequence[Sequence[float | None]],
    *,
    title: str = "",
    cell_fmt: Callable[[float], str] = lambda v: f"{v:.1f}",
    cmap_name: str = "Blues",
    width_pts: float | None = None,
    figure_height_in: float | None = None,
    layout: Layout | None = None,
    palette: Palette | None = None,
):
    """2-D heatmap with cell-level value labels.

    ``matrix[r][c]`` may be ``None`` for missing cells; those render as
    blank slate-light squares.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()
    width_pts = width_pts or layout.frame_width

    mpl = _try_matplotlib()
    if mpl is None:
        return _fallback("matplotlib not installed", palette=palette)
    plt, _ = mpl

    n_rows = len(rows)
    n_cols = len(cols)
    if n_rows == 0 or n_cols == 0:
        return _fallback("no data", palette=palette)

    if figure_height_in is None:
        figure_height_in = max(2.0, 0.35 * n_rows + 1.0)

    fig, ax = plt.subplots(figsize=(width_pts / 72.0, figure_height_in))

    # Fill missing cells with NaN so matplotlib renders them as the cmap's
    # bad-value colour (we'll set that to slate_light below).
    import math

    data: list[list[float]] = []
    for r in range(n_rows):
        row_out: list[float] = []
        for c in range(n_cols):
            v = matrix[r][c] if r < len(matrix) and c < len(matrix[r]) else None
            row_out.append(float(v) if v is not None else math.nan)
        data.append(row_out)

    try:
        # matplotlib >= 3.7
        cmap = plt.colormaps.get_cmap(cmap_name).copy()
    except (AttributeError, KeyError):
        cmap = plt.cm.get_cmap(cmap_name).copy()
    cmap.set_bad(_hex(palette.slate_light))

    im = ax.imshow(data, aspect="auto", cmap=cmap)
    ax.set_xticks(list(range(n_cols)))
    ax.set_yticks(list(range(n_rows)))
    ax.set_xticklabels(
        list(cols), rotation=30, ha="right", fontsize=8, color=_hex(palette.text_dark)
    )
    ax.set_yticklabels(list(rows), fontsize=8, color=_hex(palette.text_dark))
    if title:
        ax.set_title(title, color=_hex(palette.navy), fontsize=11, fontweight="bold", pad=10)

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.ax.tick_params(labelsize=8, colors=_hex(palette.text_dark))

    # Cell labels (skip NaNs)
    for r in range(n_rows):
        for c in range(n_cols):
            v = data[r][c]
            if v != v:  # NaN check
                continue
            ax.text(
                c,
                r,
                cell_fmt(v),
                ha="center",
                va="center",
                fontsize=7,
                color=_hex(palette.white) if v >= im.norm.vmax * 0.6 else _hex(palette.text_dark),
            )

    ax.set_xticks([x - 0.5 for x in range(1, n_cols)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, n_rows)], minor=True)
    ax.grid(which="minor", color=_hex(palette.slate_mid), linewidth=0.4)
    ax.tick_params(which="minor", length=0)

    return _figure_to_rl_image(fig, width_pts=width_pts, layout=layout)


# ─── Phase Gantt ─────────────────────────────────────────────────────────────


# Brand-aligned color used for each manifest status; reports build the
# Gantt chart from the phases list which already carries ``status``.
_STATUS_COLORS_HEX = {
    "SUCCESS": "#2563EB",  # palette.blue
    "RUNNING": "#1D4ED8",  # palette.accent_blue_dark
    "PARTIAL": "#D97706",  # palette.amber
    "COMPLETE_WITH_ERRORS": "#D97706",
    "FAILED": "#B91C1C",  # red-700
    "TIMEOUT": "#B91C1C",
    "OOM": "#B91C1C",
    "SKIPPED": "#94A3B8",  # slate-400
    "CACHED": "#475569",  # slate
}


def gantt_chart(
    phases: Sequence[Mapping[str, object]],
    *,
    title: str = "",
    width_pts: float | None = None,
    figure_height_in: float | None = None,
    log_x: bool = False,
    layout: Layout | None = None,
    palette: Palette | None = None,
):
    """Horizontal-bar Gantt chart of phase timing.

    Args:
        phases: Sequence of dicts with at least ``name`` (str), ``status``
            (str), and ``elapsed_s`` (float). Bars are stacked in source
            order, drawn left-to-right with the cumulative offset on the
            x-axis (``0..total_elapsed``). Bar colors are picked from a
            small status palette.
        title: Optional chart title.
        log_x: Render the x-axis on a log scale (handy when one phase
            dwarfs the others, e.g. perplexity at 10000+ s vs dataset_pull
            at 0.4 s).
    """
    layout = layout or default_layout()
    palette = palette or default_palette()
    width_pts = width_pts or layout.frame_width

    mpl = _try_matplotlib()
    if mpl is None:
        return _fallback("matplotlib not installed", palette=palette)
    plt, _ = mpl

    if not phases:
        return _fallback("no phases", palette=palette)

    n = len(phases)
    if figure_height_in is None:
        figure_height_in = max(2.0, 0.32 * n + 1.0)

    fig, ax = plt.subplots(figsize=(width_pts / 72.0, figure_height_in))
    text_color = _hex(palette.text_dark)
    grid_color = _hex(palette.slate_mid)

    names = [str(p.get("name", "")) for p in phases]
    durations = []
    for p in phases:
        try:
            durations.append(max(0.0, float(p.get("elapsed_s", 0.0) or 0.0)))
        except (TypeError, ValueError):
            durations.append(0.0)

    # If we're log-scale, give zero-duration phases a tiny non-zero so the
    # patch is at least visible.
    if log_x:
        durations = [d if d > 0 else 0.05 for d in durations]

    # Cumulative starts.
    starts: list[float] = []
    acc = 0.0
    for d in durations:
        starts.append(acc)
        acc += d

    statuses = [str(p.get("status", "")).upper() for p in phases]

    # Bottom-up bar positions so phases read top→bottom in source order.
    y_positions = list(range(n - 1, -1, -1))

    for i, (start, dur, status) in enumerate(zip(starts, durations, statuses)):
        color = _STATUS_COLORS_HEX.get(status, _hex(palette.blue))
        ax.barh(
            y_positions[i],
            dur,
            left=start,
            height=0.7,
            color=color,
            edgecolor=text_color,
            linewidth=0.4,
        )

    if log_x:
        ax.set_xscale("symlog", linthresh=0.1)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(names, fontsize=9, color=text_color)
    ax.tick_params(axis="x", colors=text_color, labelsize=9)
    ax.set_xlabel("Cumulative wall-clock (seconds)", color=text_color, fontsize=9)
    if title:
        ax.set_title(title, color=_hex(palette.navy), fontsize=11, fontweight="bold", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", color=grid_color, alpha=0.4, linestyle="--", linewidth=0.5)

    # Build a status legend (only for statuses we actually drew).
    seen = []
    for s in statuses:
        if s not in seen:
            seen.append(s)
    handles = []
    try:
        from matplotlib.patches import Patch

        for s in seen:
            handles.append(
                Patch(
                    facecolor=_STATUS_COLORS_HEX.get(s, _hex(palette.blue)),
                    edgecolor=text_color,
                    linewidth=0.4,
                    label=s.title() if s else "—",
                )
            )
        ax.legend(handles=handles, loc="lower right", fontsize=8, frameon=False)
    except Exception:
        pass

    return _figure_to_rl_image(fig, width_pts=width_pts, layout=layout)


# ─── Multi-panel timeline ───────────────────────────────────────────────────


def multi_panel_timeline(
    x: Sequence[float],
    panels: Sequence[Mapping[str, object]],
    *,
    title: str = "",
    xlabel: str = "elapsed (seconds)",
    phase_boundaries: Sequence[Mapping[str, object]] | None = None,
    width_pts: float | None = None,
    figure_height_in: float | None = None,
    layout: Layout | None = None,
    palette: Palette | None = None,
):
    """Stacked line-chart panels sharing the same x-axis.

    Args:
        x: Shared x values (typically elapsed seconds since run start).
        panels: List of dicts, one per panel, each with:

            * ``label`` (str): y-axis label.
            * ``y`` (Sequence[float]): values aligned with ``x``.
            * ``color`` (str, optional): hex string. Defaults to the
              brand blue / amber / navy / slate cycle by panel index.

        phase_boundaries: Optional list of dicts. Each dict may carry:

            * ``x`` (float): start time in seconds.
            * ``name`` (str): phase name.
            * ``duration`` (float, optional): phase duration in seconds.
              When provided, the chart renders a thin ``phase strip``
              axis ABOVE the panels with one status-coloured horizontal
              bar per phase. Phase names are rendered inside the bar
              when wide enough, or above the strip with a white bbox
              when too narrow. Vertical guide lines at each phase start
              are still drawn through every panel.
            * ``status`` (str, optional): manifest status used to colour
              the strip bar.

            When ``duration`` is missing on every entry, falls back to
            the legacy rotated-label-on-first-panel layout.

    Returns a single ReportLab :class:`Image` flowable.
    """
    layout = layout or default_layout()
    palette = palette or default_palette()
    width_pts = width_pts or layout.frame_width

    mpl = _try_matplotlib()
    if mpl is None:
        return _fallback("matplotlib not installed", palette=palette)
    plt, _ = mpl

    if not panels or not x:
        return _fallback("no data", palette=palette)

    has_strip = bool(phase_boundaries) and any(b.get("duration") for b in (phase_boundaries or []))

    n_panels = len(panels)
    if figure_height_in is None:
        figure_height_in = max(3.5, 1.6 * n_panels + 0.6)
        if has_strip:
            figure_height_in += 0.55

    if has_strip:
        # Reserve a slim top track for the phase strip (~0.55 in / panel
        # ratios are relative; using 0.4 against panel rows of 1.0 keeps
        # the strip narrow but readable).
        height_ratios = [0.4] + [1.0] * n_panels
        fig, all_axes = plt.subplots(
            n_panels + 1,
            1,
            sharex=True,
            figsize=(width_pts / 72.0, figure_height_in),
            gridspec_kw={"height_ratios": height_ratios, "hspace": 0.18},
        )
        strip_ax = all_axes[0]
        axes = list(all_axes[1:])
    else:
        fig, axes = plt.subplots(
            n_panels,
            1,
            sharex=True,
            figsize=(width_pts / 72.0, figure_height_in),
        )
        if n_panels == 1:
            axes = [axes]
        strip_ax = None

    text_color = _hex(palette.text_dark)
    grid_color = _hex(palette.slate_mid)
    accent_colors = [
        _hex(palette.blue),
        _hex(palette.amber),
        _hex(palette.navy),
        _hex(palette.slate),
        _hex(palette.accent_blue_dark),
    ]

    # ── Phase strip ──────────────────────────────────────────────────────
    if has_strip and strip_ax is not None:
        strip_ax.set_ylim(0, 1)
        strip_ax.set_yticks([])
        strip_ax.tick_params(axis="x", colors=text_color, labelsize=8)
        for spine in ("top", "right", "left"):
            strip_ax.spines[spine].set_visible(False)
        strip_ax.spines["bottom"].set_color(grid_color)
        # Track the right-most x so we can size the strip's xlim.
        max_x = 0.0
        # Pre-compute text widths so we can decide "fits inside the bar"
        # vs "label above with bbox". We use the axes-data transform.
        for b in phase_boundaries or []:
            try:
                bx = float(b.get("x", 0.0))
                dur = float(b.get("duration", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            max_x = max(max_x, bx + dur)

        # Threshold for narrow-phase labels: skip phases that are
        # < 1% of the total run AND < 30 seconds — they add visual
        # noise without conveying useful information. Their bar (and
        # the vertical guide lines through every panel) remain visible
        # for context.
        label_min_dur = max(30.0, max_x * 0.01)

        # Stagger rotated above-bar labels at three alternating heights
        # so adjacent narrow-phase labels don't collide.
        stagger_levels = [1.05, 1.55, 2.05]

        narrow_label_idx = 0
        -float("inf")
        for b in phase_boundaries or []:
            try:
                bx = float(b.get("x", 0.0))
                dur = float(b.get("duration", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            name = str(b.get("name", ""))
            status = str(b.get("status", "")).upper()
            color = _STATUS_COLORS_HEX.get(status, _hex(palette.blue))
            # Floor very-thin bars to a tiny minimum so they're visible.
            visible_dur = dur if dur > 0 else max_x * 0.001 if max_x else 0.0
            strip_ax.barh(
                0.5,
                visible_dur,
                left=bx,
                height=0.7,
                color=color,
                edgecolor=text_color,
                linewidth=0.4,
            )
            if not name:
                continue

            # Estimate label width vs bar width to decide where to draw.
            # Heuristic: ~5.5 axes-data points per character at fontsize 7.
            chars_that_fit = int(dur / max(1.0, max_x * 0.012)) if max_x else 0
            if chars_that_fit >= len(name) and dur >= max_x * 0.04:
                # Label fits inside the bar.
                strip_ax.text(
                    bx + dur / 2.0,
                    0.5,
                    name,
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    fontweight="bold",
                    clip_on=True,
                )
            elif dur >= label_min_dur:
                # Stagger above the bar with a white bbox.
                y = stagger_levels[narrow_label_idx % len(stagger_levels)]
                narrow_label_idx += 1
                strip_ax.annotate(
                    name,
                    xy=(bx, 1.0),
                    xytext=(bx, y),
                    textcoords="data",
                    rotation=30,
                    ha="left",
                    va="bottom",
                    fontsize=6.5,
                    color=text_color,
                    bbox=dict(
                        boxstyle="round,pad=0.15",
                        facecolor="white",
                        edgecolor=grid_color,
                        linewidth=0.4,
                        alpha=0.95,
                    ),
                    arrowprops=dict(
                        arrowstyle="-",
                        color=grid_color,
                        linewidth=0.4,
                    ),
                )
            # else: phase is too short to bother labelling — its
            # status-coloured tick remains in the strip and its
            # vertical guide line still threads every panel below.
        # Allow the staggered labels to extend above the strip top.
        strip_ax.set_ylim(0, 2.5)

    # ── Data panels ──────────────────────────────────────────────────────
    for i, panel in enumerate(panels):
        ax = axes[i]
        ys = list(panel.get("y", []))  # type: ignore[arg-type]
        label = str(panel.get("label", ""))
        color = str(panel.get("color", "") or accent_colors[i % len(accent_colors)])
        ax.plot(list(x), ys, color=color, linewidth=1.2)
        ax.set_ylabel(label, color=text_color, fontsize=9)
        ax.tick_params(axis="both", colors=text_color, labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(color=grid_color, alpha=0.35, linestyle="--", linewidth=0.4)

        if phase_boundaries:
            for b in phase_boundaries:
                try:
                    bx = float(b.get("x", 0.0))
                except (TypeError, ValueError):
                    continue
                ax.axvline(bx, color=grid_color, linewidth=0.6, alpha=0.7)

        # Legacy fallback: when the caller only supplied {x, name} with no
        # duration, render the old rotated-label-on-first-panel scheme.
        if i == 0 and phase_boundaries and not has_strip:
            top = ax.get_ylim()[1]
            for b in phase_boundaries:
                try:
                    bx = float(b.get("x", 0.0))
                except (TypeError, ValueError):
                    continue
                name = str(b.get("name", ""))
                if not name:
                    continue
                ax.text(
                    bx,
                    top,
                    name,
                    rotation=45,
                    ha="left",
                    va="bottom",
                    fontsize=6,
                    color=_hex(palette.slate),
                    bbox=dict(
                        boxstyle="round,pad=0.15",
                        facecolor="white",
                        edgecolor="none",
                        alpha=0.85,
                    ),
                )

    axes[-1].set_xlabel(xlabel, color=text_color, fontsize=9)
    if title:
        # Title goes above the phase strip when present, otherwise above
        # the topmost panel.
        fig.suptitle(title, color=_hex(palette.navy), fontsize=11, fontweight="bold")
        fig.subplots_adjust(top=0.93 if has_strip else 0.95)

    return _figure_to_rl_image(fig, width_pts=width_pts, layout=layout)
