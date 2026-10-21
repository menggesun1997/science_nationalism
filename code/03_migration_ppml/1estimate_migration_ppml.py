#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration-flow gravity PPML, built to mirror the bilateral-collaboration PPML
in code/02_ppml_partners_* one-for-one.

Outcome:  Flow_{jt} = number of scholars migrating between the focal country and
          partner j in year t (OpenAlex residence-change events).
Model  :  E[Flow_{jt}] = exp( alpha_j + lambda_t
                              + delta_k * ( 1{j=k} x Post_t )
                              + gamma * ln(PartnerSize_{jt}) )
          - alpha_j : partner fixed effects   (absorb)
          - lambda_t: year fixed effects      (absorb; replaces the collaboration
                       model's ln(total_vol) offset -- in a single-focal panel the
                       year FE absorbs the focal country's overall flow trend)
          - delta_k : partner-specific post interaction  ==  i(partner, post)
          - PartnerSize_{jt}: partner j's active-researcher stock that year
          vce: cluster by partner.

This is deliberately the SAME estimator (Poisson w/ high-dim FE == ppmlhdfe) and
the SAME delta_k object as the collaboration analysis, so the two sets of
partner coefficients are directly comparable (see 2isomorphism.py).

Direction:
  out  -> focal is ORIGIN (brain-drain destinations: where talent goes)
  in   -> focal is DEST   (where incoming talent comes from)
The out-direction is the primary object compared against collaboration reshuffling.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pyfixest as pf

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULTS = REPO / "migration_data" / "openalex_pipeline" / "results"
FLOWS_CSV = RESULTS / "openalex_bilateral_flows_1998_2025.csv"
CY_CSV = RESULTS / "openalex_country_year_1998_2025.csv"

YEAR_MIN, YEAR_MAX = 2005, 2024  # match the collaboration analysis window

# focal country (ISO2) -> (post-treatment start year, min cumulative flow to keep partner)
FOCALS = {
    "GB": {"post_year": 2017, "min_total": 50, "label": "uk_brexit"},   # 2016 referendum
    "RU": {"post_year": 2022, "min_total": 20, "label": "russia_war"},  # 2022 invasion
    "UA": {"post_year": 2022, "min_total": 10, "label": "ukraine_war"},
}


def build_panel(flows, size, focal, post_year, direction):
    """Return a balanced partner x year panel for one focal country/direction."""
    if direction == "out":
        sub = flows[flows.from_country == focal].rename(columns={"to_country": "partner"})
    else:
        sub = flows[flows.to_country == focal].rename(columns={"from_country": "partner"})
    sub = sub[["year", "partner", "n_migrations"]].dropna(subset=["partner"])
    sub = sub[sub.partner.astype(str).str.match(r"^[A-Za-z]{2}$")]

    partners = sorted(sub.partner.unique())
    years = list(range(YEAR_MIN, YEAR_MAX + 1))
    grid = pd.MultiIndex.from_product([partners, years], names=["partner", "year"]).to_frame(index=False)

    panel = grid.merge(sub, on=["partner", "year"], how="left")
    panel["flow"] = panel["n_migrations"].fillna(0.0)
    panel = panel.drop(columns=["n_migrations"])

    # partner scientific-size mass control (active researchers that year)
    panel = panel.merge(
        size.rename(columns={"country": "partner", "n_researchers": "partner_size"})[
            ["partner", "year", "partner_size"]
        ],
        on=["partner", "year"], how="left",
    )
    panel["partner_size"] = panel["partner_size"].fillna(0).clip(lower=1)
    panel["ln_partner_size"] = np.log(panel["partner_size"])

    panel["post"] = (panel["year"] >= post_year).astype(int)

    # keep partners with enough volume and both pre/post positive support
    tot = panel.groupby("partner")["flow"].sum()
    pre_pos = panel[panel.post == 0].groupby("partner")["flow"].apply(lambda s: (s > 0).any())
    post_pos = panel[panel.post == 1].groupby("partner")["flow"].apply(lambda s: (s > 0).any())
    keep = tot[tot >= 1].index  # placeholder, refined by caller via min_total
    return panel, tot, pre_pos, post_pos


def estimate(focal, cfg, flows, size, direction):
    post_year = cfg["post_year"]
    panel, tot, pre_pos, post_pos = build_panel(flows, size, focal, post_year, direction)

    good = [p for p in tot.index
            if tot[p] >= cfg["min_total"]
            and bool(pre_pos.get(p, False))
            and bool(post_pos.get(p, False))
            and p != focal]
    panel = panel[panel.partner.isin(good)].copy()

    n_partners = panel.partner.nunique()
    n_years = panel.year.nunique()
    print(f"    [{focal}/{direction}] partners kept={n_partners}, years={n_years}, "
          f"rows={len(panel)}, zero-share={(panel.flow==0).mean():.1%}")

    m = pf.fepois(
        "flow ~ ln_partner_size + i(partner, post) | partner + year",
        data=panel, vcov={"CRV1": "partner"},
    )

    tab = m.tidy().reset_index()
    coef_col = tab.columns[0]
    intr = tab[tab[coef_col].str.contains("post")].copy()
    # coefficient labels look like  C(partner)[T.US]:post  /  i(partner,post)[US] etc.
    intr["partner"] = intr[coef_col].str.extract(r"partner[,)\]]*.*?([A-Z]{2})\b")
    # robust fallback: pull the trailing 2-letter iso code
    iso = intr[coef_col].str.findall(r"[A-Z]{2}").apply(lambda xs: xs[-1] if xs else None)
    intr["partner"] = intr["partner"].fillna(iso)

    out = intr[["partner", "Estimate", "Std. Error", "t value", "Pr(>|t|)"]].copy()
    out.columns = ["partner_iso", "coef", "se", "tstat", "pvalue"]
    out["sig_10"] = (out.pvalue < 0.10).astype(int)
    out["sig_05"] = (out.pvalue < 0.05).astype(int)
    out["sig_01"] = (out.pvalue < 0.01).astype(int)
    out["direction"] = np.sign(out.coef).astype(int)
    out["focal"] = focal
    out["flow_direction"] = direction
    out = out.dropna(subset=["partner_iso"]).sort_values("coef", ascending=False)
    return out


def main():
    flows = pd.read_csv(FLOWS_CSV)
    size = pd.read_csv(CY_CSV)
    flows = flows[(flows.year >= YEAR_MIN) & (flows.year <= YEAR_MAX)]

    print("=" * 80)
    print("Migration-flow gravity PPML  (mirrors collaboration PPML)")
    print("=" * 80)

    for focal, cfg in FOCALS.items():
        print(f"\n### focal={focal}  ({cfg['label']})  post>={cfg['post_year']}")
        for direction in ("out", "in"):
            res = estimate(focal, cfg, flows, size, direction)
            fn = HERE / f"migration_coef_{cfg['label']}_{direction}.csv"
            res.to_csv(fn, index=False)
            top = res.head(6)[["partner_iso", "coef", "pvalue"]].to_string(index=False)
            bot = res.tail(6)[["partner_iso", "coef", "pvalue"]].to_string(index=False)
            print(f"  saved {fn.name}  (n={len(res)})")
            print("   strongest positive deviations:\n" + top)
            print("   strongest negative deviations:\n" + bot)


if __name__ == "__main__":
    main()
