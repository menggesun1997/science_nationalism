*===========================================================*
* 99_combine_figure1.do
* Figure 1 layout: drop EU panels, put UK first, row labels at left
*===========================================================*
clear all
set more off

* ── Path resolution ──────────────────────────────────────────────────────
* Sets $ROOT, $CODE, $PAPER and the shared colour palette via code/config.do,
* so no absolute path appears below. Resolution order:
*   1. $CODE already set by a calling master do-file
*   2. $SCIENCE_NATIONALISM_ROOT environment variable
*   3. walk up from the working directory looking for code/config.do
* If none succeed, set it manually once per session:
*   global ROOT "/path/to/sicence nationism"
*   do "$ROOT/code/config.do"
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
        di as error "or define global ROOT before running this file. See README.md."
        exit 601
    }
    do "`_cfg'"
}

cd "$CODE"

capture set scheme white_tableau
capture graph set window fontface "Arial"
graph set eps fontface "Arial"

global C_SHADE "238 238 238"
global C_GREY  "85 85 85"

local gph_dir "$CODE/figures/gph"
local out_dir "$CODE/figures"

local missing 0
foreach p in c d c2 d2 e f g h i j k l {
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
    local label = cond("`row'" == "brexit", "Brexit", cond("`row'" == "crimea", "Crimea crisis", "Russia-Ukraine war"))
    twoway scatter y x, msymbol(none) ///
        text(1 1.05 "{bf:`label'}", size(medium) orientation(vertical)) ///
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

* Horizontal legend strip, drawn once and placed as a short full-width row
* at the bottom of the figure.
twoway ///
    (rarea lo hi x if inrange(x,2,4), color("${C_SHADE}%60") lwidth(none)) ///
    (connected actual x, lpattern(solid) lcolor("${C_GREY}") lwidth(medthick) msymbol(O) msize(tiny) mcolor("${C_GREY}") mlcolor("${C_GREY}") mlwidth(vthin)) ///
    (connected synth x, lpattern(dash) lcolor("${C_GREY}") lwidth(medthick) msymbol(O) msize(tiny) mcolor("${C_GREY}") mlcolor("${C_GREY}") mlwidth(vthin)) ///
    (connected intv x, lpattern(shortdash) lcolor("${C_GREY}") lwidth(thin) msymbol(none)) ///
    , ///
    legend(order(2 "Actual (observed)" 3 "Synthetic counterfactual" ///
                 1 "Post-treatment period" 4 "Intervention year") ///
           rows(1) size(medsmall) region(lstyle(none)) symxsize(8) ///
           position(6)) ///
    xscale(off) yscale(off) fysize(12) ///
    graphregion(color(white)) plotregion(margin(zero) lstyle(none)) ///
    name(legend_panel, replace)
graph save "`gph_dir'/legend_panel.gph", replace

* Row 1 carries both Brexit dates (2016 referendum and 2021 formal exit).
* The grid is now 5 columns (row label + 4 panels) with no empty cells, and
* the legend is stacked underneath as a short strip via a nested combine.
graph combine ///
    "`gph_dir'/row_brexit.gph" ///
    "`gph_dir'/panel_c.gph" "`gph_dir'/panel_d.gph" ///
    "`gph_dir'/panel_c2.gph" "`gph_dir'/panel_d2.gph" ///
    "`gph_dir'/row_crimea.gph" ///
    "`gph_dir'/panel_e.gph" "`gph_dir'/panel_f.gph" ///
    "`gph_dir'/panel_g.gph" "`gph_dir'/panel_h.gph" ///
    "`gph_dir'/row_war.gph" ///
    "`gph_dir'/panel_i.gph" "`gph_dir'/panel_j.gph" ///
    "`gph_dir'/panel_k.gph" "`gph_dir'/panel_l.gph" ///
    , ///
    cols(5) ///
    iscale(0.62) imargin(tiny) ///
    graphregion(color(white) margin(l=2 r=3 t=3 b=1)) ///
    name(figure1_grid, replace)
graph save "`gph_dir'/figure1_grid.gph", replace

graph combine ///
    "`gph_dir'/figure1_grid.gph" "`gph_dir'/legend_panel.gph" ///
    , ///
    cols(1) imargin(zero) ///
    graphregion(color(white) margin(zero)) ///
    name(figure1, replace)
graph display figure1, ysize(11) xsize(18)
graph export "`out_dir'/figure1.pdf", replace
graph export "`out_dir'/figure1.png", replace width(3800)
graph close _all

di as result "Figure 1 saved to `out_dir'/figure1.pdf"
