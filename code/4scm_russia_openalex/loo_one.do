* Leave-one-out SCM: drop one donor, re-estimate treated unit + placebo.
* Called as: do loo_one.do "EXCL"   e.g. do loo_one.do "IDN"
* Expects globals set by caller, or defaults below for Russia.
args EXCL

if "`EXCL'"=="" {
    display as error "usage: do loo_one.do EXCL_ISO3"
    exit 198
}

* Caller should set DIR, TRTISO, OUTPREFIX before running; else Russia defaults.
if "$DIR"=="" {
    global DIR "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/4scm_russia_openalex"
}
if "$TRTISO"=="" {
    global TRTISO "RUS"
}
if "$OUTPREFIX"=="" {
    global OUTPREFIX "scm_russia"
}

cap mkdir "$DIR/results"
cap mkdir "$DIR/results/loo"

import delimited "$DIR/scm_panel.csv", clear varnames(1)
drop if country=="`EXCL'"

encode country, gen(cid)
tsset cid year
gen inflow = number_of_inmigrations

summarize cid if country=="$TRTISO", meanonly
global TRT = r(min)

* Point estimate (nested) — for ATT / weights
cap frame drop scm_loo_main
synth2 inflow ///
    inflow(2005(1)2009) inflow(2010(1)2014) inflow(2015(1)2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2005(1)2021) mspeperiod(2005(1)2021) ///
    nested ///
    frame(scm_loo_main) nofigure

display _n "=== LOO drop `EXCL' nested done ==="

* Placebo for MSPE-ratio p (no nested)
cap frame drop scm_loo
synth2 inflow ///
    inflow(2005(1)2009) inflow(2010(1)2014) inflow(2015(1)2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2005(1)2021) mspeperiod(2005(1)2021) ///
    placebo(unit) frame(scm_loo) nofigure

frame scm_loo {
    export delimited "$DIR/results/loo/${OUTPREFIX}_loo_drop_`EXCL'.csv", replace
}

display _n "✅ LOO drop `EXCL' -> results/loo/${OUTPREFIX}_loo_drop_`EXCL'.csv"
