#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 UK x 伙伴国 x 年 的双边面板，用于 "UK to EU" 方向。

与 1build_dyad_panel.py 的区别只在对照集：
- EU to UK：在 EU 国家 i 的伙伴组合内部，比较 i-UK 与 i 的其他伙伴
- UK to EU：在 UK 的伙伴组合内部，比较 UK-k 与 UK 的其他伙伴

同一个 pair 的计数 P_ij 是同一个数，但参照组不同，因此两个方向的
beta 不同。输入 uk_articles.txt 收录全部含英国作者的论文。

输出 uk_dyad_panel.csv: partner_country, year, paper_count
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, require  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = CODE / "00_data_processing/uk_articles/uk_articles.txt"

YEAR_MIN, YEAR_MAX = 2005, 2024
UK = "UNITED KINGDOM"

# 复用 1build_dyad_panel.py 的国名解析，保证两个面板口径一致
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "dyad_build", HERE / "1build_dyad_panel.py")
_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_build)
parse_countries = _build.parse_countries


def main() -> None:
    print("=" * 78)
    print("Build UK x partner x year dyadic panel")
    print("=" * 78)
    require(RAW, "Licensed OST/Clarivate export of UK-authored articles.")

    tally: Counter[tuple[str, int]] = Counter()
    n_rows = 0
    reader = pd.read_csv(
        RAW,
        dtype={"OST_BK": str, "Annee_Bibliographique": str, "countries": str},
        chunksize=500_000,
    )
    for chunk in reader:
        chunk = chunk.dropna(subset=["countries", "Annee_Bibliographique"])
        years = pd.to_numeric(chunk["Annee_Bibliographique"], errors="coerce")
        keep = years.between(YEAR_MIN, YEAR_MAX)
        chunk, years = chunk[keep], years[keep].astype(int)
        n_rows += len(chunk)

        for year, raw in zip(years, chunk["countries"]):
            uniq = set(parse_countries(raw))
            if UK not in uniq or len(uniq) < 2:
                continue
            for partner in uniq - {UK}:
                tally[(partner, year)] += 1
        print(f"  ... scanned {n_rows:,} articles, {len(tally):,} dyad-years")

    panel = pd.DataFrame(
        [(p, y, n) for (p, y), n in tally.items()],
        columns=["partner_country", "year", "paper_count"],
    ).sort_values(["partner_country", "year"])

    print(f"\nrows      {len(panel):,}")
    print(f"partners  {panel.partner_country.nunique()}")
    print(f"years     {panel.year.min()}-{panel.year.max()}")

    out = HERE / "uk_dyad_panel.csv"
    panel.to_csv(out, index=False)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
