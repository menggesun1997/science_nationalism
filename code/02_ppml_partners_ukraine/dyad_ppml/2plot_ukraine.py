#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ukraine dyadic PPML 结果图：三格。

(a) 事件研究（EU 组为例）：2014 与 2022 两个断点都可见，说明为何需要
    两个 step 而非 Russia 式单断点。
(b) 两断点 + 趋势的分集团系数：b2014 与 b2022 并列。
(c) 验证：趋势 + 2014 step 调整后残余 pre-trend 归零。

图表约定遵循 .cursor/rules/figure-conventions.mdc。
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
GROUP_SHORT = {"EU": "EU", "NORTH_AMERICA": "N. America",
               "ASIA": "Adv. Asia", "CHINA": "China", "OTHER": "Rest"}
GROUP_COLOR = {"EU": "#2b5d8a", "NORTH_AMERICA": "#4f9d69",
               "ASIA": "#c87d2b", "CHINA": "#a8405b", "OTHER": "#7a7a7a"}
THIN = {"NORTH_AMERICA", "ASIA", "CHINA"}   # 体量薄、仅探索性


def intx(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{int(round(v))}"))


def main():
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "grid.linestyle": "--",
                         "grid.linewidth": 0.6})
    res = pd.read_csv(HERE / "ukraine_two_event_trend.csv")
    ev = pd.read_csv(HERE / "ukraine_event_study.csv")

    fig = plt.figure(figsize=(12.5, 5.0))
    g = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], wspace=0.26)

    # ── (a) 事件研究（放大为主图）──
    ax = fig.add_subplot(g[0, 0])
    for grp in GROUP_ORDER:
        s = ev[ev["group"] == grp].sort_values("year")
        thin = grp in THIN
        ax.plot(s["year"], s["pct"], color=GROUP_COLOR[grp],
                lw=1.6 if thin else 2.4,
                ls="--" if thin else "-",
                marker="o", ms=4,
                label=GROUP_LABEL[grp] + (" (thin)" if thin else ""),
                alpha=0.6 if thin else 1.0, zorder=3 if thin else 4)
    ax.axhline(0, color="black", lw=0.8)
    ax.axvspan(2014, 2021.5, color="#efe6d0", alpha=0.45, zorder=0)
    ax.axvline(2014, color="#999999", ls=":", lw=1.4)
    ax.axvline(2022, color="#b03030", ls="--", lw=1.5)
    ax.annotate("2014\nCrimea + Donbas", (2014, 0.97),
                xycoords=("data", "axes fraction"), ha="center",
                va="top", fontsize=8, color="#666666")
    ax.annotate("2022\ninvasion", (2022, 0.97),
                xycoords=("data", "axes fraction"), ha="center",
                va="top", fontsize=8, color="#b03030")
    ax.set_xlabel("Year")
    ax.set_ylabel("Ukraine collaboration share, %  (relative to 2021)")
    ax.set_title("(a) Event study: two visible breaks (2014 and 2022) "
                 "motivate the two-step design", loc="left",
                 fontsize=9.8)
    intx(ax)
    ax.legend(frameon=False, fontsize=7.8, ncol=2, loc="upper right")

    # ── (b) 两断点系数 ──
    ax2 = fig.add_subplot(g[0, 1])
    x = np.arange(len(GROUP_ORDER))
    w = 0.38
    b14 = [float(res.loc[res.group == gg, "b2014_pct"].iloc[0])
           for gg in GROUP_ORDER]
    b22 = [float(res.loc[res.group == gg, "b2022_pct"].iloc[0])
           for gg in GROUP_ORDER]
    p22 = [float(res.loc[res.group == gg, "b2022_p"].iloc[0])
           for gg in GROUP_ORDER]
    ax2.bar(x - w / 2, b14, width=w, color="#b0a070",
            label="2014 break ($\\beta^{14}_g$)")
    bars = ax2.bar(x + w / 2, b22, width=w, color="#2b5d8a",
                   label="2022 break ($\\beta^{22}_g$)")
    for b, v, pv in zip(bars, b22, p22):
        if pv < 0.05:
            ax2.annotate("*", (b.get_x() + b.get_width() / 2,
                               v + (1 if v >= 0 else -3)),
                         ha="center", fontsize=11, fontweight="bold")
    ax2.axhline(0, color="black", lw=0.9)
    ax2.set_xticks(x)
    ax2.set_xticklabels([GROUP_SHORT[gg] for gg in GROUP_ORDER],
                        fontsize=8, rotation=18, ha="right")
    ax2.set_ylabel("$e^{\\beta_g}-1$, %")
    ax2.set_title("(b) Group breaks (trend-adjusted).\n"
                  "Thin groups: wide CIs, exploratory", loc="left",
                  fontsize=9.5)
    ax2.legend(frameon=False, fontsize=8, loc="lower right")
    ax2.grid(axis="x", visible=False)

    fig.suptitle("Ukraine dyadic PPML: two-event (2014 + 2022) trend "
                 "adjustment", fontsize=11.5, fontweight="bold",
                 y=1.02)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"ukraine_dyad_results.{ext}",
                    dpi=200 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved ukraine_dyad_results.png / .pdf")


if __name__ == "__main__":
    main()
