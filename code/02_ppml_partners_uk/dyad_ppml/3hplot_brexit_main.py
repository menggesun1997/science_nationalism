#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brexit 主图：大国对照池下的事件研究路径 + 逐个 EU 国家累计效应。

输入 big_control_event.csv、big_control_by_country.csv
输出 brexit_dyad_main.pdf / .png
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
REF_START, POST_YEAR, REF_YEAR = 2016, 2021, 2020

BLUE = "#2E6F9E"
ORANGE = "#D98C3F"
GREY = "#7F7F7F"


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def panel_event(ax, es: pd.DataFrame) -> None:
    d = es[es["spec"] == "big_control"].sort_values("year")
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(REF_START, color=GREY, ls="--", lw=1.1,
               label=f"Referendum ({REF_START})")
    ax.axvline(POST_YEAR, color=ORANGE, ls="--", lw=1.3,
               label=f"Formal exit ({POST_YEAR})")
    ax.fill_between(d["year"], d["ci_lo_pct"], d["ci_hi_pct"],
                    color=BLUE, alpha=0.16, lw=0)
    ax.plot(d["year"], d["pct_change"], marker="o", ms=4.2, lw=1.7,
            color=BLUE, label="EU collaboration with the UK")
    ax.set_xlabel("Year")
    ax.set_ylabel("Change relative to "
                  f"{REF_YEAR} (%)")
    ax.set_title("(a) Event-study path", fontsize=10.5, loc="left")
    # Nature 风格：横排整数年刻度，每 5 年一个主刻度，年度小刻度，刻度朝内。
    yr_min, yr_max = int(d["year"].min()), int(d["year"].max())
    ax.set_xticks(range(2005, yr_max + 1, 5))
    ax.set_xticks(range(yr_min, yr_max + 1), minor=True)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))
    ax.set_xlim(yr_min - 0.5, yr_max + 0.5)
    ax.tick_params(axis="both", which="major", direction="in", length=4)
    ax.tick_params(axis="x", which="minor", direction="in", length=2)
    ax.tick_params(axis="x", rotation=0)
    ax.grid(alpha=0.25, ls=":")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def panel_country(ax, bc: pd.DataFrame, term: str, title: str,
                  order: list[str] | None = None) -> None:
    """逐国点估计。order 给定时按该国家顺序排列（两个面板共用一套纵轴）。"""
    if order is None:
        d = bc.sort_values(f"{term}_pct").reset_index(drop=True)
    else:
        d = (bc.set_index("focal_country").loc[order]
             .reset_index())
    y = np.arange(len(d))
    sig = (d[f"{term}_p"] < 0.05).values
    colors = np.where(d[f"{term}_pct"] < 0, BLUE, ORANGE)

    ax.axvline(0, color="black", lw=0.8)
    for yi, (lo, hi, c) in enumerate(zip(d[f"{term}_lo"], d[f"{term}_hi"],
                                         colors)):
        ax.hlines(yi, lo, hi, color=c, lw=1.4, alpha=0.45)
    ax.scatter(d.loc[sig, f"{term}_pct"], y[sig], s=42,
               color=colors[sig], zorder=3, label="$p < 0.05$")
    ax.scatter(d.loc[~sig, f"{term}_pct"], y[~sig], s=42, facecolors="white",
               edgecolors=colors[~sig], linewidths=1.2, zorder=3,
               label="not significant")

    ax.set_yticks(y)
    ax.set_yticklabels([c.title() for c in d["focal_country"]], fontsize=7.0)
    # 对 p<0.05 的国家，纵轴标签加粗并上色，和填充点一致，便于一眼识别。
    for tick, is_sig, c in zip(ax.get_yticklabels(), sig, colors):
        if is_sig:
            tick.set_fontweight("bold")
            tick.set_color(c)
    ax.set_ylim(-0.8, len(d) - 0.2)
    ax.set_xlabel("Change in collaboration with the UK (%)")
    ax.set_title(title, fontsize=10.5, loc="left")
    ax.grid(axis="x", alpha=0.25, ls=":")


def main() -> None:
    es = pd.read_csv(HERE / "big_control_event.csv")
    bc = pd.read_csv(HERE / "big_control_by_country.csv")

    fig, axes = plt.subplots(1, 3, figsize=(15.8, 6.6),
                             gridspec_kw={"width_ratios": [1.3, 1.0, 1.0]})
    panel_event(axes[0], es)
    # 面板 (b) 按 β1 排序；面板 (c) 沿用同一国家顺序，便于逐行对照。
    b1_order = bc.sort_values("b1_pct")["focal_country"].tolist()
    panel_country(axes[1], bc, "b1",
                  "(b) Referendum period, $\\beta_1$", order=b1_order)
    panel_country(axes[2], bc, "b2",
                  "(c) Post-exit period, $\\beta_2$", order=b1_order)

    h0, l0 = axes[0].get_legend_handles_labels()
    h1, l1 = axes[1].get_legend_handles_labels()
    fig.legend(h0 + h1, l0 + l1, frameon=False, loc="lower center",
               ncol=len(l0 + l1), bbox_to_anchor=(0.5, -0.01), fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"brexit_dyad_main.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved brexit_dyad_main.pdf / .png")


if __name__ == "__main__":
    main()
