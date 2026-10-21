#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot the UK Brexit in-time placebo tests (EU dropped).

Two layouts per outcome, matching the two options requested:
  (a) 2x2 grid — one panel per pseudo-treatment year, UK actual (solid) vs
      synthetic (dashed), with a vertical line at the pseudo year. This is the
      classic Abadie-style in-time placebo display.
  (b) single overlay — the UK gap curve for all four pseudo years on one axis,
      coloured by year, to show every pseudo date yields a small gap.

Reads code/01_scm_brexit/<outcome>/in_time/uk_intime_<year>.dta produced by
run_in_time_placebo.do. Outputs PDF + PNG next to this script.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent


def integer_xaxis(ax):
    """Force integer year ticks with no decimal point."""
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))

plt.rcParams["font.family"] = "Arial"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

UK_RED = "#BE2738"
SYN_GREY = "#888888"
INT_LINE = "#444444"
PSEUDO_YEARS = [2013, 2014, 2015, 2016]

# Per-year colours for the overlay plot (sequential, distinguishable).
YEAR_COLORS = {2013: "#F2B84B", 2014: "#5B7553", 2015: "#4C5B9B", 2016: "#BE2738"}

OUTCOMES = {
    "total": {
        "subdir": "total_publications",
        "val": "actual_real",
        "syn": "synthetic_real",
        "gapcol": "gap_pct",
        "ylab_level": "Publications",
        "ylab_gap": "Gap (% of actual)",
        "scale": 1.0,
    },
    "ratio": {
        "subdir": "intl_ratio",
        "val": "actual",
        "syn": "synthetic",
        "gapcol": "gap",
        "ylab_level": "International collaboration ratio",
        "ylab_gap": "Gap (percentage points)",
        "scale": 100.0,  # ratio -> percentage points for the gap
    },
}


def load(outcome, year):
    cfg = OUTCOMES[outcome]
    path = HERE / cfg["subdir"] / "in_time" / f"uk_intime_{year}.dta"
    return pd.read_stata(path).sort_values("Year")


def style_axis(ax):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(labelsize=9, width=1)
    ax.set_facecolor("white")
    integer_xaxis(ax)


def plot_grid(outcome):
    cfg = OUTCOMES[outcome]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    axes = axes.flatten()
    letters = "abcd"

    for i, year in enumerate(PSEUDO_YEARS):
        ax = axes[i]
        df = load(outcome, year)
        if outcome == "ratio":
            actual = df[cfg["val"]] * 100
            synth = df[cfg["syn"]] * 100
        else:
            actual = df[cfg["val"]]
            synth = df[cfg["syn"]]

        # Dot-line style with solid filled markers, matching figure 1.
        ax.plot(df["Year"], actual, color=UK_RED, lw=1.8, marker="o", ms=4,
                mfc=UK_RED, mec=UK_RED, label="United Kingdom")
        ax.plot(df["Year"], synth, color=SYN_GREY, lw=1.5, ls=(0, (5, 3)),
                marker="o", ms=4, mfc=SYN_GREY, mec=SYN_GREY,
                label="Synthetic UK")
        ax.axvline(year, color=INT_LINE, lw=1.5, ls=(0, (2, 2)))
        ax.set_title(f"({letters[i]}) Pseudo-treatment {year}",
                     fontsize=12, fontweight="bold", pad=8)
        ax.set_xlim(df["Year"].min(), df["Year"].max())
        style_axis(ax)
        if i % 2 == 0:
            ax.set_ylabel(
                "International collaboration ratio (%)" if outcome == "ratio"
                else cfg["ylab_level"], fontsize=10)
        if i >= 2:
            ax.set_xlabel("Year", fontsize=10)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10,
               loc="lower center", ncol=len(labels),
               bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    stem = HERE / f"brexit_in_time_placebo_{outcome}_grid"
    fig.savefig(f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {stem}.pdf / .png")


def plot_overlay(outcome):
    cfg = OUTCOMES[outcome]
    fig, ax = plt.subplots(figsize=(8, 5))

    for year in PSEUDO_YEARS:
        df = load(outcome, year)
        gap = df[cfg["gapcol"]]
        if outcome == "ratio":
            gap = gap * cfg["scale"]
        lw = 2.6 if year == 2016 else 1.8
        ax.plot(df["Year"], gap, color=YEAR_COLORS[year], lw=lw,
                label=f"{year}" + ("  (actual)" if year == 2016 else ""))

    ax.axhline(0, color="#999999", lw=1)
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel(cfg["ylab_gap"], fontsize=11)
    ax.set_title("UK in-time placebo: gap by pseudo-treatment year",
                 fontsize=13, fontweight="bold", pad=10)
    style_axis(ax)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10,
               loc="lower center", ncol=len(labels),
               bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    stem = HERE / f"brexit_in_time_placebo_{outcome}_overlay"
    fig.savefig(f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {stem}.pdf / .png")


def main():
    for outcome in ("total", "ratio"):
        plot_grid(outcome)
        plot_overlay(outcome)


if __name__ == "__main__":
    main()
