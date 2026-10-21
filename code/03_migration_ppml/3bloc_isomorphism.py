#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bloc-level isomorphism: aggregate partner-level deviations into West (NATO) vs
East (SCO) blocs, for BOTH migration and collaboration, and compare the tilt.

This complements 2isomorphism.py: partner-by-partner the two networks are noisy,
but the paper's substantive claim is about macro realignment (West vs East).
Here we test whether talent and collaboration tilt in the SAME direction.
"""
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
COOP = REPO / "code"

# NATO members as of early 2022 (matches paper footnote) -> ISO2
NATO = {
    "AL": "Albania", "BE": "Belgium", "BG": "Bulgaria", "CA": "Canada",
    "HR": "Croatia", "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia",
    "FR": "France", "DE": "Germany", "GR": "Greece", "HU": "Hungary",
    "IS": "Iceland", "IT": "Italy", "LV": "Latvia", "LT": "Lithuania",
    "LU": "Luxembourg", "ME": "Montenegro", "NL": "Netherlands",
    "MK": "North Macedonia", "NO": "Norway", "PL": "Poland", "PT": "Portugal",
    "RO": "Romania", "SK": "Slovakia", "SI": "Slovenia", "ES": "Spain",
    "TR": "Turkey", "GB": "United Kingdom", "US": "United States",
}
# SCO members as of early 2022 -> ISO2
SCO = {
    "CN": "China", "IN": "India", "KZ": "Kazakhstan", "KG": "Kyrgyzstan",
    "PK": "Pakistan", "RU": "Russia", "TJ": "Tajikistan", "UZ": "Uzbekistan",
}

PAIRS = {
    "RU": ("russia_war", "Russia (2022 invasion)"),
    "UA": ("ukraine_war", "Ukraine (2022 invasion)"),
    "GB": ("uk_brexit", "United Kingdom (Brexit)"),
}
FOLDER = {"RU": "02_ppml_partners_russia", "UA": "02_ppml_partners_ukraine", "GB": "02_ppml_partners_uk"}

# reuse the same name->iso map from script 2
from importlib import util as _util
_spec = _util.spec_from_file_location("iso2mod", HERE / "2isomorphism.py")
_iso = _util.module_from_spec(_spec)
_spec.loader.exec_module(_iso)
to_iso2 = _iso.to_iso2


def bloc_mean(df, coefcol, focal):
    """Weighted-by-nothing simple mean deviation for West and East blocs."""
    d = df[df.iso2 != focal]
    west = d[d.iso2.isin(NATO)][coefcol]
    east = d[d.iso2.isin(SCO)][coefcol]
    return west.mean(), east.mean(), len(west), len(east)


def main():
    rows = []
    for focal, (label, title) in PAIRS.items():
        coop = pd.read_csv(COOP / FOLDER[focal] / "partner_coefficients.csv")
        coop["iso2"] = coop.partner_country.map(to_iso2)
        coop = coop.dropna(subset=["iso2"]).drop_duplicates("iso2")

        mig = pd.read_csv(HERE / f"migration_coef_{label}_out.csv")
        mig = mig.rename(columns={"partner_iso": "iso2"})
        mig["iso2"] = mig.iso2.str.upper()

        cw, ce, ncw, nce = bloc_mean(coop, "coef", focal)
        mw, me, nmw, nme = bloc_mean(mig, "coef", focal)

        coop_tilt = cw - ce          # >0: collaboration tilts West
        mig_tilt = mw - me           # >0: talent tilts West
        rows.append({
            "focal": focal, "title": title,
            "coop_West": cw, "coop_East": ce, "coop_tilt(W-E)": coop_tilt,
            "mig_West": mw, "mig_East": me, "mig_tilt(W-E)": mig_tilt,
            "same_direction": bool(np.sign(coop_tilt) == np.sign(mig_tilt)),
        })

    res = pd.DataFrame(rows)
    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", lambda v: f"{v:.3f}")
    print("=" * 100)
    print("BLOC-LEVEL TILT  (mean partner deviation delta_k; >0 = tilt toward that bloc)")
    print("=" * 100)
    print(res[["focal", "coop_tilt(W-E)", "mig_tilt(W-E)", "same_direction"]].to_string(index=False))
    print()
    print(res.to_string(index=False))
    res.to_csv(HERE / "bloc_isomorphism_summary.csv", index=False)
    print(f"\nsaved: bloc_isomorphism_summary.csv")


if __name__ == "__main__":
    main()
