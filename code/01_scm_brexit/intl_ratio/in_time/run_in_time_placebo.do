*===============================================================*
* run_in_time_placebo.do — UK in-time (in-place-of-time) placebo SCM
*
* For each pseudo-treatment year t in {2013, 2014, 2015, 2016} we refit the
* UK synthetic control using ONLY pre-t information:
*   - fitting window  xperiod = 2008 .. (t-1)
*   - the lagged-outcome predictor is taken at (t-1)
*   - covariate pre-means are averaged over 2008 .. (t-1)
* This is the standard in-time placebo: if the model is valid, pseudo dates
* before the true 2016 referendum should not produce large post-t gaps.
*
* Only the UK is treated (EU is dropped from the exercise). Donor pool excludes
* EU and the UK. Outputs go to <outcome>/in_time/uk_intime_<t>.dta with a tidy
* Year / actual / synthetic / gap layout for the plotting script.
*
* Run standalone:  stata-mp -e do code/01_scm_brexit/run_in_time_placebo.do
*===============================================================*
clear all
set more off

global ROOT "c:/Users/91916/Dropbox/GitHub/sicence nationism"
do "$ROOT/code/config.do"

local brexit "$CODE/01_scm_brexit"

*---------------------------------------------------------------*
* Program: one pseudo-year fit for a given outcome
*---------------------------------------------------------------*
capture program drop fit_intime
program define fit_intime
    syntax, OUTdir(string) OUTCOME(string) Treatyear(integer)

    local before = `treatyear' - 1
    * cd into the in_time folder so synth's keep() gets a bare filename;
    * synth mishandles absolute paths that contain spaces (the repo path does).
    cd "`outdir'/in_time"
    use "`outdir'/processed_data.dta", clear

    * UK id and donor pool (exclude EU + UK)
    quietly summarize country_id if Country == "UNITED_KINGDOM"
    local uk_id = r(mean)
    levelsof country_id if !inlist(Country, "EU", "UNITED_KINGDOM"), ///
        local(control_ids) clean

    if "`outcome'" == "total" {
        * Pre-mean covariate averaged over 2005..(before), lagged outcome at before.
        capture drop log_pub_pre_intime log_pub_pre_intime_final
        bysort country_id: egen log_pub_pre_intime = ///
            mean(log_pub_total) if Year >= 2005 & Year <= `before'
        bysort country_id: egen log_pub_pre_intime_final = ///
            max(log_pub_pre_intime)
        capture noisily synth log_pub_total ///
            log_pub_pre_intime_final log_pub_total(`before'), ///
            trunit(`uk_id') trperiod(`treatyear') ///
            counit(`control_ids') ///
            xperiod(2008(1)`before') ///
            nested allopt ///
            keep("_raw_`treatyear'.dta", replace)
    }
    else {
        * ratio: pre-mean plus up to four pre-t lags of intl_ratio.
        capture drop intl_ratio_mean_it intl_ratio_mean_it_final
        bysort country_id: egen intl_ratio_mean_it = ///
            mean(intl_ratio) if Year >= 2005 & Year <= `before'
        bysort country_id: egen intl_ratio_mean_it_final = ///
            max(intl_ratio_mean_it)
        * Build lag list: the four most recent years strictly before t.
        local lags ""
        forvalues k = 1/4 {
            local ly = `before' - `k' + 1
            local lags "`lags' intl_ratio(`ly')"
        }
        capture noisily synth intl_ratio ///
            intl_ratio_mean_it_final `lags', ///
            trunit(`uk_id') trperiod(`treatyear') ///
            counit(`control_ids') ///
            xperiod(2008(1)`before') ///
            nested allopt ///
            keep("_raw_`treatyear'.dta", replace)
    }

    * Tidy the raw synth output into Year/actual/synthetic/gap.
    use "_raw_`treatyear'.dta", clear
    rename _time Year
    rename _Y_treated actual
    rename _Y_synthetic synthetic
    keep Year actual synthetic
    drop if missing(Year)
    gen gap = actual - synthetic
    gen pseudo_year = `treatyear'
    if "`outcome'" == "total" {
        gen actual_real = exp(actual) - 1
        gen synthetic_real = exp(synthetic) - 1
        gen gap_pct = (actual_real - synthetic_real) / actual_real * 100
    }
    save "uk_intime_`treatyear'.dta", replace
    erase "_raw_`treatyear'.dta"
end

*---------------------------------------------------------------*
* Total publications
*---------------------------------------------------------------*
local tot "`brexit'/total_publications"
capture mkdir "`tot'/in_time"
foreach t in 2013 2014 2015 2016 {
    di as result "=== TOTAL pseudo-year `t' ==="
    fit_intime, outdir("`tot'") outcome("total") treatyear(`t')
}

*---------------------------------------------------------------*
* International collaboration ratio
*---------------------------------------------------------------*
local rat "`brexit'/intl_ratio"
capture mkdir "`rat'/in_time"
foreach t in 2013 2014 2015 2016 {
    di as result "=== RATIO pseudo-year `t' ==="
    fit_intime, outdir("`rat'") outcome("ratio") treatyear(`t')
}

di as result "=== IN-TIME PLACEBO SCM DONE ==="
