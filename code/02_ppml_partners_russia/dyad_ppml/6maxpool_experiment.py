#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主实验：最大化控制池的分集团 dyadic PPML（俄罗斯，2022 全面入侵）。

设计
----
控制焦点池不再是精选的少数"最像俄罗斯"的国家，而是**世界上所有国家**，
仅剔除三类不能充当对照的单元：

  1. 移民接收国（Russian_emigration wiki）——俄罗斯人/学者外流落脚地，
     用作对照会把转移出去的合作误算进来。清单见
     `wiki_russian_emigration_destinations.txt`。
  2. 伙伴集团成员（EU / 北美 / 发达亚洲 / 中国）——它们是 beta_g 要
     度量的对象，必须留在 partner 维度 (i) 以定义 G_g(i)，不能进控制
     焦点池 (j)。"加上中美"即指此：China / US 照常作伙伴，不作控制。
  3. 直接受冲击 / 参战方（Ukraine, Belarus, Moldova, Georgia）。

这样得到 ~149 个控制焦点国。相比精选池，它是"最大化、最少主观判断"的
控制组，用来证明核心结论不依赖控制组的具体挑选。

规格
----
  simple   P_ijt = exp( a_ij + mu_it + sum_g beta_g · Post_t·RU_j·G_g(i) )
  trend    再加  sum_g theta_g · s_t·RU_j·G_g(i)   （s_t = t-2021）

因为大池含大量战前增速远快于俄罗斯的全球南方国家，simple 规格的 beta_g
被 pre-trend 严重污染而虚高；趋势调整剥离既有漂移后才是可解读的断点。
趋势调整后残余 pre-trend 应 0/5 显著（本脚本一并验证）。

输入  all_country_dyad_panel.csv（0build_all_country_panel.py 产出）
      wiki_russian_emigration_destinations.txt（口径依据，脚本内置清单）
输出  maxpool_results.csv   simple / trend 两规格的 beta_g
      maxpool_event.csv     趋势调整事件研究逐年系数
      maxpool_pool.txt      最终控制池国家清单 + 剔除计数
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

# 维基移民接收国（映射到面板国名标签）
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


def pct(b: float) -> float:
    return (np.exp(b) - 1.0) * 100.0


def load_long() -> pd.DataFrame:
    d = pd.read_csv(PANEL)
    a = d.rename(columns={"country_a": "focal", "country_b": "partner"})
    b = d.rename(columns={"country_b": "focal", "country_a": "partner"})
    long = pd.concat([a, b], ignore_index=True)
    long["group"] = long.partner.map(_GOF).fillna("OTHER")
    return long


def control_pool(long: pd.DataFrame) -> list[str]:
    allc = set(long.focal.unique())
    return sorted(allc - {RUSSIA} - PARTNER_MEMBERS
                  - EMIGRATION_DEST - BELLIGERENT)


def build(long: pd.DataFrame, controls: list[str]) -> pd.DataFrame:
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
    p["s"] = p.year - REF_YEAR
    p["group"] = p.partner.map(_GOF).fillna("OTHER")
    p["pair"] = p.partner + "|" + p.focal
    p["partner_year"] = p.partner + "|" + p.year.astype(str)
    return p


def _grp(p: pd.DataFrame, base: str, prefix: str) -> list[str]:
    cols = []
    for g in GROUP_ORDER:
        c = f"{prefix}_{g.lower()}"
        p[c] = p[base] * p["ru"] * (p["group"] == g)
        cols.append(c)
    return cols


def _row(m, t: str) -> dict:
    r = m.tidy().loc[t]
    b, se = float(r["Estimate"]), float(r["Std. Error"])
    return {"coef": b, "se": se, "pvalue": float(r["Pr(>|t|)"]),
            "pct_change": pct(b), "ci_lo_pct": pct(b - 1.96 * se),
            "ci_hi_pct": pct(b + 1.96 * se)}


def estimate(p: pd.DataFrame, trend: bool) -> pd.DataFrame:
    bt = _grp(p, "post", "pru")
    terms = (_grp(p, "s", "tr") + bt) if trend else bt
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | {FE}",
                  data=p, vcov=VCOV)
    spec = "trend" if trend else "simple"
    return pd.DataFrame([{"spec": spec, "group": g, **_row(m, f"pru_{g.lower()}")}
                         for g in GROUP_ORDER])


def residual_pretrend(p: pd.DataFrame) -> pd.DataFrame:
    pre = p[p.year <= PRE[1]].copy()
    tt = _grp(pre, "s", "tr")
    m0 = pf.fepois(f"paper_count ~ {' + '.join(tt)} | {FE}",
                   data=pre, vcov=VCOV)
    theta = {g: float(m0.tidy().loc[f"tr_{g.lower()}", "Estimate"])
             for g in GROUP_ORDER}
    pre["off"] = 0.0
    for g in GROUP_ORDER:
        sel = (pre.group == g) & (pre.ru == 1)
        pre.loc[sel, "off"] = theta[g] * pre.loc[sel, "s"]
    pre["adj"] = pre.paper_count * np.exp(-pre.off)
    tt2 = _grp(pre, "s", "rtr")
    m = pf.fepois(f"adj ~ {' + '.join(tt2)} | {FE}", data=pre, vcov=VCOV)
    rows = []
    for g in GROUP_ORDER:
        r = m.tidy().loc[f"rtr_{g.lower()}"]
        rows.append({"group": g, "theta_pct_per_yr": theta[g] * 100,
                     "residual_pct_per_yr": float(r["Estimate"]) * 100,
                     "pvalue": float(r["Pr(>|t|)"])})
    out = pd.DataFrame(rows)
    out["fails_05"] = (out.pvalue < 0.05).astype(int)
    return out


def event_study(p: pd.DataFrame) -> pd.DataFrame:
    """趋势调整事件研究：逐年系数减去战前拟合趋势外推。"""
    d = p.copy()
    years = [y for y in range(WINDOW[0], WINDOW[1] + 1) if y != REF_YEAR]
    terms, keys = [], []
    for g in GROUP_ORDER:
        ing = d.group == g
        for y in years:
            c = f"ev_{g.lower()}_{y}"
            d[c] = ((d.year == y) & (d.ru == 1) & ing).astype(int)
            terms.append(c)
            keys.append((g, y))
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | {FE}",
                  data=d, vcov=VCOV)
    rows = [{"group": g, "year": REF_YEAR, "coef": 0.0} for g in GROUP_ORDER]
    for (g, y), t in zip(keys, terms):
        rows.append({"group": g, "year": y,
                     "coef": float(m.tidy().loc[t, "Estimate"])})
    ev = pd.DataFrame(rows)
    out = []
    for g, s in ev.groupby("group"):
        s = s.sort_values("year").copy()
        pre = s[s.year <= PRE[1]]
        sl, ic = np.polyfit(pre.year, pre.coef, 1)
        s["pct_raw"] = s.coef.map(pct)
        s["pct_adj"] = (s.coef - (sl * s.year + ic)).map(pct)
        s["pre_slope_pct"] = sl * 100
        out.append(s)
    return pd.concat(out, ignore_index=True)


def main() -> None:
    print("=" * 74)
    print("MAIN EXPERIMENT: maximal control pool (all countries minus")
    print("emigration destinations, partner-group members, belligerents)")
    print("=" * 74)

    long = load_long()
    controls = control_pool(long)
    n_all = long.focal.nunique()
    print(f"\nall countries {n_all}  ->  control pool {len(controls)}")

    p = build(long, controls)
    print(f"panel: {len(p):,} obs, {p.partner.nunique()} partners, "
          f"zeros {(p.paper_count == 0).mean():.1%}")

    simple = estimate(p, trend=False)
    trend = estimate(p, trend=True)
    res = pd.concat([simple, trend], ignore_index=True)

    print("\nexp(beta_g)-1, %:")
    piv = res.pivot(index="group", columns="spec",
                    values="pct_change").reindex(list(GROUP_ORDER))
    print(piv[["simple", "trend"]].round(1).to_string())

    rp = residual_pretrend(p)
    print("\nresidual pre-trend after adjustment "
          f"({int(rp.fails_05.sum())}/5 fail):")
    print(rp[["group", "residual_pct_per_yr", "pvalue"]]
          .to_string(index=False, float_format="%.3f"))

    ev = event_study(p)

    res.to_csv(HERE / "maxpool_results.csv", index=False)
    ev.to_csv(HERE / "maxpool_event.csv", index=False)
    with (HERE / "maxpool_pool.txt").open("w", encoding="utf-8") as fh:
        fh.write("MAIN EXPERIMENT control pool\n")
        fh.write(f"all countries: {n_all}\n")
        fh.write(f"removed: emigration destinations "
                 f"({len(EMIGRATION_DEST)}), partner-group members "
                 f"({len(PARTNER_MEMBERS)}), belligerents "
                 f"({len(BELLIGERENT)})\n")
        fh.write(f"control pool: {len(controls)} countries\n\n")
        fh.write(", ".join(c.title() for c in controls) + "\n")
    # 残余检验并入结果表
    rp.to_csv(HERE / "maxpool_residual_pretrend.csv", index=False)
    print("\nsaved maxpool_results.csv / maxpool_event.csv / "
          "maxpool_pool.txt / maxpool_residual_pretrend.csv")


if __name__ == "__main__":
    main()
