clear all
set more off

********************************************************************************
* Refresh 2014 Crimean-crisis in-space placebo results for intl_ratio.
*
* This re-runs only the donor-placebo SCM fits and rewrites gap_*.dta files so
* the placebo distribution extends through 2024. It preserves the predictor
* specification used by the existing intl_ratio_compare.do placebo block.
********************************************************************************

local base_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/crimes"
local treated_year 2014
local before_treated_year 2013

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
global control_vars_ukraine "intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2009) intl_ratio(2008)"

foreach country of local control_countries {
    di as text "Refreshing Crimean intl_ratio placebo for `country'"

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
        $control_vars_ukraine, ///
        trunit(`treat_id') trperiod(`treated_year') ///
        counit(`placebo_controls') ///
        xperiod(2008(1)`before_treated_year') ///
        nested allopt ///
        keep("synth_`country'.dta", replace)

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

use "gap_ARGENTINA.dta", clear
foreach country of local control_countries {
    if "`country'" != "ARGENTINA" {
        capture merge 1:1 Year using "gap_`country'.dta", nogenerate
    }
}
merge 1:1 Year using "`base_dir'/intl_ratio/ukraine_synth_results.dta", nogenerate
merge 1:1 Year using "`base_dir'/intl_ratio/russia_synth_results.dta", nogenerate

foreach country of local control_countries {
    capture confirm variable gap_`country'
    if !_rc {
        gen pre_sq_error_`country' = gap_`country'^2 if Year <= `before_treated_year' & Year >= 2008
        egen pre_mspe_`country' = mean(pre_sq_error_`country')
        gen pre_rmspe_`country' = sqrt(pre_mspe_`country')

        gen post_sq_error_`country' = gap_`country'^2 if Year >= `treated_year'
        egen post_mspe_`country' = mean(post_sq_error_`country')
        gen post_rmspe_`country' = sqrt(post_mspe_`country')
        gen rmspe_ratio_`country' = post_rmspe_`country' / pre_rmspe_`country'
    }
}

save "`base_dir'/intl_ratio/final_results.dta", replace

display as text "Crimean intl_ratio donor-placebo gaps refreshed through 2024."
