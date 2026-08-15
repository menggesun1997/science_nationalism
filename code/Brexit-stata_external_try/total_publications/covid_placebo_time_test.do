clear all
set more off

********************************************************************************
* Placebo-in-time test for Covid robustness
*
* Purpose:
* 1. Re-run the main Brexit synthetic control with treatment year = 2016.
* 2. Re-run a placebo-in-time synthetic control with treatment year = 2020.
* 3. Keep the same fitting convention as compare.do: xperiod() uses 2008-2015,
*    while synth uses its default pre-treatment MSPE period.
* 4. Compare the Brexit gap with the Covid placebo gap.
********************************************************************************

local base_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/Brexit-stata_external_try"
local out_dir "`base_dir'/total_publications"

local brexit_year 2016
local covid_year 2020
local before_brexit_year 2015
local pre_period_start 2008

capture mkdir "`out_dir'/covid_placebo_time"
local test_dir "`out_dir'/covid_placebo_time"

********************************************************************************
* 1. Load prepared data, or rebuild it if processed_data.dta is absent
********************************************************************************

capture confirm file "`out_dir'/processed_data.dta"
if _rc {
    import excel "`base_dir'/brexit_non_eu.xlsx", sheet("Sheet1") firstrow clear

    replace Country = subinstr(Country, " ", "_", .)
    levelsof Country, local(countries) clean

    gen country_id = .
    local i = 1
    foreach country of local countries {
        replace country_id = `i' if Country == "`country'"
        local ++i
    }

    xtset country_id Year

    gen log_pub_total = log(pub_total + 1)
    gen log_gdp_per_capita = log(gdp_per_capita + 1)
    gen log_gdp_per_capita_10 = log_gdp_per_capita / 10
    gen log_rp = log(ResearchersinRD + 1)
    gen log_rp_10 = log_rp / 10

    bysort country_id: egen gdp_pre_mean = mean(gdp_per_capita) ///
        if Year >= `pre_period_start' & Year <= `before_brexit_year'
    bysort country_id: egen log_gdp_pre_mean = mean(log_gdp_per_capita) ///
        if Year >= `pre_period_start' & Year <= `before_brexit_year'
    bysort country_id: egen researchers_pre_mean = mean(ResearchersinRD) ///
        if Year >= `pre_period_start' & Year <= `before_brexit_year'
    bysort country_id: egen log_rp_pre_mean = mean(log_rp) ///
        if Year >= `pre_period_start' & Year <= `before_brexit_year'
    bysort country_id: egen rd_pre_mean = mean(RD) ///
        if Year >= `pre_period_start' & Year <= `before_brexit_year'
    bysort country_id: egen log_pub_pre_mean_uk = mean(log_pub_total) ///
        if Year >= 2005 & Year <= 2012
    bysort country_id: egen log_pub_pre_mean_eu = mean(log_pub_total) ///
        if Year >= 2005 & Year <= 2014

    bysort country_id: egen gdp_pre_final = max(gdp_pre_mean)
    bysort country_id: egen log_gdp_pre_final = max(log_gdp_pre_mean)
    bysort country_id: egen researchers_pre_final = max(researchers_pre_mean)
    bysort country_id: egen log_rp_pre_final = max(log_rp_pre_mean)
    bysort country_id: egen rd_pre_final = max(rd_pre_mean)
    bysort country_id: egen log_pub_pre_mean_uk_final = max(log_pub_pre_mean_uk)
    bysort country_id: egen log_pub_pre_mean_eu_final = max(log_pub_pre_mean_eu)

    drop gdp_pre_mean log_gdp_pre_mean researchers_pre_mean log_rp_pre_mean rd_pre_mean
    drop log_pub_pre_mean_uk log_pub_pre_mean_eu

    save "`out_dir'/processed_data.dta", replace
}
else {
    use "`out_dir'/processed_data.dta", clear
}

********************************************************************************
* 2. Define treated and donor units
********************************************************************************

levelsof Country, local(countries) clean

local control_countries
foreach country of local countries {
    if !inlist("`country'", "EU", "UNITED_KINGDOM") {
        local control_countries `"`control_countries' "`country'""'
    }
}

local control_ids
foreach country of local control_countries {
    quietly summarize country_id if Country == "`country'"
    local control_ids "`control_ids' `r(mean)'"
}

quietly summarize country_id if Country == "UNITED_KINGDOM"
local uk_id = r(mean)
quietly summarize country_id if Country == "EU"
local eu_id = r(mean)

global uk_control_vars "log_pub_pre_mean_uk_final"
global uk_control_vars_1 "log_pub_total(2013)"
global eu_control_vars "log_pub_pre_mean_eu_final"
global eu_control_vars_1 "log_pub_total(2015)"

********************************************************************************
* 3. Program: run one synthetic control and produce a cleaned gap file
********************************************************************************

capture program drop run_gap_model
program define run_gap_model
    syntax, unitname(string) unitid(integer) treatyear(integer) ///
        controls(string) extracontrols(string) outstub(string)

    use "`c(pwd)'/processed_data_for_covid_placebo.dta", clear

    quietly synth log_pub_total ///
        `controls' ///
        `extracontrols', ///
        trunit(`unitid') trperiod(`treatyear') ///
        counit($donor_ids) ///
        xperiod($pre_start(1)$pre_end) ///
        nested allopt ///
        keep("`outstub'_raw", replace)

    use "`outstub'_raw.dta", clear
    rename _time Year
    rename _Y_treated actual_log
    rename _Y_synthetic synthetic_log
    drop if missing(Year)

    gen gap_log = actual_log - synthetic_log
    gen actual_real = exp(actual_log) - 1
    gen synthetic_real = exp(synthetic_log) - 1
    gen gap_real = actual_real - synthetic_real
    gen gap_pct = gap_real / actual_real * 100

    gen unit = "`unitname'"
    gen treatment_year = `treatyear'

    keep unit treatment_year Year actual_log synthetic_log gap_log ///
        actual_real synthetic_real gap_real gap_pct
    order unit treatment_year Year actual_log synthetic_log gap_log ///
        actual_real synthetic_real gap_real gap_pct

    save "`outstub'_gap.dta", replace
end

********************************************************************************
* 4. Run main Brexit and Covid placebo-in-time models
********************************************************************************

save "`test_dir'/processed_data_for_covid_placebo.dta", replace
cd "`test_dir'"

global donor_ids "`control_ids'"
global pre_start `pre_period_start'
global pre_end `before_brexit_year'

run_gap_model, unitname("UK") unitid(`uk_id') treatyear(`brexit_year') ///
    controls("$uk_control_vars") extracontrols("$uk_control_vars_1") ///
    outstub("uk_brexit2016")

run_gap_model, unitname("UK") unitid(`uk_id') treatyear(`covid_year') ///
    controls("$uk_control_vars") extracontrols("$uk_control_vars_1") ///
    outstub("uk_covid2020_placebo")

run_gap_model, unitname("EU") unitid(`eu_id') treatyear(`brexit_year') ///
    controls("$eu_control_vars") extracontrols("$eu_control_vars_1") ///
    outstub("eu_brexit2016")

run_gap_model, unitname("EU") unitid(`eu_id') treatyear(`covid_year') ///
    controls("$eu_control_vars") extracontrols("$eu_control_vars_1") ///
    outstub("eu_covid2020_placebo")

********************************************************************************
* 5. Merge gaps for direct comparison
********************************************************************************

use "uk_brexit2016_gap.dta", clear
rename (actual_log synthetic_log gap_log actual_real synthetic_real gap_real gap_pct) ///
    (uk_brexit_actual_log uk_brexit_synthetic_log uk_brexit_gap_log ///
     uk_brexit_actual_real uk_brexit_synthetic_real uk_brexit_gap_real ///
     uk_brexit_gap_pct)
keep Year uk_brexit_*
save "uk_brexit2016_for_merge.dta", replace

use "uk_covid2020_placebo_gap.dta", clear
rename (actual_log synthetic_log gap_log actual_real synthetic_real gap_real gap_pct) ///
    (uk_covid_actual_log uk_covid_synthetic_log uk_covid_gap_log ///
     uk_covid_actual_real uk_covid_synthetic_real uk_covid_gap_real ///
     uk_covid_gap_pct)
keep Year uk_covid_*
save "uk_covid2020_for_merge.dta", replace

use "eu_brexit2016_gap.dta", clear
rename (actual_log synthetic_log gap_log actual_real synthetic_real gap_real gap_pct) ///
    (eu_brexit_actual_log eu_brexit_synthetic_log eu_brexit_gap_log ///
     eu_brexit_actual_real eu_brexit_synthetic_real eu_brexit_gap_real ///
     eu_brexit_gap_pct)
keep Year eu_brexit_*
save "eu_brexit2016_for_merge.dta", replace

use "eu_covid2020_placebo_gap.dta", clear
rename (actual_log synthetic_log gap_log actual_real synthetic_real gap_real gap_pct) ///
    (eu_covid_actual_log eu_covid_synthetic_log eu_covid_gap_log ///
     eu_covid_actual_real eu_covid_synthetic_real eu_covid_gap_real ///
     eu_covid_gap_pct)
keep Year eu_covid_*
save "eu_covid2020_for_merge.dta", replace

use "uk_brexit2016_for_merge.dta", clear
merge 1:1 Year using "uk_covid2020_for_merge.dta", nogenerate
merge 1:1 Year using "eu_brexit2016_for_merge.dta", nogenerate
merge 1:1 Year using "eu_covid2020_for_merge.dta", nogenerate

save "`test_dir'/covid_placebo_time_gaps.dta", replace
export excel using "`test_dir'/covid_placebo_time_gaps.xlsx", ///
    firstrow(variables) replace

********************************************************************************
* 6. Build summary table
********************************************************************************

tempname results
postfile `results' str8 unit ///
    brexit_gap_pct_2016_2019 ///
    brexit_gap_pct_2016_end ///
    covid_placebo_gap_pct_2020_end ///
    covid_to_brexit_pre_covid_ratio ///
    covid_to_brexit_all_post_ratio ///
    using "`test_dir'/covid_placebo_time_summary.dta", replace

summarize uk_brexit_gap_pct if inrange(Year, `brexit_year', `covid_year' - 1), meanonly
local uk_brexit_pre_covid = r(mean)
summarize uk_brexit_gap_pct if Year >= `brexit_year', meanonly
local uk_brexit_all_post = r(mean)
summarize uk_covid_gap_pct if Year >= `covid_year', meanonly
local uk_covid_post = r(mean)
local uk_ratio_pre = abs(`uk_covid_post') / abs(`uk_brexit_pre_covid')
local uk_ratio_all = abs(`uk_covid_post') / abs(`uk_brexit_all_post')

post `results' ("UK") ///
    (`uk_brexit_pre_covid') (`uk_brexit_all_post') (`uk_covid_post') ///
    (`uk_ratio_pre') (`uk_ratio_all')

summarize eu_brexit_gap_pct if inrange(Year, `brexit_year', `covid_year' - 1), meanonly
local eu_brexit_pre_covid = r(mean)
summarize eu_brexit_gap_pct if Year >= `brexit_year', meanonly
local eu_brexit_all_post = r(mean)
summarize eu_covid_gap_pct if Year >= `covid_year', meanonly
local eu_covid_post = r(mean)
local eu_ratio_pre = abs(`eu_covid_post') / abs(`eu_brexit_pre_covid')
local eu_ratio_all = abs(`eu_covid_post') / abs(`eu_brexit_all_post')

post `results' ("EU") ///
    (`eu_brexit_pre_covid') (`eu_brexit_all_post') (`eu_covid_post') ///
    (`eu_ratio_pre') (`eu_ratio_all')

postclose `results'

use "`test_dir'/covid_placebo_time_summary.dta", clear
gen str80 interpretation = ""
replace interpretation = "Brexit gap is larger than Covid placebo gap" ///
    if covid_to_brexit_all_post_ratio < 0.50
replace interpretation = "Covid placebo gap is non-trivial relative to Brexit gap" ///
    if inrange(covid_to_brexit_all_post_ratio, 0.50, 0.90)
replace interpretation = "Covid placebo gap is close to Brexit gap" ///
    if covid_to_brexit_all_post_ratio >= 0.90

export excel using "`test_dir'/covid_placebo_time_summary.xlsx", ///
    firstrow(variables) replace
list, noobs abbrev(24)

********************************************************************************
* 7. Visual comparison of gaps
********************************************************************************

use "`test_dir'/covid_placebo_time_gaps.dta", clear

graph set window fontface "Helvetica"
set scheme s1color
graph set eps fontface "Helvetica"

quietly summarize uk_brexit_gap_pct, meanonly
local uk_ymin = r(min)
local uk_ymax = r(max)
quietly summarize uk_covid_gap_pct, meanonly
local uk_ymin = min(`uk_ymin', r(min))
local uk_ymax = max(`uk_ymax', r(max))
local uk_ymin = floor(`uk_ymin' / 5) * 5
local uk_ymax = ceil(`uk_ymax' / 5) * 5
if `uk_ymin' == `uk_ymax' {
    local uk_ymin = `uk_ymin' - 5
    local uk_ymax = `uk_ymax' + 5
}

twoway ///
    (line uk_brexit_gap_pct Year, lcolor("213 94 0") lwidth(thick)) ///
    (line uk_covid_gap_pct Year, lcolor("0 114 178") lpattern(dash) lwidth(medthick)) ///
    , ///
    xline(`brexit_year', lpattern(shortdash) lcolor("80 80 80") lwidth(thin)) ///
    xline(`covid_year', lpattern(shortdash) lcolor("80 80 80") lwidth(thin)) ///
    yline(0, lpattern(solid) lcolor("160 160 160") lwidth(thin)) ///
    text(`uk_ymax' `=`brexit_year' + 0.15' "Brexit 2016", ///
        size(vsmall) color("80 80 80") placement(e)) ///
    text(`uk_ymax' `=`covid_year' + 0.15' "Covid 2020", ///
        size(vsmall) color("80 80 80") placement(e)) ///
    subtitle("{bf:a} UK", size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Gap (% of actual publications)", size(small)) ///
    xtitle("") ///
    xlabel(2005(5)2024, labsize(small) nogrid tposition(inside)) ///
    xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(, angle(0) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`uk_ymin' `uk_ymax')) ///
    xscale(lcolor(black) lwidth(thin)) ///
    legend(order(1 "Brexit SC gap" 2 "Covid placebo gap") ///
        pos(6) rows(1) size(small) region(lstyle(none))) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    name(covid_placebo_uk_gap, replace)

quietly summarize eu_brexit_gap_pct, meanonly
local eu_ymin = r(min)
local eu_ymax = r(max)
quietly summarize eu_covid_gap_pct, meanonly
local eu_ymin = min(`eu_ymin', r(min))
local eu_ymax = max(`eu_ymax', r(max))
local eu_ymin = floor(`eu_ymin' / 5) * 5
local eu_ymax = ceil(`eu_ymax' / 5) * 5
if `eu_ymin' == `eu_ymax' {
    local eu_ymin = `eu_ymin' - 5
    local eu_ymax = `eu_ymax' + 5
}

twoway ///
    (line eu_brexit_gap_pct Year, lcolor("213 94 0") lwidth(thick)) ///
    (line eu_covid_gap_pct Year, lcolor("0 114 178") lpattern(dash) lwidth(medthick)) ///
    , ///
    xline(`brexit_year', lpattern(shortdash) lcolor("80 80 80") lwidth(thin)) ///
    xline(`covid_year', lpattern(shortdash) lcolor("80 80 80") lwidth(thin)) ///
    yline(0, lpattern(solid) lcolor("160 160 160") lwidth(thin)) ///
    text(`eu_ymax' `=`brexit_year' + 0.15' "Brexit 2016", ///
        size(vsmall) color("80 80 80") placement(e)) ///
    text(`eu_ymax' `=`covid_year' + 0.15' "Covid 2020", ///
        size(vsmall) color("80 80 80") placement(e)) ///
    subtitle("{bf:b} EU", size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Gap (% of actual publications)", size(small)) ///
    xtitle("") ///
    xlabel(2005(5)2024, labsize(small) nogrid tposition(inside)) ///
    xmtick(2005(1)2024, tposition(inside)) ///
    ylabel(, angle(0) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`eu_ymin' `eu_ymax')) ///
    xscale(lcolor(black) lwidth(thin)) ///
    legend(order(1 "Brexit SC gap" 2 "Covid placebo gap") ///
        pos(6) rows(1) size(small) region(lstyle(none))) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    name(covid_placebo_eu_gap, replace)

graph combine covid_placebo_uk_gap covid_placebo_eu_gap, ///
    cols(1) imargin(2 2 2 2) graphregion(color(white))

graph export "`test_dir'/covid_placebo_time_gap_comparison.pdf", replace
graph export "`test_dir'/covid_placebo_time_gap_comparison.png", ///
    replace width(2400)

********************************************************************************
* 8. Main outputs
********************************************************************************

di as text "Covid placebo-in-time test complete."
di as text "Gap data:       `test_dir'/covid_placebo_time_gaps.dta"
di as text "Gap Excel:      `test_dir'/covid_placebo_time_gaps.xlsx"
di as text "Summary Excel:  `test_dir'/covid_placebo_time_summary.xlsx"
di as text "Figure PDF:     `test_dir'/covid_placebo_time_gap_comparison.pdf"
di as text "Figure PNG:     `test_dir'/covid_placebo_time_gap_comparison.png"
