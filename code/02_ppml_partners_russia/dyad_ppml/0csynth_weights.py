#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 2 的正式实现：合成 DiD 权重。

为什么需要权重
--------------
0bdiagnose_controls.py 显示，无论池子取 3、6 还是 10 国，等权平均都无法
通过分集团平行趋势：合格池里几乎所有国家的战前增速都系统性快于俄罗斯
（EU 组 +1.5 到 +4.6 个百分点/年，ASIA 组 +1.8 到 +4.9）。等权平均只能
平移水平，不能抵消斜率差。

但凸组合可以。若池中同时存在增速快于和慢于俄罗斯的国家，加权平均能把
合成斜率压到与俄罗斯一致。本脚本对每个集团 g 单独求解

    min_w  || log P_RU,g,t - sum_j w_j log P_j,g,t ||^2
    s.t.   w_j >= 0,  sum_j w_j = 1,   t in 战前窗口

逐集团求权重，而非在总量上求一组权重：beta_g 的识别只用到集团 g 的
单元，所以拟合也应在该维度上进行。

输入  all_country_dyad_panel.csv, control_screening.xlsx
输出  synth_weights.xlsx   逐集团权重与拟合优度
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

HERE = Path(__file__).resolve().parent
PANEL = HERE / "all_country_dyad_panel.csv"
SCREEN = HERE / "control_screening.xlsx"
OUT = HERE / "synth_weights.xlsx"

TREATED = "RUSSIAN FEDERATION"
PRE = (2012, 2021)

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


def load_group_series() -> pd.DataFrame:
    """(focal, group, year) -> log 合作量。"""
    d = pd.read_csv(PANEL)
    a = d.rename(columns={"country_a": "focal", "country_b": "partner"})
    b = d.rename(columns={"country_b": "focal", "country_a": "partner"})
    long = pd.concat([a, b], ignore_index=True)
    long["group"] = long.partner.map(_GOF).fillna("OTHER")
    pre = long[(long.year >= PRE[0]) & (long.year <= PRE[1])]
    agg = pre.groupby(["focal", "group", "year"]).paper_count.sum()
    agg = agg.reset_index()
    agg["ly"] = np.log(agg.paper_count + 1)
    return agg


def simplex_fit(y: np.ndarray, X: np.ndarray,
                n_iter: int = 400) -> tuple[np.ndarray, float]:
    """求 min ||y - Xw||, w>=0, sum w = 1。

    用增广惩罚把单位和约束并入最小二乘，再交给 nnls。惩罚权重逐步加大，
    收敛后归一化。
    """
    n = X.shape[1]
    best_w, best_r = None, np.inf
    for pen in np.logspace(0, 4, 9):
        Xa = np.vstack([X, pen * np.ones((1, n))])
        ya = np.concatenate([y, [pen]])
        w, _ = nnls(Xa, ya)
        s = w.sum()
        if s <= 0:
            continue
        w = w / s
        r = float(np.sqrt(np.mean((y - X @ w) ** 2)))
        if r < best_r:
            best_w, best_r = w, r
    if best_w is None:
        best_w = np.ones(n) / n
        best_r = float(np.sqrt(np.mean((y - X @ best_w) ** 2)))
    return best_w, best_r


def slope(years: np.ndarray, vals: np.ndarray) -> float:
    return float(np.polyfit(years, vals, 1)[0])


def fit_group(agg: pd.DataFrame, g: str,
              pool: list[str]) -> tuple[pd.Series, dict]:
    """对集团 g 求合成权重。"""
    sub = agg[agg.group == g]
    piv = sub.pivot(index="year", columns="focal", values="ly")
    years = piv.index.to_numpy()

    cols = [c for c in pool if c in piv.columns
            and piv[c].notna().all()]
    y = piv[TREATED].to_numpy()
    X = piv[cols].to_numpy()

    w, rmse = simplex_fit(y, X)
    synth = X @ w
    ru_sl = slope(years, y)
    sy_sl = slope(years, synth)

    # 等权基准，用于说明权重的增益
    w_eq = np.ones(len(cols)) / len(cols)
    eq = X @ w_eq
    stats = {
        "group": g,
        "n_pool": len(cols),
        "n_positive_weight": int((w > 1e-4).sum()),
        "rmse_synth": rmse,
        "rmse_equal": float(np.sqrt(np.mean((y - eq) ** 2))),
        "ru_slope_pct": ru_sl * 100,
        "synth_slope_pct": sy_sl * 100,
        "equal_slope_pct": slope(years, eq) * 100,
        "slope_gap_synth_pct": (sy_sl - ru_sl) * 100,
        "slope_gap_equal_pct": (slope(years, eq) - ru_sl) * 100,
    }
    return pd.Series(w, index=cols).sort_values(ascending=False), stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool-size", type=int, default=25,
                    help="取 Step 2 排名前 N 的合格国进入权重求解")
    args = ap.parse_args()

    print("=" * 78)
    print("Synthetic DiD weights, estimated separately by partner group")
    print("=" * 78)

    agg = load_group_series()
    s2 = pd.read_excel(SCREEN, sheet_name="step2_slope_match", index_col=0)
    pool = s2.index.tolist()[:args.pool_size]
    print(f"eligible pool: {len(pool)} countries")

    all_w, all_s = {}, []
    for g in GROUP_ORDER:
        w, st = fit_group(agg, g, pool)
        all_w[g] = w
        all_s.append(st)
        print(f"\n[{g}]  pool {st['n_pool']}, "
              f"positive weights {st['n_positive_weight']}")
        print(f"  RMSE   synth {st['rmse_synth']:.4f}   "
              f"equal {st['rmse_equal']:.4f}")
        print(f"  slope  Russia {st['ru_slope_pct']:+.2f}%/yr   "
              f"synth {st['synth_slope_pct']:+.2f}%/yr   "
              f"equal {st['equal_slope_pct']:+.2f}%/yr")
        print(f"  gap    synth {st['slope_gap_synth_pct']:+.3f} pp   "
              f"equal {st['slope_gap_equal_pct']:+.3f} pp")
        top = w[w > 1e-4]
        print("  weights: " + ", ".join(f"{k} {v:.3f}"
                                        for k, v in top.items()))

    stats = pd.DataFrame(all_s)
    wide = pd.DataFrame(all_w).fillna(0.0)
    wide = wide.loc[wide.max(axis=1) > 1e-4]

    print("\n" + "=" * 78)
    print("weights by group (rows = control countries)")
    print(wide.round(3).to_string())

    with pd.ExcelWriter(OUT, engine="openpyxl") as w_:
        stats.round(5).to_excel(w_, sheet_name="fit_stats", index=False)
        wide.round(5).to_excel(w_, sheet_name="weights")
    print(f"\nsaved {OUT}")


if __name__ == "__main__":
    main()
