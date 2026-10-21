#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""识别策略对比：换对照组 vs 截断时间窗 vs 规则化对照组。

对每个规格报告：
  (1) 平行趋势检验 —— pre-period 上 uk x linear trend 的系数，应不显著；
  (2) 两段 beta —— b1 (PostRef 2016-)、b2 (Brexit 2021-, 增量)。

两个 pre-trend 检验窗口：
  pre-ref  : 样本起点 ~ 2015（检验 b1 的识别前提）
  pre-exit : 样本起点 ~ 2020（检验 b2 的识别前提）

输出 design_comparison.csv
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
REF_START, POST_YEAR = 2016, 2021

BIG = {
    "GERMANY", "FRANCE", "ITALY", "SPAIN", "NETHERLANDS", "BELGIUM",
    "SWITZERLAND", "SWEDEN", "DENMARK", "AUSTRIA", "FINLAND", "NORWAY",
    "UNITED STATES", "CANADA", "AUSTRALIA", "JAPAN", UK,
}

FE = "pair + focal_year"
VC = {"CRV1": "pair"}


def pct(c: float) -> float:
    return (np.exp(c) - 1.0) * 100.0


def read_long() -> pd.DataFrame:
    long = pd.read_csv(CSV)
    for c in ("focal_country", "partner_country"):
        long[c] = long[c].str.upper().str.strip()
    return long


def rule_based_pool(long: pd.DataFrame, keep_frac: float = 0.25) -> set[str]:
    """规则化对照池：按 2005-2015 平均合作量取前 keep_frac 的伙伴。

    避免手写名单的酌情选择。阈值用 pre-period 数据定义，与结果无关。
    """
    pre = long[long["year"] <= 2015]
    vol = pre.groupby("partner_country")["paper_count"].mean()
    cut = vol.quantile(1 - keep_frac)
    return set(vol[vol >= cut].index) | {UK}


def build(long: pd.DataFrame, pool: set[str] | None,
          year_min: int) -> pd.DataFrame:
    """按伙伴池与起始年切样本，补零成平衡面板并造变量。"""
    d = long.copy()
    if pool is not None:
        d = d[d["partner_country"].isin(pool)]
    d = d[d["year"] >= year_min]

    years = sorted(d["year"].unique())
    pairs = d[["focal_country", "partner_country"]].drop_duplicates()
    grid = pairs.merge(pd.DataFrame({"year": years}), how="cross")
    p = grid.merge(d, how="left",
                   on=["focal_country", "partner_country", "year"])
    p["paper_count"] = p["paper_count"].fillna(0.0)

    p["uk"] = (p["partner_country"] == UK).astype(int)
    p["postref_uk"] = ((p["year"] >= REF_START) * p["uk"]).astype(int)
    p["brexit_uk"] = ((p["year"] >= POST_YEAR) * p["uk"]).astype(int)
    p["pair"] = p["focal_country"] + "|" + p["partner_country"]
    p["focal_year"] = p["focal_country"] + "|" + p["year"].astype(str)
    return p


def pretrend(p: pd.DataFrame, upto: int) -> dict:
    """pre-period 上 uk x 线性趋势的系数。显著 => 平行趋势被拒。"""
    d = p[p["year"] <= upto].copy()
    n_yrs = d["year"].nunique()
    if n_yrs < 3:
        return {"pct": np.nan, "p": np.nan, "n_yrs": n_yrs}
    d["uk_trend"] = d["uk"] * (d["year"] - d["year"].min())
    m = pf.fepois(f"paper_count ~ uk_trend | {FE}", data=d, vcov=VC)
    r = m.tidy().loc["uk_trend"]
    return {"pct": pct(float(r["Estimate"])),
            "p": float(r["Pr(>|t|)"]), "n_yrs": n_yrs}


def two_period(p: pd.DataFrame) -> dict:
    """b1 / b2 / 累计。若 year_min >= REF_START 则 b1 不可识别。"""
    has_b1 = p["year"].min() < REF_START
    rhs = "postref_uk + brexit_uk" if has_b1 else "brexit_uk"
    m = pf.fepois(f"paper_count ~ {rhs} | {FE}", data=p, vcov=VC)
    t = m.tidy()

    out = {}
    if has_b1:
        b1 = float(t.loc["postref_uk", "Estimate"])
        se1 = float(t.loc["postref_uk", "Std. Error"])
        out["b1_pct"] = pct(b1)
        out["b1_p"] = 2 * norm.cdf(-abs(b1 / se1))
    else:
        b1, se1 = np.nan, np.nan
        out["b1_pct"], out["b1_p"] = np.nan, np.nan

    b2 = float(t.loc["brexit_uk", "Estimate"])
    se2 = float(t.loc["brexit_uk", "Std. Error"])
    out["b2_pct"] = pct(b2)
    out["b2_p"] = 2 * norm.cdf(-abs(b2 / se2))

    if has_b1:
        V = m._vcov
        names = list(t.index)
        i, j = names.index("postref_uk"), names.index("brexit_uk")
        se3 = float(np.sqrt(V[i, i] + V[j, j] + 2 * V[i, j]))
        b3 = b1 + b2
        out["cum_pct"] = pct(b3)
        out["cum_p"] = 2 * norm.cdf(-abs(b3 / se3))
    else:
        out["cum_pct"], out["cum_p"] = out["b2_pct"], out["b2_p"]
    return out


def event(p: pd.DataFrame, label: str, ref_year: int = 2020) -> pd.DataFrame:
    """逐年 event study，省略参照年。用于跨设计画路径对比。"""
    d = p.copy()
    years = [y for y in sorted(d["year"].unique()) if y != ref_year]
    terms = []
    for y in years:
        col = f"uk_{y}"
        d[col] = ((d["year"] == y) & (d["uk"] == 1)).astype(int)
        terms.append(col)
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | {FE}",
                  data=d, vcov=VC)
    t = m.tidy()
    rows = [{"design": label, "year": ref_year, "pct_change": 0.0,
             "ci_lo_pct": 0.0, "ci_hi_pct": 0.0}]
    for y, col in zip(years, terms):
        b = float(t.loc[col, "Estimate"])
        se = float(t.loc[col, "Std. Error"])
        rows.append({"design": label, "year": y, "pct_change": pct(b),
                     "ci_lo_pct": pct(b - 1.96 * se),
                     "ci_hi_pct": pct(b + 1.96 * se)})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)


def star(p: float) -> str:
    if np.isnan(p):
        return ""
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .10 else ""


def fmt(v: float, p: float) -> str:
    if np.isnan(v):
        return "     n/a"
    return f"{v:+7.2f}%{star(p):<3}"


def main() -> None:
    long = read_long()
    rule_pool = rule_based_pool(long)

    designs = [
        ("A0  all partners, 2005-",        None,      2005),
        ("A1  BIG list, 2005-",            BIG,       2005),
        ("A2  top-25% volume, 2005-",      rule_pool, 2005),
        ("B1  all partners, 2015-",        None,      2015),
        ("B2  all partners, 2012-",        None,      2012),
        ("C   BIG list, 2015-",            BIG,       2015),
    ]

    print(f"rule-based pool: {len(rule_pool)} partners "
          f"(top 25% by mean 2005-2015 volume)")

    rows = []
    es_all = []
    for name, pool, ymin in designs:
        p = build(long, pool, ymin)
        pt_ref = pretrend(p, 2015)
        pt_exit = pretrend(p, 2020)
        tp = two_period(p)
        es_all.append(event(p, name))
        rows.append({"design": name, "n_partners":
                     p["partner_country"].nunique(), "n_obs": len(p),
                     "pretrend_ref_pct": pt_ref["pct"],
                     "pretrend_ref_p": pt_ref["p"],
                     "pretrend_ref_nyrs": pt_ref["n_yrs"],
                     "pretrend_exit_pct": pt_exit["pct"],
                     "pretrend_exit_p": pt_exit["p"], **tp})
        print(f"  ran {name}")

    res = pd.DataFrame(rows)
    res.to_csv(HERE / "design_comparison.csv", index=False)
    pd.concat(es_all, ignore_index=True).to_csv(
        HERE / "design_comparison_event.csv", index=False)

    print("\n" + "=" * 104)
    print("Pre-trend tests: uk x linear trend within pre-period")
    print("(insignificant = parallel trends plausible)")
    print("=" * 104)
    print(f"{'design':<30}{'prtnrs':>7}{'pre-ref slope':>18}"
          f"{'yrs':>5}{'pre-exit slope':>18}")
    print("-" * 104)
    for _, r in res.iterrows():
        print(f"{r['design']:<30}{int(r['n_partners']):>7}"
              f"{fmt(r['pretrend_ref_pct'], r['pretrend_ref_p']):>18}"
              f"{int(r['pretrend_ref_nyrs']):>5}"
              f"{fmt(r['pretrend_exit_pct'], r['pretrend_exit_p']):>18}")

    print("\n" + "=" * 104)
    print("Two-period estimates, exp(beta)-1")
    print("=" * 104)
    print(f"{'design':<30}{'b1 PostRef':>16}{'b2 Brexit':>16}"
          f"{'cumulative':>16}")
    print("-" * 104)
    for _, r in res.iterrows():
        print(f"{r['design']:<30}{fmt(r['b1_pct'], r['b1_p']):>16}"
              f"{fmt(r['b2_pct'], r['b2_p']):>16}"
              f"{fmt(r['cum_pct'], r['cum_p']):>16}")
    print("-" * 104)
    print("\nsaved design_comparison.csv")


if __name__ == "__main__":
    main()
