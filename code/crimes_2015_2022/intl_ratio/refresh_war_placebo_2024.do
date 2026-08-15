clear all
set more off

********************************************************************************
* Refresh 2022 full-scale-invasion in-space placebo results for intl_ratio.
*
* This script only re-runs donor placebo files that do not yet extend through
* 2024, using the predictor specification in intl_ratio_compare.do.
********************************************************************************

local base_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/crimes_2015_2022"
local treated_year 2022
local before_treated_year 2021
local fit_start_year 2015

use "`base_dir'/intl_ratio/processed_data.dta", clear
cd "`base_dir'/intl_ratio"

levelsof Country, local(countries) clean

local control_countries
foreach country of local countries {
    if !inlist("`country'", "UKRAINE", "RUSSIAN_FEDERATION") {
        local control_countries `"`control_countries' "`country'""'
    }
}

global control_vars "log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD"
global control_vars_russia "intl_ratio(2021) intl_ratio(2019) intl_ratio(2017) intl_ratio(2015)"
global control_vars_ukraine "intl_ratio(2021) intl_ratio(2020) intl_ratio(2019) intl_ratio(2018) intl_ratio(2017)"

foreach country of local control_countries {
    capture confirm file "gap_`country'.dta"
    if !_rc {
        use "gap_`country'.dta", clear
        quietly summarize Year
        if r(max) >= 2024 {
            continue
        }
    }

    di as text "Refreshing war intl_ratio placebo for `country'"

    use "`base_dir'/intl_ratio/processed_data.dta", clear
    quietly summarize country_id if Country == "`country'"
    local treat_id = r(mean)
    if missing(`treat_id') {
        di as error "No country_id for `country'; skipped"
        continue
    }

    local placebo_controls
    foreach ctrl of local control_countries {
        if "`ctrl'" != "`country'" {
            quietly summarize country_id if Country == "`ctrl'"
            if !missing(r(mean)) local placebo_controls "`placebo_controls' `=r(mean)'"
        }
    }

    capture quietly synth intl_ratio ///
        $control_vars ///
        $control_vars_russia, ///
        trunit(`treat_id') trperiod(`treated_year') ///
        counit(`placebo_controls') ///
        xperiod(`fit_start_year'(1)`before_treated_year') ///
        nested allopt ///
        keep("synth_`country'.dta", replace)

    if _rc {
        di as text "Standard model failed for `country'; trying Ukraine-lag specification"
        capture quietly synth intl_ratio ///
            $control_vars ///
            $control_vars_ukraine, ///
            trunit(`treat_id') trperiod(`treated_year') ///
            counit(`placebo_controls') ///
            xperiod(`fit_start_year'(1)`before_treated_year') ///
            nested allopt ///
            keep("synth_`country'.dta", replace)
    }

    if _rc {
        di as error "synth failed for `country'; skipped"
        continue
    }

    use "synth_`country'.dta", clear
    rename _time Year
    rename _Y_treated cc_actual
    rename _Y_synthetic cc_synthetic
    gen gap_`country' = cc_actual - cc_synthetic
    egen avg_effect = mean(gap_`country') if Year >= `treated_year'
    gen avg_gap_`country' = avg_effect
    keep Year gap_`country' avg_gap_`country'
    drop if missing(Year)
    save "gap_`country'.dta", replace
}

display as text "War intl_ratio stale donor-placebo gaps refreshed through 2024 where synth succeeded."
