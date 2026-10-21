#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法国、德国各自 top10 合作伙伴的份额逐年演变。

对每个焦点国 i：
  - 份额_ijt = P_ijt / sum_j P_ijt   （该国当年全部对外合作中，伙伴 j 的占比）
  - top10 按整段 2005-2024 的合作总量选取
  - 其余伙伴合并为 "Others"

每国出两张图：
  堆叠面积图（看整体结构） + 折线图（看单个伙伴的升降）

输入 dyad_panel.csv（focal_country, partner_country, year, paper_count）
输出 top10_<country>_stack.pdf/.png、top10_<country>_lines.pdf/.png
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, require  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = CODE / "00_data_processing/eu_articles/eu_articles.txt"

FOCALS = ["FRANCE", "GERMANY"]
TOPN = 10
TOP_HEAT = 50          # 热力图展示的合作国数量
HEAT_FOCALS = ["FRANCE"]
REF = 2016.5

# 与 1build_dyad_panel.py 口径一致：英国各地区合并、异名归并
ALIASES = {
    "CZECH REPUBLIC": "CZECHIA", "SLOVAKIA": "SLOVAK REPUBLIC",
    "FRENCH-POLYNESIA": "FRANCE", "GUADELOUPE": "FRANCE",
    "FRENCH-GUIANA": "FRANCE", "SERBIA AND MONTENEGRO": "REPUBLIC OF SERBIA",
    "BYELARUS": "BELARUS", "IRAN, ISLAMIC REP.": "IRAN",
    "KOREA, REP.": "SOUTH KOREA", "UK": "UNITED KINGDOM",
    "GREAT BRITAIN": "UNITED KINGDOM", "ENGLAND": "UNITED KINGDOM",
    "SCOTLAND": "UNITED KINGDOM", "WALES": "UNITED KINGDOM",
    "NORTHERN IRELAND": "UNITED KINGDOM", "NORTH-IRELAND": "UNITED KINGDOM",
}
SPECIAL_SUFFIXES = ("REP.", "ISLAMIC REP.")


def parse_countries(s: str) -> list[str]:
    if not s:
        return []
    parts = [p.strip().upper() for p in s.split(",")]
    out, i = [], 0
    while i < len(parts):
        p = parts[i]
        if not p or p == "NAN":
            i += 1
            continue
        if i + 1 < len(parts) and parts[i + 1] in SPECIAL_SUFFIXES:
            p = f"{p}, {parts[i + 1]}"
            i += 2
        else:
            i += 1
        out.append(ALIASES.get(p, p))
    return out


def build_counts(focals: list[str]):
    """直接扫源文件。

    返回 (dyad 计数表, 焦点国国际合作文章数表)：
      - tally[(f, j, y)]      焦点国 f 当年与伙伴 j 共同发表的文章数（一篇算一次）
      - intl_total[(f, y)]    焦点国 f 当年至少含一个外国合作者的文章数（一篇算一次）
                              这是份额的分母，纯本土文章不计入。
    """
    require(RAW, "Run 6rebuild_eu_articles.py first.")
    fset = set(focals)
    tally: dict[tuple[str, str, int], int] = defaultdict(int)
    intl_total: dict[tuple[str, int], int] = defaultdict(int)
    n = 0
    for ch in pd.read_csv(RAW, dtype=str, chunksize=500_000):
        for raw_c, raw_y in zip(ch["countries"].fillna(""),
                                ch["Annee_Bibliographique"].fillna("")):
            try:
                y = int(raw_y)
            except ValueError:
                continue
            if not (2005 <= y <= 2024):
                continue
            uniq = set(parse_countries(raw_c))
            hit = uniq & fset
            if not hit:
                continue
            for f in hit:
                partners = uniq - {f}
                if not partners:          # 纯本土文章，不计入国际合作
                    continue
                intl_total[(f, y)] += 1    # 国际合作文章：一篇算一次
                for j in partners:
                    tally[(f, j, y)] += 1
        n += len(ch)
        print(f"  ... scanned {n:,} articles")
    rows = [(f, j, y, c) for (f, j, y), c in tally.items()]
    counts = pd.DataFrame(rows, columns=["focal_country", "partner_country",
                                         "year", "paper_count"])
    totals = pd.DataFrame(
        [(f, y, c) for (f, y), c in intl_total.items()],
        columns=["focal_country", "year", "intl_articles"],
    )
    return counts, totals


def pretty(s: str) -> str:
    special = {
        "UNITED STATES": "United States", "UNITED KINGDOM": "United Kingdom",
        "SLOVAK REPUBLIC": "Slovakia", "CZECHIA": "Czechia",
        "RUSSIAN FEDERATION": "Russia", "SOUTH KOREA": "South Korea",
    }
    return special.get(s, s.title())


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def shares_for(d: pd.DataFrame, totals: pd.DataFrame, focal: str):
    """返回 (份额透视表[year x top10], top10 列表)。

    份额 = 与伙伴 j 共同发表的文章数 / 该国当年国际合作文章总数。
    分子分母都按"一篇文章算一次"统计；分母是去重后的国际合作文章数，
    一篇多国论文只计一次（不再是 dyad 链接数之和）。
    """
    g = d[d["focal_country"] == focal].copy()
    years = sorted(g["year"].unique())

    tot_by_year = (totals[totals["focal_country"] == focal]
                   .set_index("year")["intl_articles"]
                   .reindex(years, fill_value=0))
    top10 = (g.groupby("partner_country")["paper_count"].sum()
             .sort_values(ascending=False).head(TOPN).index.tolist())

    piv = (g[g["partner_country"].isin(top10)]
           .pivot_table(index="year", columns="partner_country",
                        values="paper_count", aggfunc="sum", fill_value=0)
           .reindex(index=years, fill_value=0))
    piv = piv.div(tot_by_year, axis=0) * 100
    return piv[[c for c in top10 if c in piv.columns]], top10


def plot_lines(piv: pd.DataFrame, focal: str) -> None:
    cols = list(piv.columns)
    cmap = plt.cm.tab10(np.linspace(0, 1, len(cols)))
    fig, ax = plt.subplots(figsize=(10, 5.6))
    yrs = piv.index.to_numpy()

    for i, c in enumerate(cols):
        ax.plot(yrs, piv[c].to_numpy(), marker="o", ms=3.5, lw=1.7,
                color=cmap[i], label=pretty(c))
    ax.axvline(REF, color="#333333", ls="--", lw=1.2, alpha=0.8,
               label="Brexit referendum")

    ax.set_xlim(yrs.min(), yrs.max())
    ax.set_ylabel("Share of the country's total collaboration (%)")
    ax.set_xlabel("Year")
    ax.set_title(f"{pretty(focal)}: each top-{TOPN} partner's share over time",
                 fontsize=12)
    ax.grid(alpha=0.22, ls=":")
    integer_xaxis(ax)

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="center left",
               bbox_to_anchor=(0.99, 0.5), fontsize=9)
    fig.tight_layout(rect=(0, 0, 0.86, 1))
    stem = f"top10_{focal.split()[0].lower()}_lines"
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {stem}.pdf / .png")


def plot_intl_total(totals: pd.DataFrame, focal: str) -> None:
    """焦点国逐年国际合作文章总数（含至少一个外国合作者，一篇算一次）。"""
    g = (totals[totals["focal_country"] == focal]
         .sort_values("year"))
    yrs = g["year"].to_numpy()
    vals = g["intl_articles"].to_numpy()

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.plot(yrs, vals, marker="o", ms=4, lw=1.9, color="#1f4e79",
            label="International collaboration articles")
    ax.axvline(REF, color="#333333", ls="--", lw=1.2, alpha=0.8,
               label="Brexit referendum")
    ax.set_xlim(yrs.min(), yrs.max())
    ax.set_ylim(0, vals.max() * 1.05)
    ax.set_ylabel("International collaboration articles")
    ax.set_xlabel("Year")
    ax.set_title(f"{pretty(focal)}: total international collaboration "
                 f"articles, 2005-2024", fontsize=12)
    ax.grid(alpha=0.22, ls=":")
    integer_xaxis(ax)

    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, loc="lower center",
               ncol=len(labels), bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    stem = f"intl_total_{focal.split()[0].lower()}_lines"
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {stem}.pdf / .png")


def top_shares(d: pd.DataFrame, totals: pd.DataFrame, focal: str, topn: int):
    """返回前 topn 合作国的 share 透视表 [partner x year]，按总量排序。

    share = 与伙伴共同发表文章数 / 该国当年国际合作文章总数 (%)。
    """
    g = d[d["focal_country"] == focal].copy()
    years = sorted(g["year"].unique())
    tot_by_year = (totals[totals["focal_country"] == focal]
                   .set_index("year")["intl_articles"].reindex(years, fill_value=0))
    order = (g.groupby("partner_country")["paper_count"].sum()
             .sort_values(ascending=False).head(topn).index.tolist())
    piv = (g[g["partner_country"].isin(order)]
           .pivot_table(index="partner_country", columns="year",
                        values="paper_count", aggfunc="sum", fill_value=0)
           .reindex(index=order, columns=years, fill_value=0))
    piv = piv.div(tot_by_year, axis=1) * 100
    return piv


def plot_heatmap(d: pd.DataFrame, totals: pd.DataFrame, focal: str) -> None:
    """前 TOP_HEAT 合作国 x 年份的 share 热力图。"""
    piv = top_shares(d, totals, focal, TOP_HEAT)
    years = list(piv.columns)
    partners = list(piv.index)

    fig, ax = plt.subplots(figsize=(11, 13))
    im = ax.imshow(piv.to_numpy(), aspect="auto", cmap="YlOrRd",
                   interpolation="nearest")
    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([f"{int(y)}" for y in years], rotation=90, fontsize=8)
    ax.set_yticks(range(len(partners)))
    ax.set_yticklabels([pretty(p) for p in partners], fontsize=8)
    ref_idx = min(range(len(years)), key=lambda i: abs(years[i] - REF))
    ax.axvline(ref_idx + 0.5, color="#1f4e79", ls="--", lw=1.3)
    ax.set_title(f"{pretty(focal)}: top-{TOP_HEAT} partners' share of "
                 f"international collaboration (%), 2005-2024", fontsize=12)

    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Share of int'l collaboration articles (%)")
    fig.tight_layout()
    stem = f"heatmap_top{TOP_HEAT}_{focal.split()[0].lower()}"
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    piv.to_csv(HERE / f"{stem}.csv")
    print(f"saved {stem}.pdf / .png / .csv")


def main() -> None:
    print("building counts from eu_articles.txt ...")
    d, totals = build_counts(FOCALS)
    for focal in HEAT_FOCALS:
        plot_heatmap(d, totals, focal)
    for focal in FOCALS:
        piv, top10 = shares_for(d, totals, focal)
        print(f"\n{focal} top-{TOPN}: {[pretty(c) for c in top10]}")
        uk = piv["UNITED KINGDOM"] if "UNITED KINGDOM" in piv else None
        if uk is not None:
            print(f"  UK share  2005={uk.iloc[0]:.2f}%  "
                  f"2016={uk.loc[2016]:.2f}%  2024={uk.iloc[-1]:.2f}%")
        plot_lines(piv, focal)
        plot_intl_total(totals, focal)
        piv.to_csv(HERE / f"top10_{focal.split()[0].lower()}_shares.csv")
        (totals[totals["focal_country"] == focal].sort_values("year")
         .to_csv(HERE / f"intl_total_{focal.split()[0].lower()}.csv",
                 index=False))


if __name__ == "__main__":
    main()
