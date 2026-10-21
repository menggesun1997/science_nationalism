#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对照组收紧到大型成熟科研国，重跑两段 beta + event study，与基线对比。

规格同 11estimate_eu_to_uk.do 的 Spec 1b：
    P_ijt = exp(a_ij + mu_it + b1 * PostRef_t x UK_j + b2 * Brexit_t x UK_j)
PostRef = 1[year >= 2016]，Brexit = 1[year >= 2021]，两者嵌套。
SE 聚类到 pair。

输出 big_control_twoperiod.csv、big_control_event.csv。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

HERE = Path(__file__).resolve().parent
CSV = HERE / "dyad_panel.csv"

UK = "UNITED KINGDOM"
REF_START = 2016   # 公投
POST_YEAR = 2021   # 正式脱欧
REF_YEAR = 2020    # event study 参照年

# 大型成熟科研经济体，与英国体量/发展阶段可比
BIG = {
    "GERMANY", "FRANCE", "ITALY", "SPAIN", "NETHERLANDS", "BELGIUM",
    "SWITZERLAND", "SWEDEN", "DENMARK", "AUSTRIA", "FINLAND", "NORWAY",
    "UNITED STATES", "CANADA", "AUSTRALIA", "JAPAN", "UNITED KINGDOM",
}


def pct(c: float) -> float:
    return (np.exp(c) - 1.0) * 100.0


def load(big_only: bool) -> pd.DataFrame:
    """读长表，可选限制伙伴池，然后补零成平衡面板并造变量。"""
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


def two_period(p: pd.DataFrame, label: str) -> pd.DataFrame:
    """跑 Spec 1b，返回 b1 / b2 / b1+b2 三行。"""
    m = pf.fepois("paper_count ~ postref_uk + brexit_uk | pair + focal_year",
                  data=p, vcov={"CRV1": "pair"})
    t = m.tidy()
    b1 = float(t.loc["postref_uk", "Estimate"])
    b2 = float(t.loc["brexit_uk", "Estimate"])
    se1 = float(t.loc["postref_uk", "Std. Error"])
    se2 = float(t.loc["brexit_uk", "Std. Error"])

    # 累计效应 b1+b2 的 SE 需含协方差项：Var(b1+b2)=V11+V22+2*V12
    V = m._vcov
    names = list(t.index)
    i, j = names.index("postref_uk"), names.index("brexit_uk")
    se3 = float(np.sqrt(V[i, i] + V[j, j] + 2 * V[i, j]))
    b3 = b1 + b2

    from scipy.stats import norm
    rows = []
    for term, b, se in (("postref_uk", b1, se1), ("brexit_uk", b2, se2),
                        ("cumulative", b3, se3)):
        rows.append({
            "spec": label, "term": term, "coef": b, "se": se,
            "pvalue": 2 * norm.cdf(-abs(b / se)),
            "pct_change": pct(b),
            "ci_lo_pct": pct(b - 1.96 * se),
            "ci_hi_pct": pct(b + 1.96 * se),
        })
    return pd.DataFrame(rows)


def event(p: pd.DataFrame, label: str) -> pd.DataFrame:
    """逐年 event study，省略参照年 REF_YEAR。"""
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

    rows = [{"spec": label, "year": REF_YEAR, "coef": 0.0,
             "pct_change": 0.0, "ci_lo_pct": 0.0, "ci_hi_pct": 0.0}]
    for y, col in zip(years, terms):
        b = float(t.loc[col, "Estimate"])
        se = float(t.loc[col, "Std. Error"])
        rows.append({"spec": label, "year": y, "coef": b,
                     "pct_change": pct(b),
                     "ci_lo_pct": pct(b - 1.96 * se),
                     "ci_hi_pct": pct(b + 1.96 * se)})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def main() -> None:
    base = load(big_only=False)
    big = load(big_only=True)

    print("=" * 72)
    print(f"baseline    {len(base):>8,} obs   "
          f"{base['partner_country'].nunique():>3} partners")
    print(f"big control {len(big):>8,} obs   "
          f"{big['partner_country'].nunique():>3} partners")
    print(f"big pool    "
          f"{sorted(big['partner_country'].unique())}")
    print("=" * 72)

    tp = pd.concat([two_period(base, "baseline"),
                    two_period(big, "big_control")], ignore_index=True)
    tp.to_csv(HERE / "big_control_twoperiod.csv", index=False)

    lab = {"postref_uk": "b1  PostRef x UK (2016-)",
           "brexit_uk": "b2  Brexit  x UK (2021-)",
           "cumulative": "b1+b2  cumulative"}
    print("\nTwo-period PPML, exp(beta)-1:")
    print(f"{'term':<26}{'baseline':>24}{'big control':>24}")
    print("-" * 74)
    for term in lab:
        out = f"{lab[term]:<26}"
        for spec in ("baseline", "big_control"):
            r = tp[(tp.spec == spec) & (tp.term == term)].iloc[0]
            pv = float(r["pvalue"])
            star = ("***" if pv < .01 else
                    "**" if pv < .05 else
                    "*" if pv < .10 else "")
            out += f"{float(r['pct_change']):>+13.2f}%{star:<8}"
        print(out)
    print("-" * 74)

    es = pd.concat([event(base, "baseline"),
                    event(big, "big_control")], ignore_index=True)
    es.to_csv(HERE / "big_control_event.csv", index=False)

    wide = es.pivot(index="year", columns="spec", values="pct_change")
    print("\nEvent study (pct vs 2020):")
    print(wide.to_string(float_format="%+.2f"))
    print("\nsaved big_control_twoperiod.csv / big_control_event.csv")


if __name__ == "__main__":
    main()
