clear all
set more off
********************************************************************************
* Leave-one-out robustness check: 2014 Crimean crisis, total publications.
* Treated units: Russia and Ukraine. Reuses total_publications/processed_data.dta
* from compare_total.do and the shared engine. The synthetic control is
* identified by the pre-2014 fit, so the 2021 effect cap does not affect it;
* plots are truncated to 2021 downstream.
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

use "$CODE/01_scm_crimea_2014/total_publications/processed_data.dta", clear
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

global control_vars "log_gdp_per_capita_10 log_rp_10 RD"
global LOO_OUTCOME  "log_pub_total"
global LOO_TRPERIOD 2014
global LOO_XSTART   2008
global LOO_BEFORE   2013
global LOO_POSTEND  2021
global LOO_ISLOG    1
global LOO_OUTDIR   "results/crimea_total"
global LOO_DONORS   "`donors'"
capture mkdir "results"
capture mkdir "results/crimea_total"
save "results/crimea_total/processed_data.dta", replace

* --- Russia ---
global LOO_TNAME  "russia"
global LOO_TRUNIT `russia_id'
global LOO_PRED   "log_pub_total(2013) log_pub_total(2012) log_pub_total(2010) log_pub_total(2009) log_pub_total(2008)"
loo_unit

* --- Ukraine ---
global LOO_TNAME  "ukraine"
global LOO_TRUNIT `ukraine_id'
global LOO_PRED   "log_pub_total(2013) log_pub_total(2012) log_pub_total(2011) log_pub_total(2010) log_pub_total(2008)"
loo_unit
