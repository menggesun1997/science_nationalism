# Science Nationalism: Geopolitical Shocks and International Research Collaboration

Replication code for a study of how three geopolitical shocks changed
international scientific collaboration and scholar migration.

| Shock | Year | Treated unit |
|---|---|---|
| Brexit referendum | 2016 | United Kingdom |
| Annexation of Crimea | 2014 | Russia, Ukraine |
| Russian invasion of Ukraine | 2022 | Russia, Ukraine |

Two outcomes are estimated throughout: **total publications** and the
**international collaboration ratio** (share of publications with at least one
foreign co-author). A parallel set of analyses examines **scholar migration**
flows.

## Quick start

```bash
git clone <repository-url>
cd "sicence nationism"

# Python environment (conda preferred: geopandas/cartopy need compiled GEOS/GDAL)
conda env create -f environment.yml
conda activate science-nationalism
# or: pip install -r requirements.txt

# Check what can run in your environment before starting anything long
python tools/smoke_test.py
```

`smoke_test.py` reports, per stage, which scripts have all their inputs and
dependencies available. Run it first: it takes seconds and tells you exactly
what is missing.

### Requirements

- **Python** 3.9+ with the packages in `requirements.txt`
- **Stata** 16+ (18 used for the published results), with `synth`, `synth2`,
  `ppmlhdfe`, `reghdfe`, `ftools`, `sdid`, `estout`, `parmest`.
  `code/config.do` installs the SSC-hosted ones automatically; `synth2` and
  `sdid` must be installed manually.
- **Snakemake** (optional) to orchestrate the full pipeline

### Running the pipeline

```bash
snakemake -n                    # dry run: show the plan without executing
snakemake --cores 4 figure1     # build Figure 1 (several hours)
snakemake --cores 4 stage3      # one stage at a time
snakemake --cores 4             # everything
```

If your Stata is not `stata-mp`:

```bash
snakemake --cores 4 --config stata=stata-se
```

Individual scripts also run standalone, from any working directory:

```bash
python "code/2ppml_did_uk_internal_control/1generate_ppml_data.py"
stata-mp -b do code/00_master.do
```

## Repository structure

Directory numbering encodes pipeline order, and script numbering encodes order
within a directory. `1generate_ppml_data.py` runs before `2ppml_analysis.do`.

```
code/
├── paths.py     ← every Python script resolves paths through this
├── config.do    ← every Stata do-file resolves paths through this
│
├── 0raw_publiations_process/     Stage 1  publication records -> country-year panel
├── 1netoworks_did_russia_ukraine/  Stage 2  network indices + DiD (Russia/Ukraine)
├── 1networks_sdid_brexit/          Stage 2  synthetic DiD (Brexit)
├── 2ppml_did_{event}_internal_control/  Stage 3  PPML DiD, internal controls
├── 2two_way_did_{event}/                Stage 4  two-way DiD, external controls
├── 3ppml_migration_did_{event}_internal_control/       Stage 5  migration ITS
├── 3ppml_migration_did_{event}_internal_control_mpidr/ Stage 5  same, MPIDR data
├── 4scm_{event}_{openalex,wos}/  Stage 6  synthetic control on migration
├── crimes/, crimes_2015_2022/    Stage 7  Figure 1 panels (Crimea, war)
├── Brexit-stata_external_try/    Stage 7  Figure 1 panels (Brexit)
├── disciplines_{brexit,crimes,crimes_2014}/  Stage 8  14 disciplines each
├── add_experiments/              Stage 9  supplementary analyses
├── picutres/                     Figure 1 output and .gph panel sources
├── 00_master.do                  entry point: builds Figure 1 end to end
└── visualization/                shared plotting routines

migration_data/   MPIDR Scholarly Migration Database (public, see DATA.md)
paper/            manuscript (separate repository, synced with Overleaf)
tools/            maintenance utilities (smoke test, path rewriter)
Snakefile         pipeline definition
```

`{event}` is one of `eu`, `russia`, `uk`, `ukraine`. Migration analyses cover
`russia`, `uk`, `ukraine` only.

### Where results come from

| Output | Produced by |
|---|---|
| Figure 1 (12 panels) | `code/00_master.do` -> `code/picutres/figure1.pdf` |
| Per-partner collaboration effects | `code/2ppml_did_*/partner_coefficients.csv` |
| Event-study coefficients | `code/2two_way_did_*/event_study_results.csv` |
| Migration event study | `code/3ppml_migration_did_*/results/eventstudy.csv` |
| Discipline heterogeneity | `code/学科avg_effect汇总.xlsx` |
| Manuscript figures | `paper/figure/`, `paper/figure_SI/` |

## Identification strategies

Four complementary designs, each with different assumptions, so that no
conclusion rests on a single specification.

**1. Synthetic control** (`crimes/`, `crimes_2015_2022/`,
`Brexit-stata_external_try/`, `disciplines_*/`) — Constructs a weighted
combination of untreated countries that tracks the treated country's
pre-treatment trajectory, then reads the post-treatment divergence as the
effect. Inference is by in-space placebo: re-run the estimator treating each
donor as if it were treated, and rank the treated unit's post/pre RMSPE ratio
against that distribution. Produces Figure 1.

**2. PPML DiD with internal controls** (`2ppml_did_*_internal_control/`) —
Within a focal country, compares its collaboration with treated partners
against its collaboration with all other partners. Because the outcome is a
publication count with many zero-valued country pairs, estimation uses Poisson
pseudo-maximum-likelihood with high-dimensional fixed effects (`ppmlhdfe`),
which handles zeros without dropping observations and is consistent under
arbitrary heteroskedasticity. Absorbs focal-country, partner-country and year
effects.

**3. Two-way DiD with external controls** (`2two_way_did_*/`) — Compares the
focal country against structurally similar countries rather than against its
own other partners. Control groups are selected by pre-trend matching or
synthetic control; `2two_way_did_ukraine/README_SCM_*.md` documents that
selection and its iterations.

**4. Migration analyses** (`3ppml_migration_did_*/`, `4scm_*/`) — Net inflow
takes negative values, so PPML does not apply; these use interrupted time
series at the focal-country level, plus synthetic control on the MPIDR
migration data. `_wos` and `_openalex` variants run the same design on
different source databases as a robustness check.

### Reading synthetic-control output

`code/crimes/变量名的含义.txt` is the authoritative variable dictionary. In
brief, for a treated unit `X`:

| Variable | Meaning |
|---|---|
| `X_gap` | actual minus synthetic, on the estimation scale |
| `X_actual_real`, `X_synthetic_real` | exponentiated back to counts |
| `X_gap_pct` | gap as a percentage of baseline output (the plotted series) |
| `X_avg_effect` | mean of `X_gap_pct` over post-treatment years |
| `pre_rmspe_X` | pre-treatment fit quality (used to screen donors) |
| `rmspe_ratio_X` | post/pre RMSPE; its rank gives the placebo p-value |

Screening uses `pre_rmspe_X` and `X_avg_effect`; plots use `X_gap_pct`.

## Conventions and quirks

**Paths.** No script contains an absolute path. Python scripts import
`code/paths.py`, which anchors everything to its own location; do-files include
`code/config.do`, which sets `$ROOT`, `$CODE`, `$PAPER`. Both resolve the
repository root by walking up for a marker file, or from
`$SCIENCE_NATIONALISM_ROOT` if set. If Stata is launched from an unusual
directory:

```stata
global ROOT "/path/to/sicence nationism"
do "$ROOT/code/config.do"
```

**Colour palette.** `config.do` defines the Okabe-Ito colour-blind-safe palette
(`$C_EU`, `$C_UK`, `$C_RU`, `$C_UA`, `$C_SHADE`, `$C_LINE`) shared by every
plot. `code/plotting_spec_stata.md` documents the full figure specification,
including Nature submission dimensions.

**Misspelled directory names are load-bearing.** `picutres` (not `pictures`),
`1netoworks_did_...` (not `networks`), `countrol_countries_articles` (not
`control`), and `intil_ratio` / `initil_ratio` — which differ between the
`disciplines_brexit` and `disciplines_crimes` trees — are all referenced
literally by scripts. Renaming any of them silently breaks the pipeline. They
were left as-is deliberately.

**`crimes` means Crimea**, not criminal activity. `crimes/` analyses the 2014
annexation; `crimes_2015_2022/` analyses the 2022 invasion with the
pre-treatment fit window restricted to 2015 onward.

**`Brexit-stata_external_try` is production code**, despite the "try" suffix.
`00_master.do` calls it to build Figure 1 panels a–d.

**`experiment_3` does not exist.** The numbering gap in `add_experiments/` is
intentional; that analysis was dropped during revision.

**Not included in this repository:** superseded analyses (`code/crimes_2022/`,
replaced by `crimes_2015_2022/`), regenerable intermediates (`*.dta`, `*.gph`,
figures under `code/`), and licensed data. See DATA.md.

## What can be reproduced without the licensed data

The article-level Web of Science records cannot be redistributed, so Stage 1
cannot run from a public checkout. Everything downstream reads the aggregated
country-year files, which **are** included.

Current status from `tools/smoke_test.py` on a full local checkout:

| Stage | Runnable | Notes |
|---|---|---|
| 1  raw processing | 30/32 | needs licensed inputs |
| 2  network DiD | 7/14 | needs licensed inputs |
| 3  PPML internal control | 27/36 | |
| 4  two-way DiD | 25/35 | |
| 5  migration ITS | 15/15 | fully reproducible |
| 6  SCM migration | 30/30 | fully reproducible (public MPIDR data) |
| 7  Figure 1 | 48/93 | |
| 8  disciplines | 28/56 | |
| 9  experiments | 2/13 | needs article-level records |

Scripts reported as blocked are missing input files, not broken. Stages 5 and 6
run end to end from public data alone.

## Troubleshooting

**`config.do could not locate the repository root`** — Stata was launched from
outside the repository. Set the environment variable before launching, or set
`global ROOT` as shown above.

```bash
export SCIENCE_NATIONALISM_ROOT="/path/to/sicence nationism"
```

**`command synth is unrecognized`** — install the community packages:

```stata
ssc install synth
ssc install ppmlhdfe
ssc install reghdfe
ssc install ftools
```

`synth2` and `sdid` are not on SSC and must be installed from their
repositories.

**`FileNotFoundError` mentioning a 0-byte file** — a cloud-storage placeholder
that was never downloaded locally, most often a licensed input. `paths.require()`
raises specifically on this case rather than letting a script fail confusingly
later.

**geopandas or cartopy fails to install via pip** — use the conda environment.
These need compiled GEOS, PROJ and GDAL libraries.

**A geopandas script tries to reach the internet** — some map scripts download
the Natural Earth shapefile at runtime and will fail offline. Fetch
`ne_110m_admin_0_countries.zip` from naturalearthdata.com in advance.

**Snakemake crashes with `module 'pulp' has no attribute 'list_solvers'`** — a
version conflict unrelated to this repository. `pip install "pulp<2.8"`.

## Maintenance tools

```bash
python tools/smoke_test.py             # per-stage runnability report
python tools/smoke_test.py --verbose   # list every blocked script and why
python tools/smoke_test.py --json out.json

python tools/rewrite_paths.py --check --all   # detect new hard-coded paths
```

Run the smoke test after any structural change. It is what surfaced the ten
distinct historical root directories left over from earlier versions of this
project.

## Data

Publication data is licensed from Clarivate and cannot be redistributed.
Migration data is public. See [DATA.md](DATA.md) for what is included, what is
not, and how to obtain the rest.

## Citation

If you use this code, please cite the paper. Details will be added on
publication.

## License

Code is released under the MIT License (see [LICENSE](LICENSE)). This covers
the analysis code only, not the third-party datasets it consumes, which carry
their own terms — see [DATA.md](DATA.md).
