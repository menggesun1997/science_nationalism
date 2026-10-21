clear all
set more off
********************************************************************************
* Leave-one-out (drop-one-donor) robustness check: Brexit, total publications.
* Treated units: UK and EU. Reuses the processed_data.dta produced by
* compare.do (identical donor pool, predictors and fitting window) and the
* shared engine in code/_loo_engine.do.
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
        di as error "Cannot locate code/config.do. Set SCIENCE_NATIONALISM_ROOT"
        exit 601
    }
    do "`_cfg'"
}
do "$CODE/07_loo_robustness/_loo_engine.do"
cd "$CODE/07_loo_robustness"

* Reuse the analysis panel saved by compare.do so the donor pool, predictors
* and fitting window match the main specification exactly.
use "$CODE/01_scm_brexit/total_publications/processed_data.dta", clear
qui sum country_id if Country == "UNITED_KINGDOM"
local uk_id = r(mean)
levelsof Country, local(countries) clean
local donors ""
foreach c of local countries {
    if !inlist("`c'", "EU", "UNITED_KINGDOM") {
        qui sum country_id if Country == "`c'"
        local donors "`donors' `=r(mean)'"
    }
}

global LOO_OUTCOME  "log_pub_total"
global LOO_TRPERIOD 2016
global LOO_XSTART   2008
global LOO_BEFORE   2015
global LOO_POSTEND  0
global LOO_ISLOG    1
global LOO_OUTDIR   "results/brexit_total"
global LOO_DONORS   "`donors'"
capture mkdir "results"
capture mkdir "results/brexit_total"
save "results/brexit_total/processed_data.dta", replace

* --- UK only (EU is no longer treated as a unit) ---
* Predictors mirror compare.do: pre-period pub mean + 2013 lag.
global control_vars "log_pub_pre_mean_uk_final"
global LOO_TNAME  "uk"
global LOO_TRUNIT `uk_id'
global LOO_PRED   "log_pub_total(2013)"
loo_unit
