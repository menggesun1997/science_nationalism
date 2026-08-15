* Export nested main estimate frame only (no placebo), for plotting AVG EFFECT.
clear all
set more off
global DIR "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/4scm_russia_openalex"
cap mkdir "$DIR/results"

import delimited "$DIR/scm_panel.csv", clear varnames(1)
encode country, gen(cid)
tsset cid year
gen inflow = number_of_inmigrations

summarize cid if country=="RUS", meanonly
global TRT = r(min)

cap frame drop scm_rus_main
synth2 inflow ///
    inflow(2005(1)2009) inflow(2010(1)2014) inflow(2015(1)2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2005(1)2021) mspeperiod(2005(1)2021) ///
    nested ///
    frame(scm_rus_main) nofigure

frame scm_rus_main {
    export delimited "$DIR/results/scm_russia_nested_frame.csv", replace
}
display _n "✅ nested frame -> results/scm_russia_nested_frame.csv"
