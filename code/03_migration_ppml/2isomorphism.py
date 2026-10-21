#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Isomorphism test: do talent flows and collaboration flows realign the same way?

For each focal country we align, partner-by-partner:
  x = collaboration post-shock deviation delta_k  (code/02_ppml_partners_*)
  y = migration    post-shock deviation delta_k  (this folder, out-direction)
and report Pearson r, Spearman rho, and sign-agreement, plus a scatter.

A positive, significant association => "where talent goes" and "where
collaboration grows" move together: the two networks realign isomorphically.
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
import pycountry
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FuncFormatter

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
COOP = REPO / "code"

# focal -> (collaboration folder, migration label)
PAIRS = {
    "RU": ("02_ppml_partners_russia", "russia_war", "Russia (2022 invasion)"),
    "UA": ("02_ppml_partners_ukraine", "ukraine_war", "Ukraine (2022 invasion)"),
    "GB": ("02_ppml_partners_uk", "uk_brexit", "United Kingdom (Brexit)"),
}

# manual fixes where the collaboration country strings don't fuzzy-match cleanly
NAME_TO_ISO = {
    "IRAN, ISLAMIC REP.": "IR", "KOREA, REP.": "KR", "KOREA, DEM. REP.": "KP",
    "NORTH KOREA": "KP", "SOUTH KOREA": "KR", "RUSSIA": "RU", "RUSSIAN FEDERATION": "RU",
    "BYELARUS": "BY", "BURMA": "MM", "CZECHIA": "CZ", "CZECH REPUBLIC": "CZ",
    "SLOVAK REPUBLIC": "SK", "TURKIYE": "TR", "TURKEY": "TR", "VIET NAM": "VN",
    "UNITED KINGDOM": "GB", "UNITED STATES": "US", "MACEDONIA": "MK",
    "REPUBLIC OF SERBIA": "RS", "REPUBLIC OF KOSOVO": "XK", "IVORY COAST": "CI",
    "BOLIVIA": "BO", "VENEZUELA": "VE", "TANZANIA": "TZ", "MOLDOVA": "MD",
    "BOSNIA & HERZEGOVINA": "BA", "BRUNEI": "BN", "LAOS": "LA", "SYRIA": "SY",
    "ANTIGUA & BARBUDA": "AG", "ST-KITTS & NEVIS": "KN", "CAPE VERDE": "CV",
    "SWAZILAND": "SZ", "VATICAN": "VA", "PALESTINE": "PS",
}


def to_iso2(name):
    n = str(name).strip().upper()
    if n in NAME_TO_ISO:
        return NAME_TO_ISO[n]
    # pycountry fuzzy on a title-cased version
    try:
        hit = pycountry.countries.search_fuzzy(name.title())
        if hit:
            return hit[0].alpha_2
    except LookupError:
        pass
    return None


def integer_xaxis(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))


def load_coop(folder):
    d = pd.read_csv(COOP / folder / "partner_coefficients.csv")
    d = d[["partner_country", "coef", "pvalue"]].rename(
        columns={"coef": "coef_coop", "pvalue": "p_coop"})
    d["iso2"] = d.partner_country.map(to_iso2)
    d = d.dropna(subset=["iso2"]).drop_duplicates("iso2")
    return d


def load_mig(label):
    d = pd.read_csv(HERE / f"migration_coef_{label}_out.csv")
    d = d[["partner_iso", "coef", "pvalue"]].rename(
        columns={"partner_iso": "iso2", "coef": "coef_mig", "pvalue": "p_mig"})
    d["iso2"] = d.iso2.str.upper()
    return d.drop_duplicates("iso2")


def main():
    summary = []
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, (focal, (folder, label, title)) in zip(axes, PAIRS.items()):
        coop = load_coop(folder)
        mig = load_mig(label)
        m = coop.merge(mig, on="iso2", how="inner")
        m = m[m.iso2 != focal]

        x, y = m.coef_coop.values, m.coef_mig.values
        r, pr = stats.pearsonr(x, y)
        rho, prho = stats.spearmanr(x, y)
        sign_agree = float(np.mean(np.sign(x) == np.sign(y)))
        # among partners significant on BOTH sides
        both_sig = m[(m.p_coop < 0.10) & (m.p_mig < 0.10)]
        sign_agree_sig = (
            float(np.mean(np.sign(both_sig.coef_coop) == np.sign(both_sig.coef_mig)))
            if len(both_sig) else np.nan)

        summary.append({
            "focal": focal, "n_partners": len(m),
            "pearson_r": r, "pearson_p": pr,
            "spearman_rho": rho, "spearman_p": prho,
            "sign_agreement": sign_agree,
            "n_both_sig": len(both_sig),
            "sign_agreement_bothsig": sign_agree_sig,
        })

        ax.axhline(0, color="grey", lw=.6)
        ax.axvline(0, color="grey", lw=.6)
        ax.scatter(x, y, s=18, alpha=.6, edgecolor="none")
        # label a few notable partners
        notable = m.reindex(m.coef_mig.abs().sort_values(ascending=False).index).head(8)
        for _, row in notable.iterrows():
            ax.annotate(row.iso2, (row.coef_coop, row.coef_mig),
                        fontsize=7, alpha=.8)
        # OLS fit line
        if len(m) > 2:
            b1, b0 = np.polyfit(x, y, 1)
            xs = np.linspace(x.min(), x.max(), 50)
            ax.plot(xs, b0 + b1 * xs, color="C3", lw=1.2)
        ax.set_title(f"{title}\nr={r:.2f} (p={pr:.3f}), rho={rho:.2f}", fontsize=10)
        ax.set_xlabel("Collaboration deviation  " + r"$\delta_k$")
        ax.set_ylabel("Migration deviation  " + r"$\delta_k$")

    fig.suptitle("Are talent-flow and collaboration realignments isomorphic?", fontsize=13)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    out_pdf = HERE / "isomorphism_scatter.pdf"
    out_png = HERE / "isomorphism_scatter.png"
    fig.savefig(out_pdf)
    fig.savefig(out_png, dpi=150)

    sdf = pd.DataFrame(summary)
    sdf.to_csv(HERE / "isomorphism_summary.csv", index=False)
    pd.set_option("display.width", 140)
    print(sdf.to_string(index=False))
    print(f"\nsaved: {out_pdf.name}, {out_png.name}, isomorphism_summary.csv")


if __name__ == "__main__":
    main()
