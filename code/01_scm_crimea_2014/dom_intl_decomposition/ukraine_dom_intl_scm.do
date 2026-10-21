clear all
set more off

********************************************************************************
* Ukraine domestic vs international publication SCM decomposition
*
* Motivation: Ukraine's post-2014 international collaboration ratio rises, but
* the aggregate ratio is a quotient and can climb purely because the domestic
* denominator is shrinking. Splitting total publications into domestic
* (= total - international) and international (co-authored) counts, and running
* SCM on each, distinguishes two possibilities:
*   - a compositional rise: domestic output falls while international output is
*     flat or also falling (the ratio rises with no absolute gain abroad), or
*   - a genuine widening: international output rises in absolute terms.
*
* This script mirrors the donor pool, fitting window and control variables of
* russia_dom_intl_scm.do, changing only the treated unit to Ukraine.
********************************************************************************

* -- Path resolution (same pattern as russia_dom_intl_scm.do) --------------
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

cd "$CODE/01_scm_crimea_2014/dom_intl_decomposition"

local src "$CODE/01_scm_crimea_2014/original_completed.xlsx"
import excel "`src'", sheet("Sheet1") firstrow clear

local treated_year 2014
local before_treated_year 2013
local post_end_year 2021

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

* Persist country_id <-> Country mapping so weights can be labeled later.
preserve
    keep country_id Country
    duplicates drop
    save "country_names_ukr.dta", replace
restore

local control_ids ""
foreach country of local countries {
    if !inlist("`country'", "RUSSIAN_FEDERATION", "UKRAINE") {
        qui sum country_id if Country == "`country'"
        local control_ids "`control_ids' `r(mean)'"
    }
}
qui sum country_id if Country == "UKRAINE"
local ukraine_id = r(mean)

* Outcome variables on the log scale, matching russia_dom_intl_scm.do.
gen log_pub_dom  = log(pub_dom + 1)
gen log_pub_intl = log(pub_intl + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)
gen log_gdp_per_capita_10 = log_gdp_per_capita / 10
gen log_rp_10 = log_rp / 10

global control_vars "log_gdp_per_capita_10 log_rp_10 RD"

save "processed_data_ukr.dta", replace

********************************************************************************
* Ukraine SCM: DOMESTIC publications
********************************************************************************
use "processed_data_ukr.dta", clear
synth log_pub_dom ///
    $control_vars ///
    log_pub_dom(2013) log_pub_dom(2012) log_pub_dom(2010) log_pub_dom(2009) log_pub_dom(2008) , ///
    trunit(`ukraine_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(2008(1)`before_treated_year') ///
    nested ///
    keep(ukraine_dom_results, replace)

* Export donor weights (domestic outcome) with country labels.
matrix W_dom = e(W_weights)
preserve
    clear
    svmat W_dom, names(col)
    rename _Co_Number country_id
    rename _W_Weight weight
    merge m:1 country_id using "country_names_ukr.dta", keep(match) nogenerate
    gsort -weight
    keep Country country_id weight
    export excel using "ukraine_dom_weights.xlsx", firstrow(variables) replace
restore

use ukraine_dom_results, clear
rename _time Year
rename _Y_treated dom_actual
rename _Y_synthetic dom_synthetic
gen dom_gap = dom_actual - dom_synthetic
gen dom_actual_real = exp(dom_actual) - 1
gen dom_synthetic_real = exp(dom_synthetic) - 1
gen dom_gap_pct = (dom_actual_real - dom_synthetic_real) / dom_actual_real * 100
egen dom_avg_effect = mean(dom_gap_pct) if Year >= `treated_year' & Year <= `post_end_year'
drop if missing(Year)
save "ukraine_dom_synth.dta", replace

********************************************************************************
* Ukraine SCM: INTERNATIONAL publications
********************************************************************************
use "processed_data_ukr.dta", clear
synth log_pub_intl ///
    $control_vars ///
    log_pub_intl(2013) log_pub_intl(2012) log_pub_intl(2010) log_pub_intl(2009) log_pub_intl(2008) , ///
    trunit(`ukraine_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(2008(1)`before_treated_year') ///
    nested ///
    keep(ukraine_intl_results, replace)

* Export donor weights (international outcome) with country labels.
matrix W_intl = e(W_weights)
preserve
    clear
    svmat W_intl, names(col)
    rename _Co_Number country_id
    rename _W_Weight weight
    merge m:1 country_id using "country_names_ukr.dta", keep(match) nogenerate
    gsort -weight
    keep Country country_id weight
    export excel using "ukraine_intl_weights.xlsx", firstrow(variables) replace
restore

use ukraine_intl_results, clear
rename _time Year
rename _Y_treated intl_actual
rename _Y_synthetic intl_synthetic
gen intl_gap = intl_actual - intl_synthetic
gen intl_actual_real = exp(intl_actual) - 1
gen intl_synthetic_real = exp(intl_synthetic) - 1
gen intl_gap_pct = (intl_actual_real - intl_synthetic_real) / intl_actual_real * 100
egen intl_avg_effect = mean(intl_gap_pct) if Year >= `treated_year' & Year <= `post_end_year'
drop if missing(Year)
save "ukraine_intl_synth.dta", replace

********************************************************************************
* Merge, report average post-treatment effects, export for plotting
********************************************************************************
use "ukraine_dom_synth.dta", clear
keep Year dom_actual dom_synthetic dom_gap dom_actual_real dom_synthetic_real dom_gap_pct dom_avg_effect
merge 1:1 Year using "ukraine_intl_synth.dta", nogenerate ///
    keepusing(intl_actual intl_synthetic intl_gap intl_actual_real intl_synthetic_real intl_gap_pct intl_avg_effect)
sort Year
save "ukraine_dom_intl_merged.dta", replace
export excel using "ukraine_dom_intl_merged.xlsx", firstrow(variables) replace

quietly summarize dom_avg_effect
local d : display %4.1f r(mean)
quietly summarize intl_avg_effect
local n : display %4.1f r(mean)
di as text "==============================================================="
di as text "Ukraine average post-treatment effect (2014-2021), log-scale SCM"
di as text "  Domestic publications:      `d'%"
di as text "  International publications: `n'%"
di as text "==============================================================="


