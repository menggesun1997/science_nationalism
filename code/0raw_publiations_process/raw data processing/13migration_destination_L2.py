# -*- coding: utf-8 -*-
# L2 — Where did the talent go, and does migration reconfiguration mirror
# collaboration reconfiguration?
#
# Two products per focal (RUS/GBR/UKR):
#  (a) migration-destination reconfiguration: partner-level PPML delta on
#      OUTFLOW (focal -> partner), i.e. relative change in emigration to each
#      partner after the shock. Ranked bar chart (gains vs losses).
#  (b) migration-delta vs collaboration-delta scatter: for partners present in
#      both channels, compare the migration PPML delta with the collaboration
#      PPML delta (paper co-authorship), to see whether people-flows and
#      collaboration-flows realign in the same direction.
#
# Inputs:
#   migration: 3ppml_migration_did_<tag>_internal_control/results/
#              partner_coefficients_{in,out}.csv  (partner_country = ISO3)
#   collab:    2ppml_did_<tag>_internal_control/partner_coefficients.csv
#              (partner_country = full name, coef = log-scale delta)
# Output: its_L2_migration/*.png,*.pdf and merged csv.

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = str(CODE)
OUT = os.path.join(ROOT, "0raw_publiations_process", "raw data processing", "its_L2_migration")
os.makedirs(OUT, exist_ok=True)

FOCALS = [("russia", "RUS", 2022, "Russia (2022 invasion)"),
          ("uk", "GBR", 2016, "United Kingdom (Brexit 2016)"),
          ("ukraine", "UKR", 2022, "Ukraine (2022 invasion)")]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25,
})


def name_to_iso3(name):
    import pycountry
    key = str(name).strip().replace("_", " ").title()
    fixes = {
        "Russian Federation": "RUS", "Russia": "RUS", "Korea": "KOR",
        "South Korea": "KOR", "Czech Republic": "CZE", "Czechia": "CZE",
        "Slovak Republic": "SVK", "Iran": "IRN", "Taiwan": "TWN",
        "Vietnam": "VNM", "Viet Nam": "VNM", "Moldova": "MDA",
        "Bolivia": "BOL", "Turkey": "TUR", "Syria": "SYR",
        "United States": "USA", "United Kingdom": "GBR",
    }
    if key in fixes:
        return fixes[key]
    try:
        return pycountry.countries.lookup(key).alpha_3
    except Exception:
        try:
            return pycountry.countries.search_fuzzy(key)[0].alpha_3
        except Exception:
            return None


def load_migration(tag, direction):
    d = f"{ROOT}/3ppml_migration_did_{tag}_internal_control/results"
    m = pd.read_csv(f"{d}/partner_coefficients_{direction}.csv")
    return m[["partner_country", "delta", "se", "pval", "pct"]].rename(
        columns={"partner_country": "iso3", "delta": "mig_delta",
                 "pval": "mig_p", "pct": "mig_pct"})


def load_collab(tag):
    d = f"{ROOT}/2ppml_did_{tag}_internal_control"
    c = pd.read_csv(f"{d}/partner_coefficients.csv")
    c["iso3"] = c["partner_country"].map(name_to_iso3)
    c = c.dropna(subset=["iso3"])
    return c[["iso3", "coef", "pvalue"]].rename(
        columns={"coef": "collab_delta", "pvalue": "collab_p"})


def panel_destinations(ax, tag, foc, title, topn=12):
    """(a) ranked emigration-destination reconfiguration (OUT delta)."""
    m = load_migration(tag, "out").copy()
    m = m[np.isfinite(m.mig_delta)]
    # keep significant + largest-magnitude partners for clarity
    m["absd"] = m.mig_delta.abs()
    sig = m[m.mig_p < 0.1].sort_values("mig_delta")
    if len(sig) > topn:
        head = sig.head(topn // 2)
        tail = sig.tail(topn // 2)
        sig = pd.concat([head, tail])
    colors = ["#c0392b" if v > 0 else "#2c6fbb" for v in sig.mig_delta]
    ax.barh(range(len(sig)), sig.mig_delta.values, color=colors)
    ax.set_yticks(range(len(sig)))
    ax.set_yticklabels(sig.iso3.values, fontsize=8)
    ax.axvline(0, color="0.3", lw=0.8)
    ax.set_title(title, fontsize=10.5)
    ax.set_xlabel(r"emigration PPML $\delta$ (log; $>0$=more outflow)")


def panel_scatter(ax, tag, foc, title):
    """(b) migration delta vs collaboration delta, matched partners."""
    mo = load_migration(tag, "out")
    cc = load_collab(tag)
    mg = mo.merge(cc, on="iso3", how="inner")
    mg = mg[np.isfinite(mg.mig_delta) & np.isfinite(mg.collab_delta)]
    sig = (mg.mig_p < 0.1) & (mg.collab_p < 0.1)
    ax.axhline(0, color="0.5", lw=0.7); ax.axvline(0, color="0.5", lw=0.7)
    ax.scatter(mg.loc[~sig, "collab_delta"], mg.loc[~sig, "mig_delta"],
               s=22, color="0.7", alpha=0.6, label="n.s.")
    ax.scatter(mg.loc[sig, "collab_delta"], mg.loc[sig, "mig_delta"],
               s=40, color="#c0392b", zorder=4, label="both sig. (p<0.1)")
    for _, r in mg[sig].iterrows():
        ax.annotate(r.iso3, (r.collab_delta, r.mig_delta), fontsize=7,
                    xytext=(3, 3), textcoords="offset points")
    if len(mg) > 2:
        rho = mg[["collab_delta", "mig_delta"]].corr().iloc[0, 1]
        ax.text(0.04, 0.92, f"r={rho:.2f} (N={len(mg)})", transform=ax.transAxes,
                fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="#f7f7f7", ec="0.8"))
    ax.set_title(title, fontsize=10.5)
    ax.set_xlabel(r"collaboration $\delta$ (co-authorship)")
    ax.set_ylabel(r"emigration $\delta$ (people)")
    return mg


def main():
    # (a) destinations: one row of 3 panels
    figA, axesA = plt.subplots(1, 3, figsize=(15, 5.5))
    for ax, (tag, foc, t0, title) in zip(axesA, FOCALS):
        panel_destinations(ax, tag, foc, title)
    figA.suptitle("L2a — Reconfiguration of scholar emigration destinations after the shock "
                  "(red=more outflow, blue=less)", fontsize=12.5, y=1.02)
    figA.tight_layout()
    for ext in ["png", "pdf"]:
        figA.savefig(os.path.join(OUT, f"L2a_migration_destinations.{ext}"),
                     dpi=200, bbox_inches="tight")
    plt.close(figA)
    print("saved L2a_migration_destinations.png")

    # (b) scatter: migration vs collaboration
    figB, axesB = plt.subplots(1, 3, figsize=(15, 5.2))
    allm = []
    for ax, (tag, foc, t0, title) in zip(axesB, FOCALS):
        mg = panel_scatter(ax, tag, foc, title)
        mg["focal"] = foc
        allm.append(mg)
    axesB[0].legend(loc="lower right", fontsize=8)
    figB.suptitle("L2b — Do people-flows and collaboration-flows realign together? "
                  "(matched partners, both PPML $\\delta$)", fontsize=12.5, y=1.02)
    figB.tight_layout()
    for ext in ["png", "pdf"]:
        figB.savefig(os.path.join(OUT, f"L2b_migration_vs_collab.{ext}"),
                     dpi=200, bbox_inches="tight")
    plt.close(figB)
    pd.concat(allm).to_csv(os.path.join(OUT, "migration_vs_collab_merged.csv"), index=False)
    print("saved L2b_migration_vs_collab.png")
    for mg in allm:
        f = mg.focal.iloc[0]
        r = mg[["collab_delta", "mig_delta"]].corr().iloc[0, 1]
        print(f"  {f}: matched N={len(mg)}, corr(mig,collab)={r:.3f}")


if __name__ == "__main__":
    main()
