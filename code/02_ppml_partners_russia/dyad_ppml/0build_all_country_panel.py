#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 raw_data_2026 构建 全国家 x 全国家 x 年 的双边合作面板。

动机
----
dyad_panel.csv 只覆盖 10 个焦点国（俄罗斯 + 9 个候选控制国），无法回答
"哪些国家能当控制组"这个问题。本脚本把焦点国维度放开到所有国家，使
控制组筛选可以在完整候选集上进行，而不是在预设的 9 国里挑。

输入（$SCIENCE_NATIONALISM_RAW_2026，默认 ~/Dropbox/brexit_rawdata/raw_data_2026）
  article_brexit.txt        OST_BK|UID|Annee_Bibliographique|Code_Discipline|...
  article_cntry_brexit.txt  OST_BK|Pays   长表，一行一个 (论文, 国家)

输出
  all_country_dyad_panel.csv   country_a, country_b, year, paper_count
                               无向对，country_a < country_b（字典序），
                               只写非零单元

口径（与 6rebuild_eu_articles.py 保持一致）
  1. 国名经 cntry_convert.csv 映射到统一标签，再过 ALIGN 对齐下游标签。
  2. 英国各地区（ENGLAND/SCOTLAND/WALES/NORTH-IRELAND）先合并再去重，
     否则英格兰+苏格兰合著会被误判成国际合作。
  3. 年份限定 2005-2024。
  4. 单国论文（去重后只剩 1 个国家）不产生任何 dyad。
"""

from __future__ import annotations

import csv
import os
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from paths import CODE, require  # noqa: E402

RAW_2026 = Path(os.environ.get(
    "SCIENCE_NATIONALISM_RAW_2026",
    Path.home() / "Dropbox/brexit_rawdata/raw_data_2026",
)).expanduser()

CNTRY_FILE = RAW_2026 / "article_cntry_brexit.txt"
ARTICLE_FILE = RAW_2026 / "article_brexit.txt"
CONV_FILE = CODE / "00_data_processing/raw data processing/cntry_convert.csv"

OUT_FILE = HERE / "all_country_dyad_panel.csv"

YEAR_MIN, YEAR_MAX = 2005, 2024

# 与 6rebuild_eu_articles.py 的 ALIGN 完全一致，保证标签可与现有面板对接
ALIGN = {
    "CZECH REPUBLIC": "CZECHIA",
    "SLOVAKIA": "SLOVAK REPUBLIC",
    "KOREA, REP.": "SOUTH KOREA",
    "RUSSIA": "RUSSIAN FEDERATION",
    "BELARUS": "BYELARUS",
    "SERBIA": "REPUBLIC OF SERBIA",
    # 2006 年前南联盟未拆分，与现有面板口径一致地归入塞尔维亚
    "SERBIA AND MONTENEGRO": "REPUBLIC OF SERBIA",
    "TURKEY": "TURKIYE",
    "VIETNAM": "VIET NAM",
    # 下游沿用旧 dyad_panel.csv 的写法
    "IRAN": "IRAN, ISLAMIC REP.",
    # 海外属地并入本国，与旧 1build_dyad_panel.py 的 ALIASES 一致
    "FRENCH-GUIANA": "FRANCE",
    "FRENCH GUIANA": "FRANCE",
    "FRENCH POLYNESIA": "FRANCE",
    "GUADELOUPE": "FRANCE",
}


def load_country_map() -> dict[str, str]:
    """原始 Clarivate 国名 -> 统一标签。"""
    require(CONV_FILE, "Country-name crosswalk shipped with the repo.")
    conv = pd.read_csv(CONV_FILE)
    out: dict[str, str] = {}
    for raw, std in zip(conv["Clarivate country"], conv["Country"]):
        if pd.isna(raw) or pd.isna(std):
            continue
        key = str(raw).upper().strip()
        val = str(std).upper().strip()
        out[key] = ALIGN.get(val, val)
    return out


def load_years() -> dict[str, int]:
    """OST_BK -> 年份，只保留窗口内的论文。"""
    require(ARTICLE_FILE, "raw_data_2026 article metadata.")
    years: dict[str, int] = {}
    n = 0
    with ARTICLE_FILE.open(encoding="utf-8", errors="replace") as fh:
        next(fh)
        for line in fh:
            n += 1
            parts = line.rstrip("\n").split("|")
            if len(parts) < 3:
                continue
            try:
                y = int(parts[2])
            except ValueError:
                continue
            if YEAR_MIN <= y <= YEAR_MAX:
                years[parts[0]] = y
            if n % 5_000_000 == 0:
                print(f"  ... {n:,} rows, {len(years):,} in window")
    print(f"  rows {n:,} -> {len(years):,} articles in "
          f"{YEAR_MIN}-{YEAR_MAX}")
    return years


def collect_countries(cmap: dict[str, str],
                      years: dict[str, int]) -> dict[str, set[str]]:
    """OST_BK -> 去重国家标签集合。英国各地区在映射阶段已合并。"""
    require(CNTRY_FILE, "raw_data_2026 article-country long table.")
    per_article: dict[str, set[str]] = defaultdict(set)
    n_rows = n_kept = n_unmapped = 0
    unmapped: Counter[str] = Counter()

    with CNTRY_FILE.open(encoding="utf-8", errors="replace") as fh:
        next(fh)
        for line in fh:
            n_rows += 1
            parts = line.rstrip("\n").split("|")
            if len(parts) != 2:
                continue
            bk, raw = parts[0], parts[1].strip().upper()
            if not raw or bk not in years:
                continue
            std = cmap.get(raw)
            if std is None:
                n_unmapped += 1
                unmapped[raw] += 1
                continue
            per_article[bk].add(std)
            n_kept += 1
            if n_rows % 10_000_000 == 0:
                print(f"  ... {n_rows:,} rows, "
                      f"{len(per_article):,} articles")

    print(f"  rows {n_rows:,}   kept {n_kept:,}   unmapped {n_unmapped:,}")
    if unmapped:
        top = ", ".join(f"{k}({v:,})" for k, v in unmapped.most_common(10))
        print(f"  top unmapped labels: {top}")
    return per_article


def tally_dyads(per_article: dict[str, set[str]],
                years: dict[str, int]) -> Counter[tuple[str, str, int]]:
    """累计无向对 (a, b, year) 的共同发表数，a < b。"""
    tally: Counter[tuple[str, str, int]] = Counter()
    n_multi = 0
    for bk, countries in per_article.items():
        if len(countries) < 2:
            continue
        n_multi += 1
        y = years[bk]
        for a, b in combinations(sorted(countries), 2):
            tally[(a, b, y)] += 1
    print(f"  multi-country articles {n_multi:,} -> "
          f"{len(tally):,} non-zero dyad-years")
    return tally


def main() -> None:
    print("=" * 78)
    print("Build all-country dyadic collaboration panel")
    print("=" * 78)
    print(f"source: {RAW_2026}")

    print("\n[1/5] country-name crosswalk ...")
    cmap = load_country_map()
    print(f"  {len(cmap):,} raw labels mapped to "
          f"{len(set(cmap.values())):,} standard labels")

    print(f"\n[2/5] article years ({YEAR_MIN}-{YEAR_MAX}) ...")
    years = load_years()

    print("\n[3/5] article-country long table ...")
    per_article = collect_countries(cmap, years)

    print("\n[4/5] tally undirected dyads ...")
    tally = tally_dyads(per_article, years)

    print("\n[5/5] write panel ...")
    with OUT_FILE.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["country_a", "country_b", "year", "paper_count"])
        for (a, b, y), n in sorted(tally.items()):
            w.writerow([a, b, y, n])

    print(f"  wrote {len(tally):,} rows to {OUT_FILE}")
    print(f"  size {OUT_FILE.stat().st_size / 1e6:,.1f} MB")

    countries = sorted({c for cs in per_article.values() for c in cs})
    print(f"\n  distinct countries {len(countries):,}")
    tot = Counter()
    for (a, b, y), n in tally.items():
        tot[a] += n
        tot[b] += n
    print("\n  top 15 by total international collaborations:")
    for c, n in tot.most_common(15):
        print(f"    {c:<28} {n:>12,}")


if __name__ == "__main__":
    main()
