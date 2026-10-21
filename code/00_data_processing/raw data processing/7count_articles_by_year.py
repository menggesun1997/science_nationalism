#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计 raw_data_2026/article_brexit.txt 中各年的发文总量。

解析口径与 6rebuild_eu_articles.py 的 load_years() 完全一致：
  管道分隔，跳表头，第 0 列 OST_BK、第 2 列 Annee_Bibliographique，
  列数 < 3 或年份非整数的行跳过。

与 6rebuild_eu_articles.py 的区别：这里不做 2005-2024 截断、不做 EU-27
筛选，输出全量年份分布，并单独汇总落在重建窗口内的部分。
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import require  # noqa: E402

RAW_2026 = Path(os.environ.get(
    "SCIENCE_NATIONALISM_RAW_2026",
    Path.home() / "Dropbox/brexit_rawdata/raw_data_2026",
)).expanduser()

ARTICLE_FILE = RAW_2026 / "article_brexit.txt"
OUT_FILE = Path(__file__).resolve().parent / "articles_by_year.csv"

YEAR_MIN, YEAR_MAX = 2005, 2024


def count_by_year() -> tuple[dict[int, int], int, int, int]:
    """返回 (年份 -> 论文数, 扫描行数, 跳过行数, 去重后的 OST_BK 数)。"""
    require(ARTICLE_FILE, "raw_data_2026 article metadata.")
    counts: dict[int, int] = defaultdict(int)
    seen: set[str] = set()
    n_rows = n_bad = 0

    with ARTICLE_FILE.open(encoding="utf-8", errors="replace") as fh:
        next(fh)
        for line in fh:
            n_rows += 1
            parts = line.rstrip("\n").split("|")
            if len(parts) < 3:
                n_bad += 1
                continue
            try:
                y = int(parts[2])
            except ValueError:
                n_bad += 1
                continue
            counts[y] += 1
            seen.add(parts[0])
            if n_rows % 10_000_000 == 0:
                print(f"  ... {n_rows:,} rows")

    return dict(counts), n_rows, n_bad, len(seen)


def main() -> None:
    print("=" * 62)
    print("Articles per year in article_brexit.txt")
    print("=" * 62)
    print(f"source: {ARTICLE_FILE}")

    counts, n_rows, n_bad, n_unique = count_by_year()

    print(f"\n  rows scanned {n_rows:,}   skipped {n_bad:,}   "
          f"unique OST_BK {n_unique:,}")

    print("\n  year        articles")
    in_window = 0
    for y in sorted(counts):
        mark = "" if YEAR_MIN <= y <= YEAR_MAX else "   (outside window)"
        if YEAR_MIN <= y <= YEAR_MAX:
            in_window += counts[y]
        print(f"  {y}  {counts[y]:>14,}{mark}")

    total = sum(counts.values())
    print(f"\n  total                 {total:>14,}")
    print(f"  {YEAR_MIN}-{YEAR_MAX} window      {in_window:>14,}")

    with OUT_FILE.open("w", encoding="utf-8", newline="") as fh:
        fh.write("year,articles\n")
        for y in sorted(counts):
            fh.write(f"{y},{counts[y]}\n")
    print(f"\n  wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
