#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate donor-weight LaTeX tables for the SI (replacing the lollipop figures).

One compact table per synthetic control. Because each donor pool has up to 43
countries, a single one-column-per-country table overflows the page; instead we
lay the donor pool out as several (Country, weight) pairs per row, following the
compact "doppelganger weights" style. Weights are read from the
*_weights_country.xlsx exported by the compare*.do scripts, so the tables stay
in sync with the Stata output. A weight in (0, 0.01) is shown as ``<0.01``; an
exactly-zero weight is shown as ``0``.

Outputs paper/tables/weights_*.tex, each a full table environment ready to be
\\input in si.tex.
"""

from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
CODE = REPO / "code"
OUTDIR = REPO / "paper" / "tables"
OUTDIR.mkdir(parents=True, exist_ok=True)

DISPLAY = {
    "RUSSIAN_FEDERATION": "Russia",
    "UNITED_STATES": "United States",
    "UNITED_KINGDOM": "United Kingdom",
    "KOREA,_REP.": "Korea",
    "KOREA": "Korea",
    "SLOVAK_REPUBLIC": "Slovak Rep.",
    "COSTA_RICA": "Costa Rica",
    "SOUTH_AFRICA": "South Africa",
    "TURKIYE": "T\\\"urkiye",
    "CZECHIA": "Czechia",
    "EU": "EU",
}
# Treated / directly exposed units never appear as their own donors.
EXCLUDE = {"UNITED_KINGDOM", "EU", "RUSSIAN_FEDERATION", "UKRAINE"}

# Pairs of (Country, weight) laid out per row.
PAIRS_PER_ROW = 4


def disp(raw):
    key = str(raw).strip().upper()
    if key in DISPLAY:
        return DISPLAY[key]
    return key.replace("_", " ").title()


def fmt(w):
    if pd.isna(w):
        return "--"
    w = float(w)
    if w <= 0:
        return "0"
    if w < 0.01:
        return "$<$0.01"
    return f"{w:.2f}"


def load(path):
    d = pd.read_excel(path)[["Country", "_W_Weight"]].copy()
    d = d[~d["Country"].str.upper().isin(EXCLUDE)]
    d["disp"] = d["Country"].map(disp)
    d = d.sort_values("disp")
    return list(zip(d["disp"], d["_W_Weight"]))


def compact_table(pairs, label, caption):
    """Lay out (country, weight) pairs as PAIRS_PER_ROW per table row."""
    k = PAIRS_PER_ROW
    colspec = "l r " * k
    lines = [
        "\\begin{table}[H]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\small",
        "\\setlength{\\tabcolsep}{5pt}",
        "\\begin{tabular}{" + colspec.strip() + "}",
        "\\toprule",
    ]
    for i in range(0, len(pairs), k):
        chunk = pairs[i:i + k]
        cells = []
        for c, w in chunk:
            cells.append(c)
            cells.append(fmt(w))
        # pad short final row so column count matches
        while len(cells) < 2 * k:
            cells.append("")
        lines.append(" & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines) + "\n"


def emit(path_xlsx, label, caption, out_name):
    pairs = load(path_xlsx)
    (OUTDIR / out_name).write_text(
        compact_table(pairs, label, caption), encoding="utf-8")


def main():
    B = CODE / "01_scm_brexit"
    C = CODE / "01_scm_crimea_2014"
    W = CODE / "01_scm_war_2022"

    jobs = [
        # Brexit: UK only.
        (B / "total_publications/uk_weights_country.xlsx",
         "tab:w_brexit_uk_total",
         "Donor weights for the synthetic UK, Brexit --- total publications.",
         "weights_brexit_uk_total.tex"),
        (B / "intl_ratio/uk_weights_country.xlsx",
         "tab:w_brexit_uk_ratio",
         "Donor weights for the synthetic UK, Brexit --- international "
         "collaboration ratio.",
         "weights_brexit_uk_ratio.tex"),
        # Crimea.
        (C / "total_publications/russia_weights_country.xlsx",
         "tab:w_crimea_ru_total",
         "Donor weights for synthetic Russia, 2014 Crimean crisis --- total "
         "publications.",
         "weights_crimea_ru_total.tex"),
        (C / "total_publications/ukraine_weights_country.xlsx",
         "tab:w_crimea_ua_total",
         "Donor weights for synthetic Ukraine, 2014 Crimean crisis --- total "
         "publications.",
         "weights_crimea_ua_total.tex"),
        (C / "intl_ratio/russia_weights_country.xlsx",
         "tab:w_crimea_ru_ratio",
         "Donor weights for synthetic Russia, 2014 Crimean crisis --- "
         "international collaboration ratio.",
         "weights_crimea_ru_ratio.tex"),
        (C / "intl_ratio/ukraine_weights_country.xlsx",
         "tab:w_crimea_ua_ratio",
         "Donor weights for synthetic Ukraine, 2014 Crimean crisis --- "
         "international collaboration ratio.",
         "weights_crimea_ua_ratio.tex"),
        # War.
        (W / "total_publications/russia_weights_country.xlsx",
         "tab:w_war_ru_total",
         "Donor weights for synthetic Russia, 2022 full-scale invasion --- "
         "total publications.",
         "weights_war_ru_total.tex"),
        (W / "total_publications/ukraine_weights_country.xlsx",
         "tab:w_war_ua_total",
         "Donor weights for synthetic Ukraine, 2022 full-scale invasion --- "
         "total publications.",
         "weights_war_ua_total.tex"),
        (W / "intl_ratio/russia_weights_country.xlsx",
         "tab:w_war_ru_ratio",
         "Donor weights for synthetic Russia, 2022 full-scale invasion --- "
         "international collaboration ratio.",
         "weights_war_ru_ratio.tex"),
        (W / "intl_ratio/ukraine_weights_country.xlsx",
         "tab:w_war_ua_ratio",
         "Donor weights for synthetic Ukraine, 2022 full-scale invasion --- "
         "international collaboration ratio.",
         "weights_war_ua_ratio.tex"),
    ]

    common = (" Each cell pairs a donor country with its weight; weights below "
              "0.01 are shown as $<$0.01 and donors receiving zero weight as 0.")
    for xlsx, label, cap, out in jobs:
        emit(xlsx, label, cap + common, out)

    print("wrote", len(jobs), "weight tables to", OUTDIR)


if __name__ == "__main__":
    main()
