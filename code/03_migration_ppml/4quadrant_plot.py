#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2x2 quadrant plot: collaboration deviation (x) vs migration deviation (y).

Quadrants:
  Q1 (x>0,y>0)  both grow           -> genuine re-anchoring (collab + talent)
  Q2 (x<0,y>0)  collab down/talent up-> ties cut but people still move there
  Q3 (x<0,y<0)  both shrink         -> full decoupling
  Q4 (x>0,y<0)  collab up/talent down-> "paper pivot" w/o people (e.g. RU->CN/IR)

Highlights key partners (blocs colour-coded). One figure-level legend at bottom.
"""
from pathlib import Path
from importlib import util as _util
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
COOP = HERE.parents[0]
_spec = _util.spec_from_file_location("iso2mod", HERE / "2isomorphism.py")
_iso = _util.module_from_spec(_spec); _spec.loader.exec_module(_iso)
to_iso2 = _iso.to_iso2

FOLDER = {"RU": "02_ppml_partners_russia", "UA": "02_ppml_partners_ukraine", "GB": "02_ppml_partners_uk"}
LABEL = {"RU": "russia_war", "UA": "ukraine_war", "GB": "uk_brexit"}
TITLE = {"RU": "Russia (2022 invasion)", "UA": "Ukraine (2022 invasion)", "GB": "United Kingdom (Brexit)"}

NATO = set("AL BE BG CA HR CZ DK EE FR DE GR HU IS IT LV LT LU ME NL MK NO PL PT RO SK SI ES TR GB US".split())
SCO = set("CN IN KZ KG PK RU TJ UZ".split())

# partners worth labelling per focal (kept short for readability)
SPOT = {
    "RU": ["CN","IR","KZ","BY","US","DE","FR","GB","FI","LT","LV","EE","PL","IL","AU","CA","GE","AM","TR","NL"],
    "UA": ["RU","BY","US","GB","DE","PL","LT","LV","EE","CN","IR","AU","NL","CA","TR","IL","KZ","FR"],
    "GB": ["US","CN","IR","DE","FR","NL","AU","IL","PL","LT","LV","EE","TR","KZ","CA","FI","GE","AM"],
}

def load(focal):
    coop = pd.read_csv(COOP / FOLDER[focal] / "partner_coefficients.csv")
    coop["iso2"] = coop.partner_country.map(to_iso2)
    coop = coop.dropna(subset=["iso2"]).drop_duplicates("iso2")[["iso2","coef","pvalue"]]
    coop.columns = ["iso2","coop","p_coop"]
    mig = pd.read_csv(HERE / f"migration_coef_{LABEL[focal]}_out.csv").rename(columns={"partner_iso":"iso2"})
    mig["iso2"] = mig.iso2.str.upper()
    mig = mig[["iso2","coef","pvalue"]]; mig.columns=["iso2","mig","p_mig"]
    m = coop.merge(mig, on="iso2").query("iso2 != @focal")
    return m

def bloc_color(iso):
    if iso in SCO: return "#c0392b"      # East / SCO  (red)
    if iso in NATO: return "#2471a3"     # West / NATO (blue)
    return "#7f8c8d"                     # other (grey)

def main():
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4))
    for ax, focal in zip(axes, ["RU","UA","GB"]):
        m = load(focal)
        # clip extreme outliers just for view
        lim_x = np.nanpercentile(np.abs(m.coop), 98)
        lim_y = np.nanpercentile(np.abs(m.mig), 98)
        m = m[(m.coop.abs() <= lim_x*1.6) & (m.mig.abs() <= lim_y*1.6)]

        ax.axhline(0, color="black", lw=.7)
        ax.axvline(0, color="black", lw=.7)
        colors = m.iso2.map(bloc_color)
        # size ~ joint significance
        sig = ((m.p_coop < .10).astype(int) + (m.p_mig < .10).astype(int))
        sizes = 20 + sig*28
        ax.scatter(m.coop, m.mig, s=sizes, c=colors, alpha=.65, edgecolor="white", linewidth=.4)

        for _, r in m[m.iso2.isin(SPOT[focal])].iterrows():
            ax.annotate(r.iso2, (r.coop, r.mig), fontsize=8, fontweight="bold",
                        xytext=(3,3), textcoords="offset points", color=bloc_color(r.iso2))

        xl = max(lim_x*1.6, 0.1); yl = max(lim_y*1.6, 0.1)
        ax.set_xlim(-xl, xl); ax.set_ylim(-yl, yl)
        # quadrant tags
        tag = dict(fontsize=8, color="#555", alpha=.8)
        ax.text(xl*.97, yl*.92, "collab ↑ / talent ↑", ha="right", **tag)
        ax.text(-xl*.97, yl*.92, "collab ↓ / talent ↑", ha="left", **tag)
        ax.text(-xl*.97, -yl*.95, "collab ↓ / talent ↓", ha="left", **tag)
        ax.text(xl*.97, -yl*.95, "collab ↑ / talent ↓", ha="right", **tag)
        r = np.corrcoef(m.coop, m.mig)[0,1]
        ax.set_title(f"{TITLE[focal]}   (r={r:.2f})", fontsize=11)
        ax.set_xlabel(r"Collaboration deviation $\delta_k$")
        ax.set_ylabel(r"Migration deviation $\delta_k$")

    # single bottom legend
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0],[0], marker='o', color='w', markerfacecolor="#2471a3", markersize=9, label="West / NATO"),
        Line2D([0],[0], marker='o', color='w', markerfacecolor="#c0392b", markersize=9, label="East / SCO"),
        Line2D([0],[0], marker='o', color='w', markerfacecolor="#7f8c8d", markersize=9, label="Other"),
    ]
    fig.legend(handles=handles, frameon=False, loc="lower center", ncol=3, bbox_to_anchor=(0.5,-0.02))
    fig.suptitle("Collaboration vs talent-migration realignment (out-flows)", fontsize=13)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(HERE / "quadrant.pdf")
    fig.savefig(HERE / "quadrant.png", dpi=150)
    print("saved quadrant.pdf / quadrant.png")

if __name__ == "__main__":
    main()
