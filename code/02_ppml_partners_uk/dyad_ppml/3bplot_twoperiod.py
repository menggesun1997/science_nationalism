#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两段 beta（公投期 + 脱欧期）可视化，并与 event study 路径对照。

左图：逐年 event study 系数（参照年 REF_YEAR），叠加两段 beta 的阶梯拟合。
右图：b1 / b2 / b1+b2 三个系数的点估计与 95% CI。
输入 st_eu_to_uk_event.csv、st_eu_to_uk_twoperiod.csv。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent

REF_START = 2016   # PostRef 起点（公投）
POST_YEAR = 2021   # Brexit 起点（正式脱欧）
REF_YEAR = 2020    # event study 省略的参照年

BLUE = "#2E6F9E"
RED = "#B5485D"
ORANGE = "#D98A3C"
GREY = "#7F7F7F"


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def load() -> tuple[pd.DataFrame, pd.Series]:
    es = pd.read_csv(HERE / "st_eu_to_uk_event.csv").sort_values("year")
    tp = pd.read_csv(HERE / "st_eu_to_uk_twoperiod.csv").set_index("term")
    return es, tp


def panel_event(ax, es: pd.DataFrame, tp: pd.DataFrame) -> None:
    """逐年系数 + 两段 beta 阶梯。"""
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(REF_START - 0.5, color=GREY, ls="--", lw=1.1, alpha=0.9,
               label=f"Referendum ({REF_START})")
    ax.axvline(POST_YEAR - 0.5, color=RED, ls="--", lw=1.2, alpha=0.9,
               label=f"Formal exit ({POST_YEAR})")

    ax.fill_between(es["year"], es["ci_lo_pct"], es["ci_hi_pct"],
                    color=BLUE, alpha=0.16, lw=0, label="95% CI")
    ax.plot(es["year"], es["pct_change"], marker="o", ms=4.0, lw=1.4,
            color=BLUE, label=r"Event study  $e^{\beta_k}-1$")

    # 两段 beta 的阶梯拟合。event study 以 REF_YEAR 为基准，而两段 beta 以
    # 2005-2015 为基准，故把阶梯整体平移，使公投前水平与 b1 的参照期对齐。
    yrs = es["year"].to_numpy()
    b1 = float(tp.loc["postref_uk", "pct_change"])
    cum = float(tp.loc["cumulative", "pct_change"])
    shift = -b1  # 把 pre 期抬到 -b1，使 PostRef 段落在 0 以下 b1 的位置
    step_x, step_y = [], []
    for y in yrs:
        if y < REF_START:
            step_y.append(shift)
        elif y < POST_YEAR:
            step_y.append(shift + b1)
        else:
            step_y.append(shift + cum)
        step_x.append(y)
    ax.step(step_x, step_y, where="mid", color=ORANGE, lw=2.0, alpha=0.9,
            label="Two-period step fit")

    ax.set_xlabel("Year")
    ax.set_ylabel("Change in collaboration with the UK (%)\n"
                  f"event study relative to {REF_YEAR}")
    ax.set_title("Yearly path vs. two-period step", fontsize=10.5)
    ax.grid(alpha=0.25, ls=":")
    integer_xaxis(ax)


def panel_coefs(ax, tp: pd.DataFrame) -> None:
    """b1 / b2 / b1+b2 的点估计与 CI。"""
    order = ["postref_uk", "brexit_uk", "cumulative"]
    labels = [
        f"$\\beta_1$  Post-ref $\\times$ UK\n({REF_START}–)",
        f"$\\beta_2$  Brexit $\\times$ UK\n({POST_YEAR}–, incremental)",
        f"$\\beta_1+\\beta_2$  cumulative\n({POST_YEAR}–)",
    ]
    colors = [BLUE, ORANGE, RED]
    y = list(range(len(order)))[::-1]

    ax.axvline(0, color="black", lw=0.8)
    for yi, term, c in zip(y, order, colors):
        r = tp.loc[term]
        ax.hlines(yi, r["ci_lo_pct"], r["ci_hi_pct"], color=c, lw=2.0,
                  alpha=0.8)
        ax.scatter(r["pct_change"], yi, s=70, color=c, zorder=3)
        star = "***" if r["pvalue"] < 0.01 else (
            "**" if r["pvalue"] < 0.05 else ("*" if r["pvalue"] < 0.10 else ""))
        ax.annotate(f"{r['pct_change']:+.2f}%{star}",
                    xy=(r["pct_change"], yi), xytext=(0, 11),
                    textcoords="offset points", ha="center", fontsize=9.5,
                    color=c, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xlabel("Change in collaboration with the UK (%)")
    ax.set_title("Two-period PPML coefficients, 95% CI", fontsize=10.5)
    ax.grid(axis="x", alpha=0.25, ls=":")


def main() -> None:
    es, tp = load()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0),
                             gridspec_kw={"width_ratios": [1.25, 1.0]})
    panel_event(axes[0], es, tp)
    panel_coefs(axes[1], tp)

    fig.suptitle("Brexit and EU-27 collaboration with the UK: two-period "
                 "decomposition\ndyadic PPML, country-pair and "
                 "EU-country-year fixed effects, SE clustered on pair",
                 fontsize=11.5)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center",
               ncol=len(labels), bbox_to_anchor=(0.5, -0.01), fontsize=9)
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"twoperiod_uk_dyadic.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved twoperiod_uk_dyadic.pdf / .png")


if __name__ == "__main__":
    main()
