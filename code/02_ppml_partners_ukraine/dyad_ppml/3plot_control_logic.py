#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控制组选择逻辑可视化（对应"选控制组的逻辑"）。

(a) 排除漏斗：200 国如何按六条 ex ante 规则筛到 50 个合格国。
(b) 接近度排名：50 个合格国按"最差集团偏差"排序，前 6 入选。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
XLSX = HERE / "ukraine_control_screening.xlsx"
SELECTED = ["ARGENTINA", "MEXICO", "MOROCCO", "CHILE",
            "SOUTH AFRICA", "BRAZIL"]

REASON_LABEL = {
    "member of a partner group": "Partner-group member\n(EU/US/CA/JP/KR/SG/CN)",
    "sanctioning country (itself treated)":
        "Other sanctioning\ncountry",
    "substitution/emigration destination":
        "Emigration /\nsubstitution dest.",
    "directly treated / belligerent": "Directly treated /\nbelligerent",
    "own contemporaneous bilateral shock": "Own bilateral\nshock",
}


def main():
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": 0.25, "grid.linestyle": "--",
                         "grid.linewidth": 0.6})
    el = pd.read_excel(XLSX, sheet_name="step1_eligibility")
    rk = pd.read_excel(XLSX, sheet_name="ranking", index_col=0)

    fig = plt.figure(figsize=(13.5, 6.2))
    g = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.15], wspace=0.28)

    # ── (a) 排除漏斗 ──
    ax = fig.add_subplot(g[0, 0])
    total = len(el)
    ex = el[el.eligible == 0].copy()
    ex["bucket"] = ex.exclusion_reason.apply(
        lambda r: "Insufficient volume\nwith some group"
        if str(r).startswith("insufficient")
        else REASON_LABEL.get(r, r))
    counts = ex.bucket.value_counts()

    labels = ["All countries"]
    vals = [total]
    for b, n in counts.items():
        labels.append(b)
        vals.append(-n)
    labels.append("Eligible pool")
    vals.append(int(el.eligible.sum()))

    pos = np.arange(len(labels))
    cum = 0
    for i, v in enumerate(vals):
        if i == 0 or i == len(vals) - 1:
            col = "#1f3b63" if i == 0 else "#4f9d69"
            ax.bar(pos[i], v, color=col, width=0.64)
            ax.annotate(f"{v}", (pos[i], v), xytext=(0, 3),
                        textcoords="offset points", ha="center",
                        fontsize=9.5, fontweight="bold")
            cum = v if i == 0 else cum
        else:
            ax.bar(pos[i], v, bottom=cum, color="#b03030", alpha=0.75,
                   width=0.64)
            ax.annotate(f"-{-v}", (pos[i], cum + v / 2), ha="center",
                        va="center", fontsize=8.5, color="white",
                        fontweight="bold")
            cum += v
    ax.set_xticks(pos)
    ax.set_xticklabels(labels, fontsize=7.0, rotation=40, ha="right")
    ax.set_ylabel("Number of countries")
    ax.set_title("(a) Ex ante exclusions: 200 countries screened to 50",
                 loc="left", fontsize=10)
    ax.grid(axis="x", visible=False)

    # ── (b) 接近度排名 ──
    ax2 = fig.add_subplot(g[0, 1])
    v = rk["max_absdiff"] * 100
    order = v.sort_values()
    cols = ["#1f3b63" if c in SELECTED else "#c8c8c8"
            for c in order.index]
    y = np.arange(len(order))
    ax2.barh(y, order.values, color=cols, height=0.8)
    ax2.set_yticks(y)
    ax2.set_yticklabels([c.title() for c in order.index], fontsize=5.8)
    ax2.invert_yaxis()
    cut = order.values[5] + (order.values[6] - order.values[5]) / 2
    ax2.axhline(5.5, color="#b03030", ls="--", lw=1.3)
    ax2.annotate("selected top-6\n(closest to Ukraine)",
                 (order.values[5] + 0.6, 2.4), fontsize=8.5,
                 color="#1f3b63", fontweight="bold")
    ax2.set_xlabel("Worst-group pre-war slope deviation from Ukraine, "
                   "pp/yr")
    ax2.set_title("(b) Ranking: 50 eligible controls by closeness "
                  "to Ukraine", loc="left", fontsize=10)
    ax2.grid(axis="y", visible=False)

    fig.suptitle("Ukraine control-group selection logic",
                 fontsize=11.5, fontweight="bold", y=1.0)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(HERE / f"ukraine_control_logic.{ext}",
                    dpi=200 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved ukraine_control_logic.png / .pdf")

    print("\n  exclusion breakdown:")
    for b, n in counts.items():
        print(f"    {b.replace(chr(10), ' '):<42} {n:>3}")
    print(f"    {'ELIGIBLE':<42} {int(el.eligible.sum()):>3}")


if __name__ == "__main__":
    main()
