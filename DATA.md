# Data

This repository ships the code and the aggregated data needed to reproduce most
results. Two categories of input are excluded: data we are not licensed to
redistribute, and public datasets too large for git.

## What is included

| Data | Location | Size |
|---|---|---|
| Country-year collaboration aggregates | `code/*/original_completed.xlsx`, `code/*/*.csv` | small |
| Control-group panels | `code/2two_way_did_*/control_group_cooperation_data.xlsx` | small |
| PPML estimation panels | `code/2ppml_did_*/ppml_data.csv` | small |
| SCM donor panels | `code/4scm_*/scm_panel.csv` | small |
| MPIDR country-level migration | `migration_data/**/2026_V2/*_country.parquet` | 3.5 MB |
| Estimated coefficients | `code/*/partner_coefficients.csv`, `event_study_results.csv` | small |

These are country-year or country-pair-year aggregates. Stages 3 through 9 read
from them, so most of the analysis reproduces without any additional downloads.

## What is excluded, and why

### 1. Web of Science article records — licensed, cannot be redistributed

The pipeline originates from article-level bibliographic records delivered by
Clarivate through the French Observatoire des Sciences et Techniques (OST). The
format is a three-column export:

```
OST_BK,Annee_Bibliographique,countries
25329403,2005,"CHINA,GERMANY,UKRAINE"
25329801,2005,UKRAINE
```

Files: `*_articles.txt` (Russia 29 MB, Brazil 26 MB, South Africa 11 MB,
Ukraine 4.2 MB, plus nine other control countries), and the contents of
`code/0raw_publiations_process/{publications_raw_data,brexit_experimental_data,raw_data_2026}/`.

**Obtaining them.** Requires a Web of Science subscription with data-access
rights, or a data request to the OST. Contact the corresponding author for the
exact extraction specification (fields, filters, year range) so an equivalent
extract can be built from your own licensed copy.

Once you have them, point the code at your copy without editing any script:

```bash
export SCIENCE_NATIONALISM_RAW=/path/to/your/raw_data_store
```

The directory should contain `publications_raw_data/`,
`brexit_experimental_data/`, `indicator_raw data/`, `indicator_clean_data/` and
`raw_data_2026/`.

A separate predecessor dataset, used only by `1networks_sdid_brexit/`, is
located via:

```bash
export SCIENCE_NATIONALISM_LEGACY_BREXIT=/path/to/cooperation_related
```

> In the original working copy these directories were symlinks into a folder
> outside the repository, and several files were unsynced cloud placeholders of
> 0 bytes. `paths.require()` detects 0-byte inputs and reports them explicitly
> rather than letting a script fail with a confusing parse error.

### 2. MPIDR Scholarly Migration Database — public, too large for git

Subnational and gender/field-disaggregated files exceed GitHub's 100 MB
per-file limit (largest: 334 MB).

**Obtaining them.** Public download from the Max Planck Institute for
Demographic Research:

- Dataset: Scholarly Migration Database
- Publication: Akbaritabar, Theile & Zagheni, *Global flows and rates of
  international migration of scholars*
- Portal: <https://www.scholarlymigration.org/>

Place the download at:

```
migration_data/Global-flows-and-rates-of-international-migration-of-scholars-2026_V2/
├── 2026_V2/           ← country-level files (small ones are committed here)
└── data_input/        ← subnational and disaggregated files (excluded)
```

The **country-level** parquet files needed by `code/4scm_*/build_scm_panel.py`
are committed, so Stage 6 runs without this download. Only the subnational
analyses require it.

### 3. World Bank indicators — public

GDP per capita, R&D expenditure as a share of GDP, and researchers per million
inhabitants, used as synthetic-control predictors. Downloadable from
<https://data.worldbank.org/>. Expected under `indicator_raw data/` within the
raw-data store.

### 4. Natural Earth boundaries — public domain

Country outlines for the choropleth maps. Some scripts download
`ne_110m_admin_0_countries.zip` from <https://www.naturalearthdata.com/> at
runtime, which fails on machines without internet access; fetch it in advance if
needed.

### 5. Regenerable intermediates — excluded to keep the repository navigable

2,229 Stata `.dta` files, `.gph` graph sources, and intermediate figures under
`code/`. All are reproduced by rerunning the pipeline. Final manuscript figures
live in `paper/` (a separate repository).

## Licensing summary

| Data | Redistributable | Terms |
|---|---|---|
| Article-level WoS records | No | Clarivate licence |
| Country-year aggregates derived from them | Included here | aggregates; confirm with Clarivate before wider redistribution |
| MPIDR migration data | Yes | public, cite the source publication |
| World Bank indicators | Yes | CC BY 4.0 |
| Natural Earth | Yes | public domain |
| Analysis code | Yes | MIT (see LICENSE) |

The aggregated files in this repository are country-year and
country-pair-year counts, several aggregation steps removed from the licensed
article records. This is the usual basis on which bibliometric aggregates are
published, but if you intend to redistribute them further, verify the terms of
your own Clarivate agreement.

## Verifying your setup

```bash
python tools/smoke_test.py
```

Reports which scripts have all inputs present, and distinguishes missing files
from 0-byte placeholders. Stages 5 and 6 should show as fully runnable from a
clean public checkout; earlier stages will show as blocked until the licensed
inputs are in place.
