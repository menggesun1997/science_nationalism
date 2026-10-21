#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基线 vs 大国对照组：event study 路径与两段 beta 对比图。

输入 big_control_event.csv、big_control_twoperiod.csv
输出 big_control_compare.pdf / .png
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
GREEN = "#3F8F6B"
RED = "#B5485D"
GREY = "#7F7F7F"
SPECS = {"baseline": ("All 200 partners (baseline)", BLUE),
         "big_control": ("17 large mature peers", GREEN)}


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def panel_event(ax, es: pd.DataFrame) -> None:
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(REF_START - 0.5, color=GREY, ls="--", lw=1.1,
               label=f"Referendum ({REF_START})")
    ax.axvline(POST_YEAR - 0.5, color=RED, ls="--", lw=1.2,
               label=f"Formal exit ({POST_YEAR})")

    for spec, (label, color) in SPECS.items():
        d = es[es["spec"] == spec].sort_values("year")
        ax.fill_between(d["year"], d["ci_lo_pct"], d["ci_hi_pct"],
                        color=color, alpha=0.14, lw=0)
        ax.plot(d["year"], d["pct_change"], marker="o", ms=4.0, lw=1.6,
                color=color, label=label)

    ax.set_xlabel("Year")
    ax.set_ylabel("Change in collaboration with the UK (%)\n"
                  f"relative to {REF_YEAR}")
    ax.set_title("Event study path by control group", fontsize=10.5)
    ax.grid(alpha=0.25, ls=":")
    integer_xaxis(ax)


def panel_coefs(ax, tp: pd.DataFrame) -> None:
    """两段 beta 的分组点估计，基线与大国对照组并排。"""
    terms = ["postref_uk", "brexit_uk", "cumulative"]
    labels = [f"$\\beta_1$ Post-ref\n({REF_START}–)",
              f"$\\beta_2$ Brexit\n({POST_YEAR}–, incr.)",
              "$\\beta_1+\\beta_2$\ncumulative"]
    offs = {"baseline": 0.17, "big_control": -0.17}

    ax.axvline(0, color="black", lw=0.8)
    for spec, (label, color) in SPECS.items():
        for k, term in enumerate(terms):
            r = tp[(tp["spec"] == spec) & (tp["term"] == term)].iloc[0]
            yi = (len(terms) - 1 - k) + offs[spec]
            ax.hlines(yi, r["ci_lo_pct"], r["ci_hi_pct"], color=color,
                      lw=2.0, alpha=0.8)
            ax.scatter(r["pct_change"], yi, s=62, color=color, zorder=3,
                       label=label if k == 0 else None)
            pv = float(r["pvalue"])
            star = ("***" if pv < .01 else "**" if pv < .05
                    else "*" if pv < .10 else "")
            ax.annotate(f"{float(r['pct_change']):+.2f}%{star}",
                        xy=(r["pct_change"], yi), xytext=(0, 8),
                        textcoords="offset points", ha="center",
                        fontsize=8.8, color=color, fontweight="bold")

    ax.set_yticks(range(len(terms)))
    ax.set_yticklabels(labels[::-1], fontsize=9)
    ax.set_ylim(-0.6, len(terms) - 0.4)
    ax.set_xlabel("Change in collaboration with the UK (%)")
    ax.set_title("Two-period coefficients, 95% CI", fontsize=10.5)
    ax.grid(axis="x", alpha=0.25, ls=":")


def main() -> None:
    es = pd.read_csv(HERE / "big_control_event.csv")
    tp = pd.read_csv(HERE / "big_control_twoperiod.csv")

    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.0),
                             gridspec_kw={"width_ratios": [1.3, 1.0]})
    panel_event(axes[0], es)
    panel_coefs(axes[1], tp)

    fig.suptitle("Control group sensitivity: all partners vs. large mature "
                 "research peers\ndyadic PPML, country-pair and "
                 "EU-country-year fixed effects, SE clustered on pair",
                 fontsize=11.5)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center",
               ncol=len(labels), bbox_to_anchor=(0.5, -0.01), fontsize=9)
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"big_control_compare.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved big_control_compare.pdf / .png")


if __name__ == "__main__":
    main()
