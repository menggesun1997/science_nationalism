clear all
set more off

********************************************************************************
* Domestic vs international publication SCM decomposition around the 2022
* full-scale invasion, for Russia and Ukraine.
*
* Motivation: the aggregate post-2022 collaboration ratio moves in opposite
* directions for the two countries, but a ratio is a quotient and cannot by
* itself distinguish a genuine change in international output from a purely
* compositional shift driven by the domestic denominator. Splitting total
* publications into domestic (= total - international) and international
* (co-authored) counts, and running SCM on each, shows in absolute terms
* whether internationally co-authored output rose or fell after 2022 relative
* to its own synthetic counterfactual.
*
* Mirrors the donor pool, fitting window (2008--2021) and predictors of the
* aggregate 2022 model (01_scm_war_2022/total_publications/compare_russia.do),
* changing only the outcome variable. Treated period is 2022.
********************************************************************************

* -- Path resolution -------------------------------------------------------
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

cd "$CODE/01_scm_war_2022/dom_intl_decomposition"

local src "$CODE/01_scm_war_2022/original_completed.xlsx"
import excel "`src'", sheet("Sheet1") firstrow clear

local treated_year 2022
replace Country = subinstr(Country, " ", "_", .)

* Decompose: domestic = total - international; international = co-authored.
gen pub_dom = pub_total - pub_intl

levelsof Country, local(countries) clean
gen country_id = .
local i = 1
foreach country of local countries {
    replace country_id = `i' if Country == "`country'"
    local ++i
}
xtset country_id Year

local control_ids ""
foreach country of local countries {
    if !inlist("`country'", "RUSSIAN_FEDERATION", "UKRAINE") {
        qui sum country_id if Country == "`country'"
        local control_ids "`control_ids' `r(mean)'"
    }
}

gen log_pub_dom  = log(pub_dom + 1)
gen log_pub_intl = log(pub_intl + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

global control_vars "log_gdp_per_capita log_rp RD"

save "processed_data_2022.dta", replace

* Persist country_id <-> Country mapping so donor weights can be labeled.
preserve
    keep country_id Country
    duplicates drop
    save "country_names_2022.dta", replace
restore

* Program: run one outcome for one treated unit, write a synth-results dta.
capture program drop run_one
program define run_one
    args outcome trunit tag
    use "processed_data_2022.dta", clear
    synth `outcome' ///
        $control_vars ///
        `outcome'(2021) `outcome'(2020) `outcome'(2019) `outcome'(2018) ///
        `outcome'(2017) `outcome'(2016) `outcome'(2015) , ///
        trunit(`trunit') trperiod(2022) ///
        counit(`control_ids') ///
        xperiod(2015(1)2021) ///
        nested allopt ///
        keep(`tag'_results, replace)

    * Export donor weights with country labels.
    matrix W = e(W_weights)
    preserve
        clear
        svmat W, names(col)
        rename _Co_Number country_id
        rename _W_Weight weight
        merge m:1 country_id using "country_names_2022.dta", keep(match) nogenerate
        gsort -weight
        keep Country country_id weight
        export excel using "`tag'_weights.xlsx", firstrow(variables) replace
    restore

    use `tag'_results, clear
    rename _time Year
    rename _Y_treated actual
    rename _Y_synthetic synthetic
    gen actual_real = exp(actual) - 1
    gen synthetic_real = exp(synthetic) - 1
    gen gap_pct = (actual_real - synthetic_real) / actual_real * 100
    * Effect window: 2022--2024 (post-invasion), matching the total-publication model.
    egen avg_effect = mean(gap_pct) if Year >= 2022 & Year <= 2024
    * Fit diagnostics on the log scale: pre-period = fitting window 2015--2021.
    gen log_gap = actual - synthetic
    gen pre_sq  = log_gap^2 if Year >= 2015 & Year <= 2021
    egen pre_mspe = mean(pre_sq)
    gen pre_rmspe = sqrt(pre_mspe)
    gen post_sq = log_gap^2 if Year >= 2022 & Year <= 2024
    egen post_mspe = mean(post_sq)
    gen post_rmspe = sqrt(post_mspe)
    gen rmspe_ratio = post_rmspe / pre_rmspe
    drop if missing(Year)
    save "`tag'_synth.dta", replace
end

qui sum country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)
qui sum country_id if Country == "UKRAINE"
local ukraine_id = r(mean)

run_one log_pub_dom  `russia_id'  russia_dom
run_one log_pub_intl `russia_id'  russia_intl
run_one log_pub_dom  `ukraine_id' ukraine_dom
run_one log_pub_intl `ukraine_id' ukraine_intl

* Report average post-treatment effects (2022--2024) and fit quality.
foreach tag in russia_dom russia_intl ukraine_dom ukraine_intl {
    use "`tag'_synth.dta", clear
    quietly summarize avg_effect
    local eff : display %5.1f r(mean)
    quietly summarize pre_rmspe
    local prr : display %6.4f r(mean)
    quietly summarize rmspe_ratio
    local rr : display %5.2f r(mean)
    di as text "`tag': avg post-2022 effect = `eff'%, pre-RMSPE = `prr', RMSPE ratio = `rr'"
}

* Merge Ukraine components for plotting. Keep log-scale actual/synthetic too,
* so the figure can compute the geometric average effect exp(mean(logA-logS))-1.
use "ukraine_dom_synth.dta", clear
keep Year actual synthetic actual_real synthetic_real gap_pct
rename (actual synthetic actual_real synthetic_real gap_pct) ///
    (dom_actual dom_synthetic dom_actual_real dom_synthetic_real dom_gap_pct)
merge 1:1 Year using "ukraine_intl_synth.dta", nogenerate ///
    keepusing(actual synthetic actual_real synthetic_real gap_pct)
rename (actual synthetic actual_real synthetic_real gap_pct) ///
    (intl_actual intl_synthetic intl_actual_real intl_synthetic_real intl_gap_pct)
sort Year
export excel using "ukraine_dom_intl_2022_merged.xlsx", firstrow(variables) replace

use "russia_dom_synth.dta", clear
keep Year actual synthetic actual_real synthetic_real gap_pct
rename (actual synthetic actual_real synthetic_real gap_pct) ///
    (dom_actual dom_synthetic dom_actual_real dom_synthetic_real dom_gap_pct)
merge 1:1 Year using "russia_intl_synth.dta", nogenerate ///
    keepusing(actual synthetic actual_real synthetic_real gap_pct)
rename (actual synthetic actual_real synthetic_real gap_pct) ///
    (intl_actual intl_synthetic intl_actual_real intl_synthetic_real intl_gap_pct)
sort Year
export excel using "russia_dom_intl_2022_merged.xlsx", firstrow(variables) replace

