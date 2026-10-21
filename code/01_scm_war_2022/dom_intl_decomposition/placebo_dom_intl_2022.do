clear all
set more off

********************************************************************************
* In-space placebo p-values for the 2022 domestic/international decomposition.
* For each outcome (domestic, international) reassign the 2022 intervention to
* every unit, collect post/pre RMSPE ratios (post window 2022--2024), and report
* the RMSPE-ratio placebo p-value and rank for Russia and for Ukraine.
* Uses the same predictors/fitting window (2015--2021) as dom_intl_scm_2022.do
* (default optimizer, matching standard placebo practice).
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

cd "$CODE/01_scm_war_2022/dom_intl_decomposition"

* Predictors, matching dom_intl_scm_2022.do (self-contained: the leading
* `clear all` wipes any globals set by a caller, so define them here).
global control_vars "log_gdp_per_capita log_rp RD"

capture program drop run_pb
program define run_pb, rclass
    args outcome
    use "processed_data_2022.dta", clear
    levelsof country_id, local(allids)
    preserve
    keep country_id Country
    duplicates drop
    tempfile cnames
    save `cnames'
    restore
    tempname mh
    tempfile ratios
    postfile `mh' double(unit pre post ratio ok) using `ratios', replace
    foreach uid of local allids {
        local others ""
        foreach j of local allids {
            if `j' != `uid' local others "`others' `j'"
        }
        local pre = .
        local post = .
        capture noisily synth `outcome' $control_vars ///
            `outcome'(2021) `outcome'(2020) `outcome'(2019) `outcome'(2018) ///
            `outcome'(2017) `outcome'(2016) `outcome'(2015) , ///
            trunit(`uid') trperiod(2022) counit(`others') ///
            xperiod(2015(1)2021) keep(_pb2022_tmp, replace)
        if _rc == 0 {
            preserve
            use _pb2022_tmp, clear
            rename _time Year
            gen g2 = (_Y_treated - _Y_synthetic)^2
            quietly summarize g2 if Year >= 2015 & Year <= 2021
            local pre = sqrt(r(mean))
            quietly summarize g2 if Year >= 2022 & Year <= 2024
            local post = sqrt(r(mean))
            restore
        }
        local ok = (!missing(`pre') & `pre' > 0 & !missing(`post'))
        local ratio = .
        if `ok' local ratio = `post'/`pre'
        post `mh' (`uid') (`pre') (`post') (`ratio') (`ok')
    }
    postclose `mh'
    use `ratios', clear
    rename unit country_id
    merge 1:1 country_id using `cnames', keep(master match) nogen
    gsort -ok -ratio
    export excel using "placebo_2022_`outcome'.xlsx", firstrow(variables) replace

    * RMSPE-ratio placebo p-value for Russia and Ukraine (units with valid fit).
    count if ok == 1
    local n_total = r(N)
    foreach who in russia ukraine {
        local rid = ${`who'_id_g}
        quietly sum ratio if country_id == `rid'
        local tr = r(mean)
        count if ok == 1 & ratio >= `tr'
        return scalar p_`who' = r(N) / `n_total'
    }
    return scalar n = `n_total'
end

* Resolve Russia and Ukraine country_id, expose to run_pb via globals.
use "processed_data_2022.dta", clear
quietly sum country_id if Country == "RUSSIAN_FEDERATION"
global russia_id_g = r(mean)
quietly sum country_id if Country == "UKRAINE"
global ukraine_id_g = r(mean)

run_pb log_pub_dom
local p_ru_dom = r(p_russia)
local p_ua_dom = r(p_ukraine)
local n_dom    = r(n)
run_pb log_pub_intl
local p_ru_intl = r(p_russia)
local p_ua_intl = r(p_ukraine)
local n_intl    = r(n)

di as text "==============================================================="
di as text "2022 in-space placebo p-values (RMSPE ratio, window 2022-2024)"
di as text "  Russia  domestic p=`p_ru_dom'  international p=`p_ru_intl'"
di as text "  Ukraine domestic p=`p_ua_dom'  international p=`p_ua_intl'"
di as text "==============================================================="

* Machine-readable p-values consumed by figure2_decomposition.do.
clear
set obs 4
gen str12 event     = "war2022"
gen str8  country   = ""
gen str12 component = ""
gen double p        = .
gen int    n_valid  = .
replace country = "russia"  in 1/2
replace country = "ukraine" in 3/4
replace component = "dom"  in 1
replace component = "intl" in 2
replace component = "dom"  in 3
replace component = "intl" in 4
replace p = `p_ru_dom'  in 1
replace p = `p_ru_intl' in 2
replace p = `p_ua_dom'  in 3
replace p = `p_ua_intl' in 4
replace n_valid = `n_dom'  in 1/2
replace n_valid = `n_intl' in 3/4
export delimited using "pvalues_2022.csv", replace

