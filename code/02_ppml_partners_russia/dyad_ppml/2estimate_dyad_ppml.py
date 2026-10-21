#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
伙伴国视角的 dyadic PPML：战争后俄罗斯在各集团伙伴合作组合中的份额变化。

规格（对应给定设定）
  (1) pooled          P_ijt = exp( a_ij + mu_it + beta * Post_t x RU_j )
  (2) by group        P_ijt = exp( a_ij + mu_it
                                   + sum_g beta_g * Post_t x RU_j x G_g(i) )
  (3) event study     P_ijt = exp( a_ij + mu_it
                                   + sum_g sum_k beta_gk * 1[t=k] x RU_j x G_g(i) )
  (4) per partner     P_ijt = exp( a_j  + mu_t  + beta * Post_t x RU_j )  对每个 i

  i 伙伴国，j 俄罗斯或控制组国家，RU_j = 1[j = RUSSIA]
  g in {EU (EU27+UK), NORTH_AMERICA (US+CA), ASIA (JP+KR+SG), CHINA, OTHER}

a_ij 吸收伙伴-焦点对的时间不变基线，mu_it 吸收伙伴 i 当年的整体合作规模，
故 exp(beta_g)-1 即集团 g 伙伴与俄罗斯合作量相对其与控制组国家合作量的
百分比变化。估计量 pyfixest.fepois（等同 Stata ppmlhdfe），SE 聚类到
country pair。

默认只用两阶段筛选出的控制组（SOUTH AFRICA / BRAZIL / GEORGIA）作参照；
`--all-controls` 用全部 9 个候选控制国做稳健性检验。

输出 res_pooled.csv / res_by_group.csv / res_event.csv / res_by_partner.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

HERE = Path(__file__).resolve().parent
CSV = HERE / "dyad_panel.csv"

RUSSIA = "RUSSIAN FEDERATION"
POST_YEAR = 2022
REF_YEAR = 2021

SELECTED_CONTROLS = ("SOUTH AFRICA", "BRAZIL", "GEORGIA")

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
_GROUP_OF = {c: g for g, m in GROUPS.items() for c in m}

# 规格 (4) 的伙伴体量门槛：与俄罗斯年均合作少于该值的伙伴不单独估计
MIN_AVG_RU = 20


def group_of(c: str) -> str:
    return _GROUP_OF.get(c, "OTHER")


def load_balanced(controls: tuple[str, ...]) -> pd.DataFrame:
    """读长表，限定焦点国为 俄罗斯 + controls，补零成平衡面板。"""
    long = pd.read_csv(CSV)
    keep = (RUSSIA,) + tuple(controls)
    long = long[long["focal_country"].isin(keep)]

    years = sorted(long["year"].unique())
    partners = sorted(long["partner_country"].unique())
    grid = pd.MultiIndex.from_product(
        [partners, keep, years],
        names=["partner_country", "focal_country", "year"],
    ).to_frame(index=False)
    p = grid.merge(long, how="left",
                   on=["focal_country", "partner_country", "year"])
    p["paper_count"] = p["paper_count"].fillna(0.0)

    p["ru"] = (p["focal_country"] == RUSSIA).astype(int)
    p["post"] = (p["year"] >= POST_YEAR).astype(int)
    p["post_ru"] = p["post"] * p["ru"]
    p["group"] = p["partner_country"].map(group_of)
    p["pair"] = p["partner_country"] + "|" + p["focal_country"]
    p["partner_year"] = p["partner_country"] + "|" + p["year"].astype(str)
    return p


def pct(b: float) -> float:
    return (np.exp(b) - 1.0) * 100.0


def tidy(model, term: str) -> dict:
    r = model.tidy().loc[term]
    b, se = float(r["Estimate"]), float(r["Std. Error"])
    return {
        "coef": b, "se": se,
        "pvalue": float(r["Pr(>|t|)"]),
        "pct_change": pct(b),
        "ci_lo_pct": pct(b - 1.96 * se),
        "ci_hi_pct": pct(b + 1.96 * se),
    }


FE = "pair + partner_year"
VCOV = {"CRV1": "pair"}


def spec1_pooled(p: pd.DataFrame, tag: str) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print("Spec 1  pooled:  a_ij + mu_it + beta * Post x RU")
    print("=" * 70)
    m = pf.fepois(f"paper_count ~ post_ru | {FE}", data=p, vcov=VCOV)
    row = tidy(m, "post_ru")
    print(f"  beta        {row['coef']:+.4f}  (se {row['se']:.4f}, "
          f"p {row['pvalue']:.3g})")
    print(f"  exp(b)-1    {row['pct_change']:+.2f}%  "
          f"[{row['ci_lo_pct']:+.2f}%, {row['ci_hi_pct']:+.2f}%]")
    out = pd.DataFrame([{"spec": "pooled", **row}])
    out.to_csv(HERE / f"res_pooled{tag}.csv", index=False)
    return out


def spec2_by_group(p: pd.DataFrame, tag: str) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print("Spec 2  by group:  a_ij + mu_it + sum_g beta_g * Post x RU x G_g")
    print("=" * 70)
    d = p.copy()
    terms = []
    for g in GROUP_ORDER:
        col = f"pru_{g.lower()}"
        d[col] = d["post_ru"] * (d["group"] == g)
        terms.append(col)
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | {FE}",
                  data=d, vcov=VCOV)
    rows = []
    for g, t in zip(GROUP_ORDER, terms):
        n = d.loc[d["group"] == g, "partner_country"].nunique()
        rows.append({"group": g, "n_partners": n, **tidy(m, t)})
    res = pd.DataFrame(rows)
    res["sig_05"] = (res["pvalue"] < 0.05).astype(int)
    print(res[["group", "n_partners", "coef", "se", "pct_change",
               "ci_lo_pct", "ci_hi_pct", "pvalue"]]
          .to_string(index=False, float_format="%.3f"))
    res.to_csv(HERE / f"res_by_group{tag}.csv", index=False)
    return res


def spec3_event(p: pd.DataFrame, tag: str) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print(f"Spec 3  event study by group (ref year {REF_YEAR})")
    print("=" * 70)
    d = p.copy()
    years = [y for y in sorted(d["year"].unique()) if y != REF_YEAR]
    terms, keys = [], []
    for g in GROUP_ORDER:
        ing = (d["group"] == g)
        for y in years:
            col = f"ru_{g.lower()}_{y}"
            d[col] = ((d["year"] == y) & (d["ru"] == 1) & ing).astype(int)
            terms.append(col)
            keys.append((g, y))
    m = pf.fepois(f"paper_count ~ {' + '.join(terms)} | {FE}",
                  data=d, vcov=VCOV)
    rows = [{"group": g, "year": REF_YEAR, "coef": 0.0, "se": 0.0,
             "pvalue": np.nan, "pct_change": 0.0, "ci_lo_pct": 0.0,
             "ci_hi_pct": 0.0} for g in GROUP_ORDER]
    for (g, y), t in zip(keys, terms):
        rows.append({"group": g, "year": y, **tidy(m, t)})
    res = pd.DataFrame(rows).sort_values(["group", "year"])
    for g in GROUP_ORDER:
        print(f"\n  [{g}]")
        print(res[res["group"] == g][["year", "pct_change", "ci_lo_pct",
                                      "ci_hi_pct", "pvalue"]]
              .to_string(index=False, float_format="%.2f"))
    res.to_csv(HERE / f"res_event{tag}.csv", index=False)
    return res


def spec4_by_partner(p: pd.DataFrame, tag: str) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print("Spec 4  per partner:  a_j + mu_t + beta * Post x RU")
    print("=" * 70)
    vol = (p[p["ru"] == 1].groupby("partner_country").paper_count.mean())
    big = sorted(vol[vol >= MIN_AVG_RU].index)
    print(f"  partners with mean RU collab >= {MIN_AVG_RU}: {len(big)}")
    rows = []
    for i in big:
        d = p[p["partner_country"] == i]
        try:
            m = pf.fepois("paper_count ~ post_ru | focal_country + year",
                          data=d, vcov="hetero")
            rows.append({"partner_country": i, "group": group_of(i),
                         "mean_ru_collab": float(vol[i]),
                         **tidy(m, "post_ru")})
        except Exception as exc:
            print(f"  !! {i}: {type(exc).__name__}")
    res = pd.DataFrame(rows).sort_values("pct_change")
    res["sig_05"] = (res["pvalue"] < 0.05).astype(int)
    print(res[["partner_country", "group", "mean_ru_collab", "pct_change",
               "ci_lo_pct", "ci_hi_pct", "pvalue"]]
          .to_string(index=False, float_format="%.2f"))
    res.to_csv(HERE / f"res_by_partner{tag}.csv", index=False)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-controls", action="store_true",
                    help="用全部 9 个候选控制国（默认只用两阶段筛选的 3 个）")
    args = ap.parse_args()

    if args.all_controls:
        long = pd.read_csv(CSV)
        controls = tuple(sorted(set(long["focal_country"]) - {RUSSIA}))
        tag = "_allctrl"
    else:
        controls = SELECTED_CONTROLS
        tag = ""

    p = load_balanced(controls)
    print(f"controls: {', '.join(controls)}")
    print(f"balanced panel: {len(p):,} obs, "
          f"{p['partner_country'].nunique()} partners, "
          f"{p['focal_country'].nunique()} focals, "
          f"zeros {(p['paper_count'] == 0).mean():.1%}")

    spec1_pooled(p, tag)
    spec2_by_group(p, tag)
    spec3_event(p, tag)
    spec4_by_partner(p, tag)
    print(f"\nsaved res_pooled{tag}.csv / res_by_group{tag}.csv / "
          f"res_event{tag}.csv / res_by_partner{tag}.csv")


if __name__ == "__main__":
    main()
