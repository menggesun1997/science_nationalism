*==============================================================================
* Plan 1: pair-specific linear trends via ppml_panel_sg (Correia-Guimaraes-
* Zylkin). Group-specific 2022 breaks for the Russia dyadic PPML, main pool.
*
*   P_ijt = exp( a_ij + gamma_ij*t + mu_it
*                + sum_g beta_g * Post_t*RU_j*G_g(i) )
*
* ppml_panel_sg absorbs partner-by-year and focal-by-year FE, pair FE, and
* with the -trend- option adds pair-specific linear trends gamma_ij*t.
*==============================================================================
clear all
set more off

local here "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/02_ppml_partners_russia/dyad_ppml"
cd "`here'"

* ---- ensure ppml_panel_sg is available ----
capture which ppml_panel_sg
if _rc {
    di as txt "installing ppml_panel_sg ..."
    capture ssc install ppml_panel_sg, replace
}
capture which hdfe
if _rc {
    di as txt "installing hdfe ..."
    capture ssc install hdfe, replace
}

* ---- load exported panel ----
import delimited "stata_pairtrend_panel.csv", clear varnames(1)

destring paper_count ru post year t pru_* focal_id partner_id pair_id, replace force

* ppml_panel_sg needs exporter / importer / time ids.
* Map: exporter = partner i, importer = focal j, time = year.
* The pair is (partner, focal) = (ex, im). Trend is pair-specific.

log using "pairtrend_stata.log", replace text

*------------------------------------------------------------------
* (1) Group-specific 2022 break WITH pair-specific trends
*------------------------------------------------------------------
di as result "=== (1) pair-trend: group-specific beta_g ==="
ppml_panel_sg paper_count pru_eu pru_north_america pru_asia ///
    pru_china pru_other, ///
    ex(partner_id) im(focal_id) y(year) trend cluster(pair_id)

matrix b1 = e(b)
matrix V1 = e(V)

* report exp(beta)-1
foreach v in pru_eu pru_north_america pru_asia pru_china pru_other {
    capture local coef = _b[`v']
    if _rc continue
    local se   = _se[`v']
    local pc   = (exp(`coef')-1)*100
    local lo   = (exp(`coef'-1.96*`se')-1)*100
    local hi   = (exp(`coef'+1.96*`se')-1)*100
    di as txt "`v': exp(b)-1 = " as result %6.1f `pc' ///
       as txt "%  [" %5.1f `lo' ", " %5.1f `hi' "]"
}

*------------------------------------------------------------------
* (2) Same WITHOUT trend (simple), for comparison
*------------------------------------------------------------------
di as result "=== (2) no trend (simple) for comparison ==="
ppml_panel_sg paper_count pru_eu pru_north_america pru_asia ///
    pru_china pru_other, ///
    ex(partner_id) im(focal_id) y(year) cluster(pair_id)

foreach v in pru_eu pru_north_america pru_asia pru_china pru_other {
    local coef = _b[`v']
    local pc   = (exp(`coef')-1)*100
    di as txt "`v' (simple): exp(b)-1 = " as result %6.1f `pc' as txt "%"
}

log close

* ---- export tidy results of model (1) to CSV ----
preserve
    clear
    set obs 5
    gen str20 group = ""
    gen double pct = .
    gen double ci_lo = .
    gen double ci_hi = .
    gen double pval = .
    local i = 1
    foreach v in pru_eu pru_north_america pru_asia pru_china pru_other {
        replace group = "`v'" in `i'
        local ++i
    }
restore
di as result "done. see pairtrend_stata.log"
