#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 Stata 的 ppml_panel_sg (pair-specific trend) 导出主实验估计面板。

控制池 = 主实验（149 国，all - emigration - partner-members -
belligerents），与 6maxpool_experiment.py 完全一致。
输出宽表 stata_pairtrend_panel.csv，列：
  paper_count, ru, post, year, t,
  pru_eu pru_north_america pru_asia pru_china pru_other,   # 分集团断点
  focal_id, partner_id, pair_id, group               # id 供 Stata encode
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PANEL = HERE / "all_country_dyad_panel.csv"
OUT = HERE / "stata_pairtrend_panel.csv"

RUSSIA = "RUSSIAN FEDERATION"
WINDOW = (2012, 2024)
POST_YEAR = 2022

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


def main():
    d = pd.read_csv(PANEL)
    a = d.rename(columns={"country_a": "focal", "country_b": "partner"})
    b = d.rename(columns={"country_b": "focal", "country_a": "partner"})
    long = pd.concat([a, b], ignore_index=True)
    long["group"] = long.partner.map(_GOF).fillna("OTHER")

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
    p["t"] = p.year - WINDOW[0]
    p["group"] = p.partner.map(_GOF).fillna("OTHER")
    for g in GROUP_ORDER:
        p[f"pru_{g.lower()}"] = (p.post * p.ru
                                 * (p.group == g)).astype(int)

    # id 列（Stata encode 更稳，但直接给数值 id 省事）
    p["focal_id"] = p.focal.astype("category").cat.codes + 1
    p["partner_id"] = p.partner.astype("category").cat.codes + 1
    p["pair_id"] = (p.partner + "|" + p.focal).astype("category").cat.codes + 1

    cols = (["paper_count", "ru", "post", "year", "t"]
            + [f"pru_{g.lower()}" for g in GROUP_ORDER]
            + ["focal_id", "partner_id", "pair_id", "group",
               "focal", "partner"])
    p[cols].to_csv(OUT, index=False)
    print(f"wrote {OUT}  ({len(p):,} rows, {p.pair_id.nunique()} pairs, "
          f"{len(controls)} controls)")


if __name__ == "__main__":
    main()
