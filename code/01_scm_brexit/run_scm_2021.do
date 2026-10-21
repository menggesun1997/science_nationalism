*===========================================================*
* run_scm_2021.do — UK synthetic control with 2021 treatment
*
* Brexit unfolded in two institutional steps: the June 2016 referendum and
* the formal exit that took effect on 1 January 2021 (end of the transition
* period, loss of automatic Horizon Europe access). The main analysis treats
* 2016 as the intervention. This file refits the UK synthetic control with
* 2021 as the intervention so that both dates can be reported side by side
* in Figure 1.
*
* Specification mirrors the 2016 analysis with every window shifted forward
* by five years:
*   total:  pre-mean of log_pub_total over 2005..2017, lagged outcome at 2018,
*           fitting window xperiod(2008..2020)
*   ratio:  pre-mean of intl_ratio plus lags at 2020, 2019, 2016, 2015,
*           fitting window xperiod(2008..2020)
* Donor pool is unchanged: non-EU countries excluding the UK.
*
* Outputs (consumed by 99_redraw_panels.do):
*   total_publications/uk_synth_results_2021.dta
*   intl_ratio/uk_synth_results_2021.dta
*   <outcome>/uk_weights_country_2021.xlsx
*===========================================================*
clear all
set more off

capture confirm file "$CODE/config.do"
if _rc {
    local _cfg ""
    local _env : environment SCIENCE_NATIONALISM_ROOT
    if "`_env'" != "" {
        capture confirm file "`_env'/code/config.do"
        if !_rc local _cfg "`_env'/code/config.do"
    }
    if "`_cfg'" == "" {
        local _d "`c(pwd)'"
        forvalues _i = 1/12 {
            capture confirm file "`_d'/code/config.do"
            if !_rc {
                local _cfg "`_d'/code/config.do"
                continue, break
            }
            local _d = regexr("`_d'", "/[^/]+$", "")
            if "`_d'" == "" continue, break
        }
    }
    if "`_cfg'" == "" {
        di as error "Cannot locate code/config.do. Set SCIENCE_NATIONALISM_ROOT."
        exit 601
    }
    do "`_cfg'"
}

local brexit "$CODE/01_scm_brexit"
local treated_year 2021
local before 2020
local pre_start 2008

*-----------------------------------------------------------*
* Program: fit the UK synthetic control for one outcome
*-----------------------------------------------------------*
capture program drop fit_2021
program define fit_2021
    syntax, OUTdir(string) OUTCOME(string)

    * synth mishandles absolute paths containing spaces, so cd in first and
    * pass a bare filename to keep().
    cd "`outdir'"
    use "`outdir'/processed_data.dta", clear

    quietly summarize country_id if Country == "UNITED_KINGDOM"
    local uk_id = r(mean)
    levelsof country_id if !inlist(Country, "EU", "UNITED_KINGDOM"), ///
        local(control_ids) clean

    if "`outcome'" == "total" {
        capture drop pre_mean_21 pre_mean_21_final
        bysort country_id: egen pre_mean_21 = ///
            mean(log_pub_total) if Year >= 2005 & Year <= 2017
        bysort country_id: egen pre_mean_21_final = max(pre_mean_21)
        synth log_pub_total pre_mean_21_final log_pub_total(2018), ///
            trunit(`uk_id') trperiod(2021) counit(`control_ids') ///
            xperiod(2008(1)2020) nested allopt ///
            keep("_raw_2021.dta", replace)
    }
    else {
        capture drop ratio_mean_21 ratio_mean_21_final
        bysort country_id: egen ratio_mean_21 = ///
            mean(intl_ratio) if Year >= 2005 & Year <= 2017
        bysort country_id: egen ratio_mean_21_final = max(ratio_mean_21)
        synth intl_ratio ratio_mean_21_final ///
            intl_ratio(2020) intl_ratio(2019) intl_ratio(2016) intl_ratio(2015), ///
            trunit(`uk_id') trperiod(2021) counit(`control_ids') ///
            xperiod(2008(1)2020) nested allopt ///
            keep("_raw_2021.dta", replace)
    }

    *-- donor weights -------------------------------------------------*
    preserve
        use "_raw_2021.dta", clear
        keep _Co_Number _W_Weight
        drop if missing(_Co_Number)
        rename _Co_Number country_id
        tempfile w
        save `w', replace
        use "`outdir'/processed_data.dta", clear
        keep country_id Country
        duplicates drop
        merge 1:1 country_id using `w', keep(match) nogenerate
        gsort -_W_Weight
        export excel Country _W_Weight using ///
            "uk_weights_country_2021.xlsx", firstrow(variables) replace
    restore

    *-- tidy series, matching the 2016 variable names with a _21 suffix --*
    use "_raw_2021.dta", clear
    rename _time Year
    rename _Y_treated uk_actual_21
    rename _Y_synthetic uk_synthetic_21
    keep Year uk_actual_21 uk_synthetic_21
    drop if missing(Year)

    gen uk_gap_21 = uk_actual_21 - uk_synthetic_21
    gen pre_sq_21  = uk_gap_21^2 if Year <= 2020 & Year > 2008
    gen post_sq_21 = uk_gap_21^2 if Year >= 2021
    egen pre_mspe_21  = mean(pre_sq_21)
    egen post_mspe_21 = mean(post_sq_21)
    gen rmspe_ratio_uk_21 = sqrt(post_mspe_21) / sqrt(pre_mspe_21)

    if "`outcome'" == "total" {
        gen uk_actual_real_21    = exp(uk_actual_21) - 1
        gen uk_synthetic_real_21 = exp(uk_synthetic_21) - 1
        gen uk_gap_pct_21 = ///
            (uk_actual_real_21 - uk_synthetic_real_21) / uk_actual_real_21 * 100
    }

    save "uk_synth_results_2021.dta", replace
    erase "_raw_2021.dta"
end

*-----------------------------------------------------------*
* Run both outcomes
*-----------------------------------------------------------*
di as result _n "=== 2021 treatment: total publications ==="
fit_2021, outdir("`brexit'/total_publications") outcome("total")

di as result _n "=== 2021 treatment: intl collaboration ratio ==="
fit_2021, outdir("`brexit'/intl_ratio") outcome("ratio")

*-----------------------------------------------------------*
* Report the estimates that go into the figure
*-----------------------------------------------------------*
use "`brexit'/total_publications/uk_synth_results_2021.dta", clear
quietly summarize uk_gap_pct_21 if Year >= 2021
local att_t : display %5.2f r(mean)
quietly summarize rmspe_ratio_uk_21
local rm_t : display %5.2f r(mean)

use "`brexit'/intl_ratio/uk_synth_results_2021.dta", clear
quietly summarize uk_gap_21 if Year >= 2021
local att_r : display %5.2f (r(mean) * 100)
quietly summarize rmspe_ratio_uk_21
local rm_r : display %5.2f r(mean)

di as result _n "{hline 58}"
di as result "UK, 2021 intervention (post period 2021-2024)"
di as result "{hline 58}"
di as result "  total publications   ATT = `att_t'%   RMSPE ratio = `rm_t'"
di as result "  intl. ratio          ATT = `att_r' pp  RMSPE ratio = `rm_r'"
di as result "{hline 58}"
di as result _n "=== BREXIT 2021 SCM DONE ==="
