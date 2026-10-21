# Code map (paper → folders)

Each numbered folder is one research block in
*The Scientific Cost of Geopolitical Conflict*. Script numbers encode
run order inside a folder (`1generate_*.py` before `2ppml_analysis.do`).

| Folder | Paper location | What it estimates |
|---|---|---|
| [`00_data_processing/`](00_data_processing/) | Data & Methods | WoS records → country-year / dyad panels |
| [`01_scm_brexit/`](01_scm_brexit/) | Fig. 1a,b; SI B | SCM: UK publications and collaboration ratio, 2016 |
| [`01_scm_crimea_2014/`](01_scm_crimea_2014/) | Fig. 1c,d; SI C | SCM: Russia & Ukraine, 2014 Crimean crisis |
| [`01_scm_war_2022/`](01_scm_war_2022/) | Fig. 1e,f; SI D | Nested SCM: additional 2022 break on the post-2014 baseline |
| [`02_ppml_partners_uk/`](02_ppml_partners_uk/) | Fig. `uk_cooperation_changes_*` | Partner-level PPML DiD (internal controls), UK |
| [`02_ppml_partners_russia/`](02_ppml_partners_russia/) | Fig. `russia_cooperation_changes_*` | Same design, Russia |
| [`02_ppml_partners_ukraine/`](02_ppml_partners_ukraine/) | Fig. `ukraine_cooperation_changes_*` | Same design, Ukraine |
| [`02_ppml_partners_eu/`](02_ppml_partners_eu/) | SI G.4 (EU-27) | Same design, EU aggregate |
| [`03_twoway_did_uk/`](03_twoway_did_uk/) | SI G.3 | External-control PPML DiD, UK |
| [`03_twoway_did_russia/`](03_twoway_did_russia/) | SI G.2 | External-control PPML DiD, Russia |
| [`03_twoway_did_ukraine/`](03_twoway_did_ukraine/) | SI G | External-control PPML DiD, Ukraine |
| [`03_twoway_did_eu/`](03_twoway_did_eu/) | SI G.4 | External-control PPML DiD, EU-27 |
| [`04_west_east_tilt/`](04_west_east_tilt/) | Methods “Geopolitical Tilt”; SI H | NATO–SCO tilt index, Russia & Ukraine |
| [`05_scm_disciplines_brexit/`](05_scm_disciplines_brexit/) | SI E | Discipline-level SCM, Brexit |
| [`05_scm_disciplines_crimea_2014/`](05_scm_disciplines_crimea_2014/) | SI F.1 | Discipline-level SCM, 2014 |
| [`05_scm_disciplines_war_2022/`](05_scm_disciplines_war_2022/) | SI F.2 | Discipline-level SCM, 2022 |
| [`06_bridging/`](06_bridging/) | SI I | Bridging-intensity matrices, pre vs post |
| [`figures/`](figures/) | Fig. 1 assembly | Combined Figure 1 output |
| [`visualization/`](visualization/) | SI in-space placebos | Shared plotting helpers |
| [`99_utilities/`](99_utilities/) | — | Standalone helpers: country-name standardisation, placebo refresh, in-time placebo (RU/UA), SI weight tables |

`00_master.do` builds Figure 1 from the three `01_scm_*` folders.

Analyses that are **not** in the current manuscript (scholar migration,
network betweenness, PCA, the superseded 2022 SCM copy) live in
`_archive/` at the repository root and are gitignored from the public
release.
