#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
描述统计的专题可视化（未加权国家均值口径）。

图 1  desc_shares_trend.pdf
      四组份额各自一个面板，带跨成员国的 IQR 带，看各自的演变路径

图 2  desc_uk_share_heatmap.pdf
      27 国 x 20 年的英国份额热力图，按 pre 期依赖度排序

图 3  desc_uk_share_slope.pdf
      各国英国份额的 pre/post 变化（dumbbell），看谁退得多

输入 desc_eu_portfolio.csv、desc_shares_country_year.csv
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

GROUPS = ["EU-internal", "UK", "CHINA+US", "other"]
COLOURS = {"EU-internal": "#214194", "UK": "#BE2738",
           "CHINA+US": "#D7B754", "other": "#6E8098"}
TITLES = {
    "EU-internal": "Other EU-27 members",
    "UK": "United Kingdom",
    "CHINA+US": "China + United States",
    "other": "Rest of the world",
}
REF = 2016.5


def pretty(s: str) -> str:
    return {"SLOVAK REPUBLIC": "Slovakia", "CZECHIA": "Czechia"}.get(
        s, s.title())


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def fig_trend(tu: pd.DataFrame) -> None:
    """四组份额各一面板，带 IQR 带。"""
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    yrs = tu.index.to_numpy()

    for ax, g in zip(axes.ravel(), GROUPS):
        c = COLOURS[g]
        ax.fill_between(yrs, tu[f"p25_{g}"], tu[f"p75_{g}"], color=c,
                        alpha=0.16, lw=0, label="IQR across members")
        ax.plot(yrs, tu[f"sh_{g}"], marker="o", ms=4, lw=1.9, color=c,
                label="mean across 27 members")
        ax.axvline(REF, color="#555555", ls="--", lw=1.1, alpha=0.75,
                   label="Brexit referendum")

        a, b = tu[f"sh_{g}"].iloc[0], tu[f"sh_{g}"].iloc[-1]
        ax.set_title(f"{TITLES[g]}    {a:.1f}% → {b:.1f}%  "
                     f"({b - a:+.1f} pp)", fontsize=10.5)
        ax.grid(alpha=0.22, ls=":")
        ax.set_ylabel("Share of portfolio (%)", fontsize=9.5)
        integer_xaxis(ax)

    for ax in axes[1]:
        ax.set_xlabel("Year")

    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=len(l),
               bbox_to_anchor=(0.5, -0.025))
    fig.suptitle("Composition of the typical EU-27 member's collaboration "
                 "portfolio\nunweighted mean of country-level shares",
                 fontsize=12.5, y=0.98)
    fig.tight_layout(rect=(0, 0.05, 1, 0.945))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"desc_shares_trend.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved desc_shares_trend.pdf / .png")


def fig_heatmap(sh: pd.DataFrame) -> None:
    """27 国 x 20 年的英国份额热力图。"""
    m = sh.pivot(index="focal_country", columns="year", values="UK")
    order = (sh[sh["year"] <= 2016].groupby("focal_country")["UK"].mean()
             .sort_values(ascending=False).index)
    m = m.loc[order]

    fig, ax = plt.subplots(figsize=(11, 7.4))
    im = ax.imshow(m.to_numpy(), aspect="auto", cmap="RdYlBu_r",
                   interpolation="nearest")

    ax.set_xticks(range(len(m.columns)))
    ax.set_xticklabels([int(y) for y in m.columns], rotation=90, fontsize=8)
    ax.set_yticks(range(len(m.index)))
    ax.set_yticklabels([pretty(c) for c in m.index], fontsize=9)

    # 2016/2017 分界
    x = list(m.columns).index(2017) - 0.5
    ax.axvline(x, color="black", lw=1.8)
    ax.text(x + 0.25, -1.1, "Post", fontsize=9, va="bottom")
    ax.text(x - 0.25, -1.1, "Pre", fontsize=9, va="bottom", ha="right")

    cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.035)
    cb.set_label("UK share of the member's portfolio (%)", fontsize=9.5)

    ax.set_title("UK's share of each EU-27 member's collaboration portfolio\n"
                 "rows sorted by pre-referendum mean", fontsize=12, pad=16)
    ax.set_xlabel("Year")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"desc_uk_share_heatmap.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved desc_uk_share_heatmap.pdf / .png")


def fig_dumbbell(sh: pd.DataFrame) -> None:
    """各国 pre vs post 的份额变化，UK 与 EU-internal 并列。"""
    sh = sh.copy()
    sh["period"] = np.where(sh["year"] <= 2016, "pre", "post")
    agg = sh.groupby(["focal_country", "period"])[
        ["UK", "EU-internal"]].mean().unstack("period")

    fig, (axl, axr) = plt.subplots(1, 2, figsize=(12.6, 7.6), sharey=True)

    for ax, g in ((axl, "UK"), (axr, "EU-internal")):
        d = pd.DataFrame({
            "pre": agg[(g, "pre")], "post": agg[(g, "post")]})
        d = d.sort_values("pre")
        y = np.arange(len(d))
        c = COLOURS[g]

        for yi, (pre, post) in enumerate(zip(d["pre"], d["post"])):
            ax.plot([pre, post], [yi, yi], color="#BBBBBB", lw=1.6, zorder=1)
        ax.scatter(d["pre"], y, s=42, facecolors="white", edgecolors=c,
                   linewidths=1.7, zorder=3, label="pre (2005-2016)")
        ax.scatter(d["post"], y, s=42, color=c, zorder=3,
                   label="post (2017-2024)")

        ax.set_yticks(y)
        ax.set_yticklabels([pretty(i) for i in d.index], fontsize=9)
        ax.set_xlabel("Share of the member's portfolio (%)")
        ax.set_title(TITLES[g], fontsize=11.5)
        ax.grid(axis="x", alpha=0.22, ls=":")
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.legend(frameon=False, fontsize=8.5, loc="lower right")

    fig.suptitle("Shift in portfolio shares, before vs after the referendum",
                 fontsize=12.5, y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"desc_uk_share_slope.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)
    print("saved desc_uk_share_slope.pdf / .png")


def main() -> None:
    tu = pd.read_csv(HERE / "desc_eu_portfolio.csv", index_col="year")
    sh = pd.read_csv(HERE / "desc_shares_country_year.csv")
    fig_trend(tu)
    fig_heatmap(sh)
    fig_dumbbell(sh)


if __name__ == "__main__":
    main()
