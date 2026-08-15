# -*- coding: utf-8 -*-
# Forest plot comparing the ITS level-break coefficient (beta1) on scholarly
# net inflow across three data sources for each political shock:
#   - Own (WoS-based)      2008-2024
#   - MPIDR SMD 2.0 OpenAlex 2008-2024
#   - MPIDR SMD 2.0 Scopus   2008-2024
# beta1 < 0  => brain drain (net outflow jump) after the shock.
# Output: its_forest/its_beta1_forest.{png,pdf} and its_beta1_summary.csv

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = str(CODE)
OUT = os.path.join(ROOT, "0raw_publiations_process", "raw data processing", "its_forest")
os.makedirs(OUT, exist_ok=True)

SHOCKS = [("uk", "GBR", 2016, "United Kingdom\nBrexit (2016)"),
          ("russia", "RUS", 2022, "Russia\ninvasion (2022)"),
          ("ukraine", "UKR", 2022, "Ukraine\ninvasion (2022)")]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
})


def fit_beta1(m):
    r = smf.ols("net_inflow ~ post + rel_year", data=m).fit()
    b, se = r.params["post"], r.bse["post"]
    df = int(r.df_resid)
    from scipy import stats
    tcrit = stats.t.ppf(0.975, df)
    # normalize by pre-event mean of gross flow (inflow) as a common scale,
    # so beta1 becomes % of baseline flow and is comparable across sources.
    base = m.loc[m.post == 0, "inflow"].mean()
    return b, se, b - tcrit * se, b + tcrit * se, r.pvalues["post"], base


def own_series(tag, t0):
    d = f"{ROOT}/3ppml_migration_did_{tag}_internal_control"
    i = (pd.read_csv(f"{d}/ppml_data_in.csv")
         .groupby(["year", "rel_year"], as_index=False).paper_count.sum()
         .rename(columns={"paper_count": "inflow"}))
    o = (pd.read_csv(f"{d}/ppml_data_out.csv")
         .groupby("year", as_index=False).paper_count.sum()
         .rename(columns={"paper_count": "outflow"}))
    m = i.merge(o, on="year").sort_values("year")
    m["net_inflow"] = m.inflow - m.outflow
    m["post"] = (m.year >= t0).astype(int)
    return m


def mpidr_series(tag, prov):
    d = f"{ROOT}/3ppml_migration_did_{tag}_internal_control_mpidr"
    return pd.read_csv(f"{d}/ppml_net_{prov}.csv")


SRC = [("Own (WoS)", "#1a1a1a", "o"),
       ("MPIDR OpenAlex", "#2c6fbb", "s"),
       ("MPIDR Scopus", "#c0392b", "^")]


def collect():
    rows = []
    for tag, foc, t0, _ in SHOCKS:
        series = {
            "Own (WoS)": own_series(tag, t0),
            "MPIDR OpenAlex": mpidr_series(tag, "openalex"),
            "MPIDR Scopus": mpidr_series(tag, "scopus"),
        }
        for src, _, _ in SRC:
            b, se, lo, hi, p, base = fit_beta1(series[src])
            sc = 100.0 / base if base else np.nan
            rows.append(dict(focal=foc, source=src, b1=b, se=se,
                             ci_lo=lo, ci_hi=hi, p=p, base_inflow=base,
                             b1_pct=b * sc, ci_lo_pct=lo * sc, ci_hi_pct=hi * sc))
    return pd.DataFrame(rows)


def stars(p):
    return "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.1 else "n.s."))


def main():
    df = collect()
    df.to_csv(os.path.join(OUT, "its_beta1_summary.csv"), index=False)

    col = {s: c for s, c, _ in SRC}
    mk = {s: m for s, _, m in SRC}

    # y positions: grouped by shock, 3 sources each, top-to-bottom
    labels, ypos, ycur = [], [], 0.0
    yticks_shock, ytick_pos = [], []
    row_of = {}
    for tag, foc, t0, disp in SHOCKS:
        block_start = ycur
        for src, _, _ in SRC:
            row_of[(foc, src)] = ycur
            ycur += 1
        ytick_pos.append((block_start + ycur - 1) / 2)
        yticks_shock.append(disp)
        ycur += 0.8  # gap between shocks

    def draw(ax, vcol, lcol, hcol, fmt, xlabel, title):
        ax.axvline(0, color="0.4", lw=1.0, ls="--", zorder=1)
        for tag, foc, t0, disp in SHOCKS:
            ys = [row_of[(foc, s)] for s, _, _ in SRC]
            ax.axhspan(min(ys) - 0.5, max(ys) + 0.5, color="0.5", alpha=0.05, zorder=0)
        for _, r in df.iterrows():
            y = row_of[(r.focal, r.source)]
            c = col[r.source]
            ax.plot([r[lcol], r[hcol]], [y, y], color=c, lw=2.0, zorder=3)
            ax.scatter([r[vcol]], [y], color=c, marker=mk[r.source], s=70,
                       zorder=4, edgecolor="white", linewidth=0.6)
            ax.annotate(f"{r[vcol]:{fmt}} {stars(r.p)}", xy=(r[hcol], y),
                        xytext=(8, 0), textcoords="offset points",
                        va="center", ha="left", fontsize=8.5, color=c)
        ax.set_yticks(ytick_pos)
        ax.set_yticklabels(yticks_shock, fontsize=11)
        ax.invert_yaxis()
        ax.set_xlabel(xlabel)
        ax.set_title(title, fontsize=11.5, pad=8)
        ax.margins(x=0.20)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 6.2), sharey=True)
    draw(axL, "b1", "ci_lo", "ci_hi", ",.0f",
         r"$\beta_1$ (persons)", "(a) Absolute level break")
    draw(axR, "b1_pct", "ci_lo_pct", "ci_hi_pct", ".1f",
         r"$\beta_1$ as % of pre-event annual inflow",
         "(b) Normalized (comparable across sources)")

    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=c, marker=m, lw=2, markersize=8,
                      markeredgecolor="white", label=s) for s, c, m in SRC]
    axL.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9,
               title="Data source")
    fig.suptitle("Effect of Political Shocks on Scholarly Net Inflow: "
                 "ITS level break ($\\beta_1$) with 95% CI  ($<0$ = brain drain)",
                 fontsize=13, y=1.01)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(OUT, f"its_beta1_forest.{ext}"),
                    dpi=200, bbox_inches="tight")
    print("saved:", os.path.join(OUT, "its_beta1_forest.png"))
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
