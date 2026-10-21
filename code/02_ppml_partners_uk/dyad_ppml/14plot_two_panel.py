#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双栏 coefficient plot：左 "UK to EU"，右 "EU to UK"。

两栏的被解释变量是同一个合著计数（合著无方向性），区别在参照组：
- EU to UK：对照组是每个 EU 国家自己的其他伙伴，mu_it 吸收该国整体增长
- UK to EU：对照组是英国自己的非 EU 伙伴，mu_t 吸收英国整体增长

点为 exp(beta)-1，横条为 99% 置信区间（与参考图一致）。

输入 Stata 产出的 st_*.csv
输出 brexit_two_panel.pdf / .png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent

Z99 = 2.5758          # 99% 双侧
NAVY = "#1F4E79"      # EU to UK
CRIM = "#B5485D"      # UK to EU
GREY = "#9A9A9A"      # 不显著

TITLECASE = {"SLOVAK REPUBLIC": "Slovakia", "CZECHIA": "Czechia"}


def pretty(name: str) -> str:
    if name in TITLECASE:
        return TITLECASE[name]
    return name.title()


def load(side: str) -> tuple[pd.DataFrame, pd.Series]:
    """读入一侧的逐国结果和 aggregate，统一算 99% CI。"""
    by = pd.read_csv(HERE / f"st_{side}_by_country.csv")
    agg = pd.read_csv(HERE / f"st_{side}_pooled.csv").iloc[0]

    for d in (by,):
        d["lo99"] = 100 * (np.exp(d["coef"] - Z99 * d["se"]) - 1)
        d["hi99"] = 100 * (np.exp(d["coef"] + Z99 * d["se"]) - 1)
    agg = agg.copy()
    agg["lo99"] = 100 * (np.exp(agg["coef"] - Z99 * agg["se"]) - 1)
    agg["hi99"] = 100 * (np.exp(agg["coef"] + Z99 * agg["se"]) - 1)
    return by, agg


def draw_panel(ax, by, agg, order, colour, sig_col, title) -> None:
    """按 order 给定的国家顺序画一栏。aggregate 置于最上方并与下方分隔。"""
    n = len(order)
    rows = by.set_index("focal_country")

    # y: aggregate 在 n+0.8，其余自上而下
    y_agg = n + 0.8
    ys = {c: n - 1 - i for i, c in enumerate(order)}

    ax.axvline(0, color="black", lw=1.1, zorder=1)

    # aggregate
    ax.hlines(y_agg, agg["lo99"], agg["hi99"], color=colour, lw=1.5)
    ax.plot([agg["lo99"], agg["hi99"]], [y_agg, y_agg], "|",
            color=colour, ms=7, mew=1.5)
    ax.scatter(agg["pct_change"], y_agg, s=46, facecolors="white",
               edgecolors=colour, linewidths=1.8, zorder=3)

    for c in order:
        if c not in rows.index:
            continue
        r = rows.loc[c]
        y = ys[c]
        col = colour if r[sig_col] else GREY
        ax.hlines(y, r["lo99"], r["hi99"], color=col, lw=1.3, alpha=0.9)
        ax.plot([r["lo99"], r["hi99"]], [y, y], "|", color=col, ms=6, mew=1.2)
        ax.scatter(r["pct_change"], y, s=34, facecolors="white",
                   edgecolors=col, linewidths=1.5, zorder=3)

    ax.set_yticks([y_agg] + [ys[c] for c in order])
    ax.set_yticklabels(["EU27 aggregate"] + [pretty(c) for c in order],
                       fontsize=9)
    for lbl in ax.get_yticklabels()[:1]:
        lbl.set_fontweight("bold")
    ax.set_ylim(-0.9, n + 1.6)
    ax.axhline(n - 0.3, color="black", lw=0.6, alpha=0.4)
    ax.set_title(title, fontsize=13, pad=12)
    ax.grid(axis="x", alpha=0.18, ls=":")
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)


def main() -> None:
    uk2eu, uk2eu_agg = load("uk_to_eu")
    eu2uk, eu2uk_agg = load("eu_to_uk")

    # 每栏各自按效应排序（与参考图一致）
    order_l = uk2eu.sort_values("pct_change")["focal_country"].tolist()
    order_r = eu2uk.sort_values("pct_change")["focal_country"].tolist()

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(12.4, 8.6))

    # UK to EU 用置换检验的 p 值判显著（该方向 dyad 即 partner，
    # cluster-robust 推断不可用）
    draw_panel(axl, uk2eu, uk2eu_agg, order_l, CRIM, "sigp_10",
               "UK to EU")
    draw_panel(axr, eu2uk, eu2uk_agg, order_r, NAVY, "sig_05",
               "EU to UK")

    # 两栏共用 x 轴范围，否则视觉上无法直接比较幅度
    lo = min(uk2eu["lo99"].min(), eu2uk["lo99"].min(),
             uk2eu_agg["lo99"], eu2uk_agg["lo99"])
    hi = max(uk2eu["hi99"].max(), eu2uk["hi99"].max(),
             uk2eu_agg["hi99"], eu2uk_agg["hi99"])
    pad = 0.04 * (hi - lo)
    for ax in (axl, axr):
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_xlabel("Change in co-authored publications after Brexit (%)",
                      fontsize=10)

    legend_l = [
        Line2D([0], [0], marker="o", color=CRIM, mfc="white", mew=1.5,
               ls="-", lw=1.3, label="placebo p < 0.10"),
        Line2D([0], [0], marker="o", color=GREY, mfc="white", mew=1.5,
               ls="-", lw=1.3, label="not significant"),
    ]
    axl.legend(handles=legend_l, frameon=True, fontsize=8.5,
               loc="lower right", framealpha=0.95)
    legend_r = [
        Line2D([0], [0], marker="o", color=NAVY, mfc="white", mew=1.5,
               ls="-", lw=1.3, label="p < 0.05"),
        Line2D([0], [0], marker="o", color=GREY, mfc="white", mew=1.5,
               ls="-", lw=1.3, label="not significant"),
    ]
    axr.legend(handles=legend_r, frameon=True, fontsize=8.5,
               loc="lower right", framealpha=0.95)

    fig.suptitle("Brexit impact on country-level PPML regressions",
                 fontsize=14, y=0.975)

    note = (
        "Co-authorship is undirected ($P_{ij}=P_{ji}$); the two panels differ "
        "only in the comparison group.\n"
        "UK to EU: $P_{jt}=\\exp(\\alpha_j+\\mu_t+\\beta_k\\,Post_t\\times"
        "\\mathbf{1}[j=k])$, controls are the UK's non-EU partners.\n"
        "EU to UK: $P_{ijt}=\\exp(\\alpha_{ij}+\\mu_{it}+\\beta\\,Post_t"
        "\\times UK_j)$, estimated within each EU country's own partner "
        "portfolio.\n"
        "ppmlhdfe, Post $=\\mathbf{1}[t\\geq2017]$, bars are 99% CIs. "
        "EU to UK clusters by country pair; UK to EU reports robust SEs with\n"
        "placebo-based p-values (50 non-EU partners), because each "
        "$\\beta_k$ there is identified off a single dyad."
    )
    fig.text(0.5, -0.012, note, ha="center", va="top", fontsize=8.2,
             color="#333333")

    fig.tight_layout(rect=(0, 0.02, 1, 0.955))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"brexit_two_panel.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved brexit_two_panel.pdf / .png")


if __name__ == "__main__":
    main()
