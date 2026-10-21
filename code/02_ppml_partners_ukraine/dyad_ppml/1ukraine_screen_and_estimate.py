#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ukraine dyadic PPML：控制池筛选 + 两断点趋势调整估计。

与 Russia 三部曲（../../02_ppml_partners_russia/dyad_ppml）的异同
----------------------------------------------------------------
相同：
  - 同一套 ex ante 控制池排除规则（直接受冲击 / 外流地 / 制裁方 /
    伙伴集团成员 / 自身双边冲击 / 体量不足）。
  - 同样需要分集团线性趋势 theta_g：Ukraine 战前 5/5 组 pre-trend 显著
    且比 Russia 更陡。
不同（Ukraine 独有）：
  1. 处理国是 UKRAINE；RUSSIA 作为参战方一并排除出控制池。
  2. 控制池按"最接近 Ukraine"而非 Russia 的战前轨迹重新排序。
  3. 2014 不是平滑过渡：Crimea + Donbas 对乌克兰是真实的 level shift，
     因此设定里保留 2014 与 2022 两个嵌套断点，再叠加趋势：

     P_ijt = exp( a_ij + mu_it
                  + sum_g theta_g * s_t      x UA_j x G_g(i)
                  + sum_g b14_g  * D2014_t   x UA_j x G_g(i)
                  + sum_g b22_g  * D2022_t   x UA_j x G_g(i) )

     D2014=1[t>=2014], D2022=1[t>=2022] 嵌套，故 b22_g 是 2022 相对
     2014-2021 的增量断裂。
  4. 北美 / 亚洲 / 中国三组体量薄（Ukraine 年均仅数百篇），其 b 估计
     置信区间宽，仅作探索性；EU 与 OTHER 组是主结果。

注意（写进论文时的 caveat，本脚本不处理）：乌克兰学者战后大量迁往
波兰、德国、捷克等 EU 国家，署名国随之改变，会从机械上抬高 EU 组的
战后合作量。这污染的是处理组本身，换控制池或调趋势都无法消除，需要
author-affiliation 级别重新归属才能解决。

输入  ../../02_ppml_partners_russia/dyad_ppml/all_country_dyad_panel.csv
输出  ukraine_control_screening.xlsx, ukraine_two_event_trend.csv,
      ukraine_event_study.csv
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

HERE = Path(__file__).resolve().parent
PANEL = (HERE.parents[1] / "02_ppml_partners_russia" / "dyad_ppml"
         / "all_country_dyad_panel.csv")
OUT_SCREEN = HERE / "ukraine_control_screening.xlsx"
OUT_RES = HERE / "ukraine_two_event_trend.csv"
OUT_EVENT = HERE / "ukraine_event_study.csv"

TREATED = "UKRAINE"
RUSSIA = "RUSSIAN FEDERATION"
WINDOW = (2012, 2024)
PRE = (2012, 2021)
CRIMEA_YEAR = 2014
WAR_YEAR = 2022
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

# ── ex ante 排除（与 Russia 口径一致，另加 Russia 本身为参战方）──
DIRECTLY_TREATED = {"UKRAINE", "BYELARUS", "MOLDOVA", "GEORGIA",
                    RUSSIA}
SUBSTITUTION_DESTINATIONS = {
    "KAZAKHSTAN", "UZBEKISTAN", "KYRGYZSTAN", "TAJIKISTAN",
    "TURKMENISTAN", "ARMENIA", "AZERBAIJAN", "REPUBLIC OF SERBIA",
    "MONTENEGRO", "TURKIYE", "ISRAEL", "UNITED ARAB EMIRATES",
}
OWN_BILATERAL_SHOCK = {"CHINA", "HONG KONG", "IRAN, ISLAMIC REP."}
PARTNER_GROUP_MEMBERS = set().union(*GROUPS.values())
OTHER_SANCTIONING = {
    "AUSTRALIA", "NEW ZEALAND", "SWITZERLAND", "NORWAY", "ICELAND",
    "LIECHTENSTEIN", "MONACO", "SAN MARINO", "ANDORRA",
    "TAIWAN", "ALBANIA", "MACEDONIA", "BOSNIA & HERZEGOVINA",
}
EXCLUSION_REASON = {
    **{c: "directly treated / belligerent" for c in DIRECTLY_TREATED},
    **{c: "substitution/emigration destination"
       for c in SUBSTITUTION_DESTINATIONS},
    **{c: "own contemporaneous bilateral shock"
       for c in OWN_BILATERAL_SHOCK},
    **{c: "member of a partner group" for c in PARTNER_GROUP_MEMBERS},
    **{c: "sanctioning country (itself treated)"
       for c in OTHER_SANCTIONING},
}
MIN_ANNUAL_BY_GROUP = {"EU": 200.0, "NORTH_AMERICA": 50.0,
                       "ASIA": 20.0, "CHINA": 20.0, "OTHER": 100.0}

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


def screen(long: pd.DataFrame):
    """Step 1：ex ante 排除 + 体量门槛 + 按接近 Ukraine 排序。"""
    pre = long[(long.year >= PRE[0]) & (long.year <= PRE[1])]
    n_yr = PRE[1] - PRE[0] + 1
    vol = (pre.groupby(["focal", "group"]).paper_count.sum() / n_yr
           ).unstack().reindex(columns=list(GROUP_ORDER)).fillna(0.0)

    rows = []
    for c in vol.index:
        if c == TREATED:
            continue
        reason = EXCLUSION_REASON.get(c)
        thin = [g for g in GROUP_ORDER
                if vol.loc[c, g] < MIN_ANNUAL_BY_GROUP[g]]
        if reason is None and thin:
            reason = "insufficient volume: " + ",".join(thin)
        rows.append({"country": c, "eligible": int(reason is None),
                     "exclusion_reason": reason or "",
                     **{f"vol_{g}": vol.loc[c, g] for g in GROUP_ORDER}})
    elig_tbl = pd.DataFrame(rows)

    # 逐集团战前 log 斜率，按"最差集团相对 Ukraine 的偏差"排序
    agg = pre.groupby(["focal", "group", "year"]).paper_count.sum()
    agg = agg.reset_index()
    agg["ly"] = np.log(agg.paper_count + 1)
    sl = {}
    for (f, g), s in agg.groupby(["focal", "group"]):
        if len(s) >= 5:
            sl[(f, g)] = np.polyfit(s.year, s.ly, 1)[0]
    slopes = pd.Series(sl).unstack().reindex(columns=list(GROUP_ORDER))

    ua = slopes.loc[TREATED]
    eligible = elig_tbl.loc[elig_tbl.eligible == 1, "country"].tolist()
    cand = slopes.loc[slopes.index.intersection(eligible)]
    absdiff = (cand - ua).abs()
    rank = pd.DataFrame({"max_absdiff": absdiff.max(axis=1),
                         "mean_absdiff": absdiff.mean(axis=1)})
    for g in GROUP_ORDER:
        rank[f"absdiff_{g}"] = absdiff[g]
        rank[f"slope_{g}"] = cand[g]
        rank[f"ua_slope_{g}"] = ua[g]
    rank = rank.sort_values("max_absdiff")
    return elig_tbl, rank


def build(long, controls, y0=WINDOW[0], y1=WINDOW[1]):
    focals = [TREATED, *controls]
    d = long[long.focal.isin(focals) & ~long.partner.isin(focals)]
    d = d[(d.year >= y0) & (d.year <= y1)]
    grid = pd.DataFrame(
        itertools.product(sorted(d.partner.unique()), focals,
                          range(y0, y1 + 1)),
        columns=["partner", "focal", "year"])
    p = grid.merge(d, how="left", on=["partner", "focal", "year"])
    p["paper_count"] = p.paper_count.fillna(0.0)
    p["ua"] = (p.focal == TREATED).astype(int)
    p["d2014"] = (p.year >= CRIMEA_YEAR).astype(int)
    p["d2022"] = (p.year >= WAR_YEAR).astype(int)
    p["s"] = p.year - REF_YEAR
    p["group"] = p.partner.map(_GOF).fillna("OTHER")
    p["pair"] = p.partner + "|" + p.focal
    p["partner_year"] = p.partner + "|" + p.year.astype(str)
    return p


def _terms(p, base, prefix):
    cols = []
    for g in GROUP_ORDER:
        c = f"{prefix}_{g.lower()}"
        p[c] = p[base] * p["ua"] * (p["group"] == g)
        cols.append(c)
    return cols


def _row(m, t):
    r = m.tidy().loc[t]
    b, se = float(r["Estimate"]), float(r["Std. Error"])
    return {"coef": b, "se": se, "pvalue": float(r["Pr(>|t|)"]),
            "pct_change": pct(b), "ci_lo_pct": pct(b - 1.96 * se),
            "ci_hi_pct": pct(b + 1.96 * se)}


def two_event_trend(p):
    """Step 3：2014 step + 2022 step + 线性趋势，分集团。"""
    d = p.copy()
    tt = _terms(d, "s", "tr")
    t14 = _terms(d, "d2014", "c14")
    t22 = _terms(d, "d2022", "w22")
    m = pf.fepois(f"paper_count ~ {' + '.join(tt + t14 + t22)} | {FE}",
                  data=d, vcov=VCOV)
    rows = []
    for g, th, a, b in zip(GROUP_ORDER, tt, t14, t22):
        rt, ra, rb = _row(m, th), _row(m, a), _row(m, b)
        rows.append({"group": g,
                     "theta_pct_per_yr": rt["coef"] * 100,
                     "theta_p": rt["pvalue"],
                     "b2014_pct": ra["pct_change"], "b2014_p": ra["pvalue"],
                     "b2022_pct": rb["pct_change"], "b2022_p": rb["pvalue"],
                     "b2022_ci_lo": rb["ci_lo_pct"],
                     "b2022_ci_hi": rb["ci_hi_pct"]})
    return pd.DataFrame(rows)


def residual_pretrend(p):
    """验证：加入趋势 + 2014 step 后，战前残余漂移是否归零。

    在战前子样本（<=2021）上，先用 s 的斜率 + 2014 step 拟合 UA 专属
    变化，再检验残余是否仍有斜率。残余 theta 不显著 = 平行趋势达成。
    """
    pre = p[p.year <= PRE[1]].copy()
    tt = _terms(pre, "s", "tr")
    t14 = _terms(pre, "d2014", "c14")
    m0 = pf.fepois(f"paper_count ~ {' + '.join(tt + t14)} | {FE}",
                   data=pre, vcov=VCOV)
    theta = {g: float(m0.tidy().loc[t, "Estimate"])
             for g, t in zip(GROUP_ORDER, tt)}
    b14 = {g: float(m0.tidy().loc[t, "Estimate"])
           for g, t in zip(GROUP_ORDER, t14)}

    d = pre.copy()
    d["off"] = 0.0
    for g in GROUP_ORDER:
        sel = (d.group == g) & (d.ua == 1)
        d.loc[sel, "off"] = (theta[g] * d.loc[sel, "s"]
                             + b14[g] * d.loc[sel, "d2014"])
    d["adj"] = d.paper_count * np.exp(-d.off)
    tt2 = _terms(d, "s", "rtr")
    m = pf.fepois(f"adj ~ {' + '.join(tt2)} | {FE}", data=d, vcov=VCOV)
    rows = []
    for g, t in zip(GROUP_ORDER, tt2):
        r = m.tidy().loc[t]
        rows.append({"group": g,
                     "residual_theta_pct": float(r["Estimate"]) * 100,
                     "pvalue": float(r["Pr(>|t|)"])})
    out = pd.DataFrame(rows)
    out["fails_05"] = (out.pvalue < 0.05).astype(int)
    return out


def event_study(p):
    d = p.copy()
    years = [y for y in range(WINDOW[0], WINDOW[1] + 1) if y != REF_YEAR]
    terms, keys = [], []
    for g in GROUP_ORDER:
        ing = d.group == g
        for y in years:
            c = f"ev_{g.lower()}_{y}"
            d[c] = ((d.year == y) & (d.ua == 1) & ing).astype(int)
            terms.append(c)
            keys.append((g, y))
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | {FE}",
                  data=d, vcov=VCOV)
    rows = [{"group": g, "year": REF_YEAR, "pct": 0.0} for g in GROUP_ORDER]
    for (g, y), t in zip(keys, terms):
        rows.append({"group": g, "year": y,
                     "pct": pct(float(m.tidy().loc[t, "Estimate"]))})
    return pd.DataFrame(rows).sort_values(["group", "year"])


def main():
    print("=" * 70)
    print("Ukraine dyadic PPML: screening + two-event trend adjustment")
    print("=" * 70)
    long = load_long()

    elig_tbl, rank = screen(long)
    n_el = int(elig_tbl.eligible.sum())
    controls = tuple(rank.index[:6])
    print(f"\nStep 1: {n_el} eligible; top-6 closest to Ukraine:")
    print("  " + ", ".join(controls))

    p = build(long, controls)
    print(f"\npanel: {len(p):,} obs, {p.partner.nunique()} partners, "
          f"zeros {(p.paper_count == 0).mean():.1%}")

    res = two_event_trend(p)
    print("\nStep 3: two-event + trend (e^b-1, %):")
    print(res[["group", "theta_pct_per_yr", "b2014_pct", "b2014_p",
               "b2022_pct", "b2022_p"]]
          .to_string(index=False, float_format="%.2f"))

    rp = residual_pretrend(p)
    print("\nValidation: residual pre-trend after 2014-step + linear "
          "adjustment")
    print(rp.to_string(index=False, float_format="%.3f"))
    n_fail = int(rp.fails_05.sum())
    print(f"  -> {n_fail}/5 groups still fail parallel trends")

    ev = event_study(p)

    with pd.ExcelWriter(OUT_SCREEN, engine="openpyxl") as w:
        elig_tbl.to_excel(w, sheet_name="step1_eligibility", index=False)
        rank.round(5).to_excel(w, sheet_name="ranking")
        res.round(5).to_excel(w, sheet_name="two_event_trend", index=False)
        rp.round(5).to_excel(w, sheet_name="residual_pretrend",
                             index=False)
    res.to_csv(OUT_RES, index=False)
    ev.to_csv(OUT_EVENT, index=False)
    print(f"\nsaved {OUT_SCREEN.name}, {OUT_RES.name}, {OUT_EVENT.name}")


if __name__ == "__main__":
    main()
