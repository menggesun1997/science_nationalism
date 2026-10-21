#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验 3：仅 6 个精选控制国，同样的 simple 公式（无趋势项）。

控制池 = 两阶段筛选出的最接近俄罗斯的 6 国：
    Mexico, Chile, Brazil, South Africa, Thailand, Argentina
规格（与主实验、实验 2 一致，simple）：
    P_ijt = exp( a_ij + mu_it + sum_g beta_g · Post_t·RU_j·G_g(i) )

与主实验（149 国）、实验 2（174 国含伙伴）对比，看控制池从"最大化"
收缩到"精选 6 国"后 beta_g 是否稳定。

输入  all_country_dyad_panel.csv
输出  exp3_results.csv, exp3_event.csv
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
POST_YEAR = 2022
REF_YEAR = 2021
CONTROLS = ["MEXICO", "CHILE", "BRAZIL", "SOUTH AFRICA",
            "THAILAND", "ARGENTINA"]

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
    focals = [RUSSIA, *CONTROLS]
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
    p["group"] = p.partner.map(_GOF).fillna("OTHER")
    p["pair"] = p.partner + "|" + p.focal
    p["partner_year"] = p.partner + "|" + p.year.astype(str)
    return p


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


def estimate_simple(p):
    bt = _grp(p, "post", "pru")
    m = pf.fepois(f"paper_count ~ {' + '.join(bt)} | {FE}",
                  data=p, vcov=VCOV)
    return pd.DataFrame([{"spec": "simple", "group": g,
                          **_row(m, f"pru_{g.lower()}")}
                         for g in GROUP_ORDER])


def event_study(p):
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
    rows = [{"group": g, "year": REF_YEAR, "pct_raw": 0.0}
            for g in GROUP_ORDER]
    for (g, y), t in zip(keys, terms):
        rows.append({"group": g, "year": y,
                     "pct_raw": pct(float(m.tidy().loc[t, "Estimate"]))})
    return pd.DataFrame(rows).sort_values(["group", "year"])


def main():
    print("=" * 70)
    print("EXPERIMENT 3: six screened controls, simple spec (no trend)")
    print("  controls:", ", ".join(c.title() for c in CONTROLS))
    print("=" * 70)
    long = load_long()
    p = build(long)
    print(f"panel: {len(p):,} obs, {p.partner.nunique()} partners, "
          f"zeros {(p.paper_count == 0).mean():.1%}")

    res = estimate_simple(p)
    print("\nexp(beta_g)-1, % (simple):")
    for _, r in res.iterrows():
        print(f"  {r['group']:14s} {r['pct_change']:+7.1f}%  "
              f"[{r['ci_lo_pct']:+.1f}, {r['ci_hi_pct']:+.1f}]  "
              f"p={r['pvalue']:.3g}")

    ev = event_study(p)
    res.to_csv(HERE / "exp3_results.csv", index=False)
    ev.to_csv(HERE / "exp3_event.csv", index=False)
    print("\nsaved exp3_results.csv / exp3_event.csv")

    # 三实验并排
    rows = []
    for tag, f in [("main-149", "maxpool_results.csv"),
                   ("exp2-174", "exp2_results.csv")]:
        fp = HERE / f
        if fp.exists():
            d = pd.read_csv(fp)
            d = d[d.spec == "simple"].set_index("group")
            rows.append((tag, d))
    s6 = res.set_index("group")
    print("\nbeta_g (simple) across pools:")
    hdr = "  group          " + "exp3-6 ".rjust(9)
    for tag, _ in rows:
        hdr += tag.rjust(10)
    print(hdr)
    for g in GROUP_ORDER:
        line = f"  {g:14s} {s6.loc[g,'pct_change']:+7.1f}% "
        for _, d in rows:
            line += f"{d.loc[g,'pct_change']:+9.1f}%"
        print(line)


if __name__ == "__main__":
    main()
