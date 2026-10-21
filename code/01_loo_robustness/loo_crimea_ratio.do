clear all
set more off
********************************************************************************
* Leave-one-out robustness check: 2014 Crimean crisis, intl collaboration ratio.
* Treated units: Russia and Ukraine. Reuses intl_ratio/processed_data.dta from
* intl_ratio_compare.do and the shared engine.
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

use "$CODE/01_scm_crimea_2014/intl_ratio/processed_data.dta", clear
qui sum country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)
qui sum country_id if Country == "UKRAINE"
local ukraine_id = r(mean)
levelsof Country, local(countries) clean
local donors ""
foreach c of local countries {
    if !inlist("`c'", "RUSSIAN_FEDERATION", "UKRAINE") {
        qui sum country_id if Country == "`c'"
        local donors "`donors' `=r(mean)'"
    }
}

global control_vars "log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD"
global LOO_OUTCOME  "intl_ratio"
global LOO_TRPERIOD 2014
global LOO_XSTART   2008
global LOO_BEFORE   2013
global LOO_POSTEND  2021
global LOO_ISLOG    0
global LOO_OUTDIR   "results/crimea_ratio"
global LOO_DONORS   "`donors'"
capture mkdir "results"
capture mkdir "results/crimea_ratio"
save "results/crimea_ratio/processed_data.dta", replace

* --- Russia ---
global LOO_TNAME  "russia"
global LOO_TRUNIT `russia_id'
global LOO_PRED   "intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2008) intl_ratio(2007) intl_ratio(2006)"
loo_unit

* --- Ukraine ---
global LOO_TNAME  "ukraine"
global LOO_TRUNIT `ukraine_id'
global LOO_PRED   "intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2009) intl_ratio(2008)"
loo_unit
