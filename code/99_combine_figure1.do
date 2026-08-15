*===========================================================*
* 99_combine_figure1.do
* Figure 1 layout: drop EU panels, put UK first, row labels at left
*===========================================================*
clear all
set more off
capture set scheme white_tableau
capture graph set window fontface "Helvetica"
graph set eps fontface "Helvetica"

global C_SHADE "238 238 238"
global C_GREY  "85 85 85"

local gph_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/picutres/gph"
local out_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/picutres"

local missing 0
foreach p in c d e f g h i j k l {
    capture confirm file "`gph_dir'/panel_`p'.gph"
    if _rc {
        di as error "Missing: `gph_dir'/panel_`p'.gph"
        local missing = `missing' + 1
    }
}
if `missing' > 0 {
    di as error "`missing' panel .gph files missing -- run 99_redraw_panels.do first"
    exit 1
}

foreach row in brexit crimea war {
    clear
    set obs 1
    gen x = 1
    gen y = 1
    local label = cond("`row'" == "brexit", "Brexit referendum", cond("`row'" == "crimea", "Crimea crisis", "Russia-Ukraine war"))
    twoway scatter y x, msymbol(none) ///
        text(1 1.05 "{bf:`label'}", size(small) orientation(vertical)) ///
        xlabel(none, noticks) ylabel(none, noticks) ///
        xtitle("") ytitle("") ///
        xscale(range(0 2) noline) yscale(range(0 2) noline) ///
        graphregion(color(white) lcolor(white) margin(zero)) plotregion(color(white) lcolor(white) margin(zero)) ///
        legend(off) fxsize(7) name(row_`row', replace)
    graph save "`gph_dir'/row_`row'.gph", replace
}

clear
set obs 5
gen x = _n
gen actual = .
gen synth = .
gen intv = .
gen lo = .
gen hi = .

twoway ///
    (rarea lo hi x if inrange(x,2,4), color("${C_SHADE}%60") lwidth(none)) ///
    (connected actual x, lpattern(solid) lcolor("${C_GREY}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_GREY}") mlcolor("${C_GREY}") mlwidth(vthin)) ///
    (connected synth x, lpattern(dash) lcolor("${C_GREY}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_GREY}") mlcolor("${C_GREY}") mlwidth(vthin)) ///
    (connected intv x, lpattern(shortdash) lcolor("${C_GREY}") lwidth(thin) msymbol(none)) ///
    , ///
    legend(order(2 "Actual (observed)" 3 "Synthetic counterfactual" ///
                 1 "Post-treatment period" 4 "Intervention year") ///
           cols(1) size(small) region(lstyle(none)) symxsize(10)) ///
    xscale(off) yscale(off) ///
    graphregion(color(white)) plotregion(margin(zero) lstyle(none)) ///
    name(legend_panel, replace)
graph save "`gph_dir'/legend_panel.gph", replace

graph combine ///
    "`gph_dir'/row_brexit.gph" "`gph_dir'/panel_c.gph" "`gph_dir'/panel_d.gph" ///
    "`gph_dir'/legend_panel.gph" ///
    "`gph_dir'/row_crimea.gph" "`gph_dir'/panel_e.gph" "`gph_dir'/panel_g.gph" ///
    "`gph_dir'/panel_f.gph" "`gph_dir'/panel_h.gph" ///
    "`gph_dir'/row_war.gph" "`gph_dir'/panel_i.gph" "`gph_dir'/panel_k.gph" ///
    "`gph_dir'/panel_j.gph" "`gph_dir'/panel_l.gph" ///
    , ///
    cols(5) holes(5) ///
    iscale(0.64) imargin(tiny) ///
    xsize(11.72) ysize(8.6) ///
    graphregion(color(white) margin(l=2 r=5 t=3 b=3)) ///
    name(figure1, replace)
graph export "`out_dir'/figure1.pdf", replace
graph export "`out_dir'/figure1.png", replace width(3800)
graph close _all

di as result "Figure 1 saved to `out_dir'/figure1.pdf"
