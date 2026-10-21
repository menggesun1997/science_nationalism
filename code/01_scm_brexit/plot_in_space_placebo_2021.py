#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""In-space placebo figure for the 2021 Brexit specification.

Two panels per outcome:
  left  — gap trajectories: every donor country reassigned the 2021
          intervention (grey) against the UK (red);
  right — distribution of post/pre MSPE ratios with the UK marked, which is
          the statistic the pseudo p-value is based on.

Reads <outcome>/in_space_2021/placebo_gaps_2021.dta and mspe_ratios_2021.dta
written by run_in_space_placebo_2021.do. Outputs PDF + PNG next to this script.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent

TREAT_YEAR = 2021
UK = "UNITED_KINGDOM"

UK_RED = "#BE2738"
DONOR_GREY = "#B0B0B0"
INT_LINE = "#444444"

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "Helvetica", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUTCOMES = {
    "total": {
        "subdir": "total_publications",
        "gapcol": "gap_pct",
        "ylab": "Gap vs. synthetic (% of actual)",
        "title": "Total publications",
        "scale": 1.0,
    },
    "ratio": {
        "subdir": "intl_ratio",
        "gapcol": "gap",
        "ylab": "Gap vs. synthetic (percentage points)",
        "title": "International collaboration ratio",
        "scale": 100.0,
    },
}


def integer_xaxis(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=9)
    ax.set_facecolor("white")


def load(outcome):
    sub = HERE / OUTCOMES[outcome]["subdir"] / "in_space_2021"
    gaps = pd.read_stata(sub / "placebo_gaps_2021.dta")
    mspe = pd.read_stata(sub / "mspe_ratios_2021.dta")
    gaps["unit"] = gaps["unit"].str.strip()
    mspe["unit"] = mspe["unit"].str.strip()
    return gaps.sort_values(["unit", "Year"]), mspe


def panel_gaps(ax, gaps, outcome, letter):
    cfg = OUTCOMES[outcome]
    col, sc = cfg["gapcol"], cfg["scale"]

    for unit, d in gaps.groupby("unit"):
        if unit == UK:
            continue
        ax.plot(d["Year"], d[col] * sc, color=DONOR_GREY, lw=0.9, alpha=0.75,
                zorder=2)

    uk = gaps[gaps["unit"] == UK]
    ax.plot(uk["Year"], uk[col] * sc, color=UK_RED, lw=2.2, marker="o", ms=3.6,
            mfc=UK_RED, mec=UK_RED, zorder=4, label="United Kingdom")
    ax.plot([], [], color=DONOR_GREY, lw=0.9, label="Donor countries (placebo)")

    ax.axhline(0, color="#999999", lw=0.9, zorder=1)
    ax.axvline(TREAT_YEAR, color=INT_LINE, lw=1.3, ls=(0, (2, 2)), zorder=3)
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel(cfg["ylab"], fontsize=10)
    ax.set_title(f"({letter}) {cfg['title']}: placebo gaps",
                 fontsize=11, loc="left")
    ax.set_xlim(gaps["Year"].min(), gaps["Year"].max())
    style(ax)
    integer_xaxis(ax)


def panel_mspe(ax, mspe, outcome, letter):
    d = mspe.sort_values("mspe_ratio").reset_index(drop=True)
    y = np.arange(len(d))
    colors = [UK_RED if u == UK else DONOR_GREY for u in d["unit"]]

    ax.barh(y, d["mspe_ratio"], color=colors, height=0.72)
    ax.set_yticks(y)
    ax.set_yticklabels(
        [u.replace("_", " ").title() for u in d["unit"]], fontsize=7.4)
    ax.set_ylim(-0.7, len(d) - 0.3)
    ax.set_xlabel("Post/pre MSPE ratio", fontsize=10)

    uk = mspe[mspe["unit"] == UK].iloc[0]
    p = float(uk["pvalue"])
    k = int(uk["rank"])
    n = int(uk["n_units"])
    ax.set_title(
        f"({letter}) {OUTCOMES[outcome]['title']}: MSPE ratios\n"
        f"UK rank {k} of {n},  $p$ = {p:.3f}",
        fontsize=11, loc="left")
    style(ax)
    ax.grid(axis="x", alpha=0.25, ls=":")


def main():
    fig, axes = plt.subplots(2, 2, figsize=(13.0, 9.4),
                             gridspec_kw={"width_ratios": [1.35, 1.0]})
    letters = [("a", "b"), ("c", "d")]

    for row, outcome in enumerate(("total", "ratio")):
        gaps, mspe = load(outcome)
        panel_gaps(axes[row][0], gaps, outcome, letters[row][0])
        panel_mspe(axes[row][1], mspe, outcome, letters[row][1])

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9.5,
               loc="lower center", ncol=len(labels), bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.045, 1, 1))

    stem = HERE / "brexit_in_space_placebo_2021"
    fig.savefig(f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {stem}.pdf / .png")


if __name__ == "__main__":
    main()
