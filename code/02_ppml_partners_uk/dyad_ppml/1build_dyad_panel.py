#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 EU 国家 x 伙伴国 x 年 的双边合作面板 (P_ijt)。

对应新设定中的因变量：
    P_ijt = 国家 i 与国家 j 在第 t 年的共同发表论文数

其中 i 遍历 EU-27（焦点国），j 遍历该论文上出现的其他所有国家（含 UNITED
KINGDOM、其他 EU 国家、以及第三国）。原始输入 eu_articles.txt 收录了所有
至少含一个 EU-27 国家的论文，因此对任意 i in EU-27，其全部双边组合都完整
可得。

输出
    dyad_panel.csv   原始长表（未筛选、未补零），供描述性/画图脚本使用：
        focal_country, partner_country, year, paper_count
    dyad_panel.dta   估计用的基线平衡面板（取代 10prepare_panel.do）：
        在 csv 基础上补零、生成
        uk/post/post_uk 处理变量与 pair/focal_year/focal_id/partner_id。
        基线 INCL_EU=1，保留 EU 内部合作，故不剔除 EU 伙伴。
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, require  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = CODE / "00_data_processing/eu_articles/eu_articles.txt"

YEAR_MIN, YEAR_MAX = 2005, 2024

UK = "UNITED KINGDOM"

# 基线分析参数（与 _setup.do 保持一致）。改这些值无需改其他文件。
POST_YEAR = 2017     # Post_t = 1[t >= 2017]


ALIASES = {
    "CZECH REPUBLIC": "CZECHIA",
    "SLOVAKIA": "SLOVAK REPUBLIC",
    "FRENCH-POLYNESIA": "FRANCE",
    "GUADELOUPE": "FRANCE",
    "FRENCH-GUIANA": "FRANCE",
    "SERBIA AND MONTENEGRO": "REPUBLIC OF SERBIA",
    "BYELARUS": "BELARUS",
    "IRAN, ISLAMIC REP.": "IRAN",
    "KOREA, REP.": "SOUTH KOREA",
    "UK": UK,
    "GREAT BRITAIN": UK,
    "ENGLAND": UK,
    "SCOTLAND": UK,
    "WALES": UK,
    "NORTHERN IRELAND": UK,
    "NORTH-IRELAND": UK,
}

SPECIAL_SUFFIXES = ("REP.", "ISLAMIC REP.")


def parse_countries(s: str) -> list[str]:
    """把 countries 字段拆成国名列表，并套用别名。"""
    if not s:
        return []
    parts = [p.strip().upper() for p in s.split(",")]
    out: list[str] = []
    i = 0
    while i < len(parts):
        p = parts[i]
        if not p or p == "NAN":
            i += 1
            continue
        # 兼容旧版带逗号的标签
        if i + 1 < len(parts) and parts[i + 1] in SPECIAL_SUFFIXES:
            p = f"{p}, {parts[i + 1]}"
            i += 2
        else:
            i += 1
        out.append(ALIASES.get(p, p))
    return out

# EU-27（与 code/06_bridging/eu/cal_heatmap.py 一致）
EU27 = (
    "AUSTRIA", "BELGIUM", "BULGARIA", "CROATIA", "CYPRUS", "CZECHIA",
    "DENMARK", "ESTONIA", "FINLAND", "FRANCE", "GERMANY", "GREECE",
    "HUNGARY", "IRELAND", "ITALY", "LATVIA", "LITHUANIA", "LUXEMBOURG",
    "MALTA", "NETHERLANDS", "POLAND", "PORTUGAL", "ROMANIA",
    "SLOVAK REPUBLIC", "SLOVENIA", "SPAIN", "SWEDEN",
)
EU27_SET = set(EU27)


def count_dyads() -> pd.DataFrame:
    """一次性读入原始论文清单，累计 (i, j, t) 的共同发表数。"""
    tally: Counter[tuple[str, str, int]] = Counter()

    df = pd.read_csv(
        RAW,
        dtype={"OST_BK": str, "Annee_Bibliographique": str, "countries": str},
    )
    df = df.dropna(subset=["countries", "Annee_Bibliographique"])
    years = pd.to_numeric(df["Annee_Bibliographique"], errors="coerce")
    keep = years.between(YEAR_MIN, YEAR_MAX)
    df = df[keep]
    years = years[keep].astype(int)
    print(f"  loaded {len(df):,} articles")

    # 第一步：生成所有 country pair（任意国家都当焦点国）
    for year, raw in zip(years, df["countries"]):
        uniq = set(parse_countries(raw))
        if len(uniq) < 2:
            continue
        for focal in uniq:
            for partner in uniq:
                if partner != focal:
                    tally[(focal, partner, year)] += 1
    print(f"  tallied {len(tally):,} dyad-years (all pairs)")

    panel = pd.DataFrame(
        [(f, p, y, n) for (f, p, y), n in tally.items()],
        columns=["focal_country", "partner_country", "year", "paper_count"],
    )

    # 第二步：筛选焦点国属于 EU-27 的 pair
    panel = panel[panel["focal_country"].isin(EU27_SET)]
    print(f"  kept    {len(panel):,} dyad-years (EU-27 focal)")

    return panel.sort_values(["focal_country", "partner_country", "year"])


def build_balanced_panel(long: pd.DataFrame) -> pd.DataFrame:
    """产出可直接估计的平衡面板（保留全部伙伴，不做体量门槛过滤）。

    步骤：
      1. 补零成 focal x partner x year 的平衡面板；
      2. 生成 uk / post / post_uk 处理变量与 pair / focal_year 分组变量。
    """
    years = sorted(long["year"].unique())
    return _balance_and_vars(long.copy(), years)


def _balance_and_vars(kept: pd.DataFrame, years: list) -> pd.DataFrame:
    """对筛后的长表补零成平衡面板并生成变量。"""
    # ── 2. 补零成平衡面板（每个 focal-partner 对 x 全部年份）────────
    pairs = kept[["focal_country", "partner_country"]].drop_duplicates()
    grid = pairs.merge(pd.DataFrame({"year": years}), how="cross")
    panel = grid.merge(kept, how="left",
                       on=["focal_country", "partner_country", "year"])
    panel["paper_count"] = panel["paper_count"].fillna(0.0)

    # ── 3. 处理变量与分组 ──────────────────────────────────────────
    panel["uk"] = (panel["partner_country"] == UK).astype("int8")
    panel["post"] = (panel["year"] >= POST_YEAR).astype("int8")
    panel["post_uk"] = (panel["post"] * panel["uk"]).astype("int8")
    panel["pair"] = panel.groupby(
        ["focal_country", "partner_country"]).ngroup() + 1
    panel["focal_id"] = panel.groupby("focal_country").ngroup() + 1
    panel["focal_year"] = panel.groupby(
        ["focal_country", "year"]).ngroup() + 1
    panel["partner_id"] = panel.groupby("partner_country").ngroup() + 1
    return panel.sort_values(["focal_country", "partner_country", "year"]) \
                .reset_index(drop=True)


def main() -> None:
    print("=" * 78)
    print("Build EU-27 x partner x year dyadic panel (P_ijt)")
    print("=" * 78)

    panel = count_dyads()

    print(f"\nrows                 {len(panel):,}")
    print(f"focal countries      {panel.focal_country.nunique()}")
    print(f"partners             {panel.partner_country.nunique()}")
    print(f"years                {panel.year.min()}-{panel.year.max()}")
    uk = panel[panel.partner_country == UK]
    print(f"\nEU-UK dyad-years     {len(uk):,}")
    print(uk.groupby("year").paper_count.sum().to_string())

    out_csv = HERE / "dyad_panel.csv"
    panel.to_csv(out_csv, index=False)
    print(f"\nsaved {out_csv}")

    # ── 直接产出估计用的平衡面板 dta（取代 10prepare_panel.do）──────
    bp = build_balanced_panel(panel)
    out_dta = HERE / "dyad_panel.dta"
    bp.to_stata(out_dta, write_index=False, version=118)

    print("\n" + "=" * 70)
    print("Balanced dyadic panel (baseline)")
    print("=" * 70)
    nz = (bp["paper_count"] == 0).mean() * 100
    print(f"obs                 {len(bp):,}")
    print(f"focal countries     {bp.focal_country.nunique()}")
    print(f"partners            {bp.partner_country.nunique()}")
    print(f"years               {bp.year.min()}-{bp.year.max()}")
    print(f"zeros               {(bp['paper_count'] == 0).sum():,}  "
          f"({nz:.1f}%)")
    print(f"Post starts         {POST_YEAR}   (all partners, no threshold)")
    print(f"\nsaved {out_dta}")


if __name__ == "__main__":
    main()
