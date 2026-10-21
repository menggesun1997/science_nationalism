*===============================================================*
* run_in_time_placebo_ruua.do — Russia/Ukraine in-time placebo SCM
*
* Covers the Crimea (2011-2014) and full-scale-invasion (2019-2022) events,
* for both outcomes. For each pseudo-treatment year t we refit each treated
* unit using only pre-t information (xperiod = fitstart..t-1, lagged outcome
* predictors drawn from years < t). Donor pool excludes Russia and Ukraine.
*
* Output: <outcome_dir>/in_time/<unit>_intime_<t>.dta with a tidy
* Year/actual/synthetic/gap layout for the plotting script.
*===============================================================*
clear all
set more off

global ROOT "c:/Users/91916/Dropbox/GitHub/sicence nationism"
do "$ROOT/code/config.do"

*---------------------------------------------------------------*
* Fit one treated unit for one pseudo-year.
*   outcome: "total" (log_pub_total) or "ratio" (intl_ratio)
*   nlags  : number of most-recent pre-t lags to use as predictors
*---------------------------------------------------------------*
capture program drop fit_ruua
program define fit_ruua
    syntax, OUTdir(string) OUTCOME(string) UNIT(string) ID(integer) ///
        Treatyear(integer) FITstart(integer) NLags(integer)

    local before = `treatyear' - 1
    cd "`outdir'/in_time"
    use "`outdir'/processed_data.dta", clear

    levelsof country_id if !inlist(Country, "RUSSIAN_FEDERATION", "UKRAINE"), ///
        local(control_ids) clean

    if "`outcome'" == "total" {
        local dv log_pub_total
        local base "log_gdp_per_capita_10 log_rp_10 RD"
    }
    else {
        local dv intl_ratio
        local base "log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD"
    }

    * Most-recent nlags years strictly before t.
    local lags ""
    forvalues k = 1/`nlags' {
        local ly = `before' - `k' + 1
        local lags "`lags' `dv'(`ly')"
    }

    capture noisily synth `dv' `base' `lags', ///
        trunit(`id') trperiod(`treatyear') ///
        counit(`control_ids') ///
        xperiod(`fitstart'(1)`before') ///
        nested allopt ///
        keep("_raw_`unit'_`treatyear'.dta", replace)

    use "_raw_`unit'_`treatyear'.dta", clear
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
    save "`unit'_intime_`treatyear'.dta", replace
    erase "_raw_`unit'_`treatyear'.dta"
end

*---------------------------------------------------------------*
* Helper: resolve treated ids from a processed_data.dta
*---------------------------------------------------------------*
capture program drop run_event
program define run_event
    syntax, OUTdir(string) OUTCOME(string) FITstart(integer) ///
        Years(numlist) NLags(integer)

    capture mkdir "`outdir'/in_time"
    use "`outdir'/processed_data.dta", clear
    quietly summarize country_id if Country == "RUSSIAN_FEDERATION"
    local ru = r(mean)
    quietly summarize country_id if Country == "UKRAINE"
    local ua = r(mean)

    foreach t of numlist `years' {
        di as result "=== `outcome' RU pseudo `t' ==="
        fit_ruua, outdir("`outdir'") outcome("`outcome'") unit("russia") ///
            id(`ru') treatyear(`t') fitstart(`fitstart') nlags(`nlags')
        di as result "=== `outcome' UA pseudo `t' ==="
        fit_ruua, outdir("`outdir'") outcome("`outcome'") unit("ukraine") ///
            id(`ua') treatyear(`t') fitstart(`fitstart') nlags(`nlags')
    }
end

*---------------------------------------------------------------*
* Crimea 2014: pseudo years 2011-2014, fit from 2008
*---------------------------------------------------------------*
run_event, outdir("$CODE/01_scm_crimea_2014/total_publications") ///
    outcome("total") fitstart(2008) years(2011 2012 2013 2014) nlags(4)
run_event, outdir("$CODE/01_scm_crimea_2014/intl_ratio") ///
    outcome("ratio") fitstart(2008) years(2011 2012 2013 2014) nlags(4)

*---------------------------------------------------------------*
* Full-scale invasion 2022: pseudo years 2019-2022, fit from 2015
*---------------------------------------------------------------*
run_event, outdir("$CODE/01_scm_war_2022/total_publications") ///
    outcome("total") fitstart(2015) years(2019 2020 2021 2022) nlags(4)
run_event, outdir("$CODE/01_scm_war_2022/intl_ratio") ///
    outcome("ratio") fitstart(2015) years(2019 2020 2021 2022) nlags(4)

di as result "=== RU/UA IN-TIME PLACEBO SCM DONE ==="
