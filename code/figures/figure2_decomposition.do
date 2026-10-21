clear all
set more off

********************************************************************************
* Figure 2: domestic vs international SCM decomposition for both events.
* 2 rows (Russia, Ukraine) x 4 columns:
*   col 1-2 = 2014 Crimean crisis (domestic, international)
*   col 3-4 = 2022 full-scale invasion (domestic, international)
* Solid = observed, dashed = synthetic; vertical line at the event year.
********************************************************************************

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
        exit 601
    }
    do "`_cfg'"
}

local d14 "$CODE/01_scm_crimea_2014/dom_intl_decomposition"
local d22 "$CODE/01_scm_war_2022/dom_intl_decomposition"

* Assemble the placebo p-values (produced by the three placebo do-files) into a
* single lookup table. If a CSV is missing the corresponding panels simply omit
* the p-value rather than failing.
tempfile pooled
local built 0
foreach pv in "`d14'/pvalues_russia.csv" "`d14'/pvalues_ukraine.csv" "`d22'/pvalues_2022.csv" {
    capture confirm file "`pv'"
    if _rc {
        di as text "note: p-value file not found, panels will omit p: `pv'"
        continue
    }
    import delimited using "`pv'", varnames(1) clear stringcols(1 2 3)
    if `built' == 0 {
        save `pooled', replace
        local built 1
    }
    else {
        append using `pooled'
        save `pooled', replace
    }
}
if `built' == 0 {
    clear
    set obs 1
    gen str12 event = ""
    gen str8  country = ""
    gen str12 component = ""
    gen double p = .
    save `pooled', replace
}
global PVAL_FILE "`pooled'"

* Program: build one panel from a merged xlsx + component prefix.
* Effect is recomputed here from the merged file (mean log gap over the
* post-treatment window, converted to a percentage) so the annotation can
* never drift from the underlying data. The p-value is looked up from the
* placebo CSVs merged into `$PVAL_FILE'; a missing entry prints effect only.
capture program drop mkpanel
program define mkpanel
    gettoken src    0 : 0
    gettoken comp   0 : 0
    gettoken evyear 0 : 0
    gettoken color  0 : 0
    gettoken title  0 : 0
    gettoken name   0 : 0
    gettoken evtag  0 : 0
    gettoken ctag   0 : 0
    gettoken postlo 0 : 0
    gettoken posthi 0 : 0
    import excel "`src'", sheet("Sheet1") firstrow clear
    quietly summarize Year
    local yr_lo = r(min)
    quietly summarize `comp'_actual_real
    local y_top = r(max)

    * Effect = exp(mean log gap over post window) - 1, in percent.
    tempvar lg
    gen double `lg' = ln(`comp'_actual_real) - ln(`comp'_synthetic_real)
    quietly summarize `lg' if Year >= `postlo' & Year <= `posthi'
    local eff = (exp(r(mean)) - 1) * 100
    local eff_s : display %4.1f `eff'
    local sign = cond(`eff' >= 0, "+", "")

    * p-value lookup from the merged placebo table (may be absent).
    local pv = .
    preserve
    quietly use "$PVAL_FILE", clear
    quietly count if event == "`evtag'" & country == "`ctag'" & component == "`comp'"
    if r(N) > 0 {
        quietly sum p if event == "`evtag'" & country == "`ctag'" & component == "`comp'"
        local pv = r(mean)
    }
    restore
    if missing(`pv') {
        local annot "Effect `sign'`eff_s'%"
    }
    else {
        local pv_s : display %4.3f `pv'
        local annot "Effect `sign'`eff_s'% (p=`pv_s')"
    }
    twoway ///
        (line `comp'_actual_real Year, lcolor("`color'") lwidth(medthick)) ///
        (line `comp'_synthetic_real Year, lcolor("`color'") lwidth(medthick) lpattern(dash)), ///
        xline(`evyear', lpattern(shortdash) lcolor(gs7)) ///
        text(`y_top' `yr_lo' "`annot'", placement(se) size(small) box bcolor(white) bmargin(vsmall) justification(left)) ///
        title("`title'", size(medsmall) placement(west) color(black)) ///
        xtitle("") ytitle("Publications", size(small)) ///
        xlabel(2005(5)2024, nogrid labsize(vsmall) tposition(inside)) ///
        ylabel(, nogrid labsize(vsmall) tposition(inside) format(%9.0gc)) ///
        legend(off) ///
        graphregion(color(white)) plotregion(style(none)) ///
        name(`name', replace)
end

mkpanel "`d14'/russia_dom_intl_merged.xlsx"        dom  2014 "$C_RU" "(a) Russia: domestic"        p_a crimea2014 russia  2014 2021
mkpanel "`d14'/russia_dom_intl_merged.xlsx"        intl 2014 "$C_RU" "(b) Russia: international"    p_b crimea2014 russia  2014 2021
mkpanel "`d22'/russia_dom_intl_2022_merged.xlsx"   dom  2022 "$C_RU" "(c) Russia: domestic"        p_c war2022    russia  2022 2024
mkpanel "`d22'/russia_dom_intl_2022_merged.xlsx"   intl 2022 "$C_RU" "(d) Russia: international"    p_d war2022    russia  2022 2024
mkpanel "`d14'/ukraine_dom_intl_merged.xlsx"       dom  2014 "$C_UA" "(e) Ukraine: domestic"       p_e crimea2014 ukraine 2014 2021
mkpanel "`d14'/ukraine_dom_intl_merged.xlsx"       intl 2014 "$C_UA" "(f) Ukraine: international"   p_f crimea2014 ukraine 2014 2021
mkpanel "`d22'/ukraine_dom_intl_2022_merged.xlsx"  dom  2022 "$C_UA" "(g) Ukraine: domestic"       p_g war2022    ukraine 2022 2024
mkpanel "`d22'/ukraine_dom_intl_2022_merged.xlsx"  intl 2022 "$C_UA" "(h) Ukraine: international"   p_h war2022    ukraine 2022 2024

graph combine p_a p_b p_c p_d p_e p_f p_g p_h, ///
    cols(4) ///
    graphregion(color(white)) ///
    note("Solid: observed. Dashed: synthetic counterfactual. Vertical line marks the event year.", size(vsmall)) ///
    name(fig2, replace)

graph export "$PAPER/figure/figure2.pdf", replace
graph export "$PAPER/figure/figure2.png", width(2400) replace
