# Build scm_panel.csv for UK Brexit SCM from MPIDR Scholarly Migration Database
# (OpenAlex 2026 V2, country-year aggregates).
#
# Treated: GBR, treatment year T0=2016 (Brexit referendum).
# Donor-pool rules (same logic as Russia/Ukraine SCM, relative to GBR):
#   pre (2005-2015) mean researchers in [1/5, 5x] of GBR;
#   mean |netmigration| >= 50;
#   exclude RUS/UKR/BLR (later war shocks in long post window);
#   keep GBR as treated unit.
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
SRC_DIR = REPO / "migration_data" / "Global-flows-and-rates-of-international-migration-of-scholars-2026_V2" / "2026_V2"
SRC_PARQUET = SRC_DIR / "openalex_2026_V2_scholarlymigration_country.parquet"
SRC_CSV = SRC_DIR / "openalex_2026_V2_scholarlymigration_country.csv"
OUT = ROOT / "scm_panel.csv"

TREATED = "GBR"
PRE_MIN, PRE_MAX = 2005, 2015  # pre-Brexit
PANEL_MIN, PANEL_MAX = 2005, 2024
EXCLUDE = {"RUS", "UKR", "BLR"}
NETMIG_MIN = 50
POP_RATIO = 5


def load_country_measures() -> pd.DataFrame:
    if SRC_PARQUET.exists():
        df = pd.read_parquet(SRC_PARQUET)
    elif SRC_CSV.exists():
        df = pd.read_csv(SRC_CSV)
    else:
        raise FileNotFoundError(f"MPIDR OpenAlex country file not found under {SRC_DIR}")

    agg = df[(df["gender"] == "all") & (df["field"] == "all")].copy()
    agg = agg.rename(columns={
        "iso3code": "country",
        "padded_population_of_researchers": "researchers",
    })
    return agg[["country", "year", "netmigration", "number_of_inmigrations",
                "number_of_outmigrations", "researchers"]]


def pre_rows(by_country: dict, country: str) -> list:
    return [x for x in by_country[country] if PRE_MIN <= x["year"] <= PRE_MAX]


def select_countries(by_country: dict) -> set[str]:
    trt_pop = st.mean([x["researchers"] for x in pre_rows(by_country, TREATED)])
    lo, hi = trt_pop / POP_RATIO, trt_pop * POP_RATIO
    keep = {TREATED}
    need = PRE_MAX - PRE_MIN + 1
    for country in by_country:
        if country in EXCLUDE or country == TREATED:
            continue
        p = pre_rows(by_country, country)
        if len(p) < need:
            continue
        mean_pop = st.mean([x["researchers"] for x in p])
        mean_abs_net = st.mean([abs(x["netmigration"]) for x in p])
        if lo <= mean_pop <= hi and mean_abs_net >= NETMIG_MIN:
            keep.add(country)
    return keep


def main() -> None:
    df = load_country_measures()
    by = defaultdict(list)
    for row in df.itertuples(index=False):
        by[row.country].append({
            "country": row.country,
            "year": int(row.year),
            "netmigration": float(row.netmigration),
            "number_of_inmigrations": float(row.number_of_inmigrations),
            "number_of_outmigrations": float(row.number_of_outmigrations),
            "researchers": float(row.researchers),
        })
    for country in by:
        by[country].sort(key=lambda x: x["year"])

    if TREATED not in by:
        raise KeyError(f"treated unit {TREATED} not found in MPIDR OpenAlex country file")

    keep = select_countries(by)
    panel = []
    for country in sorted(keep):
        by_year = {x["year"]: x for x in by[country]}
        for year in range(PANEL_MIN, PANEL_MAX + 1):
            if year not in by_year:
                raise KeyError(f"missing {country}-{year} in source data")
            x = by_year[year]
            panel.append({
                "country": country,
                "year": year,
                "netmigration": int(x["netmigration"]),
                "number_of_inmigrations": int(x["number_of_inmigrations"]),
                "number_of_outmigrations": int(x["number_of_outmigrations"]),
                "researchers": int(x["researchers"]),
            })

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(panel[0].keys()))
        writer.writeheader()
        writer.writerows(panel)

    print(f"wrote {OUT} | units={len(keep)} donors={len(keep) - 1}")
    print(f"treated={TREATED}; T0=2016; pre donor window={PRE_MIN}-{PRE_MAX}")
    print("countries:", ", ".join(sorted(keep)))


if __name__ == "__main__":
    main()
