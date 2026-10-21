#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pooled beta 的稳健性检验：对照池、样本窗口、预趋势调整。"""

from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd
import pyfixest as pf

HERE = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "dyad_est", HERE / "2estimate_dyad_ppml.py")
est = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(est)

FORMULA = "paper_count ~ post_uk | pair + focal_year"
ROWS: list[dict] = []


def report(label: str, p: pd.DataFrame, formula: str = FORMULA) -> None:
    m = pf.fepois(formula, data=p, vcov={"CRV1": "pair"})
    r = est.tidy_row(m, "post_uk")
    print(f"{label:<40s} {r['pct_change']:+7.2f}%  "
          f"[{r['ci_lo_pct']:+7.2f}, {r['ci_hi_pct']:+7.2f}]  "
          f"p={r['pvalue']:.4f}  obs={len(p):,}")
    ROWS.append({"spec": label, "n_obs": len(p), **r})
    if "uk_trend" in formula:
        t = est.tidy_row(m, "uk_trend")
        print(f"{'  (UK linear trend)':<40s} {t['pct_change']:+7.2f}%/yr"
              f"{'':>22}p={t['pvalue']:.4f}")


def main() -> None:
    print("=" * 92)
    print("Robustness of pooled beta  (exp(beta)-1, 95% CI clustered by pair)")
    print("=" * 92)

    # 基线纳入 EU 内部合作（与 _setup.do 的 $INCL_EU = 1 一致）
    p = est.load_panel(include_eu_partners=True)
    report("baseline: incl. EU-internal, min 5/yr", p)
    report("excl. other EU-27 from pool",
           est.load_panel(include_eu_partners=False))
    report("window 2010-2024", p[p.year >= 2010])
    report("window 2013-2024", p[p.year >= 2013])

    # 预趋势调整：允许 UK dyad 有自己的线性时间趋势
    q = p.copy()
    q["uk_trend"] = q["uk"] * (q["year"] - est.REF_YEAR)
    report("baseline + linear UK pre-trend", q,
           "paper_count ~ post_uk + uk_trend | pair + focal_year")

    q13 = q[q.year >= 2013]
    report("2013-2024 + linear UK pre-trend", q13,
           "paper_count ~ post_uk + uk_trend | pair + focal_year")

    pd.DataFrame(ROWS).to_csv(HERE / "results_robustness.csv", index=False)
    print("\nsaved results_robustness.csv")


if __name__ == "__main__":
    main()
