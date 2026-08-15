clear all
set more off

********************************************************************************
* Rebuild in-space placebo outputs after country-name standardization.
*
* Country names are standardized in the source xlsx files and again after import.
* Donor-placebo loops no longer use treat_id filters. Stale gap_*.dta files are
* removed before each rebuild so old countries cannot leak into the figures.
********************************************************************************


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

global root "$ROOT"
global standardize "$root/code/standardize_country_names.do"

capture program drop setup_common_data
program define setup_common_data
    syntax, Source(string) OUTdir(string)

    import excel "`source'", sheet("Sheet1") firstrow clear
    do "$standardize"

    gen country_id = .
    levelsof Country, local(countries) clean
    local i = 1
    foreach country of local countries {
        replace country_id = `i' if Country == "`country'"
        local ++i
    }
    xtset country_id Year

    gen log_pub_total = log(pub_total + 1)
    capture confirm variable intl_ratio
    if _rc {
        gen double intl_ratio = pub_intl / pub_total if pub_total > 0
    }
    else {
        replace intl_ratio = pub_intl / pub_total if pub_total > 0
    }
    gen log_gdp_per_capita = log(gdp_per_capita + 1)
    gen log_rp = log(ResearchersinRD + 1)
    gen log_pub_total_10 = log_pub_total / 10
    gen log_gdp_per_capita_10 = log_gdp_per_capita / 10
    gen log_rp_10 = log_rp / 10

    save "`outdir'/processed_data.dta", replace
end

capture program drop clear_gap_outputs
program define clear_gap_outputs
    local files : dir "." files "gap_*.dta"
    foreach file of local files {
        erase "`file'"
    }
end

capture program drop build_controls
program define build_controls
    syntax, EXclude(string)

    levelsof Country, local(countries) clean
    local control_countries
    foreach country of local countries {
        local skip = 0
        foreach excluded of local exclude {
            if "`country'" == "`excluded'" local skip = 1
        }
        if !`skip' {
            local control_countries `"`control_countries' "`country'""'
        }
    }

    local control_ids
    foreach country of local control_countries {
        quietly summarize country_id if Country == "`country'"
        local control_ids "`control_ids' `=r(mean)'"
    }

    c_local countries `"`countries'"'
    c_local control_countries `"`control_countries'"'
    c_local control_ids "`control_ids'"
end

capture program drop run_total_treated
program define run_total_treated
    syntax, OUTdir(string) NAME(string) ID(integer) Treatyear(integer) ///
        Beforeyear(integer) FITstart(integer) CONTROLS(string) LAGS(string)

    cd "`outdir'"
    use "`outdir'/processed_data.dta", clear
    capture quietly synth log_pub_total `controls' `lags', ///
        trunit(`id') trperiod(`treatyear') ///
        counit($control_ids) ///
        xperiod(`fitstart'(1)`beforeyear') ///
        nested allopt ///
        keep("`name'_synth_results.dta", replace)
    if _rc {
        capture quietly synth log_pub_total `controls' `lags', ///
            trunit(`id') trperiod(`treatyear') ///
            counit($control_ids) ///
            xperiod(`fitstart'(1)`beforeyear') ///
            allopt ///
            keep("`name'_synth_results.dta", replace)
    }
    if _rc {
        synth log_pub_total `controls' `lags', ///
            trunit(`id') trperiod(`treatyear') ///
            counit($control_ids) ///
            xperiod(`fitstart'(1)`beforeyear') ///
            keep("`name'_synth_results.dta", replace)
    }

    use "`name'_synth_results.dta", clear
    rename _time Year
    rename _Y_treated `name'_actual
    rename _Y_synthetic `name'_synthetic
    gen `name'_gap = `name'_actual - `name'_synthetic
    gen `name'_actual_real = exp(`name'_actual) - 1
    gen `name'_synthetic_real = exp(`name'_synthetic) - 1
    gen `name'_gap_pct_effect = `name'_actual_real - `name'_synthetic_real
    gen `name'_gap_pct = (`name'_actual_real - `name'_synthetic_real) / `name'_actual_real * 100
    gen log_gap_`name' = `name'_actual - `name'_synthetic
    gen pre_sq_error_`name' = log_gap_`name'^2 if Year <= `beforeyear' & Year >= `fitstart'
    egen pre_mspe_`name' = mean(pre_sq_error_`name')
    gen pre_rmspe_`name' = sqrt(pre_mspe_`name')
    gen post_sq_error_`name' = log_gap_`name'^2 if Year >= `treatyear'
    egen post_mspe_`name' = mean(post_sq_error_`name')
    gen post_rmspe_`name' = sqrt(post_mspe_`name')
    gen rmspe_ratio_`name' = post_rmspe_`name' / pre_rmspe_`name'
    drop if missing(Year)
    save "`outdir'/`name'_synth_results.dta", replace
end

capture program drop run_ratio_treated
program define run_ratio_treated
    syntax, OUTdir(string) NAME(string) ID(integer) Treatyear(integer) ///
        Beforeyear(integer) FITstart(integer) CONTROLS(string) LAGS(string)

    cd "`outdir'"
    use "`outdir'/processed_data.dta", clear
    capture quietly synth intl_ratio `controls' `lags', ///
        trunit(`id') trperiod(`treatyear') ///
        counit($control_ids) ///
        xperiod(`fitstart'(1)`beforeyear') ///
        nested allopt ///
        keep("`name'_synth_results.dta", replace)
    if _rc {
        capture quietly synth intl_ratio `controls' `lags', ///
            trunit(`id') trperiod(`treatyear') ///
            counit($control_ids) ///
            xperiod(`fitstart'(1)`beforeyear') ///
            allopt ///
            keep("`name'_synth_results.dta", replace)
    }
    if _rc {
        synth intl_ratio `controls' `lags', ///
            trunit(`id') trperiod(`treatyear') ///
            counit($control_ids) ///
            xperiod(`fitstart'(1)`beforeyear') ///
            keep("`name'_synth_results.dta", replace)
    }

    use "`name'_synth_results.dta", clear
    rename _time Year
    rename _Y_treated `name'_actual
    rename _Y_synthetic `name'_synthetic
    gen `name'_gap = `name'_actual - `name'_synthetic
    egen `name'_avg_effect = mean(`name'_gap) if Year >= `treatyear'
    gen pre_sq_error_`name' = `name'_gap^2 if Year <= `beforeyear' & Year >= `fitstart'
    egen pre_mspe_`name' = mean(pre_sq_error_`name')
    gen pre_rmspe_`name' = sqrt(pre_mspe_`name')
    gen post_sq_error_`name' = `name'_gap^2 if Year >= `treatyear'
    egen post_mspe_`name' = mean(post_sq_error_`name')
    gen post_rmspe_`name' = sqrt(post_mspe_`name')
    gen rmspe_ratio_`name' = post_rmspe_`name' / pre_rmspe_`name'
    drop if missing(Year)
    save "`outdir'/`name'_synth_results.dta", replace
end

capture program drop run_total_placebos
program define run_total_placebos
    syntax, OUTdir(string) Treatyear(integer) Beforeyear(integer) FITstart(integer) ///
        CONTROLS(string) LAGS(string) [FALLBACK(string)]

    cd "`outdir'"
    clear_gap_outputs

    foreach country of global control_countries {
        di as text "Total placebo: `country'"
        use "`outdir'/processed_data.dta", clear
        quietly summarize country_id if Country == "`country'"
        local treat_id = r(mean)

        local placebo_controls
        foreach ctrl of global control_countries {
            if "`ctrl'" != "`country'" {
                quietly summarize country_id if Country == "`ctrl'"
                if !missing(r(mean)) local placebo_controls "`placebo_controls' `=r(mean)'"
            }
        }

        capture quietly synth log_pub_total `controls' `lags', ///
            trunit(`treat_id') trperiod(`treatyear') ///
            counit(`placebo_controls') ///
            xperiod(`fitstart'(1)`beforeyear') ///
            allopt ///
            keep("synth_`country'.dta", replace)

        if _rc & "`fallback'" != "" {
            capture quietly synth log_pub_total `controls' `fallback', ///
                trunit(`treat_id') trperiod(`treatyear') ///
                counit(`placebo_controls') ///
                xperiod(`fitstart'(1)`beforeyear') ///
                allopt ///
                keep("synth_`country'.dta", replace)
        }

        if _rc {
            capture quietly synth log_pub_total `controls' `lags', ///
                trunit(`treat_id') trperiod(`treatyear') ///
                counit(`placebo_controls') ///
                xperiod(`fitstart'(1)`beforeyear') ///
                allopt ///
                keep("synth_`country'.dta", replace)
        }

        if _rc {
            capture quietly synth log_pub_total `controls' `lags', ///
                trunit(`treat_id') trperiod(`treatyear') ///
                counit(`placebo_controls') ///
                xperiod(`fitstart'(1)`beforeyear') ///
                keep("synth_`country'.dta", replace)
        }

        if _rc {
            di as error "Total placebo failed for `country'"
            continue
        }

        use "synth_`country'.dta", clear
        rename _time Year
        gen actual_real = exp(_Y_treated) - 1
        gen synthetic_real = exp(_Y_synthetic) - 1
        gen gap_effect_`country' = actual_real - synthetic_real
        gen gap_pct_`country' = (actual_real - synthetic_real) / actual_real * 100
        egen avg_effect = mean(gap_pct_`country') if Year >= `treatyear'
        gen avg_gap_pct_`country' = avg_effect
        keep Year gap_effect_`country' gap_pct_`country' avg_gap_pct_`country'
        drop if missing(Year)
        save "gap_`country'.dta", replace
    }
end

capture program drop run_ratio_placebos
program define run_ratio_placebos
    syntax, OUTdir(string) Treatyear(integer) Beforeyear(integer) FITstart(integer) ///
        CONTROLS(string) LAGS(string) [FALLBACK(string)]

    cd "`outdir'"
    clear_gap_outputs

    foreach country of global control_countries {
        di as text "Ratio placebo: `country'"
        use "`outdir'/processed_data.dta", clear
        quietly summarize country_id if Country == "`country'"
        local treat_id = r(mean)

        local placebo_controls
        foreach ctrl of global control_countries {
            if "`ctrl'" != "`country'" {
                quietly summarize country_id if Country == "`ctrl'"
                if !missing(r(mean)) local placebo_controls "`placebo_controls' `=r(mean)'"
            }
        }

        capture quietly synth intl_ratio `controls' `lags', ///
            trunit(`treat_id') trperiod(`treatyear') ///
            counit(`placebo_controls') ///
            xperiod(`fitstart'(1)`beforeyear') ///
            allopt ///
            keep("synth_`country'.dta", replace)

        if _rc & "`fallback'" != "" {
            capture quietly synth intl_ratio `controls' `fallback', ///
                trunit(`treat_id') trperiod(`treatyear') ///
                counit(`placebo_controls') ///
                xperiod(`fitstart'(1)`beforeyear') ///
                allopt ///
                keep("synth_`country'.dta", replace)
        }

        if _rc {
            capture quietly synth intl_ratio `controls' `lags', ///
                trunit(`treat_id') trperiod(`treatyear') ///
                counit(`placebo_controls') ///
                xperiod(`fitstart'(1)`beforeyear') ///
                allopt ///
                keep("synth_`country'.dta", replace)
        }

        if _rc {
            capture quietly synth intl_ratio `controls' `lags', ///
                trunit(`treat_id') trperiod(`treatyear') ///
                counit(`placebo_controls') ///
                xperiod(`fitstart'(1)`beforeyear') ///
                keep("synth_`country'.dta", replace)
        }

        if _rc {
            di as error "Ratio placebo failed for `country'"
            continue
        }

        use "synth_`country'.dta", clear
        rename _time Year
        rename _Y_treated cc_actual
        rename _Y_synthetic cc_synthetic
        gen gap_`country' = cc_actual - cc_synthetic
        egen avg_effect = mean(gap_`country') if Year >= `treatyear'
        gen avg_gap_`country' = avg_effect
        keep Year gap_`country' avg_gap_`country'
        drop if missing(Year)
        save "gap_`country'.dta", replace
    }
end

capture program drop merge_total_outputs
program define merge_total_outputs
    syntax, OUTdir(string) TREATEDfiles(string)

    cd "`outdir'"
    local first ""
    foreach country of global control_countries {
        capture confirm file "gap_`country'.dta"
        if !_rc & "`first'" == "" {
            use "gap_`country'.dta", clear
            local first "`country'"
        }
    }
    foreach country of global control_countries {
        if "`country'" != "`first'" {
            capture merge 1:1 Year using "gap_`country'.dta", nogenerate
        }
    }
    foreach file of local treatedfiles {
        merge 1:1 Year using "`file'", nogenerate
    }
    save "all_gaps_merged.dta", replace
end

capture program drop merge_ratio_outputs
program define merge_ratio_outputs
    syntax, OUTdir(string) TREATEDfiles(string)

    cd "`outdir'"
    local first ""
    foreach country of global control_countries {
        capture confirm file "gap_`country'.dta"
        if !_rc & "`first'" == "" {
            use "gap_`country'.dta", clear
            local first "`country'"
        }
    }
    foreach country of global control_countries {
        if "`country'" != "`first'" {
            capture merge 1:1 Year using "gap_`country'.dta", nogenerate
        }
    }
    foreach file of local treatedfiles {
        merge 1:1 Year using "`file'", nogenerate
    }
    save "final_results.dta", replace
end

********************************************************************************
* Brexit
********************************************************************************

local base "$root/code/Brexit-stata_external_try"
local total_out "`base'/total_publications"
local ratio_out "`base'/intl_ratio"

setup_common_data, source("`base'/brexit_non_eu.xlsx") outdir("`total_out'")
use "`total_out'/processed_data.dta", clear
build_controls, exclude("EU UNITED_KINGDOM")
global control_countries `"`control_countries'"'
global control_ids "`control_ids'"
global uk_total_controls "log_pub_pre_mean_uk_final"

* Brexit-specific pre-treatment means for total publications.
bysort country_id: egen log_pub_pre_mean_uk = mean(log_pub_total) if Year >= 2005 & Year <= 2012
bysort country_id: egen log_pub_pre_mean_uk_final = max(log_pub_pre_mean_uk)
save "`total_out'/processed_data.dta", replace
quietly summarize country_id if Country == "UNITED_KINGDOM"
local uk_id = r(mean)
run_total_treated, outdir("`total_out'") name("uk") id(`uk_id') treatyear(2016) beforeyear(2015) fitstart(2008) controls("log_pub_pre_mean_uk_final") lags("log_pub_total(2013)")
run_total_placebos, outdir("`total_out'") treatyear(2016) beforeyear(2015) fitstart(2008) controls("log_pub_pre_mean_uk_final") lags("log_pub_total(2013)")
merge_total_outputs, outdir("`total_out'") treatedfiles("uk_synth_results.dta")

setup_common_data, source("`base'/brexit_non_eu.xlsx") outdir("`ratio_out'")
use "`ratio_out'/processed_data.dta", clear
build_controls, exclude("EU UNITED_KINGDOM")
global control_countries `"`control_countries'"'
global control_ids "`control_ids'"
bysort country_id: egen intl_ratio_mean = mean(intl_ratio) if Year >= 2005 & Year <= 2015
bysort country_id: egen intl_ratio_mean_final = max(intl_ratio_mean)
save "`ratio_out'/processed_data.dta", replace
quietly summarize country_id if Country == "UNITED_KINGDOM"
local uk_id = r(mean)
run_ratio_treated, outdir("`ratio_out'") name("uk") id(`uk_id') treatyear(2016) beforeyear(2015) fitstart(2008) controls("intl_ratio_mean_final") lags("intl_ratio(2015) intl_ratio(2014) intl_ratio(2011) intl_ratio(2010)")
run_ratio_placebos, outdir("`ratio_out'") treatyear(2016) beforeyear(2015) fitstart(2008) controls("intl_ratio_mean_final") lags("intl_ratio(2015) intl_ratio(2014) intl_ratio(2011) intl_ratio(2010)")
merge_ratio_outputs, outdir("`ratio_out'") treatedfiles("uk_synth_results.dta")

********************************************************************************
* Crimean crisis
********************************************************************************

local base "$root/code/crimes"
local total_out "`base'/total_publications"
local ratio_out "`base'/intl_ratio"

setup_common_data, source("`base'/original_completed.xlsx") outdir("`total_out'")
use "`total_out'/processed_data.dta", clear
build_controls, exclude("RUSSIAN_FEDERATION UKRAINE")
global control_countries `"`control_countries'"'
global control_ids "`control_ids'"
quietly summarize country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)
quietly summarize country_id if Country == "UKRAINE"
local ukraine_id = r(mean)
run_total_treated, outdir("`total_out'") name("russia") id(`russia_id') treatyear(2014) beforeyear(2013) fitstart(2008) controls("log_gdp_per_capita_10 log_rp_10 RD") lags("log_pub_total(2013) log_pub_total(2012) log_pub_total(2010) log_pub_total(2009) log_pub_total(2008)")
run_total_treated, outdir("`total_out'") name("ukraine") id(`ukraine_id') treatyear(2014) beforeyear(2013) fitstart(2008) controls("log_gdp_per_capita_10 log_rp_10 RD") lags("log_pub_total(2013) log_pub_total(2012) log_pub_total(2011) log_pub_total(2010) log_pub_total(2008)")
run_total_placebos, outdir("`total_out'") treatyear(2014) beforeyear(2013) fitstart(2008) controls("log_gdp_per_capita_10 log_rp_10 RD") lags("log_pub_total(2013) log_pub_total(2012) log_pub_total(2011) log_pub_total(2010) log_pub_total(2008)") fallback("log_pub_total(2013) log_pub_total(2012) log_pub_total(2010) log_pub_total(2009) log_pub_total(2008)")
merge_total_outputs, outdir("`total_out'") treatedfiles("ukraine_synth_results.dta russia_synth_results.dta")

setup_common_data, source("`base'/original_completed.xlsx") outdir("`ratio_out'")
use "`ratio_out'/processed_data.dta", clear
build_controls, exclude("RUSSIAN_FEDERATION UKRAINE")
global control_countries `"`control_countries'"'
global control_ids "`control_ids'"
quietly summarize country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)
quietly summarize country_id if Country == "UKRAINE"
local ukraine_id = r(mean)
run_ratio_treated, outdir("`ratio_out'") name("russia") id(`russia_id') treatyear(2014) beforeyear(2013) fitstart(2008) controls("log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD") lags("intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2008) intl_ratio(2007) intl_ratio(2006)")
run_ratio_treated, outdir("`ratio_out'") name("ukraine") id(`ukraine_id') treatyear(2014) beforeyear(2013) fitstart(2008) controls("log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD") lags("intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2009) intl_ratio(2008)")
run_ratio_placebos, outdir("`ratio_out'") treatyear(2014) beforeyear(2013) fitstart(2008) controls("log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD") lags("intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2009) intl_ratio(2008)") fallback("intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2008) intl_ratio(2007) intl_ratio(2006)")
merge_ratio_outputs, outdir("`ratio_out'") treatedfiles("ukraine_synth_results.dta russia_synth_results.dta")

********************************************************************************
* 2022 full-scale invasion
********************************************************************************

local base "$root/code/crimes_2015_2022"
local total_out "`base'/total_publications"
local ratio_out "`base'/intl_ratio"

setup_common_data, source("`base'/original_completed.xlsx") outdir("`total_out'")
use "`total_out'/processed_data.dta", clear
build_controls, exclude("RUSSIAN_FEDERATION UKRAINE")
global control_countries `"`control_countries'"'
global control_ids "`control_ids'"
quietly summarize country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)
quietly summarize country_id if Country == "UKRAINE"
local ukraine_id = r(mean)
run_total_treated, outdir("`total_out'") name("russia") id(`russia_id') treatyear(2022) beforeyear(2021) fitstart(2015) controls("log_gdp_per_capita_10 log_rp_10 RD") lags("log_pub_total(2021) log_pub_total(2020) log_pub_total(2018) log_pub_total(2017) log_pub_total(2015)")
run_total_treated, outdir("`total_out'") name("ukraine") id(`ukraine_id') treatyear(2022) beforeyear(2021) fitstart(2015) controls("log_gdp_per_capita_10 log_rp_10 RD") lags("log_pub_total(2021) log_pub_total(2020) log_pub_total(2019) log_pub_total(2018) log_pub_total(2017)")
run_total_placebos, outdir("`total_out'") treatyear(2022) beforeyear(2021) fitstart(2015) controls("log_gdp_per_capita_10 log_rp_10 RD") lags("log_pub_total(2021) log_pub_total(2020) log_pub_total(2019) log_pub_total(2018) log_pub_total(2017)") fallback("log_pub_total(2021) log_pub_total(2020) log_pub_total(2018) log_pub_total(2017) log_pub_total(2015)")
merge_total_outputs, outdir("`total_out'") treatedfiles("ukraine_synth_results.dta russia_synth_results.dta")

setup_common_data, source("`base'/original_completed.xlsx") outdir("`ratio_out'")
use "`ratio_out'/processed_data.dta", clear
build_controls, exclude("RUSSIAN_FEDERATION UKRAINE")
global control_countries `"`control_countries'"'
global control_ids "`control_ids'"
quietly summarize country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)
quietly summarize country_id if Country == "UKRAINE"
local ukraine_id = r(mean)
run_ratio_treated, outdir("`ratio_out'") name("russia") id(`russia_id') treatyear(2022) beforeyear(2021) fitstart(2015) controls("log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD") lags("intl_ratio(2021) intl_ratio(2019) intl_ratio(2017) intl_ratio(2015)")
run_ratio_treated, outdir("`ratio_out'") name("ukraine") id(`ukraine_id') treatyear(2022) beforeyear(2021) fitstart(2015) controls("log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD") lags("intl_ratio(2021) intl_ratio(2020) intl_ratio(2019) intl_ratio(2018) intl_ratio(2017)")
run_ratio_placebos, outdir("`ratio_out'") treatyear(2022) beforeyear(2021) fitstart(2015) controls("log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD") lags("intl_ratio(2021) intl_ratio(2020) intl_ratio(2019) intl_ratio(2018) intl_ratio(2017)") fallback("intl_ratio(2021) intl_ratio(2019) intl_ratio(2017) intl_ratio(2015)")
merge_ratio_outputs, outdir("`ratio_out'") treatedfiles("ukraine_synth_results.dta russia_synth_results.dta")

display as text "Standardized total and ratio placebo outputs rebuilt."
