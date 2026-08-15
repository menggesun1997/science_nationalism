*===========================================================*
* 99_redraw_panels.do
* 从已保存的 synth 结果 .dta 重绘 12 个 panel
* 配色：Science earthy；connected lines；treatment effect 框在左上
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

capture set scheme white_tableau
capture graph set window fontface "Helvetica"
graph set eps fontface "Helvetica"

global C_EU    "31 78 121"      // #1F4E79 Navy
global C_UK    "181 72 42"      // #B5482A Rust
global C_RU    "91 117 83"      // #5B7553 Olive
global C_UA    "210 162 76"     // #D2A24C Mustard
global C_SHADE "238 238 238"    // #EEEEEE
global C_LINE  "68 68 68"       // #444444
global C_GREY  "85 85 85"       // #555555

local gph_dir "$CODE/picutres/gph"
capture mkdir "`gph_dir'"

*===========================================================*
*  ROW 1: Brexit – Total Publications (panels a, c)
*===========================================================*
local d1 "$CODE/Brexit-stata_external_try/total_publications"
local treated_year 2016
local x_start_year 2005

use "`d1'/eu_synth_results.dta", clear
drop _Co_Number _W_Weight
merge 1:1 Year using "`d1'/uk_synth_results.dta", nogenerate keepusing(Year uk_actual_real uk_synthetic_real uk_gap_pct rmspe_ratio_uk)

qui sum Year
local max_year = r(max)

gen eu_actual_k    = eu_actual_real    / 1000
gen eu_synthetic_k = eu_synthetic_real / 1000
gen uk_actual_k    = uk_actual_real    / 1000
gen uk_synthetic_k = uk_synthetic_real / 1000

local y_lo_eu   0
local y_hi_eu   30
local y_step_eu 10
local y_lo_uk   0
local y_hi_uk   200
local y_step_uk 50

gen _slo_eu = `y_lo_eu'
gen _shi_eu = `y_hi_eu'
gen _slo_uk = `y_lo_uk'
gen _shi_uk = `y_hi_uk'

* Panel a
sum rmspe_ratio_eu
local rmspe : display %4.2f r(mean)
sum eu_gap_pct if Year >= `treated_year'
local att_val : display %4.2f r(mean)

twoway ///
    (rarea _slo_eu _shi_eu Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected eu_synthetic_k Year, lpattern(dash)  lcolor("${C_EU}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_EU}") mlcolor("${C_EU}") mlwidth(vthin)) ///
    (connected eu_actual_k    Year, lpattern(solid) lcolor("${C_EU}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_EU}") mlcolor("${C_EU}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_eu' + (`y_hi_eu'-`y_lo_eu')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:EU · Total publications}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("Publications (×1,000)", size(small)) xtitle("") ///
    xlabel(2005 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(`y_lo_eu'(`y_step_eu')`y_hi_eu', angle(0) format(%4.0f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_eu' `y_hi_eu') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_a, replace)
graph save "`gph_dir'/panel_a.gph", replace

* Panel c
sum rmspe_ratio_uk
local rmspe : display %4.2f r(mean)
sum uk_gap_pct if Year >= `treated_year'
local att_val : display %4.2f r(mean)

twoway ///
    (rarea _slo_uk _shi_uk Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected uk_synthetic_k Year, lpattern(dash)  lcolor("${C_UK}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_UK}") mlcolor("${C_UK}") mlwidth(vthin)) ///
    (connected uk_actual_k    Year, lpattern(solid) lcolor("${C_UK}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_UK}") mlcolor("${C_UK}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_uk' + (`y_hi_uk'-`y_lo_uk')*1.18' `=`x_start_year'-0.7' "{bf:a}", ///
        size(medium) color(black) placement(w)) ///
    text(`=`y_lo_uk' + (`y_hi_uk'-`y_lo_uk')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:UK · Total publications}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("Publications (×1,000)", size(small)) xtitle("") ///
    xlabel(2005 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(`y_lo_uk'(`y_step_uk')`y_hi_uk', angle(0) format(%4.0f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_uk' `y_hi_uk') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_c, replace)
graph save "`gph_dir'/panel_c.gph", replace
drop eu_actual_k eu_synthetic_k uk_actual_k uk_synthetic_k _slo_eu _shi_eu _slo_uk _shi_uk

*===========================================================*
*  ROW 1: Brexit – Intl. Ratio (panels b, d)
*===========================================================*
local d2 "$CODE/Brexit-stata_external_try/intl_ratio"

use "`d2'/eu_synth_results.dta", clear
drop _Co_Number _W_Weight
merge 1:1 Year using "`d2'/uk_synth_results.dta", nogenerate keepusing(Year uk_actual uk_synthetic uk_gap rmspe_ratio_uk)

qui sum Year
local min_year = r(min)
local max_year = r(max)

local y_lo_b  0.25
local y_hi_b  0.45
local y_step_b 0.05
local y_lo_d  0.40
local y_hi_d  0.75
local y_step_d 0.05

gen _slo_b = `y_lo_b'
gen _shi_b = `y_hi_b'
gen _slo_d = `y_lo_d'
gen _shi_d = `y_hi_d'

* Panel b
sum rmspe_ratio_eu
local rmspe : display %4.2f r(mean)
sum eu_gap if Year >= `treated_year'
local att_val : display %4.2f (r(mean)*100)

twoway ///
    (rarea _slo_b _shi_b Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected eu_synthetic Year, lpattern(dash)  lcolor("${C_EU}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_EU}") mlcolor("${C_EU}") mlwidth(vthin)) ///
    (connected eu_actual    Year, lpattern(solid) lcolor("${C_EU}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_EU}") mlcolor("${C_EU}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_b' + (`y_hi_b'-`y_lo_b')*0.92' `=`min_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("b   EU · Intl. publication ratio", size(small) justification(left) position(11) margin(b=2)) ///
    ytitle("Intl. publication ratio", size(small)) xtitle("") ///
    xlabel(2005 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(`y_lo_b'(`y_step_b')`y_hi_b', angle(0) format(%4.2f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_b' `y_hi_b') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_b, replace)
graph save "`gph_dir'/panel_b.gph", replace

* Panel d
sum rmspe_ratio_uk
local rmspe : display %4.2f r(mean)
sum uk_gap if Year >= `treated_year'
local att_val : display %4.2f (r(mean)*100)

twoway ///
    (rarea _slo_d _shi_d Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected uk_synthetic Year, lpattern(dash)  lcolor("${C_UK}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_UK}") mlcolor("${C_UK}") mlwidth(vthin)) ///
    (connected uk_actual    Year, lpattern(solid) lcolor("${C_UK}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_UK}") mlcolor("${C_UK}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_d' + (`y_hi_d'-`y_lo_d')*1.18' `=`min_year'-0.7' "{bf:b}", ///
        size(medium) color(black) placement(w)) ///
    text(`=`y_lo_d' + (`y_hi_d'-`y_lo_d')*0.92' `=`min_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:UK · Intl. ratio}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("Intl. publication ratio", size(small)) xtitle("") ///
    xlabel(2005 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(`y_lo_d'(`y_step_d')`y_hi_d', angle(0) format(%4.2f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_d' `y_hi_d') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_d, replace)
graph save "`gph_dir'/panel_d.gph", replace
drop _slo_b _shi_b _slo_d _shi_d

*===========================================================*
*  ROW 2: Crimea – Total Publications (panels e, g)
*===========================================================*
local d3 "$CODE/crimes/total_publications"
local treated_year 2014
local x_start_year 2005

use "`d3'/russia_synth_results.dta", clear
drop _Co_Number _W_Weight
merge 1:1 Year using "`d3'/ukraine_synth_results.dta", nogenerate keepusing(Year ukraine_actual_real ukraine_synthetic_real ukraine_gap_pct rmspe_ratio_ukraine)

qui sum Year
local max_year = r(max)

gen russia_actual_k    = russia_actual_real    / 1000
gen russia_synthetic_k = russia_synthetic_real / 1000
gen ukraine_actual_k   = ukraine_actual_real   / 1000
gen ukraine_synthetic_k= ukraine_synthetic_real/ 1000

local y_lo_ru   0
local y_hi_ru   60
local y_step_ru 10
local y_lo_ua   0
local y_hi_ua   12
local y_step_ua  3

gen _slo_ru = `y_lo_ru'
gen _shi_ru = `y_hi_ru'
gen _slo_ua = `y_lo_ua'
gen _shi_ua = `y_hi_ua'

* Panel e
sum rmspe_ratio_russia
local rmspe : display %4.2f r(mean)
sum russia_gap_pct if Year >= `treated_year'
local att_val : display %4.2f r(mean)

twoway ///
    (rarea _slo_ru _shi_ru Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected russia_synthetic_k Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_RU}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    (connected russia_actual_k    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_RU}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*1.18' `=`x_start_year'-0.7' "{bf:c}", ///
        size(medium) color(black) placement(w)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Russia · Total publications}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("Publications (×1,000)", size(small)) xtitle("") ///
    xlabel(`x_start_year' 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ru'(`y_step_ru')`y_hi_ru', angle(0) format(%4.0f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ru' `y_hi_ru') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_e, replace)
graph save "`gph_dir'/panel_e.gph", replace

* Panel g
sum rmspe_ratio_ukraine
local rmspe : display %4.2f r(mean)
sum ukraine_gap_pct if Year >= `treated_year'
local att_val : display %4.2f r(mean)

twoway ///
    (rarea _slo_ua _shi_ua Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected ukraine_synthetic_k Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_UA}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    (connected ukraine_actual_k    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_UA}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ua' + (`y_hi_ua'-`y_lo_ua')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Ukraine · Total publications}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("") xtitle("") ///
    xlabel(`x_start_year' 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ua'(`y_step_ua')`y_hi_ua', angle(0) format(%4.0f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ua' `y_hi_ua') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_g, replace)
graph save "`gph_dir'/panel_g.gph", replace
drop russia_actual_k russia_synthetic_k ukraine_actual_k ukraine_synthetic_k _slo_ru _shi_ru _slo_ua _shi_ua

*===========================================================*
*  ROW 2: Crimea – Intl. Ratio (panels f, h)
*===========================================================*
local d4 "$CODE/crimes/intl_ratio"

use "`d4'/russia_synth_results.dta", clear
drop _Co_Number _W_Weight
merge 1:1 Year using "`d4'/ukraine_synth_results.dta", nogenerate keepusing(Year ukraine_actual ukraine_synthetic ukraine_gap rmspe_ratio_ukraine)

qui sum Year
local max_year = r(max)

local y_lo_ru  0.3
local y_hi_ru  0.8
local y_step_ru 0.1
local y_lo_ua  0.4
local y_hi_ua  0.8
local y_step_ua 0.1

gen _slo_ru = `y_lo_ru'
gen _shi_ru = `y_hi_ru'
gen _slo_ua = `y_lo_ua'
gen _shi_ua = `y_hi_ua'

* Panel f
sum rmspe_ratio_russia
local rmspe : display %4.2f r(mean)
sum russia_gap if Year >= 2014
local att_val : display %4.2f (r(mean)*100)

twoway ///
    (rarea _slo_ru _shi_ru Year if Year >= 2014 & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected russia_synthetic Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_RU}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    (connected russia_actual    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_RU}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    , ///
    xline(2014, lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*1.18' `=`x_start_year'-0.7' "{bf:d}", ///
        size(medium) color(black) placement(w)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Russia · Intl. ratio}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("Intl. publication ratio", size(small)) xtitle("") ///
    xlabel(`x_start_year' 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ru'(`y_step_ru')`y_hi_ru', angle(0) format(%4.2f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ru' `y_hi_ru') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_f, replace)
graph save "`gph_dir'/panel_f.gph", replace

* Panel h
sum rmspe_ratio_ukraine
local rmspe : display %4.2f r(mean)
sum ukraine_gap if Year >= 2014
local att_val : display %4.2f (r(mean)*100)

twoway ///
    (rarea _slo_ua _shi_ua Year if Year >= 2014 & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected ukraine_synthetic Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_UA}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    (connected ukraine_actual    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_UA}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    , ///
    xline(2014, lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ua' + (`y_hi_ua'-`y_lo_ua')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Ukraine · Intl. ratio}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("") xtitle("") ///
    xlabel(`x_start_year' 2010 2015 2020, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ua'(`y_step_ua')`y_hi_ua', angle(0) format(%4.2f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ua' `y_hi_ua') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_h, replace)
graph save "`gph_dir'/panel_h.gph", replace
drop _slo_ru _shi_ru _slo_ua _shi_ua

*===========================================================*
*  ROW 3: War – Total Publications (panels i, k)
*===========================================================*
local d5 "$CODE/crimes_2015_2022/total_publications"
local treated_year 2022
local x_start_year 2015

use "`d5'/russia_synth_results.dta", clear
drop _Co_Number _W_Weight
merge 1:1 Year using "`d5'/ukraine_synth_results.dta", nogenerate keepusing(Year ukraine_actual_real ukraine_synthetic_real ukraine_gap_pct rmspe_ratio_ukraine)

qui sum Year
local max_year = r(max)

gen russia_actual_k    = russia_actual_real    / 1000
gen russia_synthetic_k = russia_synthetic_real / 1000
gen ukraine_actual_k   = ukraine_actual_real   / 1000
gen ukraine_synthetic_k= ukraine_synthetic_real/ 1000

local y_lo_ru   0
local y_hi_ru   60
local y_step_ru 10
local y_lo_ua   0
local y_hi_ua   12
local y_step_ua  3

gen _slo_ru = `y_lo_ru'
gen _shi_ru = `y_hi_ru'
gen _slo_ua = `y_lo_ua'
gen _shi_ua = `y_hi_ua'

* Panel i
sum rmspe_ratio_russia
local rmspe : display %4.2f r(mean)
sum russia_gap_pct if Year >= `treated_year'
local att_val : display %4.2f r(mean)

twoway ///
    (rarea _slo_ru _shi_ru Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected russia_synthetic_k Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_RU}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    (connected russia_actual_k    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_RU}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*1.18' `=`x_start_year'-0.7' "{bf:e}", ///
        size(medium) color(black) placement(w)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Russia · Total publications}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("Publications (×1,000)", size(small)) xtitle("") ///
    xlabel(2016 2018 2020 2022 2024, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ru'(`y_step_ru')`y_hi_ru', angle(0) format(%4.0f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ru' `y_hi_ru') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_i, replace)
graph save "`gph_dir'/panel_i.gph", replace

* Panel k
sum rmspe_ratio_ukraine
local rmspe : display %4.2f r(mean)
sum ukraine_gap_pct if Year >= `treated_year'
local att_val : display %4.2f r(mean)

twoway ///
    (rarea _slo_ua _shi_ua Year if Year >= `treated_year' & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected ukraine_synthetic_k Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_UA}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    (connected ukraine_actual_k    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_UA}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ua' + (`y_hi_ua'-`y_lo_ua')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Ukraine · Total publications}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("") xtitle("") ///
    xlabel(2016 2018 2020 2022 2024, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ua'(`y_step_ua')`y_hi_ua', angle(0) format(%4.0f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ua' `y_hi_ua') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_k, replace)
graph save "`gph_dir'/panel_k.gph", replace
drop russia_actual_k russia_synthetic_k ukraine_actual_k ukraine_synthetic_k _slo_ru _shi_ru _slo_ua _shi_ua

*===========================================================*
*  ROW 3: War – Intl. Ratio (panels j, l)
*===========================================================*
local d6 "$CODE/crimes_2015_2022/intl_ratio"

use "`d6'/russia_synth_results.dta", clear
drop _Co_Number _W_Weight
merge 1:1 Year using "`d6'/ukraine_synth_results.dta", nogenerate keepusing(Year ukraine_actual ukraine_synthetic ukraine_gap rmspe_ratio_ukraine)

qui sum Year
local max_year = r(max)

local y_lo_ru  0.3
local y_hi_ru  0.8
local y_step_ru 0.1
local y_lo_ua  0.4
local y_hi_ua  0.8
local y_step_ua 0.1

gen _slo_ru = `y_lo_ru'
gen _shi_ru = `y_hi_ru'
gen _slo_ua = `y_lo_ua'
gen _shi_ua = `y_hi_ua'

* Panel j
sum rmspe_ratio_russia
local rmspe : display %4.2f r(mean)
sum russia_gap if Year >= 2022
local att_val : display %4.2f (r(mean)*100)

twoway ///
    (rarea _slo_ru _shi_ru Year if Year >= 2022 & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected russia_synthetic Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_RU}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    (connected russia_actual    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_RU}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_RU}") mlcolor("${C_RU}") mlwidth(vthin)) ///
    , ///
    xline(2022, lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*1.18' `=`x_start_year'-0.7' "{bf:f}", ///
        size(medium) color(black) placement(w)) ///
    text(`=`y_lo_ru' + (`y_hi_ru'-`y_lo_ru')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Russia · Intl. ratio}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("Intl. publication ratio", size(small)) xtitle("") ///
    xlabel(2016 2018 2020 2022 2024, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ru'(`y_step_ru')`y_hi_ru', angle(0) format(%4.2f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ru' `y_hi_ru') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_j, replace)
graph save "`gph_dir'/panel_j.gph", replace

* Panel l
sum rmspe_ratio_ukraine
local rmspe : display %4.2f r(mean)
sum ukraine_gap if Year >= 2022
local att_val : display %4.2f (r(mean)*100)

twoway ///
    (rarea _slo_ua _shi_ua Year if Year >= 2022 & Year <= `max_year', sort color("${C_SHADE}%60") lwidth(none)) ///
    (connected ukraine_synthetic Year if Year >= `x_start_year', lpattern(dash)  lcolor("${C_UA}") lwidth(medthick)  msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    (connected ukraine_actual    Year if Year >= `x_start_year', lpattern(solid) lcolor("${C_UA}") lwidth(medthick) msymbol(O) msize(vsmall) mcolor("${C_UA}") mlcolor("${C_UA}") mlwidth(vthin)) ///
    , ///
    xline(2022, lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`y_lo_ua' + (`y_hi_ua'-`y_lo_ua')*0.92' `=`x_start_year'+0.5' "Effect = `att_val'%", ///
        size(vsmall) box bcolor(white) bmargin(vsmall) justification(left) placement(e)) ///
    subtitle("{bf:Ukraine · Intl. ratio}", size(vsmall) justification(center) position(12) margin(b=2)) ///
    ytitle("") xtitle("") ///
    xlabel(2016 2018 2020 2022 2024, labsize(vsmall) nogrid tposition(inside)) xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ua'(`y_step_ua')`y_hi_ua', angle(0) format(%4.2f) labsize(vsmall) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ua' `y_hi_ua') noextend) xscale(range(`x_start_year' `max_year') noextend lcolor(black) lwidth(thin)) ///
    aspectratio(0.82) graphregion(color(white)) plotregion(margin(l=2 r=2 t=2 b=1)) ///
    legend(off) name(panel_l, replace)
graph save "`gph_dir'/panel_l.gph", replace
drop _slo_ru _shi_ru _slo_ua _shi_ua

di as result "=== 12 panels saved to `gph_dir' ==="
