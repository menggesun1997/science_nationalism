#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 raw_data_2026 重建 eu_articles.txt。

旧文件 code/00_data_processing/eu_articles/eu_articles.txt 的来源已不可追溯，
这里用 2026 年交付的原始文件重建，口径显式化：

输入（$RAW_2026，默认 ~/Dropbox/brexit_rawdata/raw_data_2026）
  article_cntry_brexit.txt   OST_BK|Pays        长表，一行一个(论文,国家)
  article_brexit.txt         OST_BK|UID|Annee_Bibliographique|...

输出（与旧文件同格式，下游脚本无需改动）
  OST_BK,Annee_Bibliographique,countries
  其中 countries 为该论文去重后的国家列表，逗号分隔，含逗号的字段加引号

口径说明
  1. 国名用 cntry_convert.csv 映射到统一标签。原始数据把英国拆成
     ENGLAND/SCOTLAND/WALES/NORTH-IRELAND，必须先合并再去重，否则一篇
     英格兰+苏格兰合著论文会被误判成"两国合作"。
  2. 只保留至少含一个 EU-27 作者国的论文（与旧文件口径一致）。
  3. 年份限定 2005-2024。
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, require  # noqa: E402

RAW_2026 = Path(os.environ.get(
    "SCIENCE_NATIONALISM_RAW_2026",
    Path.home() / "Dropbox/brexit_rawdata/raw_data_2026",
)).expanduser()

CNTRY_FILE = RAW_2026 / "article_cntry_brexit.txt"
ARTICLE_FILE = RAW_2026 / "article_brexit.txt"
CONV_FILE = Path(__file__).resolve().parent / "cntry_convert.csv"

OUT_DIR = CODE / "00_data_processing/eu_articles"
OUT_FILE = OUT_DIR / "eu_articles.txt"

YEAR_MIN, YEAR_MAX = 2005, 2024

EU27 = frozenset({
    "AUSTRIA", "BELGIUM", "BULGARIA", "CROATIA", "CYPRUS", "CZECHIA",
    "DENMARK", "ESTONIA", "FINLAND", "FRANCE", "GERMANY", "GREECE",
    "HUNGARY", "IRELAND", "ITALY", "LATVIA", "LITHUANIA", "LUXEMBOURG",
    "MALTA", "NETHERLANDS", "POLAND", "PORTUGAL", "ROMANIA",
    "SLOVAK REPUBLIC", "SLOVENIA", "SPAIN", "SWEDEN",
})

# cntry_convert.csv 的目标标签与下游脚本使用的标签不完全一致，这里对齐。
# 下游（dyad_ppml、06_bridging 等）用的是旧 eu_articles.txt 的标签。
ALIGN = {
    "CZECH REPUBLIC": "CZECHIA",
    "SLOVAKIA": "SLOVAK REPUBLIC",
    "KOREA, REP.": "KOREA, REP.",
    "RUSSIA": "RUSSIAN FEDERATION",
    "BELARUS": "BYELARUS",
    "SERBIA": "REPUBLIC OF SERBIA",
    "TURKEY": "TURKIYE",
    "VIETNAM": "VIET NAM",
}


def load_country_map() -> dict[str, str]:
    """原始国名 -> 统一标签。"""
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
    """OST_BK -> 年份，只保留 YEAR_MIN..YEAR_MAX。"""
    require(ARTICLE_FILE, "raw_data_2026 article metadata.")
    years: dict[str, int] = {}
    with ARTICLE_FILE.open(encoding="utf-8", errors="replace") as fh:
        next(fh)
        for line in fh:
            parts = line.rstrip("\n").split("|")
            if len(parts) < 3:
                continue
            try:
                y = int(parts[2])
            except ValueError:
                continue
            if YEAR_MIN <= y <= YEAR_MAX:
                years[parts[0]] = y
    return years


def collect_countries(cmap: dict[str, str],
                      years: dict[str, int]) -> dict[str, set[str]]:
    """OST_BK -> 去重后的国家标签集合。英国各地区在此合并。"""
    require(CNTRY_FILE, "raw_data_2026 article-country long table.")
    per_article: dict[str, set[str]] = defaultdict(set)
    n_rows = n_kept = n_unmapped = 0

    with CNTRY_FILE.open(encoding="utf-8", errors="replace") as fh:
        next(fh)
        for line in fh:
            n_rows += 1
            parts = line.rstrip("\n").split("|")
            if len(parts) != 2:
                continue
            bk, raw = parts[0], parts[1].strip().upper()
            if bk not in years:
                continue
            if not raw:
                continue
            std = cmap.get(raw)
            if std is None:
                n_unmapped += 1
                continue
            per_article[bk].add(std)
            n_kept += 1
            if n_rows % 10_000_000 == 0:
                print(f"  ... {n_rows:,} rows, {len(per_article):,} articles")

    print(f"  rows scanned {n_rows:,}   kept {n_kept:,}   "
          f"unmapped {n_unmapped:,}")
    return per_article


def main() -> None:
    print("=" * 78)
    print("Rebuild eu_articles.txt from raw_data_2026")
    print("=" * 78)
    print(f"source: {RAW_2026}")

    print("\n[1/4] country-name crosswalk ...")
    cmap = load_country_map()
    print(f"  {len(cmap):,} raw labels mapped")

    print(f"\n[2/4] article years ({YEAR_MIN}-{YEAR_MAX}) ...")
    years = load_years()
    print(f"  {len(years):,} articles in window")

    print("\n[3/4] article-country long table ...")
    per_article = collect_countries(cmap, years)

    print("\n[4/4] filter to EU-27 papers and write ...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_out = 0
    year_counts: dict[int, int] = defaultdict(int)

    with OUT_FILE.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["OST_BK", "Annee_Bibliographique", "countries"])
        for bk, countries in per_article.items():
            if not (countries & EU27):
                continue
            w.writerow([bk, years[bk], ",".join(sorted(countries))])
            n_out += 1
            year_counts[years[bk]] += 1

    print(f"  wrote {n_out:,} articles to {OUT_FILE}")
    print(f"  size {OUT_FILE.stat().st_size / 1e6:,.0f} MB")
    print("\n  articles per year:")
    for y in sorted(year_counts):
        print(f"    {y}  {year_counts[y]:>9,}")


if __name__ == "__main__":
    main()
