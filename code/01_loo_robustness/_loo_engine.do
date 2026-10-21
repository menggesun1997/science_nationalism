********************************************************************************
* Shared leave-one-out (LOO) engine for the aggregate SCM analyses.
*
* Defines program loo_unit, which re-estimates a synthetic control for one
* treated unit while dropping each donor country in turn, then assembles the
* distribution of synthetic trajectories (mean +/- 1.96 SD). This is a donor-
* sensitivity robustness check: it shows how much the counterfactual, and thus
* the estimated effect, depends on any single donor.
*
* The placebo/reference optimizer is the default regression-based one (no
* nested/allopt): running nested allopt across every dropped-donor refit for
* all analyses is prohibitively slow and unnecessary for a sensitivity band.
*
* Inputs are passed via globals so the same program serves every analysis:
*   $LOO_OUTCOME  outcome variable (e.g. log_pub_total or intl_ratio)
*   $LOO_TRUNIT   treated country_id
*   $LOO_TNAME    short treated label used in file/var names (e.g. russia)
*   $LOO_TRPERIOD treatment year
*   $LOO_XSTART   first year of the predictor/fitting window
*   $LOO_BEFORE   last pre-treatment year (fitting window end)
*   $LOO_POSTEND  last post-treatment year for effect summaries (0 = no cap)
*   $LOO_ISLOG    1 if the outcome is on the log scale (back-transform for levels)
*   $LOO_OUTDIR   output subfolder (must already contain processed_data.dta)
*   $LOO_PRED     outcome-lag predictor spec for this treated unit
*   $LOO_DONORS   space-separated donor country_id list (full pool)
*   $control_vars covariate predictors (set by the caller)
********************************************************************************

capture program drop loo_unit
program define loo_unit
    local oc     "$LOO_OUTCOME"
    local trunit = $LOO_TRUNIT
    local tname  "$LOO_TNAME"
    local trp    = $LOO_TRPERIOD
    local xs     = $LOO_XSTART
    local before = $LOO_BEFORE
    local islog  = $LOO_ISLOG
    local od     "$LOO_OUTDIR"
    local donors "$LOO_DONORS"

    * ---- one refit per dropped donor -------------------------------------
    * Track which refits succeeded; the treated 'actual' series is invariant to
    * which donor is dropped, so it is stored once from the first success.
    local ok_ids ""
    local have_actual 0
    foreach did of local donors {
        local others ""
        foreach j of local donors {
            if `j' != `did' local others "`others' `j'"
        }
        use "`od'/processed_data.dta", clear
        xtset country_id Year
        capture noisily synth `oc' $control_vars $LOO_PRED , ///
            trunit(`trunit') trperiod(`trp') counit(`others') ///
            xperiod(`xs'(1)`before') keep("`od'/_loo_`tname'_`did'.dta", replace)
        if _rc continue
        use "`od'/_loo_`tname'_`did'.dta", clear
        rename _time Year
        rename _Y_treated actual
        rename _Y_synthetic syn`did'
        drop if missing(Year)
        if !`have_actual' {
            preserve
            keep Year actual
            save "`od'/_loo_`tname'_actual.dta", replace
            restore
            local have_actual 1
        }
        keep Year syn`did'
        save "`od'/_loop_`tname'_`did'.dta", replace
        local ok_ids "`ok_ids' `did'"
    }

    * ---- assemble the leave-one-out distribution -------------------------
    use "`od'/_loo_`tname'_actual.dta", clear
    foreach did of local ok_ids {
        merge 1:1 Year using "`od'/_loop_`tname'_`did'.dta", nogenerate
    }
    * Back-transform to levels when the outcome is logged.
    if `islog' {
        quietly replace actual = exp(actual) - 1
        foreach v of varlist syn* {
            quietly replace `v' = exp(`v') - 1
        }
    }
    egen mean_synth = rowmean(syn*)
    egen sd_synth   = rowsd(syn*)
    gen ci_lower = mean_synth - 1.96 * sd_synth
    gen ci_upper = mean_synth + 1.96 * sd_synth
    sort Year
    save "`od'/loo_`tname'_merged.dta", replace
    export excel Year actual mean_synth sd_synth ci_lower ci_upper ///
        using "`od'/loo_`tname'_band.xlsx", firstrow(variables) replace
    di as text "LOO done for `tname': `: word count `donors'' donor refits"
end
