"""
Brexit synthetic control – 4-panel figure (a–d)
Reads pre-computed .dta results from Stata and plots:
  a: EU  · Total publications
  b: EU  · Intl. publication ratio
  c: UK  · Total publications
  d: UK  · Intl. publication ratio
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import glob
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import pyreadstat

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = str(CODE / "Brexit-stata_external_try")
TP   = f"{BASE}/total_publications"
IR   = f"{BASE}/intl_ratio"
OUT  = f"{BASE}/figure1_brexit_panels.pdf"

TREAT_YEAR = 2016
EU_COLOR   = "#00339A"   # RGB(0, 51, 154)
UK_COLOR   = "#C9062B"   # RGB(201, 6, 43)

# Nature-style font: Arial preferred, fallback to Helvetica / DejaVu Sans
mpl.rcParams.update({
    "font.family":      "sans-serif",
    "font.sans-serif":  ["Arial", "Helvetica Neue", "Helvetica", "DejaVu Sans"],
    "font.size":        8,
    "axes.linewidth":   0.75,
    "pdf.fonttype":     42,   # embed fonts as TrueType (required by Nature)
    "ps.fonttype":      42,
})


# ── Helpers ────────────────────────────────────────────────────────────────────
def load(path):
    df, _ = pyreadstat.read_dta(path)
    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)
    return df.sort_values("Year").reset_index(drop=True)


def k_fmt(x, _):
    """Format axis labels: 10000 → '10k', 1500 → '1.5k'."""
    if x >= 1000:
        v = x / 1000
        return f"{int(v)}k" if v == int(v) else f"{v:.0f}k"
    return str(int(x))


# ── Load results ───────────────────────────────────────────────────────────────
eu_tp = load(f"{TP}/eu_synth_results.dta")
uk_tp = load(f"{TP}/uk_synth_results.dta")
eu_ir = load(f"{IR}/eu_synth_results.dta")
uk_ir = load(f"{IR}/uk_synth_results.dta")

# ── Compute ATT (mean post-treatment gap) ─────────────────────────────────────
def att_pct(df, gap_col):
    return df.loc[df["Year"] >= TREAT_YEAR, gap_col].mean()

eu_att_tp = att_pct(eu_tp, "eu_gap_pct")
uk_att_tp = att_pct(uk_tp, "uk_gap_pct")
eu_att_ir = att_pct(eu_ir, "eu_gap") * 100  # convert ratio → %
uk_att_ir = att_pct(uk_ir, "uk_gap") * 100


# ── Draw one panel ─────────────────────────────────────────────────────────────
def draw_panel(ax, df, act_col, syn_col,
               color, ylabel, panel_letter, panel_title,
               att_pct_val,
               yformatter=None, y_lo=None, y_hi=None,
               event_label="Brexit (2016)"):

    years = df["Year"].values
    actual    = df[act_col].values
    synthetic = df[syn_col].values

    min_yr = int(years.min())
    max_yr = int(years.max())

    # ── post-treatment shading ────────────────────────────────────────────────
    ax.axvspan(TREAT_YEAR, max_yr + 0.5, color="#E8E8E8", lw=0, zorder=0)

    # ── treatment vertical line ───────────────────────────────────────────────
    ax.axvline(TREAT_YEAR, color="#555555", lw=0.9, ls="--", zorder=2)

    # ── synthetic line: dashed, smaller solid dots, slightly lighter ──────────
    syn_color = color + "BB"   # add slight transparency via hex alpha
    ax.plot(years, synthetic, ls="--", color=syn_color, lw=1.4,
            marker="o", markersize=3.0, markerfacecolor=syn_color,
            markeredgewidth=0, zorder=4, label="Synthetic counterfactual")

    # ── actual line: solid, larger solid dots, full opacity ───────────────────
    ax.plot(years, actual, ls="-", color=color, lw=1.9,
            marker="o", markersize=4.5, markerfacecolor=color,
            markeredgewidth=0, zorder=5, label="Actual (observed)")

    # ── axes labels & title ───────────────────────────────────────────────────
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_xlabel("")
    ax.set_title(
        f"$\\bf{{{panel_letter}}}$  {panel_title}",
        fontsize=8.5, loc="left", pad=5,
    )

    # ── x-axis ────────────────────────────────────────────────────────────────
    ax.set_xlim(min_yr - 0.5, max_yr + 0.5)
    xticks = list(range(min_yr, max_yr + 1, 5))
    ax.set_xticks(xticks)
    ax.tick_params(axis="x", which="major", length=3.5, direction="in")
    ax.tick_params(axis="y", which="major", length=3.5, direction="in")

    # ── y-axis ────────────────────────────────────────────────────────────────
    if y_lo is not None and y_hi is not None:
        ax.set_ylim(y_lo, y_hi)
    if yformatter:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(yformatter))

    # ── event label inside shaded zone ────────────────────────────────────────
    ylims = ax.get_ylim()
    yspan = ylims[1] - ylims[0]
    ax.text(
        TREAT_YEAR + 0.3, ylims[1] - 0.03 * yspan,
        event_label,
        fontsize=6.5, color="#666666", style="italic",
        va="top", ha="left",
    )

    # ── ATT annotation box (no p-value) ───────────────────────────────────────
    sign = "+" if att_pct_val > 0 else ""
    ann_text = f"ATT = {sign}{att_pct_val:.2f}%"
    ax.text(
        0.05, 0.10, ann_text,
        transform=ax.transAxes,
        fontsize=8, color=color,
        va="bottom", ha="left",
        bbox=dict(boxstyle="round,pad=0.35", fc="white",
                  ec=color, lw=0.8, alpha=0.92),
    )

    # ── spines ────────────────────────────────────────────────────────────────
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.75)
    ax.spines["bottom"].set_linewidth(0.75)


# ── Build figure (more square panels: taller figure) ──────────────────────────
fig, axes = plt.subplots(1, 4, figsize=(13, 4.5))
fig.subplots_adjust(wspace=0.42, left=0.07, right=0.98, top=0.90, bottom=0.16)

panels = [
    # ax, df, act_col, syn_col, color, ylabel, letter, title, att, yfmt, y_lo, y_hi
    (axes[0], eu_tp, "eu_actual_real", "eu_synthetic_real",
     EU_COLOR, "Publications", "a", "EU · Total publications",
     eu_att_tp, k_fmt, None, None),

    (axes[1], eu_ir, "eu_actual", "eu_synthetic",
     EU_COLOR, "Intl. ratio", "b", "EU · Intl. publication ratio",
     eu_att_ir, None, None, None),

    (axes[2], uk_tp, "uk_actual_real", "uk_synthetic_real",
     UK_COLOR, "Publications", "c", "UK · Total publications",
     uk_att_tp, k_fmt, None, None),

    (axes[3], uk_ir, "uk_actual", "uk_synthetic",
     UK_COLOR, "Intl. ratio", "d", "UK · Intl. publication ratio",
     uk_att_ir, None, None, None),
]

for (ax, df, act_col, syn_col, color, ylabel,
     letter, title, att, yfmt, ylo, yhi) in panels:
    df2 = df.dropna(subset=[act_col, syn_col]).copy()
    draw_panel(ax, df2, act_col, syn_col,
               color, ylabel, letter, title,
               att, yformatter=yfmt, y_lo=ylo, y_hi=yhi)

# ── Shared legend ──────────────────────────────────────────────────────────────
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches

legend_handles = [
    Line2D([0], [0], color="gray", lw=1.9, ls="-",
           marker="o", markersize=4.5, markerfacecolor="gray",
           markeredgewidth=0, label="Actual (observed)"),
    Line2D([0], [0], color="#999999", lw=1.4, ls="--",
           marker="o", markersize=3.0, markerfacecolor="#999999",
           markeredgewidth=0, label="Synthetic counterfactual"),
    mpatches.Patch(color="#E8E8E8", label="Post-treatment period"),
    Line2D([0], [0], color="#555555", lw=0.9, ls="--",
           label="Intervention year"),
]
fig.legend(
    handles=legend_handles,
    loc="lower center", ncol=4,
    frameon=False, fontsize=7.5,
    bbox_to_anchor=(0.5, -0.01),
)

fig.savefig(OUT, bbox_inches="tight", dpi=300)
print(f"Saved → {OUT}")
