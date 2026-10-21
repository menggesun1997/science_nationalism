********************************************************************************
* EU-donor robustness for Brexit (treated unit: UK)
*
* The main Brexit SCM deliberately excludes the 27 EU member states from the
* donor pool (it runs on brexit_non_eu.xlsx). A natural concern is whether the
* estimated UK effect is an artefact of that donor-selection choice. This
* script re-estimates the synthetic UK on the SAME data, predictors and
* pre-treatment window, changing ONLY the donor pool:
*
*   base : 17 non-EU donors (reproduces the main-text donor pool)
*   eu   : 44 donors = the same 17 non-EU donors PLUS the 27 EU members
*
* Because we reuse code/01_scm_crimea_2014/original_completed.xlsx, which
* contains UK + the 27 EU members + the 17 non-EU donors (45 units total),
* both pools are drawn from one consistent panel and the only thing that moves
* between the two runs is whether EU members are admitted as controls.
*
* Outcomes: log total publications and the international-collaboration ratio,
* matching the main specification (trperiod 2016, xperiod 2008-2015,
* nested allopt). Writes one tidy xlsx per outcome with the observed series and
* both synthetic series to results/, for plotting by plot_eu_donor.py.
*
* Usage (from repo root):
*   "C:\Program Files\Stata18\StataMP-64.exe" -b do code/08_eu_donor_robustness/eu_donor_brexit.do
********************************************************************************
clear all
set more off

* ── Path resolution (config.do sets $ROOT, $CODE, colours) ─────────────────
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
        di as error "Cannot locate code/config.do. Set SCIENCE_NATIONALISM_ROOT."
        exit 601
    }
    do "`_cfg'"
}

local OUTDIR "$CODE/08_eu_donor_robustness/results"
cap mkdir "`OUTDIR'"
cd "$CODE/08_eu_donor_robustness"

* ── EU member states (27), used to split the donor pool ────────────────────
global EU27 "AUSTRIA BELGIUM BULGARIA CROATIA CYPRUS CZECHIA DENMARK ESTONIA FINLAND FRANCE GERMANY GREECE HUNGARY IRELAND ITALY LATVIA LITHUANIA LUXEMBOURG MALTA NETHERLANDS POLAND PORTUGAL ROMANIA SLOVAK_REPUBLIC SLOVENIA SPAIN SWEDEN"

* ── 1. Load the full 45-country panel and build variables ──────────────────
* original_completed.xlsx = UK + 27 EU members + 17 non-EU donors, 2005-2024.
import excel "$CODE/01_scm_crimea_2014/original_completed.xlsx", ///
    sheet("Sheet1") firstrow clear

local treated_year 2016
local before_treated_year 2015
local pre_period_start 2008

replace Country = subinstr(Country, " ", "_", .)
levelsof Country, local(countries) clean

gen country_id = .
local i = 1
foreach country of local countries {
    replace country_id = `i' if Country == "`country'"
    local ++i
}
xtset country_id Year

* Outcomes and predictors, defined exactly as in the main Brexit scripts.
gen log_pub_total = log(pub_total + 1)
capture confirm variable intl_ratio
if _rc  gen double intl_ratio = pub_intl / pub_total if pub_total > 0
else    replace  intl_ratio = pub_intl / pub_total if pub_total > 0

* pre-treatment mean predictors
bysort country_id: egen log_pub_pre_mean_uk = mean(log_pub_total) ///
    if Year >= 2005 & Year <= 2012
bysort country_id: egen log_pub_pre_mean_uk_final = max(log_pub_pre_mean_uk)
bysort country_id: egen intl_ratio_mean = mean(intl_ratio) ///
    if Year >= 2005 & Year <= 2015
bysort country_id: egen intl_ratio_mean_final = max(intl_ratio_mean)
drop log_pub_pre_mean_uk intl_ratio_mean

save "`OUTDIR'/processed_data.dta", replace

* ── 2. Resolve treated + donor IDs for each pool ───────────────────────────
qui sum country_id if Country == "UNITED_KINGDOM"
local uk_id = r(mean)

* base pool = every donor that is NOT the UK and NOT an EU member
* eu   pool = every donor that is NOT the UK (EU members admitted)
local base_ids ""
local eu_ids   ""
foreach country of local countries {
    if "`country'" == "UNITED_KINGDOM" continue
    qui sum country_id if Country == "`country'"
    local id = r(mean)
    local eu_ids "`eu_ids' `id'"
    local is_eu = 0
    foreach m of global EU27 {
        if "`country'" == "`m'" local is_eu = 1
    }
    if !`is_eu' local base_ids "`base_ids' `id'"
}
di as text "Base (non-EU) donor pool: `: word count `base_ids'' units"
di as text "EU-inclusive donor pool : `: word count `eu_ids'' units"

* ── 3. Estimation helper: run synth for one outcome + one pool ─────────────
* Reads processed_data.dta fresh, fits the synthetic UK, and returns a tidy
* per-year file `synth_`tag'.dta' with columns Year + <tag>_synth (and, on the
* first call for an outcome, the observed series uk_actual).
capture program drop run_scm
program define run_scm
    args outcome preds tag pool trunit outdir
    use "`outdir'/processed_data.dta", clear
    capture noisily {
        synth `outcome' `preds' , ///
            trunit(`trunit') trperiod(2016) ///
            counit(`pool') ///
            xperiod(2008(1)2015) ///
            nested allopt ///
            keep(_scm_`tag', replace)
    }
    use _scm_`tag', clear
    rename _time Year
    rename _Y_synthetic `tag'_synth
    rename _Y_treated   `tag'_actual
    keep Year `tag'_synth `tag'_actual
    keep if !missing(Year)
    save "`outdir'/synth_`tag'.dta", replace
    erase _scm_`tag'.dta
end

* ── 4. Total publications: base vs EU-inclusive donor pool ─────────────────
local uk_pred_total "log_pub_pre_mean_uk_final log_pub_total(2013)"
run_scm log_pub_total "`uk_pred_total'" tot_base "`base_ids'" `uk_id' "`OUTDIR'"
run_scm log_pub_total "`uk_pred_total'" tot_eu   "`eu_ids'"   `uk_id' "`OUTDIR'"

use "`OUTDIR'/synth_tot_base.dta", clear
merge 1:1 Year using "`OUTDIR'/synth_tot_eu.dta", nogen
* back-transform log outcome to publication counts for a readable figure
gen actual        = exp(tot_base_actual) - 1
gen synth_base    = exp(tot_base_synth)  - 1
gen synth_eu      = exp(tot_eu_synth)    - 1
keep Year actual synth_base synth_eu
order Year actual synth_base synth_eu
sort Year
export excel using "`OUTDIR'/eu_donor_brexit_total.xlsx", ///
    firstrow(variables) replace

* ── 5. International-collaboration ratio: base vs EU-inclusive ─────────────
local uk_pred_ratio "intl_ratio_mean_final intl_ratio(2015) intl_ratio(2014) intl_ratio(2011) intl_ratio(2010)"
run_scm intl_ratio "`uk_pred_ratio'" rat_base "`base_ids'" `uk_id' "`OUTDIR'"
run_scm intl_ratio "`uk_pred_ratio'" rat_eu   "`eu_ids'"   `uk_id' "`OUTDIR'"

use "`OUTDIR'/synth_rat_base.dta", clear
merge 1:1 Year using "`OUTDIR'/synth_rat_eu.dta", nogen
gen actual     = rat_base_actual
gen synth_base = rat_base_synth
gen synth_eu   = rat_eu_synth
keep Year actual synth_base synth_eu
order Year actual synth_base synth_eu
sort Year
export excel using "`OUTDIR'/eu_donor_brexit_ratio.xlsx", ///
    firstrow(variables) replace

di as text "==============================================================="
di as text "EU-donor robustness (Brexit / UK) complete."
di as text "  results/eu_donor_brexit_total.xlsx"
di as text "  results/eu_donor_brexit_ratio.xlsx"
di as text "==============================================================="
