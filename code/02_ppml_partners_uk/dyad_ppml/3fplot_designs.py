#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对照组选择对 event study 路径的影响（A0 / A1 / A2）。

三个设计的样本窗口都是 2005-2024，只有伙伴池不同：
  A0  全部 200 个伙伴（基线）
  A1  17 个大型成熟科研国（BIG 名单）
  A2  按 2005-2015 平均体量取前 25%（50 个伙伴）

输入 design_comparison_event.csv、design_comparison.csv
输出 design_overview.pdf / .png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent
REF_START, POST_YEAR, REF_YEAR = 2016, 2021, 2020

ORDER = ["A0  all partners, 2005-",
         "A1  BIG list, 2005-",
         "A2  top-25% volume, 2005-"]
LABEL = {ORDER[0]: "A0  all 200 partners (baseline)",
         ORDER[1]: "A1  17 large mature peers",
         ORDER[2]: "A2  top-25% by volume (50)"}
COLOR = {ORDER[0]: "#2E6F9E", ORDER[1]: "#3F8F6B", ORDER[2]: "#D98A3C"}
GREY, RED = "#7F7F7F", "#B5485D"


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def main() -> None:
    es = pd.read_csv(HERE / "design_comparison_event.csv")
    es = es[es["design"].isin(ORDER)]

    fig, ax = plt.subplots(figsize=(9.2, 5.4))

    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(REF_START - 0.5, color=GREY, ls="--", lw=1.1,
               label=f"Referendum ({REF_START})")
    ax.axvline(POST_YEAR - 0.5, color=RED, ls="--", lw=1.2,
               label=f"Formal exit ({POST_YEAR})")

    for d in ORDER:
        s = es[es["design"] == d].sort_values("year")
        emph = d == ORDER[1]
        ax.fill_between(s["year"], s["ci_lo_pct"], s["ci_hi_pct"],
                        color=COLOR[d], alpha=0.13 if emph else 0.08, lw=0)
        ax.plot(s["year"], s["pct_change"], marker="o",
                ms=4.4 if emph else 3.8, lw=2.2 if emph else 1.5,
                color=COLOR[d], alpha=1.0 if emph else 0.8, label=LABEL[d])

    ax.set_xlabel("Year")
    ax.set_ylabel("Change in collaboration with the UK (%)\n"
                  f"relative to {REF_YEAR}")
    ax.set_title("Control-group choice and the estimated Brexit path\n"
                 "EU-27 collaboration with the UK, dyadic PPML with "
                 "country-pair and EU-country-year FE, 95% CI",
                 fontsize=11)
    ax.grid(alpha=0.25, ls=":")
    integer_xaxis(ax)

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center",
               ncol=len(labels), bbox_to_anchor=(0.5, -0.02), fontsize=8.8)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"design_overview.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved design_overview.pdf / .png")


if __name__ == "__main__":
    main()
