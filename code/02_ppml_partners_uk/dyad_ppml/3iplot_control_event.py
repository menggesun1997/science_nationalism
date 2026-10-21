#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Control-pool sensitivity: event-study paths only (SI figure).

Keeps a single event-study panel comparing the three control pools that differ
only in composition (not in estimation window):
  all partners (200), top-quartile by volume (50), 16 large mature peers.

Reads design_comparison_event.csv (3ecompare_designs.py).
Outputs brexit_dyad_control_sensitivity.pdf / .png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent
REF_START, POST_YEAR, REF_YEAR = 2016, 2021, 2020

GREY = "#7F7F7F"
RED = "#B5485D"

# design key in the csv -> (legend label, colour)
POOLS = {
    "A0  all partners, 2005-":   ("All partners (200)", "#2E6F9E"),
    "A2  top-25% volume, 2005-": ("Top-quartile by volume (50)", "#D98C3F"),
    "A1  BIG list, 2005-":       ("16 mature peers (17)", "#3F8F6B"),
}


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def main() -> None:
    es = pd.read_csv(HERE / "design_comparison_event.csv")

    fig, ax = plt.subplots(figsize=(9.0, 5.4))
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(REF_START - 0.5, color=GREY, ls="--", lw=1.1,
               label=f"Referendum ({REF_START})")
    ax.axvline(POST_YEAR - 0.5, color=RED, ls="--", lw=1.2,
               label=f"Formal exit ({POST_YEAR})")

    for key, (label, color) in POOLS.items():
        d = es[es["design"] == key].sort_values("year")
        if d.empty:
            continue
        ax.fill_between(d["year"], d["ci_lo_pct"], d["ci_hi_pct"],
                        color=color, alpha=0.12, lw=0)
        ax.plot(d["year"], d["pct_change"], marker="o", ms=4.0, lw=1.7,
                color=color, label=label)

    ax.set_xlabel("Year")
    ax.set_ylabel("Change in collaboration with the UK (%)\n"
                  f"relative to {REF_YEAR}")
    ax.grid(alpha=0.25, ls=":")
    integer_xaxis(ax)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center",
               ncol=len(labels), bbox_to_anchor=(0.5, -0.02), fontsize=9)
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"brexit_dyad_control_sensitivity.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved brexit_dyad_control_sensitivity.pdf / .png")


if __name__ == "__main__":
    main()
