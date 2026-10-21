# The Scientific Cost of Geopolitical Conflict

Replication code for the analyses in the manuscript. Three geopolitical
shocks are compared:

| Shock | Year | Treated unit |
|---|---|---|
| Brexit referendum | 2016 | United Kingdom |
| Annexation of Crimea | 2014 | Russia, Ukraine |
| Full-scale invasion of Ukraine | 2022 | Russia, Ukraine (nested on the post-2014 baseline) |

Two outcomes run through the aggregate analyses: **total publications** and
the **international collaboration ratio** (share of publications with at
least one foreign co-author). Partner-level models then estimate how
bilateral collaboration is reallocated after each shock.

Folder names under `code/` match research blocks in the paper. See
[`code/README.md`](code/README.md) for the figure-by-figure map.

## Quick start

```bash
git clone <repository-url>
cd "sicence nationism"

conda env create -f environment.yml
conda activate science-nationalism
# or: pip install -r requirements.txt

python tools/smoke_test.py
```

`smoke_test.py` reports, per module, which scripts have their inputs and
dependencies. Run it first: it takes seconds and lists exactly what is
missing.

### Requirements

- **Python** 3.9+ (`requirements.txt`)
- **Stata** 16+ (18 used for the published results), with `synth`,
  `synth2`, `ppmlhdfe`, `reghdfe`, `ftools`, `sdid`, `estout`, `parmest`.
  `code/config.do` installs the SSC-hosted packages; `synth2` and `sdid`
  must be installed manually.
- **Snakemake** (optional) to orchestrate the pipeline

```bash
snakemake -n                    # dry run
snakemake --cores 4 figure1     # Figure 1 (several hours)
snakemake --cores 4             # everything in the current paper
```

If your Stata is not `stata-mp`:

```bash
snakemake --cores 4 --config stata=stata-se
```

Standalone:

```bash
python code/02_ppml_partners_uk/1generate_ppml_data.py
stata-mp -b do code/00_master.do
```

## Repository structure

```
code/
├── README.md                 paper section → folder
├── paths.py                  Python path hub
├── config.do                 Stata path hub + colour palette
├── 00_master.do              Figure 1 end to end
│
├── 00_data_processing/       WoS records → country-year panels
├── 01_scm_brexit/            Fig. 1a,b  + SI B
├── 01_scm_crimea_2014/       Fig. 1c,d  + SI C
├── 01_scm_war_2022/          Fig. 1e,f  + SI D
├── 02_ppml_partners_{uk,russia,ukraine,eu}/   partner PPML DiD (main maps)
├── 03_twoway_did_{uk,russia,ukraine,eu}/      external-control DiD (SI G)
├── 04_west_east_tilt/        NATO–SCO tilt index (SI H)
├── 05_scm_disciplines_*/     field-level SCM (SI E, F)
├── 06_bridging/              bridging matrices (SI I)
├── figures/                  combined Figure 1
└── visualization/            shared plotting
```

### Where results come from

| Output | Produced by |
|---|---|
| Figure 1 | `code/00_master.do` → `code/figures/figure1.pdf` |
| Partner maps (UK / Russia / Ukraine) | `code/02_ppml_partners_*/4visualize_partner_changes_geopandas.py` |
| West–East tilt DiD | `code/04_west_east_tilt/` |
| Discipline bars (SI E, F) | `code/extract_avg_effects.py`, `code/visualize_effects.py` |
| Manuscript figures | `paper/figure/`, `paper/figure_SI/` |

## Identification strategies

**Synthetic control** (`01_scm_*`, `05_scm_disciplines_*`) — weighted
combination of untreated donors that tracks the treated country's
pre-treatment trajectory. Inference is by in-space placebo (MSPE ratios)
and in-time placebo (backdated intervention years).

**PPML DiD with internal controls** (`02_ppml_partners_*`) — within a
focal country, compares collaboration with partner *k* against the rest
of that country's partner portfolio. Poisson PML with high-dimensional
fixed effects (`ppmlhdfe`). This is the specification behind the main-text
maps.

**Two-way DiD with external controls** (`03_twoway_did_*`) — compares the
focal country against structurally similar countries selected by
pre-trend matching (SI G).

**West–East tilt** (`04_west_east_tilt/`) — NATO minus SCO collaboration
shares; linear two-way fixed-effects DiD (SI H).

### Reading synthetic-control output

`code/01_scm_crimea_2014/变量名的含义.txt` is the variable dictionary. For
a treated unit `X`:

| Variable | Meaning |
|---|---|
| `X_gap` | actual minus synthetic, on the estimation scale |
| `X_actual_real`, `X_synthetic_real` | exponentiated back to counts |
| `X_gap_pct` | gap as a percentage of the counterfactual (the plotted series) |
| `X_avg_effect` | mean of `X_gap_pct` over post-treatment years |
| `pre_rmspe_X` | pre-treatment fit (used to screen donors) |
| `rmspe_ratio_X` | post/pre RMSPE; its rank gives the placebo *p*-value |

## Paths and conventions

Python scripts import `code/paths.py`. Do-files include `code/config.do`,
which sets `$ROOT`, `$CODE`, `$PAPER`. Both walk up for a marker file, or
read `$SCIENCE_NATIONALISM_ROOT`. From an unusual Stata working directory:

```stata
global ROOT "/path/to/sicence nationism"
do "$ROOT/code/config.do"
```

`config.do` also defines the Okabe–Ito palette (`$C_EU`, `$C_UK`, `$C_RU`,
`$C_UA`, `$C_SHADE`, `$C_LINE`). See `code/plotting_spec_stata.md`.

Some inner directory names remain misspelled because do-files reference
them literally: `countrol_countries_articles`, and `intil_ratio` vs
`initil_ratio` under the discipline trees. Renaming those inner folders
breaks the pipeline.

The 2022 SCM uses 2015–2021 as the pre-treatment window so that estimates
are *marginal* to the post-Crimea trajectory, not total effects relative
to a pre-2014 peace-time path.

## What can be reproduced without licensed data

Article-level Web of Science records cannot be redistributed, so
`00_data_processing/` cannot run from a public checkout. Downstream
scripts read aggregated country-year files, which **are** included. See
[DATA.md](DATA.md).

## Troubleshooting

**`config.do could not locate the repository root`**

```bash
export SCIENCE_NATIONALISM_ROOT="/path/to/sicence nationism"
```

**`command synth is unrecognized`**

```stata
ssc install synth
ssc install ppmlhdfe
ssc install reghdfe
ssc install ftools
```

`synth2` and `sdid` are not on SSC and must be installed from their
repositories.

**`FileNotFoundError` mentioning a 0-byte file** — unsynced cloud
placeholder, usually a licensed input. `paths.require()` reports this
explicitly.

**geopandas / cartopy fail via pip** — use the conda environment.

**Map scripts try to reach the internet** — fetch
`ne_110m_admin_0_countries.zip` from naturalearthdata.com first.

**Snakemake `pulp` error** — `pip install "pulp<2.8"`.

## Data and license

Publication data is licensed from Clarivate and cannot be redistributed.
See [DATA.md](DATA.md). Code is MIT (see [LICENSE](LICENSE)).

If you use this code, please cite the paper (details on publication).
