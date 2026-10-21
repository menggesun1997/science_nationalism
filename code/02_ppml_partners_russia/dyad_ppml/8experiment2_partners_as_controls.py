#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 2：把伙伴国（EU / 北美-加 / 发达亚洲）也放进控制焦点池。

对比主实验（6maxpool_experiment.py）：
  主实验   控制池 = 全部 − 移民接收国 − 伙伴集团成员 − 参战国
  实验 2   控制池 = 全部 − 移民接收国 − {CHINA, US}
           即把 EU-27+UK / Canada / Japan / Korea / Singapore 也当控制，
           只保留 China 与 US 不进控制池（它们是最想度量、且自身有冲击）。

机制注意
--------
主实验把控制焦点国从伙伴维度剔除。若在此沿用，EU/Asia 国家全成了焦点，
伙伴维度里就没有 EU/Asia 成员，G_EU / G_ASIA 变空、无法估计。为使五个
集团仍可识别，这里放松伙伴剔除规则为**只剔除自我配对**（country i 作
焦点 j 时不与自己配对，但仍可作其他焦点的伙伴）。这样 EU/亚洲成员既是
控制焦点、又能作伙伴定义集团。

这个设定本身是"反面教材"：用伙伴集团成员当控制，等于拿同样在对俄脱钩
的西方国家作参照（France–Russia vs France–Germany），预期会把 beta_g
推向更极端。实验目的就是看这个扭曲有多大。

输入  all_country_dyad_panel.csv
输出  exp2_results.csv
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

EMIGRATION_DEST = {
    "GEORGIA", "REPUBLIC OF SERBIA", "TURKIYE", "KAZAKHSTAN", "ARMENIA",
    "ARGENTINA", "AZERBAIJAN", "UNITED ARAB EMIRATES", "GREECE",
    "BULGARIA", "ROMANIA", "KYRGYZSTAN", "UZBEKISTAN", "SPAIN", "ISRAEL",
    "TAJIKISTAN", "MONGOLIA", "AUSTRALIA", "CANADA", "UNITED STATES",
    "GERMANY", "FINLAND",
}
BELLIGERENT = {"UKRAINE", "BYELARUS", "MOLDOVA", "GEORGIA"}
# 实验 2 唯一保持排除出控制池的伙伴成员
KEEP_OUT = {"CHINA", "UNITED STATES"}

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


def build_exp2(long):
    """控制 = 全部 − 移民接收 − 参战 − {China,US}；伙伴只剔自我配对。"""
    allc = set(long.focal.unique())
    controls = sorted(allc - {RUSSIA} - EMIGRATION_DEST
                      - BELLIGERENT - KEEP_OUT)
    focals = [RUSSIA, *controls]
    p = long[long.focal.isin(focals)]
    p = p[p.partner != p.focal]                 # 只剔自我配对
    p = p[(p.year >= WINDOW[0]) & (p.year <= WINDOW[1])]
    grid = pd.DataFrame(
        itertools.product(sorted(p.partner.unique()), focals,
                          range(WINDOW[0], WINDOW[1] + 1)),
        columns=["partner", "focal", "year"])
    p = grid.merge(p, how="left", on=["partner", "focal", "year"])
    p = p[p.partner != p.focal]
    p["paper_count"] = p.paper_count.fillna(0.0)
    p["ru"] = (p.focal == RUSSIA).astype(int)
    p["post"] = (p.year >= POST_YEAR).astype(int)
    p["s"] = p.year - REF_YEAR
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


def estimate(p, trend):
    bt = _grp(p, "post", "pru")
    terms = (_grp(p, "s", "tr") + bt) if trend else bt
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | {FE}",
                  data=p, vcov=VCOV)
    spec = "trend" if trend else "simple"
    return pd.DataFrame([{"spec": spec, "group": g,
                          **_row(m, f"pru_{g.lower()}")}
                         for g in GROUP_ORDER])


def event_study(p):
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
    rows = [{"group": g, "year": REF_YEAR, "coef": 0.0}
            for g in GROUP_ORDER]
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
        out.append(s)
    return pd.concat(out, ignore_index=True)


def residual(p):
    pre = p[p.year <= PRE[1]].copy()
    tt = _grp(pre, "s", "tr")
    m0 = pf.fepois(f"paper_count ~ {' + '.join(tt)} | {FE}",
                   data=pre, vcov=VCOV)
    th = {g: float(m0.tidy().loc[f"tr_{g.lower()}", "Estimate"])
          for g in GROUP_ORDER}
    pre["off"] = 0.0
    for g in GROUP_ORDER:
        sel = (pre.group == g) & (pre.ru == 1)
        pre.loc[sel, "off"] = th[g] * pre.loc[sel, "s"]
    pre["adj"] = pre.paper_count * np.exp(-pre.off)
    tt2 = _grp(pre, "s", "rtr")
    m = pf.fepois(f"adj ~ {' + '.join(tt2)} | {FE}", data=pre, vcov=VCOV)
    rows = []
    for g in GROUP_ORDER:
        r = m.tidy().loc[f"rtr_{g.lower()}"]
        rows.append({"group": g, "residual_pct": float(r["Estimate"]) * 100,
                     "pvalue": float(r["Pr(>|t|)"])})
    out = pd.DataFrame(rows)
    out["fails_05"] = (out.pvalue < 0.05).astype(int)
    return out


def main():
    print("=" * 74)
    print("EXPERIMENT 2: partner-group members allowed as controls")
    print("  controls = all - emigration - belligerents - {China, US}")
    print("  partner rule relaxed to self-pair-only (keep groups estimable)")
    print("=" * 74)

    long = load_long()
    p, controls = build_exp2(long)
    print(f"\ncontrol focals: {len(controls)}  "
          f"(incl. EU/Canada/Japan/Korea/Singapore)")
    print(f"panel: {len(p):,} obs, {p.partner.nunique()} partners, "
          f"zeros {(p.paper_count == 0).mean():.1%}")

    simple = estimate(p, trend=False)
    trend = estimate(p, trend=True)
    res = pd.concat([simple, trend], ignore_index=True)

    print("\nexp(beta_g)-1, %:")
    piv = res.pivot(index="group", columns="spec",
                    values="pct_change").reindex(list(GROUP_ORDER))
    print(piv[["simple", "trend"]].round(1).to_string())

    rp = residual(p)
    print(f"\nresidual pre-trend ({int(rp.fails_05.sum())}/5 fail):")
    print(rp.to_string(index=False, float_format="%.3f"))

    # 并排对比主实验
    main_path = HERE / "maxpool_results.csv"
    if main_path.exists():
        mr = pd.read_csv(main_path)
        mr = mr[mr.spec == "trend"].set_index("group")
        tr = res[res.spec == "trend"].set_index("group")
        print("\ntrend-adjusted beta_g:  MAIN vs EXP2")
        for g in GROUP_ORDER:
            print(f"  {g:14s} main {mr.loc[g,'pct_change']:+6.1f}%   "
                  f"exp2 {tr.loc[g,'pct_change']:+6.1f}%")

    ev = event_study(p)
    res.to_csv(HERE / "exp2_results.csv", index=False)
    rp.to_csv(HERE / "exp2_residual_pretrend.csv", index=False)
    ev.to_csv(HERE / "exp2_event.csv", index=False)
    print("\nsaved exp2_results.csv / exp2_residual_pretrend.csv / "
          "exp2_event.csv")


if __name__ == "__main__":
    main()
