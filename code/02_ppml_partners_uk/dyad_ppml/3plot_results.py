#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""绘制 dyadic PPML 结果：event study 路径 + 各 EU 国家效应。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent
REF_YEAR = 2016
POST_YEAR = 2017

BLUE = "#2E6F9E"
RED = "#B5485D"
GREY = "#7F7F7F"


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def plot_event_study() -> None:
    es = pd.read_csv(HERE / "st_eu_to_uk_event.csv").sort_values("year")
    fig, ax = plt.subplots(figsize=(8, 4.6))

    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(POST_YEAR - 0.5, color=RED, ls="--", lw=1.2, alpha=0.8,
               label="Brexit referendum / Post period starts")
    ax.fill_between(es["year"], es["ci_lo_pct"], es["ci_hi_pct"],
                    color=BLUE, alpha=0.18, lw=0, label="95% CI")
    ax.plot(es["year"], es["pct_change"], marker="o", ms=4.5, lw=1.6,
            color=BLUE, label=r"$e^{\beta_k}-1$")

    ax.set_xlabel("Year")
    ax.set_ylabel("Change in collaboration with the UK (%)\n"
                  f"relative to {REF_YEAR}")
    ax.set_title("Brexit and EU-27 collaboration with the UK\n"
                 "dyadic PPML, country-pair and EU-country-year fixed effects",
                 fontsize=11)
    ax.grid(alpha=0.25, ls=":")
    integer_xaxis(ax)

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center",
               ncol=len(labels), bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"event_study_uk_dyadic.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved event_study_uk_dyadic.pdf / .png")


def plot_by_country() -> None:
    d = pd.read_csv(HERE / "st_eu_to_uk_by_country.csv").sort_values("pct_change")
    pooled = pd.read_csv(HERE / "st_eu_to_uk_pooled.csv").iloc[0]
    y = range(len(d))

    fig, ax = plt.subplots(figsize=(7.2, 8))
    colors = [BLUE if s else GREY for s in d["sig_05"]]
    ax.hlines(y, d["ci_lo_pct"], d["ci_hi_pct"], color=colors, lw=1.6,
              alpha=0.75)
    ax.scatter(d["pct_change"], y, s=34, color=colors, zorder=3,
               label="Point estimate (solid = p < 0.05)")
    ax.axvline(0, color="black", lw=0.8)
    pooled_pct = float(pooled["pct_change"])
    ax.axvline(pooled_pct, color=RED, ls="--", lw=1.2,
               label=f"Pooled EU-27: {pooled_pct:+.1f}%")

    ax.set_yticks(list(y))
    ax.set_yticklabels(d["focal_country"], fontsize=9)
    ax.set_xlabel("Change in collaboration with the UK after Brexit (%)")
    ax.set_title("Country-specific Brexit effect on collaboration with the UK\n"
                 "PPML with partner and year fixed effects, 95% CI",
                 fontsize=11)
    ax.grid(axis="x", alpha=0.25, ls=":")
    ax.set_ylim(-0.8, len(d) - 0.2)

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center",
               ncol=len(labels), bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.045, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"brexit_effect_by_eu_country.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved brexit_effect_by_eu_country.pdf / .png")


if __name__ == "__main__":
    plot_event_study()
    plot_by_country()
