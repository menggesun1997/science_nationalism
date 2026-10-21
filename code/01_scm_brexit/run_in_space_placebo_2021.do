*===========================================================*
* run_in_space_placebo_2021.do — in-space placebo for the 2021 intervention
*
* The 2016 in-space placebos are produced by refresh_standardized_placebos.do.
* This file is the counterpart for the 2021 formal-exit specification fitted by
* run_scm_2021.do: the same SCM is applied to each donor country in turn, as if
* it rather than the UK had left the EU in 2021.
*
* Inference follows the main text: for unit i we compute the ratio of
* post-treatment to pre-treatment mean squared prediction error,
*     R_i = MSPE_post(i) / MSPE_pre(i),
* and report the one-sided pseudo p-value
*     p = (1/(N+1)) * #{ i : R_i >= R_uk }.
* A large R for the UK relative to the placebo distribution indicates a
* post-2021 divergence that is unusual given the pre-2021 fit.
*
* Specification is identical to run_scm_2021.do (windows shifted five years
* relative to the 2016 analysis):
*   total:  pre-mean of log_pub_total over 2005-2017 + lag at 2018
*   ratio:  pre-mean of intl_ratio over 2005-2017 + lags 2020/2019/2016/2015
*   both:   xperiod(2008..2020), trperiod(2021)
*
* Outputs:
*   <outcome>/in_space_2021/placebo_gaps_2021.dta   tidy gaps, all units
*   <outcome>/in_space_2021/mspe_ratios_2021.xlsx   R_i, rank and p-value
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
        di as error "Cannot locate code/config.do. Set SCIENCE_NATIONALISM_ROOT."
        exit 601
    }
    do "`_cfg'"
}

local brexit "$CODE/01_scm_brexit"

*-----------------------------------------------------------*
* Program: run the 2021 SCM for every unit (UK + donors)
*-----------------------------------------------------------*
capture program drop placebo_2021
program define placebo_2021
    syntax, OUTdir(string) OUTCOME(string)

    capture mkdir "`outdir'/in_space_2021"
    cd "`outdir'/in_space_2021"

    * Unit list: the UK plus every donor. EU is a composite unit and is never
    * treated or used as a donor, so it is excluded throughout.
    use "`outdir'/processed_data.dta", clear
    levelsof Country if Country != "EU", local(units) clean

    tempfile acc
    local nacc 0

    foreach u of local units {
        use "`outdir'/processed_data.dta", clear

        quietly summarize country_id if Country == "`u'"
        local tid = r(mean)

        * Donors for this run: all units except the treated one and EU.
        local dids ""
        foreach d of local units {
            if "`d'" != "`u'" {
                quietly summarize country_id if Country == "`d'"
                local dids "`dids' `=r(mean)'"
            }
        }

        * Predictors are rebuilt inside the loop so each run is self-contained.
        if "`outcome'" == "total" {
            capture drop pm21 pm21_final
            bysort country_id: egen pm21 = ///
                mean(log_pub_total) if Year >= 2005 & Year <= 2017
            bysort country_id: egen pm21_final = max(pm21)
            capture quietly synth log_pub_total pm21_final log_pub_total(2018), ///
                trunit(`tid') trperiod(2021) counit(`dids') ///
                xperiod(2008(1)2020) nested allopt ///
                keep("_p_`u'.dta", replace)
            if _rc {
                capture quietly synth log_pub_total pm21_final log_pub_total(2018), ///
                    trunit(`tid') trperiod(2021) counit(`dids') ///
                    xperiod(2008(1)2020) allopt ///
                    keep("_p_`u'.dta", replace)
            }
            if _rc {
                capture quietly synth log_pub_total pm21_final log_pub_total(2018), ///
                    trunit(`tid') trperiod(2021) counit(`dids') ///
                    xperiod(2008(1)2020) ///
                    keep("_p_`u'.dta", replace)
            }
        }
        else {
            capture drop rm21 rm21_final
            bysort country_id: egen rm21 = ///
                mean(intl_ratio) if Year >= 2005 & Year <= 2017
            bysort country_id: egen rm21_final = max(rm21)
            capture quietly synth intl_ratio rm21_final ///
                intl_ratio(2020) intl_ratio(2019) intl_ratio(2016) intl_ratio(2015), ///
                trunit(`tid') trperiod(2021) counit(`dids') ///
                xperiod(2008(1)2020) nested allopt ///
                keep("_p_`u'.dta", replace)
            if _rc {
                capture quietly synth intl_ratio rm21_final ///
                    intl_ratio(2020) intl_ratio(2019) intl_ratio(2016) intl_ratio(2015), ///
                    trunit(`tid') trperiod(2021) counit(`dids') ///
                    xperiod(2008(1)2020) allopt ///
                    keep("_p_`u'.dta", replace)
            }
            if _rc {
                capture quietly synth intl_ratio rm21_final ///
                    intl_ratio(2020) intl_ratio(2019) intl_ratio(2016) intl_ratio(2015), ///
                    trunit(`tid') trperiod(2021) counit(`dids') ///
                    xperiod(2008(1)2020) ///
                    keep("_p_`u'.dta", replace)
            }
        }

        if _rc {
            di as error "  !! placebo failed: `u' (rc = " _rc ")"
            continue
        }

        *-- tidy this unit's gap series and its MSPE ratio ------------*
        use "_p_`u'.dta", clear
        rename _time Year
        rename _Y_treated actual
        rename _Y_synthetic synthetic
        keep Year actual synthetic
        drop if missing(Year)

        gen gap = actual - synthetic
        gen str32 unit = "`u'"

        * MSPE on the model's own scale (log points for total, ratio for ratio),
        * matching how pre/post fit is assessed for the treated unit.
        quietly gen sq = gap^2
        quietly summarize sq if Year >= 2008 & Year <= 2020
        gen double mspe_pre = r(mean)
        quietly summarize sq if Year >= 2021
        gen double mspe_post = r(mean)
        gen double mspe_ratio = mspe_post / mspe_pre
        drop sq

        if "`outcome'" == "total" {
            gen actual_real = exp(actual) - 1
            gen synthetic_real = exp(synthetic) - 1
            gen gap_pct = (actual_real - synthetic_real) / actual_real * 100
        }

        if `nacc' == 0 {
            save `acc', replace
        }
        else {
            append using `acc'
            save `acc', replace
        }
        local nacc = `nacc' + 1

        erase "_p_`u'.dta"
        di as text "  done: `u'"
    }

    use `acc', clear
    sort unit Year
    save "`outdir'/in_space_2021/placebo_gaps_2021.dta", replace

    *-- one row per unit: MSPE ratio, rank and p-value --------------*
    keep unit mspe_pre mspe_post mspe_ratio
    duplicates drop
    gsort -mspe_ratio
    gen int rank = _n
    quietly count
    local N = r(N)
    gen int n_units = `N'

    * p = #{ R_i >= R_uk } / N, with the treated unit included in both the
    * numerator and N. Since rows are sorted in descending order, the UK's
    * rank is exactly that count; using the rank avoids the floating-point
    * comparison failing on the UK's own row.
    quietly summarize rank if unit == "UNITED_KINGDOM"
    local uk_rank = r(mean)
    gen double pvalue = `uk_rank' / `N'

    quietly summarize mspe_ratio if unit == "UNITED_KINGDOM"
    local uk_ratio = r(mean)

    export excel using "`outdir'/in_space_2021/mspe_ratios_2021.xlsx", ///
        firstrow(variables) replace
    save "`outdir'/in_space_2021/mspe_ratios_2021.dta", replace

    list unit mspe_ratio rank n_units pvalue, noobs sep(0) abbrev(16)

    di as result _n "UK MSPE ratio = " %6.3f `uk_ratio' ///
        "   rank " `uk_rank' " of `N'" ///
        "   p = " %5.3f `uk_rank' / `N'
end

*-----------------------------------------------------------*
* Run both outcomes
*-----------------------------------------------------------*
di as result _n _dup(60) "="
di as result "In-space placebo, 2021 intervention: total publications"
di as result _dup(60) "="
placebo_2021, outdir("`brexit'/total_publications") outcome("total")

di as result _n _dup(60) "="
di as result "In-space placebo, 2021 intervention: intl. collaboration ratio"
di as result _dup(60) "="
placebo_2021, outdir("`brexit'/intl_ratio") outcome("ratio")

*-----------------------------------------------------------*
* Final summary for the paper
*-----------------------------------------------------------*
di as result _n "{hline 64}"
di as result "UK, 2021 intervention: in-space placebo inference"
di as result "{hline 64}"
foreach o in total_publications intl_ratio {
    use "`brexit'/`o'/in_space_2021/mspe_ratios_2021.dta", clear
    quietly summarize mspe_ratio if unit == "UNITED_KINGDOM"
    local r : display %6.3f r(mean)
    quietly summarize rank if unit == "UNITED_KINGDOM"
    local k = r(mean)
    quietly summarize pvalue
    local p : display %5.3f r(mean)
    quietly count
    local n = r(N)
    di as result "  `o'"
    di as result "    UK MSPE ratio `r'   rank `k' of `n'   p = `p'"
}
di as result "{hline 64}"

di as result _n "=== IN-SPACE PLACEBO 2021 DONE ==="
