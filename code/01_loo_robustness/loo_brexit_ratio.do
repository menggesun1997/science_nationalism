clear all
set more off
********************************************************************************
* Leave-one-out robustness check: Brexit, international collaboration ratio.
* Treated units: UK and EU. Reuses intl_ratio/processed_data.dta from
* compare_intl_ratio.do and the shared engine.
********************************************************************************
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
        di as error "Cannot locate code/config.do."
        exit 601
    }
    do "`_cfg'"
}
do "$CODE/07_loo_robustness/_loo_engine.do"
cd "$CODE/07_loo_robustness"

use "$CODE/01_scm_brexit/intl_ratio/processed_data.dta", clear
qui sum country_id if Country == "UNITED_KINGDOM"
local uk_id = r(mean)
qui sum country_id if Country == "EU"
local eu_id = r(mean)
levelsof Country, local(countries) clean
local donors ""
foreach c of local countries {
    if !inlist("`c'", "EU", "UNITED_KINGDOM") {
        qui sum country_id if Country == "`c'"
        local donors "`donors' `=r(mean)'"
    }
}

global control_vars "intl_ratio_mean_final"
global LOO_OUTCOME  "intl_ratio"
global LOO_TRPERIOD 2016
global LOO_XSTART   2008
global LOO_BEFORE   2015
global LOO_POSTEND  0
global LOO_ISLOG    0
global LOO_OUTDIR   "results/brexit_ratio"
global LOO_DONORS   "`donors'"
capture mkdir "results"
capture mkdir "results/brexit_ratio"
save "results/brexit_ratio/processed_data.dta", replace

* --- UK (EU is no longer treated as a unit; only the UK is estimated) ---
global LOO_TNAME  "uk"
global LOO_TRUNIT `uk_id'
global LOO_PRED   "intl_ratio(2015) intl_ratio(2014) intl_ratio(2011) intl_ratio(2010)"
loo_unit
