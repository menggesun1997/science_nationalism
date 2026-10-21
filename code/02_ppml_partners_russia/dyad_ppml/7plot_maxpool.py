#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主实验结果图（最大化控制池）。两格：

(a) 趋势调整事件研究：战前平直（残余 0/5 失败），2022 断裂并逐年加深。
(b) 主结果 beta_g 森林图 + 两点对比：simple 规格（被 pre-trend 污染、
    虚高）vs trend 规格（可解读）。说明趋势调整在大池上更关键。
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
    res = pd.read_csv(HERE / "maxpool_results.csv")
    ev = pd.read_csv(HERE / "maxpool_event.csv")
    sm = res[res.spec == "simple"].set_index("group")

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
    ax.set_title("(a) Maximal-pool event study", loc="left",
                 fontsize=9.8)
    intx(ax)

    # ── (b) beta_g 森林图 ──
    ax2 = fig.add_subplot(g[0, 1])
    y = np.arange(len(GROUP_ORDER))
    for gg, yy in zip(GROUP_ORDER, y):
        lo = sm.loc[gg, "ci_lo_pct"]
        hi = sm.loc[gg, "ci_hi_pct"]
        sig = sm.loc[gg, "pvalue"] < 0.05
        ax2.hlines(yy, lo, hi, color=GROUP_COLOR[gg], lw=3,
                   alpha=0.9 if sig else 0.5)
        ax2.scatter([sm.loc[gg, "pct_change"]], [yy], s=120,
                    color=GROUP_COLOR[gg] if sig else "white",
                    edgecolor=GROUP_COLOR[gg], lw=2, zorder=5)
    ax2.axvline(0, color="black", lw=1.0)
    ax2.set_yticks(y)
    ax2.set_yticklabels([GROUP_LABEL[gg] for gg in GROUP_ORDER],
                        fontsize=8.2)
    ax2.invert_yaxis()
    ax2.set_xlabel("$e^{\\beta_g}-1$, %")
    ax2.set_title("(b) Group-specific break at 2022\n"
                  "(hollow marker = not significant)", loc="left",
                  fontsize=9.6)
    ax2.grid(axis="y", visible=False)

    fig.suptitle("Russia dyadic PPML — main experiment (maximal "
                 "control pool, 149 countries)",
                 fontsize=11.3, fontweight="bold", y=1.02)
    # 集团图例：横排放在最下方
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=len(l),
               bbox_to_anchor=(0.5, -0.02), fontsize=8.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"maxpool_results.{ext}",
                    dpi=200 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved maxpool_results.png / .pdf")

    print("\n  beta_g (simple):")
    for gg in GROUP_ORDER:
        print(f"    {GROUP_LABEL[gg]:<24} {sm.loc[gg,'pct_change']:+6.1f}%"
              f"  [{sm.loc[gg,'ci_lo_pct']:+.1f}, "
              f"{sm.loc[gg,'ci_hi_pct']:+.1f}]  p={sm.loc[gg,'pvalue']:.3g}")


if __name__ == "__main__":
    main()
