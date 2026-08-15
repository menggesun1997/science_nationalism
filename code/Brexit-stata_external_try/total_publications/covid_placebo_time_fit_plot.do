clear all
set more off

********************************************************************************
* Plot actual vs synthetic fit for the Covid placebo-in-time test
*
* This file does not re-run synth. It uses the saved results from
* covid_placebo_time_test.do and draws the actual outcome against the fitted
* synthetic-control series, so the pre-2016 fit and post-period divergence are
* visible directly.
********************************************************************************

local base_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/Brexit-stata_external_try"
local test_dir "`base_dir'/total_publications/covid_placebo_time"

local brexit_year 2016
local covid_year 2020
local before_brexit_year 2015
local pre_period_start 2008

graph set window fontface "Helvetica"
set scheme s1color
graph set eps fontface "Helvetica"

********************************************************************************
* 1. Build pre-fit metrics
********************************************************************************

tempname fitstats
postfile `fitstats' str8 unit str16 model ///
    pre_rmspe_log pre_mean_abs_gap_pct pre_mean_gap_pct ///
    post_2016_2019_mean_gap_pct post_2020_end_mean_gap_pct ///
    using "`test_dir'/covid_placebo_time_fit_stats.dta", replace

foreach unit in uk eu {
    foreach model in brexit2016 covid2020_placebo {
        use "`test_dir'/`unit'_`model'_gap.dta", clear

        gen abs_gap_pct = abs(gap_pct)

        quietly summarize gap_log if inrange(Year, `pre_period_start', `before_brexit_year'), meanonly
        gen pre_sq_gap_log = gap_log^2 if inrange(Year, `pre_period_start', `before_brexit_year')
        quietly summarize pre_sq_gap_log, meanonly
        local pre_rmspe_log = sqrt(r(mean))

        quietly summarize abs_gap_pct if inrange(Year, `pre_period_start', `before_brexit_year'), meanonly
        local pre_mean_abs_gap_pct = r(mean)

        quietly summarize gap_pct if inrange(Year, `pre_period_start', `before_brexit_year'), meanonly
        local pre_mean_gap_pct = r(mean)

        quietly summarize gap_pct if inrange(Year, `brexit_year', `covid_year' - 1), meanonly
        local post_2016_2019_mean_gap_pct = r(mean)

        quietly summarize gap_pct if Year >= `covid_year', meanonly
        local post_2020_end_mean_gap_pct = r(mean)

        local unit_label = upper("`unit'")
        if "`model'" == "brexit2016" local model_label "Brexit 2016"
        if "`model'" == "covid2020_placebo" local model_label "Covid 2020"

        post `fitstats' ("`unit_label'") ("`model_label'") ///
            (`pre_rmspe_log') (`pre_mean_abs_gap_pct') (`pre_mean_gap_pct') ///
            (`post_2016_2019_mean_gap_pct') (`post_2020_end_mean_gap_pct')
    }
}

postclose `fitstats'

use "`test_dir'/covid_placebo_time_fit_stats.dta", clear
export excel using "`test_dir'/covid_placebo_time_fit_stats.xlsx", ///
    firstrow(variables) replace
list, noobs abbrev(24)

********************************************************************************
* 2. Draw actual vs synthetic levels for the Covid 2020 placebo model
********************************************************************************

use "`test_dir'/uk_covid2020_placebo_gap.dta", clear
gen _shade_lo = 0
gen _shade_hi = 200000

twoway ///
    (rarea _shade_lo _shade_hi Year if Year >= `covid_year', ///
        sort color("238 238 238%60") lwidth(none)) ///
    (line synthetic_real Year, lcolor("0 114 178") lpattern(dash) lwidth(medthick)) ///
    (line actual_real Year, lcolor("213 94 0") lpattern(solid) lwidth(thick)) ///
    , ///
    xline(`brexit_year', lpattern(shortdash) lcolor("120 120 120") lwidth(thin)) ///
    xline(`covid_year', lpattern(shortdash) lcolor("60 60 60") lwidth(thin)) ///
    text(195000 `=`brexit_year' + 0.15' "Brexit 2016", ///
        size(vsmall) color("90 90 90") placement(e)) ///
    text(195000 `=`covid_year' + 0.15' "Placebo 2020", ///
        size(vsmall) color("60 60 60") placement(e)) ///
    subtitle("{bf:a} UK actual vs synthetic", ///
        size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Publications", size(small)) ///
    xtitle("") ///
    xlabel(2005(5)2024, labsize(small) nogrid tposition(inside)) ///
    xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(0(50000)200000, angle(0) format(%9.0gc) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(0 200000) noextend) ///
    xscale(lcolor(black) lwidth(thin)) ///
    legend(order(3 "Actual" 2 "Synthetic") ///
        pos(6) rows(1) size(small) region(lstyle(none))) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    name(fit_uk_covid, replace)

use "`test_dir'/eu_covid2020_placebo_gap.dta", clear
gen _shade_lo = 0
gen _shade_hi = 30000

twoway ///
    (rarea _shade_lo _shade_hi Year if Year >= `covid_year', ///
        sort color("238 238 238%60") lwidth(none)) ///
    (line synthetic_real Year, lcolor("0 114 178") lpattern(dash) lwidth(medthick)) ///
    (line actual_real Year, lcolor("213 94 0") lpattern(solid) lwidth(thick)) ///
    , ///
    xline(`brexit_year', lpattern(shortdash) lcolor("120 120 120") lwidth(thin)) ///
    xline(`covid_year', lpattern(shortdash) lcolor("60 60 60") lwidth(thin)) ///
    text(29250 `=`brexit_year' + 0.15' "Brexit 2016", ///
        size(vsmall) color("90 90 90") placement(e)) ///
    text(29250 `=`covid_year' + 0.15' "Placebo 2020", ///
        size(vsmall) color("60 60 60") placement(e)) ///
    subtitle("{bf:b} EU actual vs synthetic", ///
        size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Publications", size(small)) ///
    xtitle("") ///
    xlabel(2005(5)2024, labsize(small) nogrid tposition(inside)) ///
    xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(0(10000)30000, angle(0) format(%9.0gc) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(0 30000) noextend) ///
    xscale(lcolor(black) lwidth(thin)) ///
    legend(order(3 "Actual" 2 "Synthetic") ///
        pos(6) rows(1) size(small) region(lstyle(none))) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    name(fit_eu_covid, replace)

graph combine fit_uk_covid fit_eu_covid, ///
    cols(1) imargin(2 2 2 2) graphregion(color(white))

graph export "`test_dir'/covid_placebo_time_actual_vs_synthetic.pdf", replace
graph export "`test_dir'/covid_placebo_time_actual_vs_synthetic.png", ///
    replace width(2400)

********************************************************************************
* 3. Also draw the main Brexit 2016 model for comparison
********************************************************************************

use "`test_dir'/uk_brexit2016_gap.dta", clear
gen _shade_lo = 0
gen _shade_hi = 200000

twoway ///
    (rarea _shade_lo _shade_hi Year if Year >= `brexit_year', ///
        sort color("238 238 238%60") lwidth(none)) ///
    (line synthetic_real Year, lcolor("0 114 178") lpattern(dash) lwidth(medthick)) ///
    (line actual_real Year, lcolor("213 94 0") lpattern(solid) lwidth(thick)) ///
    , ///
    xline(`brexit_year', lpattern(shortdash) lcolor("60 60 60") lwidth(thin)) ///
    xline(`covid_year', lpattern(shortdash) lcolor("120 120 120") lwidth(thin)) ///
    text(195000 `=`brexit_year' + 0.15' "Brexit 2016", ///
        size(vsmall) color("60 60 60") placement(e)) ///
    text(195000 `=`covid_year' + 0.15' "Covid 2020", ///
        size(vsmall) color("90 90 90") placement(e)) ///
    subtitle("{bf:a} UK main model", ///
        size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Publications", size(small)) ///
    xtitle("") ///
    xlabel(2005(5)2024, labsize(small) nogrid tposition(inside)) ///
    xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(0(50000)200000, angle(0) format(%9.0gc) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(0 200000) noextend) ///
    xscale(lcolor(black) lwidth(thin)) ///
    legend(order(3 "Actual" 2 "Synthetic") ///
        pos(6) rows(1) size(small) region(lstyle(none))) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    name(fit_uk_brexit, replace)

use "`test_dir'/eu_brexit2016_gap.dta", clear
gen _shade_lo = 0
gen _shade_hi = 30000

twoway ///
    (rarea _shade_lo _shade_hi Year if Year >= `brexit_year', ///
        sort color("238 238 238%60") lwidth(none)) ///
    (line synthetic_real Year, lcolor("0 114 178") lpattern(dash) lwidth(medthick)) ///
    (line actual_real Year, lcolor("213 94 0") lpattern(solid) lwidth(thick)) ///
    , ///
    xline(`brexit_year', lpattern(shortdash) lcolor("60 60 60") lwidth(thin)) ///
    xline(`covid_year', lpattern(shortdash) lcolor("120 120 120") lwidth(thin)) ///
    text(29250 `=`brexit_year' + 0.15' "Brexit 2016", ///
        size(vsmall) color("60 60 60") placement(e)) ///
    text(29250 `=`covid_year' + 0.15' "Covid 2020", ///
        size(vsmall) color("90 90 90") placement(e)) ///
    subtitle("{bf:b} EU main model", ///
        size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Publications", size(small)) ///
    xtitle("") ///
    xlabel(2005(5)2024, labsize(small) nogrid tposition(inside)) ///
    xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(0(10000)30000, angle(0) format(%9.0gc) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(0 30000) noextend) ///
    xscale(lcolor(black) lwidth(thin)) ///
    legend(order(3 "Actual" 2 "Synthetic") ///
        pos(6) rows(1) size(small) region(lstyle(none))) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    name(fit_eu_brexit, replace)

graph combine fit_uk_brexit fit_eu_brexit, ///
    cols(1) imargin(2 2 2 2) graphregion(color(white))

graph export "`test_dir'/brexit2016_actual_vs_synthetic.pdf", replace
graph export "`test_dir'/brexit2016_actual_vs_synthetic.png", ///
    replace width(2400)

di as text "Fit plots complete."
di as text "Covid placebo fit figure: `test_dir'/covid_placebo_time_actual_vs_synthetic.pdf"
di as text "Brexit main fit figure:   `test_dir'/brexit2016_actual_vs_synthetic.pdf"
di as text "Fit stats:                `test_dir'/covid_placebo_time_fit_stats.xlsx"
