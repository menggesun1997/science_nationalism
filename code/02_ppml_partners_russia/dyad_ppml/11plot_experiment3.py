#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 3 结果图（6 个精选控制国，simple 规格）。两格：
(a) 事件研究（原始逐年系数，无趋势调整）。
(b) beta_g 森林图，叠加主实验(149)、实验2(174)点作对比。
图例横排放最下方。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent
GROUP_ORDER = ("EU", "NORTH_AMERICA", "ASIA", "CHINA", "OTHER")
GROUP_LABEL = {"EU": "EU-27 + UK", "NORTH_AMERICA": "US + Canada",
               "ASIA": "Japan/Korea/Singapore", "CHINA": "China",
               "OTHER": "Rest of world"}
GROUP_COLOR = {"EU": "#2b5d8a", "NORTH_AMERICA": "#4f9d69",
               "ASIA": "#c87d2b", "CHINA": "#a8405b", "OTHER": "#7a7a7a"}


def intx(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{int(round(v))}"))


def main():
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "grid.linestyle": "--",
                         "grid.linewidth": 0.6})
    res = pd.read_csv(HERE / "exp3_results.csv").set_index("group")
    ev = pd.read_csv(HERE / "exp3_event.csv")

    def load_simple(fn):
        fp = HERE / fn
        if not fp.exists():
            return None
        d = pd.read_csv(fp)
        return d[d.spec == "simple"].set_index("group")

    main_sm = load_simple("maxpool_results.csv")
    exp2_sm = load_simple("exp2_results.csv")

    fig = plt.figure(figsize=(12.5, 5.0))
    g = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.26)

    # ── (a) 事件研究 ──
    ax = fig.add_subplot(g[0, 0])
    for gg in GROUP_ORDER:
        s = ev[ev["group"] == gg].sort_values("year")
        ax.plot(s["year"], s["pct_raw"], color=GROUP_COLOR[gg], lw=2.1,
                marker="o", ms=4, label=GROUP_LABEL[gg])
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(2022, color="#b03030", ls="--", lw=1.4)
    ax.annotate("2022", (2022, 1.01), xycoords=("data", "axes fraction"),
                ha="center", fontsize=8, color="#b03030")
    ax.set_xlabel("Year")
    ax.set_ylabel("Change in Russia's share, %  (relative to 2021)")
    ax.set_title("(a) Six-control event study", loc="left",
                 fontsize=9.8)
    intx(ax)

    # ── (b) 森林图 + 跨池对比 ──
    ax2 = fig.add_subplot(g[0, 1])
    y = np.arange(len(GROUP_ORDER))
    for gg, yy in zip(GROUP_ORDER, y):
        lo, hi = res.loc[gg, "ci_lo_pct"], res.loc[gg, "ci_hi_pct"]
        sig = res.loc[gg, "pvalue"] < 0.05
        ax2.hlines(yy, lo, hi, color=GROUP_COLOR[gg], lw=3,
                   alpha=0.9 if sig else 0.5)
        ax2.scatter([res.loc[gg, "pct_change"]], [yy], s=120,
                    color=GROUP_COLOR[gg] if sig else "white",
                    edgecolor=GROUP_COLOR[gg], lw=2, zorder=5,
                    label="Exp 3 (6 controls)" if gg == "EU" else None)
        if main_sm is not None:
            ax2.scatter([main_sm.loc[gg, "pct_change"]], [yy + 0.24],
                        s=55, marker="D", facecolor="none",
                        edgecolor="#333333", lw=1.1, zorder=6,
                        label="Main (149)" if gg == "EU" else None)
        if exp2_sm is not None:
            ax2.scatter([exp2_sm.loc[gg, "pct_change"]], [yy - 0.24],
                        s=45, marker="x", color="#999999", zorder=6,
                        label="Exp 2 (174)" if gg == "EU" else None)
    ax2.axvline(0, color="black", lw=1.0)
    ax2.set_yticks(y)
    ax2.set_yticklabels([GROUP_LABEL[gg] for gg in GROUP_ORDER],
                        fontsize=8.2)
    ax2.invert_yaxis()
    ax2.set_xlabel("$e^{\\beta_g}-1$, %")
    ax2.set_title("(b) Group-specific break at 2022\n"
                  "(hollow marker = not significant)", loc="left",
                  fontsize=9.6)
    ax2.legend(frameon=False, fontsize=7.2, loc="lower left")
    ax2.grid(axis="y", visible=False)

    fig.suptitle("Russia dyadic PPML — six screened controls "
                 "(Mexico, Chile, Brazil, South Africa, Thailand, "
                 "Argentina)", fontsize=10.6, fontweight="bold", y=1.02)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=len(l),
               bbox_to_anchor=(0.5, -0.02), fontsize=8.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"exp3_results.{ext}",
                    dpi=200 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved exp3_results.png / .pdf")


if __name__ == "__main__":
    main()
