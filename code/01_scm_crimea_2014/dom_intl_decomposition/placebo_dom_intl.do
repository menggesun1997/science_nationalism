clear all
set more off

********************************************************************************
* In-space placebo p-values for the Russia domestic/international decomposition.
*
* For each outcome (domestic, international) we reassign the 2014 intervention
* to every donor country, collect the resulting post/pre RMSPE ratios on the
* log scale, and compute Russia's RMSPE-ratio placebo p-value. The window for
* the post-treatment RMSPE is capped at 2021, matching the main Crimea design.
********************************************************************************

capture confirm file "$CODE/config.do"
if _rc {
    local _env : environment SCIENCE_NATIONALISM_ROOT
    local _cfg ""
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
    do "`_cfg'"
}

cd "$CODE/01_scm_crimea_2014/dom_intl_decomposition"

* Predictors, matching russia_dom_intl_scm.do (self-contained for standalone runs).
global control_vars "log_gdp_per_capita_10 log_rp_10 RD"

local treated_year 2014
local before_treated_year 2013
local post_end_year 2021

* Program: run placebo synth over all units for one outcome, return Russia's
* RMSPE-ratio placebo p-value. Uses the same predictors/window as the main run.
capture program drop run_placebo
program define run_placebo, rclass
    args outcome
    use "processed_data.dta", clear
    levelsof country_id, local(allids)
    * Map country_id -> Country name for the audit table.
    preserve
    keep country_id Country
    duplicates drop
    tempfile cnames
    save `cnames'
    restore
    tempname memhold
    tempfile ratios
    * Record every unit's pre/post RMSPE and ratio so completeness can be audited.
    postfile `memhold' double(unit pre post ratio ok) using `ratios', replace

    foreach uid of local allids {
        local others ""
        foreach j of local allids {
            if `j' != `uid' local others "`others' `j'"
        }
        * Placebo distribution uses the default regression-based optimizer
        * (no nested/allopt): these are prohibitively slow across all donors and
        * unnecessary for the reference distribution. Russia is included in the
        * same loop, so its RMSPE ratio is computed identically to the donors,
        * keeping the placebo comparison internally consistent.
        local pre = .
        local post = .
        capture noisily synth `outcome' $control_vars ///
            `outcome'(2013) `outcome'(2012) `outcome'(2010) `outcome'(2009) `outcome'(2008) , ///
            trunit(`uid') trperiod(2014) counit(`others') ///
            xperiod(2008(1)2013) keep(_pb_tmp, replace)
        if _rc == 0 {
            preserve
            use _pb_tmp, clear
            rename _time Year
            gen g2 = (_Y_treated - _Y_synthetic)^2
            quietly summarize g2 if Year <= 2013
            local pre = sqrt(r(mean))
            quietly summarize g2 if Year >= 2014 & Year <= 2021
            local post = sqrt(r(mean))
            restore
        }
        local ok = (!missing(`pre') & `pre' > 0 & !missing(`post'))
        local ratio = .
        if `ok' local ratio = `post'/`pre'
        post `memhold' (`uid') (`pre') (`post') (`ratio') (`ok')
    }
    postclose `memhold'

    use `ratios', clear
    rename unit country_id
    merge 1:1 country_id using `cnames', keep(master match) nogen
    gsort -ok -ratio
    order country_id Country pre post ratio ok
    export excel using "placebo_audit_`outcome'.xlsx", firstrow(variables) replace
    list Country ratio ok, sepby(ok) noobs

    * Russia id is resolved by the caller and passed via a global.
    local rid = $russia_id_g
    quietly sum ratio if country_id == `rid'
    local treated_ratio = r(mean)
    * Inference uses only units with a valid pre/post fit (ok==1).
    count if ok == 1 & ratio >= `treated_ratio'
    local n_extreme = r(N)
    count if ok == 1
    local n_total = r(N)
    count
    local n_all = r(N)
    return scalar p = `n_extreme' / `n_total'
    return scalar treated_ratio = `treated_ratio'
    return scalar n = `n_total'
    return scalar n_all = `n_all'
end

* Resolve Russia's country_id and expose it to the program via a global.
use "processed_data.dta", clear
quietly sum country_id if Country == "RUSSIAN_FEDERATION"
global russia_id_g = r(mean)

run_placebo log_pub_dom
local p_dom : display %5.3f r(p)
local n_dom = r(n)
local nall_dom = r(n_all)
local tr_dom : display %5.3f r(treated_ratio)

run_placebo log_pub_intl
local p_intl : display %5.3f r(p)
local n_intl = r(n)
local nall_intl = r(n_all)
local tr_intl : display %5.3f r(treated_ratio)

di as text "==============================================================="
di as text "In-space placebo p-values (RMSPE ratio, 2014, window<=2021)"
di as text "  Domestic:      p = `p_dom'  valid N=`n_dom' of `nall_dom' units (ratio=`tr_dom')"
di as text "  International: p = `p_intl'  valid N=`n_intl' of `nall_intl' units (ratio=`tr_intl')"
di as text "  (Per-country audit exported to placebo_audit_*.xlsx)"
di as text "==============================================================="

* Machine-readable p-values consumed by figure2_decomposition.do.
preserve
clear
set obs 2
gen str12 event     = "crimea2014"
gen str8  country   = "russia"
gen str12 component = ""
gen double p        = .
gen int    n_valid  = .
replace component = "dom"  in 1
replace component = "intl" in 2
replace p       = `p_dom'  in 1
replace p       = `p_intl' in 2
replace n_valid = `n_dom'  in 1
replace n_valid = `n_intl' in 2
export delimited using "pvalues_russia.csv", replace
restore

