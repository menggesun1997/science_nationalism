#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势调整的分集团 dyadic PPML（Russia, 2022 全面入侵）。

动机
----
0bdiagnose_controls.py 证明：无论控制池取 3/6/10 国还是合成 DiD 权重，
EU / NORTH_AMERICA / ASIA 三组的战前 theta_g 都显著非零。根因不是控制组
选得差，而是俄罗斯战前十年集团份额本身在单调漂移（EU 份额 2012 年
51.4% -> 2021 年 46.5%，中国 3.4% -> 5.4%），且五个份额之和恒为 1，
五个 theta_g 不独立。任何控制组匹配了总量，就必然在各集团上正负相抵。

因此本脚本不再声称"若无战争各集团份额会平行演化"，而是把既有趋势显式
写进设定，让 beta_g 识别为**既有趋势之上的额外断裂**：

  (T1) 趋势调整两期
       P_ijt = exp( a_ij + mu_it
                    + sum_g theta_g * s_t x RU_j x G_g(i)
                    + sum_g beta_g  * Post_t x RU_j x G_g(i) )
       s_t = t - 2021（趋势项贯穿全窗口，由战前十年钉住）
       theta_g 既有漂移，beta_g 2022 年的水平跳变

  (T2) 趋势钉在战前
       theta_g 只用战前子样本估计，再作为 offset 固定代入全窗口，
       避免战后三年反过来影响趋势估计、从而低估 beta_g。

  (T3) 趋势调整事件研究
       逐年 beta_gk 减去战前拟合趋势的外推值，用于作图。

对照
----
同时报告未调整的基线（现有 2estimate_dyad_ppml.py 的规格）与多个控制池，
以便判断分集团结论是否依赖趋势处理方式。

输入  all_country_dyad_panel.csv, control_screening.xlsx, synth_weights.xlsx
输出  res_trend_adj.csv, res_trend_adj_event.csv, trend_adjusted.xlsx
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

HERE = Path(__file__).resolve().parent
PANEL = HERE / "all_country_dyad_panel.csv"
SCREEN = HERE / "control_screening.xlsx"
WEIGHTS = HERE / "synth_weights.xlsx"

TREATED = "RUSSIAN FEDERATION"
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

OLD_BASELINE = ("SOUTH AFRICA", "BRAZIL", "GEORGIA")

FE = "pair + partner_year"
VCOV = {"CRV1": "pair"}


def pct(b: float) -> float:
    return (np.exp(b) - 1.0) * 100.0


def load_long() -> pd.DataFrame:
    d = pd.read_csv(PANEL)
    a = d.rename(columns={"country_a": "focal", "country_b": "partner"})
    b = d.rename(columns={"country_b": "focal", "country_a": "partner"})
    return pd.concat([a, b], ignore_index=True)


def build(long: pd.DataFrame, controls: tuple[str, ...],
          y0: int = WINDOW[0], y1: int = WINDOW[1]) -> pd.DataFrame:
    """焦点国 = 俄罗斯 + controls，伙伴维度剔除焦点国自身，补零平衡。"""
    focals = [TREATED, *controls]
    d = long[long.focal.isin(focals) & ~long.partner.isin(focals)]
    d = d[(d.year >= y0) & (d.year <= y1)]

    grid = pd.DataFrame(
        itertools.product(sorted(d.partner.unique()), focals,
                          range(y0, y1 + 1)),
        columns=["partner", "focal", "year"],
    )
    p = grid.merge(d, how="left", on=["partner", "focal", "year"])
    p["paper_count"] = p.paper_count.fillna(0.0)

    p["ru"] = (p.focal == TREATED).astype(int)
    p["post"] = (p.year >= POST_YEAR).astype(int)
    p["group"] = p.partner.map(_GOF).fillna("OTHER")
    p["s"] = p.year - REF_YEAR
    p["pair"] = p.partner + "|" + p.focal
    p["partner_year"] = p.partner + "|" + p.year.astype(str)
    return p


def _grp_terms(p: pd.DataFrame, base: str, prefix: str) -> list[str]:
    """为每个集团生成 base x RU x G_g 交互列，返回列名。"""
    cols = []
    for g in GROUP_ORDER:
        c = f"{prefix}_{g.lower()}"
        p[c] = p[base] * p["ru"] * (p["group"] == g)
        cols.append(c)
    return cols


def _row(m, term: str) -> dict:
    r = m.tidy().loc[term]
    b, se = float(r["Estimate"]), float(r["Std. Error"])
    return {
        "coef": b, "se": se, "pvalue": float(r["Pr(>|t|)"]),
        "pct_change": pct(b),
        "ci_lo_pct": pct(b - 1.96 * se),
        "ci_hi_pct": pct(b + 1.96 * se),
    }


def spec_baseline(p: pd.DataFrame) -> pd.DataFrame:
    """未调整基线：只有 Post x RU x G_g（现有主文规格）。"""
    d = p.copy()
    bt = _grp_terms(d, "post", "pru")
    m = pf.fepois(f"paper_count ~ {' + '.join(bt)} | {FE}",
                  data=d, vcov=VCOV)
    return pd.DataFrame([{"group": g, "spec": "no trend", **_row(m, t)}
                         for g, t in zip(GROUP_ORDER, bt)])


def spec_trend_joint(p: pd.DataFrame) -> pd.DataFrame:
    """(T1) 趋势与断点联合估计。"""
    d = p.copy()
    tt = _grp_terms(d, "s", "tr")
    bt = _grp_terms(d, "post", "pru")
    m = pf.fepois(
        f"paper_count ~ {' + '.join(tt + bt)} | {FE}",
        data=d, vcov=VCOV)
    rows = []
    for g, t, b in zip(GROUP_ORDER, tt, bt):
        rb = _row(m, b)
        rt = _row(m, t)
        rows.append({"group": g, "spec": "trend joint", **rb,
                     "theta_pct_per_yr": rt["coef"] * 100,
                     "theta_p": rt["pvalue"]})
    return pd.DataFrame(rows)


def spec_trend_pinned(p: pd.DataFrame) -> pd.DataFrame:
    """(T2) theta_g 用战前子样本估计，再固定代入全窗口。"""
    pre = p[p.year <= PRE[1]].copy()
    tt = _grp_terms(pre, "s", "tr")
    m0 = pf.fepois(f"paper_count ~ {' + '.join(tt)} | {FE}",
                   data=pre, vcov=VCOV)
    theta = {g: float(m0.tidy().loc[t, "Estimate"])
             for g, t in zip(GROUP_ORDER, tt)}

    d = p.copy()
    d["offset_lin"] = 0.0
    for g in GROUP_ORDER:
        sel = (d.group == g) & (d.ru == 1)
        d.loc[sel, "offset_lin"] = theta[g] * d.loc[sel, "s"]
    # 把既有趋势从结果里剥离：等价于给 PPML 加 exposure
    d["adj_count"] = d.paper_count * np.exp(-d.offset_lin)

    bt = _grp_terms(d, "post", "pru")
    m = pf.fepois(f"adj_count ~ {' + '.join(bt)} | {FE}",
                  data=d, vcov=VCOV)
    rows = []
    for g, t in zip(GROUP_ORDER, bt):
        rows.append({"group": g, "spec": "trend pinned", **_row(m, t),
                     "theta_pct_per_yr": theta[g] * 100,
                     "theta_p": np.nan})
    return pd.DataFrame(rows)


def spec_event_trend_adj(p: pd.DataFrame) -> pd.DataFrame:
    """(T3) 逐年 beta_gk，并给出减去战前拟合趋势后的调整值。"""
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

    rows = [{"group": g, "year": REF_YEAR, "coef": 0.0, "se": 0.0,
             "pvalue": np.nan} for g in GROUP_ORDER]
    for (g, y), t in zip(keys, terms):
        r = m.tidy().loc[t]
        rows.append({"group": g, "year": y,
                     "coef": float(r["Estimate"]),
                     "se": float(r["Std. Error"]),
                     "pvalue": float(r["Pr(>|t|)"])})
    ev = pd.DataFrame(rows)

    # 用战前年份拟合各集团的线性趋势，外推到战后并相减
    out = []
    for g, s in ev.groupby("group"):
        s = s.sort_values("year").copy()
        pre = s[s.year <= PRE[1]]
        sl, ic = np.polyfit(pre.year, pre.coef, 1)
        s["trend_fit"] = sl * s.year + ic
        s["coef_adj"] = s.coef - s.trend_fit
        s["pct_raw"] = s.coef.map(pct)
        s["pct_adj"] = s.coef_adj.map(pct)
        s["pre_slope_pct_per_yr"] = sl * 100
        out.append(s)
    return pd.concat(out, ignore_index=True)


def residual_pretrend(p: pd.DataFrame) -> pd.DataFrame:
    """趋势调整后的残余战前漂移检验。

    T2 把 theta_g 固定代入后，战前残余应无系统趋势。等价检验：在
    adj_count 上只放战前子样本，重估一个趋势项，看是否仍显著。
    这是对 T2 的内部一致性检查，也是写进 SI 的平行趋势证据。
    """
    pre = p[p.year <= PRE[1]].copy()
    tt = _grp_terms(pre, "s", "tr")
    m0 = pf.fepois(f"paper_count ~ {' + '.join(tt)} | {FE}",
                   data=pre, vcov=VCOV)
    theta = {g: float(m0.tidy().loc[t, "Estimate"])
             for g, t in zip(GROUP_ORDER, tt)}

    d = pre.copy()
    d["offset_lin"] = 0.0
    for g in GROUP_ORDER:
        sel = (d.group == g) & (d.ru == 1)
        d.loc[sel, "offset_lin"] = theta[g] * d.loc[sel, "s"]
    d["adj_count"] = d.paper_count * np.exp(-d.offset_lin)

    tt2 = _grp_terms(d, "s", "rtr")
    m = pf.fepois(f"adj_count ~ {' + '.join(tt2)} | {FE}",
                  data=d, vcov=VCOV)
    rows = []
    for g, t in zip(GROUP_ORDER, tt2):
        r = m.tidy().loc[t]
        rows.append({
            "group": g,
            "theta_raw_pct": theta[g] * 100,
            "theta_residual_pct": float(r["Estimate"]) * 100,
            "se_pct": float(r["Std. Error"]) * 100,
            "pvalue": float(r["Pr(>|t|)"]),
        })
    out = pd.DataFrame(rows)
    out["fails_05"] = (out.pvalue < 0.05).astype(int)
    return out


def event_pretrend_joint_test(ev: pd.DataFrame) -> pd.DataFrame:
    """对趋势调整后的逐年系数，检验战前是否仍有残余斜率。"""
    rows = []
    for g, s in ev.groupby("group"):
        pre = s[(s.year <= PRE[1]) & (s.se > 0)]
        if len(pre) < 4:
            continue
        # 以 1/se^2 加权的线性拟合，近似 GLS 趋势检验
        w = 1.0 / pre.se.to_numpy() ** 2
        x = pre.year.to_numpy(dtype=float)
        y = pre.coef_adj.to_numpy()
        X = np.column_stack([np.ones_like(x), x - PRE[1]])
        WX = X * w[:, None]
        beta = np.linalg.solve(X.T @ WX, WX.T @ y)
        resid = y - X @ beta
        dof = max(len(x) - 2, 1)
        s2 = float((w * resid ** 2).sum() / dof)
        cov = s2 * np.linalg.inv(X.T @ WX)
        se = float(np.sqrt(cov[1, 1]))
        t = beta[1] / se if se > 0 else np.nan
        rows.append({
            "group": g,
            "residual_slope_pct_per_yr": beta[1] * 100,
            "se_pct": se * 100,
            "t_stat": t,
            "abs_t_gt_196": int(abs(t) > 1.96),
        })
    return pd.DataFrame(rows).set_index("group").reindex(
        list(GROUP_ORDER)).reset_index()


def run_pool(long: pd.DataFrame, label: str,
             controls: tuple[str, ...]) -> pd.DataFrame:
    p = build(long, controls)
    print(f"\n{'=' * 74}")
    print(f"pool: {label}  ({len(controls)} controls)")
    print(f"  {len(p):,} obs, {p.partner.nunique()} partners, "
          f"zeros {(p.paper_count == 0).mean():.1%}")

    frames = [spec_baseline(p), spec_trend_joint(p),
              spec_trend_pinned(p)]
    res = pd.concat(frames, ignore_index=True)
    res.insert(0, "pool", label)

    piv = res.pivot(index="group", columns="spec",
                    values="pct_change").reindex(list(GROUP_ORDER))
    piv = piv[["no trend", "trend joint", "trend pinned"]]
    print("\n  exp(beta_g)-1, % :")
    print(piv.round(1).to_string())
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()

    print("=" * 78)
    print("Trend-adjusted group-specific dyadic PPML (Russia, 2022)")
    print("=" * 78)

    long = load_long()
    s2 = pd.read_excel(SCREEN, sheet_name="step2_slope_match", index_col=0)
    ranked = s2.index.tolist()

    # 吸收稳健性：把事前排除的外流目的地放回池中。若 beta_g 变得更负，
    # 说明排除它们是保守的做法，而非在挑结果。
    INCLUSIVE = tuple(ranked[:args.top]) + (
        "KAZAKHSTAN", "UNITED ARAB EMIRATES", "TURKIYE", "ARMENIA")

    pools = {
        "old baseline (ZA/BR/GE)": OLD_BASELINE,
        f"screened top-{args.top}": tuple(ranked[:args.top]),
        "screened top-12": tuple(ranked[:12]),
        "inclusive (absorbers added)": INCLUSIVE,
    }

    res = pd.concat([run_pool(long, k, v) for k, v in pools.items()],
                    ignore_index=True)

    print("\n" + "=" * 78)
    print("[T3] trend-adjusted event study  "
          f"(pool: screened top-{args.top})")
    p = build(long, tuple(ranked[:args.top]))
    ev = spec_event_trend_adj(p)
    show = ev.pivot(index="year", columns="group", values="pct_adj")
    print(show.reindex(columns=list(GROUP_ORDER)).round(1).to_string())

    print("\n  pre-war slope removed, % per year:")
    print(ev.groupby("group").pre_slope_pct_per_yr.first()
          .reindex(list(GROUP_ORDER)).round(2).to_string())

    print("\n[PT] residual pre-trend after adjustment  "
          "(p<0.05 => still fails)")
    rp = residual_pretrend(p)
    print(rp.to_string(index=False, float_format="%.3f"))

    print("\n[PT2] residual slope in adjusted event-study coefficients")
    ept = event_pretrend_joint_test(ev)
    print(ept.to_string(index=False, float_format="%.3f"))

    res.to_csv(HERE / "res_trend_adj.csv", index=False)
    ev.to_csv(HERE / "res_trend_adj_event.csv", index=False)
    with pd.ExcelWriter(HERE / "trend_adjusted.xlsx",
                        engine="openpyxl") as w:
        res.round(5).to_excel(w, sheet_name="two_period", index=False)
        ev.round(5).to_excel(w, sheet_name="event_study", index=False)
        rp.round(5).to_excel(w, sheet_name="residual_pretrend",
                             index=False)
        ept.round(5).to_excel(w, sheet_name="event_pretrend_test",
                              index=False)
    print("\nsaved res_trend_adj.csv / res_trend_adj_event.csv / "
          "trend_adjusted.xlsx")


if __name__ == "__main__":
    main()
