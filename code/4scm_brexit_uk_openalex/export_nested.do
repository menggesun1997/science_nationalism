* Export nested main estimate frame only (no placebo), for plotting AVG EFFECT.
clear all
set more off
global DIR "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/4scm_brexit_uk_openalex"
cap mkdir "$DIR/results"

import delimited "$DIR/scm_panel.csv", clear varnames(1)
encode country, gen(cid)
tsset cid year
gen inflow = number_of_inmigrations

summarize cid if country=="GBR", meanonly
global TRT = r(min)

cap frame drop scm_gbr_main
synth2 inflow ///
    inflow(2005(1)2008) inflow(2009(1)2012) inflow(2013(1)2014) ///
    inflow(2015), ///
    trunit($TRT) trperiod(2016) ///
    xperiod(2005(1)2015) mspeperiod(2005(1)2015) ///
    nested ///
    frame(scm_gbr_main) nofigure

frame scm_gbr_main {
    export delimited "$DIR/results/scm_brexit_uk_nested_frame.csv", replace
}
display _n "✅ nested frame -> results/scm_brexit_uk_nested_frame.csv"
