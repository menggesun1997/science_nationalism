# Migration-flow gravity PPML & isomorphism with collaboration reshuffling

Answers: *"where does talent go"* vs *"where does collaboration grow"* — are the
two realignments **isomorphic**?

## Data
- `migration_data/openalex_pipeline/results/openalex_bilateral_flows_1998_2025.csv`
  — `year, from_country, to_country, n_migrations` (OpenAlex residence-change events, ISO2).
- `openalex_country_year_1998_2025.csv` — per-country active-researcher stock
  (used as the partner scientific-size control).

## Model (mirrors the collaboration PPML in `code/02_ppml_partners_*`)
```
E[Flow_jt] = exp( alpha_j + lambda_t + delta_k * (1{j=k} x Post_t)
                  + gamma * ln(PartnerSize_jt) )
```
- partner FE `alpha_j`, year FE `lambda_t` (absorbed), partner-clustered SE.
- `delta_k` = partner-specific post-shock deviation, the SAME object as in the
  collaboration analysis, so the two are directly comparable.
- Poisson w/ high-dim FE via `pyfixest.fepois` == Stata `ppmlhdfe`.
- Focal/Post: UK 2017 (Brexit 2016), Russia & Ukraine 2022 (full-scale invasion).
- Direction `out` = focal is origin (where talent leaves TO); `in` = destinations of arrivals.

## Scripts
1. `1estimate_migration_ppml.py` → `migration_coef_{label}_{out,in}.csv`
2. `2isomorphism.py` → partner-level Pearson/Spearman/sign-agreement + `isomorphism_scatter.pdf`
3. `3bloc_isomorphism.py` → West(NATO) vs East(SCO) tilt for both networks

## Findings (out-direction vs collaboration)
Partner-level correlations are **weak** (RU r=0.08, UA r=0.03, GB r=-0.18):
talent flows and collaboration do **not** realign partner-for-partner. Bloc-level
tilt is also **not** cleanly isomorphic (only Ukraine shares sign, both toward West).

Interpretation: collaboration reconfiguration and talent migration are **distinct
mechanisms**, not two views of one process. Collaboration can pivot (e.g. Russia→Iran/China)
without a matching bulk movement of people, and displaced talent (Ukraine) follows
host-capacity/visa geography rather than the pre-existing collaboration map. This is
a genuine, publishable *dissociation* result, not a null artifact.
