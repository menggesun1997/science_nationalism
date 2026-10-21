#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot Russia/Ukraine in-time placebo tests (Crimea 2014 and War 2022).

2x2 grid per (event, outcome): one panel per pseudo-treatment year, showing
each treated unit's actual (solid) vs synthetic (dashed) trajectory with a
vertical line at the pseudo year. Matches the Brexit in-time grid style.

Reads <event>/<outcome_dir>/in_time/<unit>_intime_<year>.dta produced by
run_in_time_placebo_ruua.do. Writes PDF + PNG into each event directory.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

CODE = Path(__file__).resolve().parents[1]


def integer_xaxis(ax):
    """Force integer year ticks with no decimal point."""
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))

plt.rcParams["font.family"] = "Arial"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RU = "#4B5C9C"   # blue-violet (published Russia colour)
UA = "#E2C341"   # golden (published Ukraine colour)
INT_LINE = "#444444"

EVENTS = {
    # Crimea is capped at 2021 so the panels are not contaminated by the 2022
    # full-scale invasion, matching the effect/p-value windows used elsewhere.
    "crimean": {"dir": "01_scm_crimea_2014", "years": [2011, 2012, 2013, 2014],
                "xmax": 2021},
    "war": {"dir": "01_scm_war_2022", "years": [2019, 2020, 2021, 2022],
            "xmax": None},
}
OUTCOMES = {
    "total": {"subdir": "total_publications",
              "val": "actual_real", "syn": "synthetic_real",
              "ylab": "Publications"},
    "ratio": {"subdir": "intl_ratio",
              "val": "actual", "syn": "synthetic",
              "ylab": "International collaboration ratio (%)"},
}


def load(event_dir, subdir, unit, year):
    return pd.read_stata(
        CODE / event_dir / subdir / "in_time" / f"{unit}_intime_{year}.dta"
    ).sort_values("Year")


def style_axis(ax):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(labelsize=9, width=1)
    ax.set_facecolor("white")
    integer_xaxis(ax)


def plot_grid(event, outcome):
    ev = EVENTS[event]
    oc = OUTCOMES[outcome]
    years = ev["years"]
    # Rows = countries (independent y-scales per row to handle the large
    # size gap between Russia and Ukraine); columns = pseudo-treatment years.
    units = [("russia", RU, "Russia"), ("ukraine", UA, "Ukraine")]
    fig, axes = plt.subplots(2, len(years), figsize=(4 * len(years), 7),
                             sharex="col", sharey="row")
    letters = "abcdefgh"

    for r, (unit, color, cname) in enumerate(units):
        for c, year in enumerate(years):
            ax = axes[r, c]
            df = load(ev["dir"], oc["subdir"], unit, year)
            if ev["xmax"]:
                df = df[df["Year"] <= ev["xmax"]]
            actual = df[oc["val"]]
            synth = df[oc["syn"]]
            if outcome == "ratio":
                actual = actual * 100
                synth = synth * 100
            ax.plot(df["Year"], actual, color=color, lw=1.8, marker="o",
                    ms=4, mfc=color, mec=color, label="Observed")
            ax.plot(df["Year"], synth, color=color, lw=1.5, ls=(0, (5, 3)),
                    marker="o", ms=4, mfc=color, mec=color, label="Synthetic")
            ax.axvline(year, color=INT_LINE, lw=1.5, ls=(0, (2, 2)))
            idx = r * len(years) + c
            ax.set_title(f"({letters[idx]}) {cname}, pseudo {year}",
                         fontsize=11, fontweight="bold", pad=6)
            ax.set_xlim(df["Year"].min(), df["Year"].max())
            style_axis(ax)
            if c == 0:
                ax.set_ylabel(oc["ylab"], fontsize=10)
            if r == 1:
                ax.set_xlabel("Year", fontsize=10)

    # One bottom legend: observed vs synthetic (line style carries meaning).
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10,
               loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    stem = CODE / ev["dir"] / f"{event}_in_time_placebo_{outcome}_grid"
    fig.savefig(f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {stem}.pdf / .png")


def main():
    for event in EVENTS:
        for outcome in OUTCOMES:
            plot_grid(event, outcome)


if __name__ == "__main__":
    main()
