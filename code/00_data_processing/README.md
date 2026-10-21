# 00_data_processing

Builds the country-year and country-pair panels used by every later
module. Starts from licensed Web of Science / OST article records
(not redistributed; see DATA.md).

Core scripts, in order, live in `raw data processing/`:

1. `0process.py` — country-name normalisation
2. `2calculate_eu_data.py` — EU aggregate
3. `3calculate_country_discipline_stats.py` / `3networks_all.py`
4. `4calculate_eu_indicators.py` — World Bank covariates
5. `4generate_discipline_excel_files.py` / `5generate_brexit_discipline_excel_files.py`

Downstream modules read the resulting `.xlsx` / `.csv` aggregates, which
**are** shipped with the repository.
