*==============================================================================
* pair-trend robustness to pre-window start year.
* Test whether starting the fit in 2015 / 2016 cures the over-fitting that
* collapsed EU to -7.7% on the full 2012-2024 window.
*==============================================================================
clear all
set more off
local here "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/02_ppml_partners_russia/dyad_ppml"
cd "`here'"

capture which ppml_panel_sg
if _rc ssc install ppml_panel_sg, replace
capture which hdfe
if _rc ssc install hdfe, replace

log using "pairtrend_windows.log", replace text

foreach y0 in 2012 2015 2016 {
    import delimited "stata_pairtrend_panel.csv", clear varnames(1)
    destring paper_count ru post year t pru_* focal_id partner_id pair_id, replace force
    keep if year >= `y0'

    di as result "================ window `y0'-2024 (pair-trend) ================"
    ppml_panel_sg paper_count pru_eu pru_north_america pru_asia ///
        pru_china pru_other, ///
        ex(partner_id) im(focal_id) y(year) trend cluster(pair_id)

    foreach v in pru_eu pru_north_america pru_asia pru_china pru_other {
        capture local coef = _b[`v']
        if _rc continue
        local pc = (exp(`coef')-1)*100
        di as txt "  `v': exp(b)-1 = " as result %6.1f `pc' as txt "%"
    }
}

log close
di as result "WINDOWS_DONE"
