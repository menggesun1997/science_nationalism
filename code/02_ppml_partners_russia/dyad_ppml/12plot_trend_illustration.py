#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势外推示意图（EU 组，最大池主实验）。

说明"战争影响 = 实际 − 趋势外推"：
  - 蓝点线 = 实际事件研究系数
  - 灰虚线 = 战前(2012-2021)线性趋势，外推到 2022-2024（反事实：没有战争
    会怎样）
  - 红色竖箭头 = 实际 − 外推 = 归因于 2022 的战争影响
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
GROUP = "EU"
GROUP_TITLE = "EU-27 + UK"


def main():
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "grid.linestyle": "--",
                         "grid.linewidth": 0.6})
    ev = pd.read_csv(HERE / "maxpool_event.csv")
    s = ev[ev.group == GROUP].sort_values("year")
    yr = s.year.to_numpy()
    act = s.pct_raw.to_numpy()

    pre = s[s.year <= 2021]
    sl, ic = np.polyfit(pre.year, pre.pct_raw, 1)
    fit_all = sl * yr + ic

    fig, ax = plt.subplots(figsize=(9.5, 6.0))

    # 实际路径
    ax.plot(yr, act, color="#2b5d8a", lw=2.4, marker="o", ms=5,
            zorder=5, label="Actual (observed)")

    # 战前趋势实线 + 战后外推虚线
    pre_mask = yr <= 2021
    ax.plot(yr[pre_mask], fit_all[pre_mask], color="#888888", lw=1.8,
            zorder=3)
    post_mask = yr >= 2021
    ax.plot(yr[post_mask], fit_all[post_mask], color="#888888", lw=1.8,
            ls="--", zorder=3,
            label="Pre-war trend, extrapolated\n(counterfactual: no war)")

    # 红色竖箭头：实际 − 外推
    for y in (2022, 2023, 2024):
        a = act[yr == y][0]
        f = fit_all[yr == y][0]
        ax.annotate("", xy=(y, a), xytext=(y, f),
                    arrowprops=dict(arrowstyle="<->", color="#b03030",
                                    lw=1.8))
        ax.annotate(f"{a - f:.0f}", (y + 0.08, (a + f) / 2),
                    color="#b03030", fontsize=9.5, va="center",
                    fontweight="bold")

    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(2022, color="#b03030", ls=":", lw=1.2, alpha=0.7)
    ax.annotate("2022", (2022, 0.98), xycoords=("data", "axes fraction"),
                ha="center", fontsize=9, color="#b03030")
    ax.annotate("war effect\n= actual − extrapolation",
                (2023, 0.12), xycoords=("data", "axes fraction"),
                ha="center", fontsize=9.5, style="italic",
                color="#b03030")

    ax.set_xlabel("Year")
    ax.set_ylabel("Change in Russia's EU-share, %  (relative to 2021)")
    ax.set_title(f"War effect = actual minus pre-war trend "
                 f"extrapolation ({GROUP_TITLE})", fontsize=11,
                 loc="left")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{int(round(v))}"))
    ax.legend(frameon=False, fontsize=9, loc="lower left")

    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"trend_illustration.{ext}",
                    dpi=200 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved trend_illustration.png / .pdf")
    print(f"\n  pre-war slope: {sl:+.2f} pp/yr")
    for y in (2022, 2023, 2024):
        a, f = act[yr == y][0], fit_all[yr == y][0]
        print(f"  {y}: actual {a:+.1f}  extrapolation {f:+.1f}  "
              f"war effect {a - f:+.1f}")


if __name__ == "__main__":
    main()
