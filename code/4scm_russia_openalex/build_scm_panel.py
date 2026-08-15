# Build scm_panel.csv for Russia SCM from MPIDR Scholarly Migration Database
# (OpenAlex 2026 V2, country-year aggregates).
#
# Source: openalex_2026_V2_scholarlymigration_country.{parquet,csv}
#   gender == "all", field == "all"
#
# Donor-pool rules (match scm_russia.do):
#   pre (2005-2021) mean researchers in [1/5, 5x] of RUS;
#   mean |netmigration| >= 50; exclude UKR/BLR; keep RUS as treated unit.
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

PRE_MIN, PRE_MAX = 2005, 2021
PANEL_MIN, PANEL_MAX = 2005, 2024
EXCLUDE = {"UKR", "BLR"}
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
    rus_pop = st.mean([x["researchers"] for x in pre_rows(by_country, "RUS")])
    lo, hi = rus_pop / POP_RATIO, rus_pop * POP_RATIO
    keep = {"RUS"}
    for country in by_country:
        if country in EXCLUDE or country == "RUS":
            continue
        p = pre_rows(by_country, country)
        if len(p) < PRE_MAX - PRE_MIN + 1:
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

    keep = select_countries(by)
    panel = []
    for country in sorted(keep):
        by_year = {x["year"]: x for x in by[country]}
        for year in range(PANEL_MIN, PANEL_MAX + 1):
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
    print("countries:", ", ".join(sorted(keep)))


if __name__ == "__main__":
    main()
