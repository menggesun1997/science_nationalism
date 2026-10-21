#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大国对照池下的逐个 EU 国家效应 + 全套数字复核（供论文正文引用）。

对照池 = BIG 的 16 个大型成熟科研体（剔除 UK 本身，UK 是处理伙伴），
对每个焦点国 i 再剔除 i 自己。

规格（同 11estimate_eu_to_uk.do spec 3，但换成两段 beta）：
    P_jt = exp( a_j + mu_t + b1 * PostRef_t x UK_j + b2 * Brexit_t x UK_j )

同时复核 pooled 两段 beta、预趋势检验与事件研究，确保正文数字与代码一致。

输出 big_control_by_country.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
CSV = HERE / "dyad_panel.csv"

UK = "UNITED KINGDOM"
REF_START, POST_YEAR, REF_YEAR = 2016, 2021, 2020

# 大型成熟科研经济体（含 UK 本身，作为处理伙伴）
BIG = {
    "GERMANY", "FRANCE", "ITALY", "SPAIN", "NETHERLANDS", "BELGIUM",
    "SWITZERLAND", "SWEDEN", "DENMARK", "AUSTRIA", "FINLAND", "NORWAY",
    "UNITED STATES", "CANADA", "AUSTRALIA", "JAPAN", UK,
}


def pct(c: float) -> float:
    return (np.exp(c) - 1.0) * 100.0


def pval(b: float, se: float) -> float:
    return float(2 * norm.cdf(-abs(b / se)))


def build(big_only: bool) -> pd.DataFrame:
    """读长表，可选限制伙伴池，补零成平衡面板并造变量。"""
    long = pd.read_csv(CSV)
    for c in ("focal_country", "partner_country"):
        long[c] = long[c].str.upper().str.strip()
    if big_only:
        long = long[long["partner_country"].isin(BIG)]

    years = sorted(long["year"].unique())
    pairs = long[["focal_country", "partner_country"]].drop_duplicates()
    grid = pairs.merge(pd.DataFrame({"year": years}), how="cross")
    p = grid.merge(long, how="left",
                   on=["focal_country", "partner_country", "year"])
    p["paper_count"] = p["paper_count"].fillna(0.0)

    p["uk"] = (p["partner_country"] == UK).astype(int)
    p["postref_uk"] = ((p["year"] >= REF_START) * p["uk"]).astype(int)
    p["brexit_uk"] = ((p["year"] >= POST_YEAR) * p["uk"]).astype(int)
    p["pair"] = p["focal_country"] + "|" + p["partner_country"]
    p["focal_year"] = p["focal_country"] + "|" + p["year"].astype(str)
    return p


def three_terms(m, t) -> list[tuple[str, float, float]]:
    """返回 b1 / b2 / b1+b2 三项，累计项的 SE 含协方差。"""
    b1 = float(t.loc["postref_uk", "Estimate"])
    b2 = float(t.loc["brexit_uk", "Estimate"])
    se1 = float(t.loc["postref_uk", "Std. Error"])
    se2 = float(t.loc["brexit_uk", "Std. Error"])
    V, names = m._vcov, list(t.index)
    i, j = names.index("postref_uk"), names.index("brexit_uk")
    se3 = float(np.sqrt(V[i, i] + V[j, j] + 2 * V[i, j]))
    return [("b1", b1, se1), ("b2", b2, se2), ("cum", b1 + b2, se3)]


def pooled(p: pd.DataFrame, label: str) -> None:
    m = pf.fepois("paper_count ~ postref_uk + brexit_uk | pair + focal_year",
                  data=p, vcov={"CRV1": "pair"})
    print(f"\n{label}  ({p['partner_country'].nunique()} partners, "
          f"{len(p):,} obs, {p['pair'].nunique()} pairs)")
    for name, b, se in three_terms(m, m.tidy()):
        print(f"  {name:<4}{pct(b):+8.2f}%   se {se:.4f}   "
              f"p {pval(b, se):.4f}   "
              f"[{pct(b - 1.96 * se):+.2f}%, {pct(b + 1.96 * se):+.2f}%]")


def pretrend(p: pd.DataFrame, upto: int, label: str) -> None:
    d = p[p["year"] <= upto].copy()
    d["uk_trend"] = d["uk"] * (d["year"] - d["year"].min())
    m = pf.fepois("paper_count ~ uk_trend | pair + focal_year",
                  data=d, vcov={"CRV1": "pair"})
    r = m.tidy().loc["uk_trend"]
    b = float(r["Estimate"])
    print(f"  {label:<34}{pct(b):+7.2f}%/yr   p {float(r['Pr(>|t|)']):.4f}"
          f"   ({d['year'].nunique()} yrs)")


def event(p: pd.DataFrame) -> pd.DataFrame:
    d = p.copy()
    years = [y for y in sorted(d["year"].unique()) if y != REF_YEAR]
    terms = []
    for y in years:
        col = f"uk_{y}"
        d[col] = ((d["year"] == y) & (d["uk"] == 1)).astype(int)
        terms.append(col)
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | pair + focal_year",
                  data=d, vcov={"CRV1": "pair"})
    t = m.tidy()
    rows = [{"year": REF_YEAR, "pct_change": 0.0, "pvalue": np.nan,
             "ci_lo_pct": 0.0, "ci_hi_pct": 0.0}]
    for y, col in zip(years, terms):
        b = float(t.loc[col, "Estimate"])
        se = float(t.loc[col, "Std. Error"])
        rows.append({"year": y, "pct_change": pct(b), "pvalue": pval(b, se),
                     "ci_lo_pct": pct(b - 1.96 * se),
                     "ci_hi_pct": pct(b + 1.96 * se)})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def by_country(p: pd.DataFrame) -> pd.DataFrame:
    """逐个焦点国：P_jt = exp(a_j + mu_t + b1*PostRef x UK + b2*Brexit x UK)。

    每个焦点国的面板只有 15-16 个伙伴，cluster 数少，故报 robust SE。
    """
    rows = []
    for fc, d in p.groupby("focal_country"):
        d = d.copy()
        try:
            m = pf.fepois(
                "paper_count ~ postref_uk + brexit_uk | partner_country + year",
                data=d, vcov="hetero")
            t = m.tidy()
            terms = dict((n, (b, se)) for n, b, se in three_terms(m, t))
        except Exception as e:                       # noqa: BLE001
            print(f"  !! {fc}: {type(e).__name__}: {e}")
            continue
        row = {"focal_country": fc,
               "n_partners": d["partner_country"].nunique()}
        for name, (b, se) in terms.items():
            row[f"{name}_pct"] = pct(b)
            row[f"{name}_p"] = pval(b, se)
            row[f"{name}_lo"] = pct(b - 1.96 * se)
            row[f"{name}_hi"] = pct(b + 1.96 * se)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("cum_pct").reset_index(drop=True)


def star(p: float) -> str:
    return ("***" if p < .01 else "**" if p < .05 else "*" if p < .10 else "")


def main() -> None:
    base = build(big_only=False)
    big = build(big_only=True)

    print("=" * 78)
    print("1. Pooled two-period PPML,  exp(beta)-1")
    print("=" * 78)
    pooled(base, "baseline (all partners)")
    pooled(big, "big control pool")

    print("\n" + "=" * 78)
    print("2. Pre-trend tests: uk x linear trend within pre-period")
    print("=" * 78)
    pretrend(base, 2015, "all partners, pre-ref (->2015)")
    pretrend(big, 2015, "big control, pre-ref (->2015)")
    pretrend(base, 2020, "all partners, pre-exit (->2020)")
    pretrend(big, 2020, "big control, pre-exit (->2020)")

    print("\n" + "=" * 78)
    print(f"3. Event study under big control pool (ref {REF_YEAR})")
    print("=" * 78)
    es = event(big)
    for _, r in es.iterrows():
        mark = "" if np.isnan(r["pvalue"]) else star(r["pvalue"])
        print(f"  {int(r['year'])}  {r['pct_change']:+7.2f}%{mark:<4}"
              f"[{r['ci_lo_pct']:+7.2f}%, {r['ci_hi_pct']:+7.2f}%]")
    pre = es[(es["year"] >= 2005) & (es["year"] <= 2015)]
    print(f"\n  pre-ref range 2005-2015: {pre['pct_change'].min():+.2f}% to "
          f"{pre['pct_change'].max():+.2f}%  "
          f"(n sig at 5%: {(pre['pvalue'] < .05).sum()}/{len(pre)})")

    print("\n" + "=" * 78)
    print("4. By focal EU country, big control pool (robust SE)")
    print("=" * 78)
    bc = by_country(big)
    bc.to_csv(HERE / "big_control_by_country.csv", index=False)
    print(f"{'country':<18}{'n':>3}{'b1 PostRef':>15}{'b2 Brexit':>15}"
          f"{'cumulative':>15}")
    print("-" * 78)
    for _, r in bc.iterrows():
        line = f"{r['focal_country']:<18}{int(r['n_partners']):>3}"
        for k in ("b1", "b2", "cum"):
            line += f"{r[f'{k}_pct']:>+11.2f}%{star(r[f'{k}_p']):<3}"
        print(line)
    print("-" * 78)
    n_neg = int((bc["cum_pct"] < 0).sum())
    n_sig = int(((bc["cum_pct"] < 0) & (bc["cum_p"] < .05)).sum())
    print(f"  {n_neg}/{len(bc)} negative;  {n_sig} negative and sig at 5%")
    print("\nsaved big_control_by_country.csv")


if __name__ == "__main__":
    main()
