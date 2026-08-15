# -*- coding: utf-8 -*-
# Build clean COUNTRY-LEVEL scholarly migration data for 2026_V2
# (by gender & field). OFFLINE ONLY -- no World Bank API calls.
#
# Keeps the core migration signal:
#   - country file: population of researchers, in/out/net migration counts & rates
#   - flow file: bilateral n_migrations + country names + normalized flows
#
# World Bank auxiliary columns (region / income / GDP / population) are
# intentionally NOT added, per user request.
#
# Output: data_processed/2026_V2/*.{parquet,csv}

import os
import duckdb

path_input = "./data_input/2026_V2/"
path_processed = "./data_processed/2026_V2/"

os.makedirs(path_processed, exist_ok=True)

YEAR_MIN = 1998
YEAR_MAX = 2024


def build_country(con, provider):
    """Clean country-level file with per (iso3, gender, field) avg pop."""
    fn_in = f"{path_input}{provider}_scholarlymigration_country_gender_and_field.parquet"
    fn_out_pq = f"{path_processed}{provider}_2026_V2_scholarlymigration_country.parquet"
    fn_out_csv = fn_out_pq[:-8] + ".csv"

    query = f"""
    SELECT
        year, area, iso2code, iso3code, countryname, gender, field,
        padded_population_of_researchers,
        number_of_inmigrations, number_of_outmigrations, netmigration,
        outmigrationrate, inmigrationrate, netmigrationrate,
        avg(padded_population_of_researchers)
            OVER (PARTITION BY iso3code, gender, field) AS avg_paddedpop
    FROM '{fn_in}'
    WHERE year >= {YEAR_MIN} AND year <= {YEAR_MAX}
    ORDER BY iso3code, gender, field, year
    """
    df = con.execute(query).df()
    con.execute(f"COPY ({query}) TO '{fn_out_pq}';")
    con.execute(f"COPY ({query}) TO '{fn_out_csv}' (HEADER, DELIMITER ',');")
    print(f"[{provider}] country -> {len(df)} rows, {df.shape[1]} cols")
    return fn_out_pq


def build_flows(con, provider, country_pq):
    """Bilateral flows enriched with from/to names + normalized flows.

    Flows are matched to the (gender, field) slice of the country table so
    that population / migration counts refer to the same subgroup.
    """
    fn_in = f"{path_input}{provider}_scholarlymigration_country_flows_gender_and_field.parquet"
    fn_out_pq = f"{path_processed}{provider}_2026_V2_scholarlymigration_countryflows.parquet"
    fn_out_csv = fn_out_pq[:-8] + ".csv"

    query = f"""
    SELECT
        f.n_migrations,
        f.year, f.gender, f.field,
        f.area_from AS iso3codefrom, f.area_to AS iso3codeto,
        cf.countryname AS countrynamefrom, ct.countryname AS countrynameto,
        cf.padded_population_of_researchers AS paddedpopfrom,
        ct.padded_population_of_researchers AS paddedpopto,
        cf.number_of_outmigrations AS number_of_outmigrationsfrom,
        ct.number_of_inmigrations AS number_of_inmigrationsto,
        100000000.0 * f.n_migrations
            / NULLIF(ct.number_of_inmigrations * cf.number_of_outmigrations, 0)
            AS normalized_migration1,
        100000000000.0 * f.n_migrations
            / NULLIF(cf.padded_population_of_researchers * ct.padded_population_of_researchers, 0)
            AS normalized_migration2
    FROM '{fn_in}' AS f
    LEFT JOIN '{country_pq}' AS cf
        ON cf.iso3code = f.area_from AND cf.year = f.year
        AND cf.gender = f.gender AND cf.field = f.field
    LEFT JOIN '{country_pq}' AS ct
        ON ct.iso3code = f.area_to AND ct.year = f.year
        AND ct.gender = f.gender AND ct.field = f.field
    WHERE f.year >= {YEAR_MIN} AND f.year <= {YEAR_MAX}
    ORDER BY f.year, f.area_from, f.area_to, f.gender, f.field
    """
    df = con.execute(query).df()
    con.execute(f"COPY ({query}) TO '{fn_out_pq}';")
    con.execute(f"COPY ({query}) TO '{fn_out_csv}' (HEADER, DELIMITER ',');")
    print(f"[{provider}] flows   -> {len(df)} rows, {df.shape[1]} cols")
    return fn_out_pq


def main():
    con = duckdb.connect(":memory:")
    for provider in ["scopus", "openalex"]:
        country_pq = build_country(con, provider)
        build_flows(con, provider, country_pq)
    print("Done. Output in", path_processed)


if __name__ == "__main__":
    main()
