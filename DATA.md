# Data

This repository ships the code and the aggregated data needed to reproduce
most results in the current manuscript. Two categories of input are
excluded: data we are not licensed to redistribute, and public datasets
too large for git.

## What is included

| Data | Location | Size |
|---|---|---|
| Country-year collaboration aggregates | `code/*/original_completed.xlsx`, `code/*/*.csv` | small |
| Control-group panels | `code/03_twoway_did_*/control_group_cooperation_data.xlsx` | small |
| PPML estimation panels | `code/02_ppml_partners_*/ppml_data.csv` | small |
| Estimated coefficients | `code/*/partner_coefficients.csv`, `event_study_results.csv` | small |

These are country-year or country-pair-year aggregates. Modules `01_`
through `05_` read from them, so most of the analysis reproduces without
additional downloads.

## What is excluded, and why

### 1. Web of Science article records — licensed, cannot be redistributed

The pipeline originates from article-level bibliographic records delivered
by Clarivate through the French Observatoire des Sciences et Techniques
(OST). The format is a three-column export:

```
OST_BK,Annee_Bibliographique,countries
25329403,2005,"CHINA,GERMANY,UKRAINE"
25329801,2005,UKRAINE
```

Files: `*_articles.txt` and the contents of
`code/00_data_processing/{publications_raw_data,brexit_experimental_data,raw_data_2026}/`.

**Obtaining them.** Requires a Web of Science subscription with data-access
rights, or a data request to the OST. Contact the corresponding author for
the exact extraction specification (fields, filters, year range).

Once you have them, point the code at your copy without editing any script:

```bash
export SCIENCE_NATIONALISM_RAW=/path/to/your/raw_data_store
```

The directory should contain `publications_raw_data/`,
`brexit_experimental_data/`, `indicator_raw data/`,
`indicator_clean_data/` and `raw_data_2026/`.

> In the original working copy these directories were symlinks into a
> folder outside the repository, and several files were unsynced cloud
> placeholders of 0 bytes. `paths.require()` detects 0-byte inputs and
> reports them explicitly.

### 2. World Bank indicators — public

GDP per capita, R&D expenditure as a share of GDP, and researchers per
million inhabitants, used as synthetic-control predictors. Downloadable
from <https://data.worldbank.org/>. Expected under `indicator_raw data/`
within the raw-data store.

### 3. Natural Earth boundaries — public domain

Country outlines for the choropleth maps. Some scripts download
`ne_110m_admin_0_countries.zip` from <https://www.naturalearthdata.com/>
at runtime; fetch it in advance if you will be offline.

### 4. Regenerable intermediates — excluded to keep the repository navigable

Stata `.dta` files, `.gph` graph sources, and intermediate figures under
`code/`. All are reproduced by rerunning the pipeline. Final manuscript
figures live in `paper/` (a separate repository).

## Licensing summary

| Data | Redistributable | Terms |
|---|---|---|
| Article-level WoS records | No | Clarivate licence |
| Country-year aggregates derived from them | Included here | aggregates; confirm with Clarivate before wider redistribution |
| World Bank indicators | Yes | CC BY 4.0 |
| Natural Earth | Yes | public domain |
| Analysis code | Yes | MIT (see LICENSE) |

The aggregated files in this repository are country-year and
country-pair-year counts, several aggregation steps removed from the
licensed article records. If you intend to redistribute them further,
verify the terms of your own Clarivate agreement.

## Verifying your setup

```bash
python tools/smoke_test.py
```

Reports which scripts have all inputs present, and distinguishes missing
files from 0-byte placeholders. Downstream modules run from the shipped
aggregates; `00_data_processing/` stays blocked until the licensed inputs
are in place.
