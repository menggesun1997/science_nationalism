#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 2 结果图（伙伴集团成员也当控制池，174 国）。两格：

(a) 趋势调整事件研究：战前平直（残余 0/5 失败），2022 断裂并逐年加深。
(b) beta_g 森林图（trend-adjusted）+ simple 规格对照点，并叠加主实验
    (149 国) 的点，直观看"把伙伴国纳入控制"对结果几乎无影响。
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
    res = pd.read_csv(HERE / "exp2_results.csv")
    ev = pd.read_csv(HERE / "exp2_event.csv")
    sm = res[res.spec == "simple"].set_index("group")
    main_sm = None
    mp = HERE / "maxpool_results.csv"
    if mp.exists():
        m = pd.read_csv(mp)
        main_sm = m[m.spec == "simple"].set_index("group")

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
    ax.set_title("(a) Experiment 2 event study", loc="left",
                 fontsize=9.6)
    intx(ax)

    # ── (b) beta_g 森林图：exp2 vs 主实验 ──
    ax2 = fig.add_subplot(g[0, 1])
    y = np.arange(len(GROUP_ORDER))
    for gg, yy in zip(GROUP_ORDER, y):
        lo, hi = sm.loc[gg, "ci_lo_pct"], sm.loc[gg, "ci_hi_pct"]
        sig = sm.loc[gg, "pvalue"] < 0.05
        ax2.hlines(yy, lo, hi, color=GROUP_COLOR[gg], lw=3,
                   alpha=0.9 if sig else 0.5)
        ax2.scatter([sm.loc[gg, "pct_change"]], [yy], s=120,
                    color=GROUP_COLOR[gg] if sig else "white",
                    edgecolor=GROUP_COLOR[gg], lw=2, zorder=5,
                    label="Exp 2 (174)" if gg == "EU" else None)
        if main_sm is not None:
            ax2.scatter([main_sm.loc[gg, "pct_change"]], [yy + 0.22],
                        s=60, marker="D", facecolor="none",
                        edgecolor="#333333", lw=1.2, zorder=6,
                        label="Main exp (149)" if gg == "EU" else None)
    ax2.axvline(0, color="black", lw=1.0)
    ax2.set_yticks(y)
    ax2.set_yticklabels([GROUP_LABEL[gg] for gg in GROUP_ORDER],
                        fontsize=8.2)
    ax2.invert_yaxis()
    ax2.set_xlabel("$e^{\\beta_g}-1$, %")
    ax2.set_title("(b) Adding partner-group members as controls barely "
                  "moves $\\beta_g$\n(diamond = main experiment)",
                  loc="left", fontsize=9.3)
    ax2.legend(frameon=False, fontsize=7.4, loc="lower left")
    ax2.grid(axis="y", visible=False)

    fig.suptitle("Russia dyadic PPML — experiment 2 (partner-group "
                 "members allowed as controls, 174 countries)",
                 fontsize=11.0, fontweight="bold", y=1.02)
    # 集团图例：横排放在最下方
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=len(l),
               bbox_to_anchor=(0.5, -0.02), fontsize=8.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"exp2_results.{ext}",
                    dpi=200 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved exp2_results.png / .pdf")

    print("\n  beta_g (simple) exp2:")
    for gg in GROUP_ORDER:
        print(f"    {GROUP_LABEL[gg]:<24} {sm.loc[gg,'pct_change']:+6.1f}%"
              f"  [{sm.loc[gg,'ci_lo_pct']:+.1f}, "
              f"{sm.loc[gg,'ci_hi_pct']:+.1f}]  p={sm.loc[gg,'pvalue']:.3g}")


if __name__ == "__main__":
    main()
