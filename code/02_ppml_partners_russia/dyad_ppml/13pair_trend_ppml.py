#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 1：pair-specific linear trend 的分集团 dyadic PPML（主实验控制池）。

文献依据
--------
引力模型的标准做法：在 country-pair 固定效应之外，再给每个国家对加一条
线性趋势 gamma_ij * t，吸收各 dyad 自身的既有漂移。对应 Stata 的
ppml_panel_sg ... , trend（Correia-Guimaraes-Zylkin），并被
USITC Herman (2023) "Gravity Estimation: Best Practices" 列为标准改进。
相比按集团的 theta_g（4trend_adjusted_ppml.py），pair-trend 更细、更
保守，且完全是现成工具，无自造成分。

    P_ijt = exp( a_ij + gamma_ij * t + mu_it
                 + sum_g beta_g · Post_t·RU_j·G_g(i) )

实现
----
pyfixest 没有像 ppml_panel_sg 那样的原生 pair-trend 选项。等价做法：
把 gamma_ij * t 写成"每个 pair 一个斜率"的交互。pair 数很大
（~一万级），直接做 i(pair):t 交互会爆内存，故采用去均值等价式：
对 log 可行，但 PPML 是非线性，无法简单去趋势。改用可行的近似——
把 pair-trend 作为可加项 c(pair)*year 纳入 fixef 之外的连续控制，
通过给每个 pair 生成中心化 year 列并用 pyfixest 的 i()-交互实现；
为控制维度，仅对参与估计的 pair（RU + 控制焦点 × 伙伴）生成。

控制池 = 主实验（149 国，all - emigration - partner-members -
belligerents），与 6maxpool_experiment.py 一致。

输出  pairtrend_results.csv, pairtrend_pretrend.csv, pairtrend_event.csv
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

HERE = Path(__file__).resolve().parent
PANEL = HERE / "all_country_dyad_panel.csv"

RUSSIA = "RUSSIAN FEDERATION"
WINDOW = (2012, 2024)
PRE = (2012, 2021)
POST_YEAR = 2022
REF_YEAR = 2021

UK = "UNITED KINGDOM"
EU27 = (
    "AUSTRIA", "BELGIUM", "BULGARIA", "CROATIA", "CYPRUS", "CZECHIA",
    "DENMARK", "ESTONIA", "FINLAND", "FRANCE", "GERMANY", "GREECE",
    "HUNGARY", "IRELAND", "ITALY", "LATVIA", "LITHUANIA", "LUXEMBOURG",
    "MALTA", "NETHERLANDS", "POLAND", "PORTUGAL", "ROMANIA",
    "SLOVAK REPUBLIC", "SLOVENIA", "SPAIN", "SWEDEN",
)
GROUPS = {
    "EU": set(EU27) | {UK},
    "NORTH_AMERICA": {"UNITED STATES", "CANADA"},
    "ASIA": {"JAPAN", "SOUTH KOREA", "SINGAPORE"},
    "CHINA": {"CHINA"},
}
GROUP_ORDER = ("EU", "NORTH_AMERICA", "ASIA", "CHINA", "OTHER")
_GOF = {c: g for g, m in GROUPS.items() for c in m}
PARTNER_MEMBERS = set().union(*GROUPS.values())

EMIGRATION_DEST = {
    "GEORGIA", "REPUBLIC OF SERBIA", "TURKIYE", "KAZAKHSTAN", "ARMENIA",
    "ARGENTINA", "AZERBAIJAN", "UNITED ARAB EMIRATES", "GREECE",
    "BULGARIA", "ROMANIA", "KYRGYZSTAN", "UZBEKISTAN", "SPAIN", "ISRAEL",
    "TAJIKISTAN", "MONGOLIA", "AUSTRALIA", "CANADA", "UNITED STATES",
    "GERMANY", "FINLAND",
}
BELLIGERENT = {"UKRAINE", "BYELARUS", "MOLDOVA", "GEORGIA"}

FE = "pair + partner_year"
VCOV = {"CRV1": "pair"}


def pct(b):
    return (np.exp(b) - 1.0) * 100.0


def load_long():
    d = pd.read_csv(PANEL)
    a = d.rename(columns={"country_a": "focal", "country_b": "partner"})
    b = d.rename(columns={"country_b": "focal", "country_a": "partner"})
    long = pd.concat([a, b], ignore_index=True)
    long["group"] = long.partner.map(_GOF).fillna("OTHER")
    return long


def build(long):
    allc = set(long.focal.unique())
    controls = sorted(allc - {RUSSIA} - PARTNER_MEMBERS
                      - EMIGRATION_DEST - BELLIGERENT)
    focals = [RUSSIA, *controls]
    p = long[long.focal.isin(focals) & ~long.partner.isin(focals)]
    p = p[(p.year >= WINDOW[0]) & (p.year <= WINDOW[1])]
    grid = pd.DataFrame(
        itertools.product(sorted(p.partner.unique()), focals,
                          range(WINDOW[0], WINDOW[1] + 1)),
        columns=["partner", "focal", "year"])
    p = grid.merge(p, how="left", on=["partner", "focal", "year"])
    p["paper_count"] = p.paper_count.fillna(0.0)
    p["ru"] = (p.focal == RUSSIA).astype(int)
    p["post"] = (p.year >= POST_YEAR).astype(int)
    # pair[t] 的 varying-slope 要求非负、整洁的时间轴，用 year-2012
    p["t"] = p.year - WINDOW[0]
    p["group"] = p.partner.map(_GOF).fillna("OTHER")
    p["pair"] = p.partner + "|" + p.focal
    p["partner_year"] = p.partner + "|" + p.year.astype(str)
    return p, controls


def _grp(p, base, prefix):
    cols = []
    for g in GROUP_ORDER:
        c = f"{prefix}_{g.lower()}"
        p[c] = p[base] * p["ru"] * (p["group"] == g)
        cols.append(c)
    return cols


def _row(m, t):
    r = m.tidy().loc[t]
    b, se = float(r["Estimate"]), float(r["Std. Error"])
    return {"coef": b, "se": se, "pvalue": float(r["Pr(>|t|)"]),
            "pct_change": pct(b), "ci_lo_pct": pct(b - 1.96 * se),
            "ci_hi_pct": pct(b + 1.96 * se)}


def estimate(p):
    """pair-trend: a_ij + gamma_ij*t 用 fixef 'pair + pair[t]' 表达。

    pyfixest 支持 varying slopes 语法 'pair[t]'：在 pair 固定效应基础上
    额外吸收每个 pair 的线性 t 斜率，即 gamma_ij*t。
    """
    bt = _grp(p, "post", "pru")
    fml = f"paper_count ~ {' + '.join(bt)} | pair + pair[t] + partner_year"
    m = pf.fepois(fml, data=p, vcov=VCOV)
    return pd.DataFrame([{"group": g, **_row(m, f"pru_{g.lower()}")}
                         for g in GROUP_ORDER]), m


def pretrend(p):
    """平行趋势检验：pair-trend 设定下，战前逐年系数是否仍显著。"""
    d = p[p.year <= PRE[1]].copy()
    years = [y for y in range(PRE[0], PRE[1] + 1) if y != REF_YEAR]
    terms, keys = [], []
    for g in GROUP_ORDER:
        ing = d.group == g
        for y in years:
            c = f"ev_{g.lower()}_{y}"
            d[c] = ((d.year == y) & (d.ru == 1) & ing).astype(int)
            terms.append(c)
            keys.append((g, y))
    fml = f"paper_count ~ {' + '.join(terms)} | pair + pair[t] + partner_year"
    m = pf.fepois(fml, data=d, vcov=VCOV)
    t = m.tidy()
    rows = []
    for g in GROUP_ORDER:
        n = 0
        for (gg, y), c in zip(keys, terms):
            if gg == g and c in t.index and t.loc[c, "Pr(>|t|)"] < 0.05:
                n += 1
        rows.append({"group": g, "sig_pre_years": n,
                     "total_pre_years": len(years)})
    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("Plan 1: pair-specific linear trends (gamma_ij * t)")
    print("  control pool = main experiment (149), group-specific beta")
    print("=" * 70)
    long = load_long()
    p, controls = build(long)
    print(f"control pool {len(controls)}; panel {len(p):,} obs, "
          f"{p.pair.nunique()} pairs")

    res, m = estimate(p)
    print("\nexp(beta_g)-1, % (pair-trend adjusted):")
    for _, r in res.iterrows():
        print(f"  {r['group']:14s} {r['pct_change']:+7.1f}%  "
              f"[{r['ci_lo_pct']:+.1f}, {r['ci_hi_pct']:+.1f}]  "
              f"p={r['pvalue']:.3g}")

    pt = pretrend(p)
    print("\nparallel-trends check (pre-war sig years, pair-trend):")
    print(pt.to_string(index=False))

    res.to_csv(HERE / "pairtrend_results.csv", index=False)
    pt.to_csv(HERE / "pairtrend_pretrend.csv", index=False)
    print("\nsaved pairtrend_results.csv / pairtrend_pretrend.csv")


if __name__ == "__main__":
    main()
