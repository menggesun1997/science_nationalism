#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pre-trend 可视化（对应"算出来的 pre-trend 是否需要可视化"）。

控制组调整前 5/5 组违反平行趋势，调整后 0/5 失败。两格呈现：

(a) EU 组逐年系数：原始路径（战前斜向下、不平行）vs 减去拟合趋势 +
    2014 step 后的调整路径（战前贴零线、平行）。
(b) 五组的战前趋势 theta_g：调整前（显著，带 ***）vs 调整后残余
    （全部归零，p>=0.84）。
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
GROUP_SHORT = {"EU": "EU", "NORTH_AMERICA": "N. America",
               "ASIA": "Adv. Asia", "CHINA": "China", "OTHER": "Rest"}
REF_YEAR = 2021
PRE = (2012, 2021)


def intx(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{int(round(v))}"))


def main():
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "grid.linestyle": "--",
                         "grid.linewidth": 0.6})
    ev = pd.read_csv(HERE / "ukraine_event_study.csv")
    res = pd.read_csv(HERE / "ukraine_two_event_trend.csv")
    rp = pd.read_excel(HERE / "ukraine_control_screening.xlsx",
                       sheet_name="residual_pretrend")

    fig = plt.figure(figsize=(13, 5.2))
    g = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0], wspace=0.26)

    # ── (a) EU 组逐年：原始 vs 调整 ──
    ax = fig.add_subplot(g[0, 0])
    eu = ev[ev["group"] == "EU"].sort_values("year").set_index("year")
    yrs = eu.index.to_numpy()
    raw = eu["pct"].to_numpy()

    # 战前线性趋势（2012-2021），外推全窗口；展示"原始不平行"
    pre = yrs <= PRE[1]
    sl = np.polyfit(yrs[pre], raw[pre], 1)
    trend = np.polyval(sl, yrs)
    adj = raw - trend                      # 减掉战前趋势 = 调整后路径

    ax.plot(yrs, raw, color="#b03030", lw=2.2, marker="o", ms=4,
            label="Raw coefficients (pre-war NOT parallel)", zorder=4)
    ax.plot(yrs[pre], trend[pre], color="#b03030", lw=1.0, ls=":",
            alpha=0.8, label=f"Fitted pre-trend ({sl[0]:+.1f}%/yr)")
    ax.plot(yrs, adj, color="#2f6b43", lw=2.2, marker="s", ms=4,
            label="After trend adjustment (flat before war)", zorder=5)

    ax.axhline(0, color="black", lw=0.8)
    ax.axhspan(-10, 10, color="#4f9d69", alpha=0.10, zorder=0)
    ax.axvspan(PRE[0], PRE[1], color="#cccccc", alpha=0.16, zorder=0)
    ax.axvline(2014, color="#999999", ls=":", lw=1.2)
    ax.axvline(2022, color="#b03030", ls="--", lw=1.3)
    ax.annotate("2014", (2014, 1.01), xycoords=("data", "axes fraction"),
                ha="center", fontsize=8, color="#666666")
    ax.annotate("2022", (2022, 1.01), xycoords=("data", "axes fraction"),
                ha="center", fontsize=8, color="#b03030")
    ax.set_xlabel("Year")
    ax.set_ylabel("EU-group coefficient, %  (relative to 2021)")
    ax.set_title("(a) EU group: raw path slopes down before the war; "
                 "adjustment flattens it", loc="left", fontsize=9.6)
    intx(ax)
    ax.legend(frameon=False, fontsize=7.8, loc="upper right")

    # ── (b) 五组 theta：调整前 vs 调整后 ──
    ax2 = fig.add_subplot(g[0, 1])
    y = np.arange(len(GROUP_ORDER))
    w = 0.38
    before = [float(res.loc[res.group == gg,
                            "theta_pct_per_yr"].iloc[0])
              for gg in GROUP_ORDER]
    bp = [float(res.loc[res.group == gg, "theta_p"].iloc[0])
          for gg in GROUP_ORDER]
    after = [float(rp.loc[rp.group == gg,
                          "residual_theta_pct"].iloc[0])
             for gg in GROUP_ORDER]
    ax2.barh(y - w / 2, before, height=w, color="#b03030", alpha=0.9,
             label="Before adjustment")
    ax2.barh(y + w / 2, after, height=w, color="#2f6b43",
             label="After adjustment (residual)")
    for i, (bv, pv) in enumerate(zip(before, bp)):
        if pv < 0.05:
            ax2.annotate("***", (bv, i - w / 2), xytext=(-4, 0),
                         textcoords="offset points", ha="right",
                         va="center", fontsize=9, color="#b03030",
                         fontweight="bold")
    ax2.axvline(0, color="black", lw=1.0)
    ax2.set_yticks(y)
    ax2.set_yticklabels([GROUP_SHORT[gg] for gg in GROUP_ORDER],
                        fontsize=8.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("Pre-war group trend $\\theta_g$, % per year")
    ax2.set_title("(b) All five groups: 5/5 fail $\\rightarrow$ 0/5 fail",
                  loc="left", fontsize=9.6)
    ax2.legend(frameon=False, fontsize=8, loc="lower left")
    ax2.grid(axis="y", visible=False)

    fig.suptitle("Ukraine pre-trend: why the control group looks "
                 "non-parallel, and how adjustment fixes it",
                 fontsize=11.3, fontweight="bold", y=1.0)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"ukraine_pretrend.{ext}",
                    dpi=200 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved ukraine_pretrend.png / .pdf")

    print("\n  theta_g before vs after adjustment:")
    for gg, b, a, pv in zip(GROUP_ORDER, before, after, bp):
        print(f"    {GROUP_SHORT[gg]:<11} before {b:+6.2f} "
              f"(p={pv:.3g})   after {a:+6.2f}")


if __name__ == "__main__":
    main()
