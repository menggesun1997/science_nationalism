********************************************************************************
* Master runner for the leave-one-out (drop-one-donor) SCM robustness checks.
*
* For each aggregate SCM (Brexit UK; 2014 Crimea and 2022 war for Russia and
* Ukraine; total publications and the international-collaboration ratio) it
* drops each donor country in turn, re-estimates the synthetic control, and
* stores the resulting distribution of counterfactuals (mean +/- 1.96 SD)
* under results/<analysis>/. (EU is no longer treated as a unit.)
*
* Reuses each analysis's processed_data.dta, so run 00_master.do first if the
* panels are stale. Placebo/refit optimizer is the default (no nested allopt):
* one full nested refit per dropped donor across all analyses would take many
* hours and is unnecessary for a donor-sensitivity band.
*
* Usage (from repo root):  stata-mp -b do code/07_loo_robustness/00_master_loo.do
********************************************************************************
capture confirm file "$CODE/config.do"
if _rc {
    local _d "`c(pwd)'"
    forvalues _i = 1/12 {
        capture confirm file "`_d'/code/config.do"
        if !_rc {
            do "`_d'/code/config.do"
            continue, break
        }
        local _d = regexr("`_d'", "/[^/]+$", "")
        if "`_d'" == "" continue, break
    }
}

do "$CODE/07_loo_robustness/loo_brexit_total.do"
do "$CODE/07_loo_robustness/loo_brexit_ratio.do"
do "$CODE/07_loo_robustness/loo_crimea_total.do"
do "$CODE/07_loo_robustness/loo_crimea_ratio.do"
do "$CODE/07_loo_robustness/loo_war_total.do"
do "$CODE/07_loo_robustness/loo_war_ratio.do"

di as text "==============================================================="
di as text "All leave-one-out robustness checks complete."
di as text "Band files: code/07_loo_robustness/results/<analysis>/loo_<unit>_band.xlsx"
di as text "==============================================================="
