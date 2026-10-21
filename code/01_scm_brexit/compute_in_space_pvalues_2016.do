*===========================================================*
* compute_in_space_pvalues_2016.do
*
* The 2016 in-space placebo fits already exist (synth_<country>.dta, written by
* refresh_standardized_placebos.do), but the MSPE-based p-value was never
* tabulated. This file reads those fits and applies exactly the same inference
* used for the 2021 specification in run_in_space_placebo_2021.do:
*     R_i = MSPE_post(i) / MSPE_pre(i),  p = #{R_i >= R_uk} / (N+1)
* with the pre-window 2008-2015 and the post-window 2016-2024.
*
* Reading the stored fits rather than refitting keeps the reported p-values
* tied to the same placebo runs that produced the SI figures.
*
* Outputs <outcome>/in_space_2016/mspe_ratios_2016.xlsx / .dta
*===========================================================*
clear all
set more off

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
        di as error "Cannot locate code/config.do."
        exit 601
    }
    do "`_cfg'"
}

local brexit "$CODE/01_scm_brexit"

capture program drop pvals_2016
program define pvals_2016
    syntax, OUTdir(string) OUTCOME(string)

    capture mkdir "`outdir'/in_space_2016"
    cd "`outdir'"

    tempfile acc
    local nacc 0

    *-- donor placebo fits ------------------------------------------*
    local files : dir "." files "synth_*.dta"
    foreach f of local files {
        local u = subinstr("`f'", "synth_", "", 1)
        local u = subinstr("`u'", ".dta", "", 1)

        use "`f'", clear
        capture confirm variable _time
        if _rc continue
        rename _time Year
        keep Year _Y_treated _Y_synthetic
        drop if missing(Year)
        gen double gap = _Y_treated - _Y_synthetic
        gen str32 unit = "`u'"
        keep Year unit gap

        if `nacc' == 0 {
            save `acc', replace
        }
        else {
            append using `acc'
            save `acc', replace
        }
        local nacc = `nacc' + 1
    }

    *-- treated unit ------------------------------------------------*
    use "`outdir'/uk_synth_results.dta", clear
    if "`outcome'" == "total" {
        gen double gap = uk_actual - uk_synthetic
    }
    else {
        gen double gap = uk_gap
    }
    keep Year gap
    drop if missing(Year)
    gen str32 unit = "UNITED_KINGDOM"
    append using `acc'

    *-- MSPE ratios -------------------------------------------------*
    gen double sq = gap^2
    collapse (mean) mspe_pre = sq if Year >= 2008 & Year <= 2015, by(unit)
    tempfile pre
    save `pre', replace

    use "`outdir'/uk_synth_results.dta", clear
    if "`outcome'" == "total" {
        gen double gap = uk_actual - uk_synthetic
    }
    else {
        gen double gap = uk_gap
    }
    keep Year gap
    drop if missing(Year)
    gen str32 unit = "UNITED_KINGDOM"
    append using `acc'
    gen double sq = gap^2
    collapse (mean) mspe_post = sq if Year >= 2016, by(unit)

    merge 1:1 unit using `pre', nogenerate
    gen double mspe_ratio = mspe_post / mspe_pre
    drop if missing(mspe_ratio)

    gsort -mspe_ratio
    gen int rank = _n
    quietly count
    local N = r(N)
    gen int n_units = `N'

    * Rows are in descending order, so the UK's rank equals #{ R_i >= R_uk }.
    quietly summarize rank if unit == "UNITED_KINGDOM"
    local uk_rank = r(mean)
    gen double pvalue = `uk_rank' / `N'

    quietly summarize mspe_ratio if unit == "UNITED_KINGDOM"
    local uk_ratio = r(mean)

    export excel using "`outdir'/in_space_2016/mspe_ratios_2016.xlsx", ///
        firstrow(variables) replace
    save "`outdir'/in_space_2016/mspe_ratios_2016.dta", replace

    list unit mspe_ratio rank pvalue, noobs sep(0) abbrev(16)
    di as result _n "UK MSPE ratio = " %7.3f `uk_ratio' ///
        "   rank `uk_rank' of `N'   p = " %5.3f `uk_rank' / `N'
end

di as result _n _dup(60) "="
di as result "In-space placebo p-values, 2016: total publications"
di as result _dup(60) "="
pvals_2016, outdir("`brexit'/total_publications") outcome("total")

di as result _n _dup(60) "="
di as result "In-space placebo p-values, 2016: intl. collaboration ratio"
di as result _dup(60) "="
pvals_2016, outdir("`brexit'/intl_ratio") outcome("ratio")

di as result _n "{hline 64}"
di as result "UK, 2016 intervention: in-space placebo inference"
di as result "{hline 64}"
foreach o in total_publications intl_ratio {
    use "`brexit'/`o'/in_space_2016/mspe_ratios_2016.dta", clear
    quietly summarize mspe_ratio if unit == "UNITED_KINGDOM"
    local r : display %7.3f r(mean)
    quietly summarize rank if unit == "UNITED_KINGDOM"
    local k = r(mean)
    quietly summarize pvalue
    local p : display %5.3f r(mean)
    quietly count
    local n = r(N)
    di as result "  `o': UK MSPE ratio `r'  rank `k' of `n'  p = `p'"
}
di as result "{hline 64}"
di as result _n "=== 2016 P-VALUES DONE ==="
