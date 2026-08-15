clear all
set more off

********************************************************************************
* In-space placebo visualization
*
* This file only visualizes existing SCM placebo outputs. It does not re-run
* synth. The plotting rule is:
*   - treated units: colored solid lines
*   - donor placebos: gray dashed lines
*   - y-axis: treatment effect
*   - p-value: RMSPE-ratio placebo p-value using all valid donor placebos
********************************************************************************

global root "/Users/sunmengge/Dropbox/GitHub/sicence nationism"
global fig_dir "$root/paper/figure_SI"
global rmspe_multiplier 5

capture program drop calc_placebo_p
program define calc_placebo_p, rclass
    syntax varname, Donors(varlist) Treatyear(integer) [Multiplier(real 5)]

    tempvar sq
    quietly gen double `sq' = `varlist'^2
    quietly summarize `sq' if Year < `treatyear'
    local pre = sqrt(r(mean))
    quietly summarize `sq' if Year >= `treatyear'
    local post = sqrt(r(mean))
    drop `sq'

    if missing(`pre') | `pre' == 0 | missing(`post') {
        return scalar p = .
        return scalar treated_ratio = .
        return scalar n_placebos = 0
        exit
    }

    local treated_ratio = `post' / `pre'
    local pre_threshold = `multiplier' * `pre'
    local n_placebos = 0
    local n_extreme = 0
    local n_qualified = 0
    local qualified ""

    foreach donor of varlist `donors' {
        tempvar dsq
        quietly gen double `dsq' = `donor'^2
        quietly summarize `dsq' if Year < `treatyear'
        local dpre = sqrt(r(mean))
        quietly summarize `dsq' if Year >= `treatyear'
        local dpost = sqrt(r(mean))
        drop `dsq'

        if !missing(`dpre') & `dpre' > 0 & !missing(`dpost') {
            local dratio = `dpost' / `dpre'
            local n_placebos = `n_placebos' + 1
            if `dratio' >= `treated_ratio' {
                local n_extreme = `n_extreme' + 1
            }
            if `dpre' <= `pre_threshold' {
                local n_qualified = `n_qualified' + 1
                local qualified "`qualified' `donor'"
            }
        }
    }

    return scalar p = (1 + `n_extreme') / (1 + `n_placebos')
    return scalar treated_ratio = `treated_ratio'
    return scalar treated_pre_rmspe = `pre'
    return scalar pre_threshold = `pre_threshold'
    return scalar n_placebos = `n_placebos'
    return scalar n_qualified = `n_qualified'
    return local qualified "`qualified'"
end

capture program drop draw_placebo_graph
program define draw_placebo_graph
    syntax, Donors(varlist) Tr1(name) Lab1(string) Color1(string) ///
        Treatyear(integer) OUTfile(string) TITLE(string) YTITLE(string) ///
        Xmin(integer) Xmax(integer) ///
        [Tr2(name) Lab2(string) Color2(string) Multiplier(real 5)]

    local treated_vars "`tr1'"
    if "`tr2'" != "" local treated_vars "`treated_vars' `tr2'"

    calc_placebo_p `tr1', donors(`donors') treatyear(`treatyear') multiplier(`multiplier')
    local p1 : display %4.3f r(p)
    local n1 = r(n_placebos)
    local qn1 = r(n_qualified)
    local q1 "`r(qualified)'"
    local donors_to_plot "`q1'"
    local ptext1 "p-value (`lab1') = `p1' (N=`n1')"

    if "`tr2'" != "" {
        calc_placebo_p `tr2', donors(`donors') treatyear(`treatyear') multiplier(`multiplier')
        local p2 : display %4.3f r(p)
        local n2 = r(n_placebos)
        local qn2 = r(n_qualified)
        local q2 "`r(qualified)'"
        local ptext2 "p-value (`lab2') = `p2' (N=`n2')"

        foreach donor of local q2 {
            if strpos(" `donors_to_plot' ", " `donor' ") == 0 {
                local donors_to_plot "`donors_to_plot' `donor'"
            }
        }
    }

    tempvar rowmin rowmax
    if "`donors_to_plot'" == "" {
        local donors_to_plot "`donors'"
    }

    egen double `rowmin' = rowmin(`donors_to_plot' `treated_vars')
    egen double `rowmax' = rowmax(`donors_to_plot' `treated_vars')
    quietly summarize `rowmin'
    local ymin = r(min)
    quietly summarize `rowmax'
    local ymax = r(max)
    local yrange = `ymax' - `ymin'
    if `yrange' <= 0 | missing(`yrange') local yrange = 1
    local ytext = `ymax' - 0.06 * `yrange'
    local xtext = `xmin' + 0.35

    if (`xmax' - `xmin') <= 10 {
        local xlabel_spec "`xmin'(1)`xmax'"
    }
    else {
        local xlabel_spec "`xmin'(2)`xmax'"
    }

    local donor_lines ""
    local ndonors = 0
    local max_high_labels = 3
    local max_low_labels = 3

    local score_count = 0
    foreach donor of varlist `donors_to_plot' {
        quietly summarize Year if !missing(`donor')
        local tail_year = r(max)
        quietly summarize `donor' if Year == `tail_year'
        local tail_value = r(mean)
        if !missing(`tail_value') {
            local score_count = `score_count' + 1
            local score_donor`score_count' "`donor'"
            local score_value`score_count' = `tail_value'
        }
    }

    local label_donors ""
    local label_indices ""
    forvalues k = 1/`max_high_labels' {
        local best_donor ""
        local best_idx = .
        local best_score = .
        forvalues j = 1/`score_count' {
            if strpos(" `label_indices' ", " `j' ") == 0 {
                if missing(`best_score') | `score_value`j'' > `best_score' {
                    local best_score = `score_value`j''
                    local best_donor "`score_donor`j''"
                    local best_idx = `j'
                }
            }
        }
        if "`best_donor'" != "" {
            local label_donors "`label_donors' `best_donor'"
            local label_indices "`label_indices' `best_idx'"
        }
    }
    forvalues k = 1/`max_low_labels' {
        local best_donor ""
        local best_idx = .
        local best_score = .
        forvalues j = 1/`score_count' {
            if strpos(" `label_indices' ", " `j' ") == 0 {
                if missing(`best_score') | `score_value`j'' < `best_score' {
                    local best_score = `score_value`j''
                    local best_donor "`score_donor`j''"
                    local best_idx = `j'
                }
            }
        }
        if "`best_donor'" != "" {
            local label_donors "`label_donors' `best_donor'"
            local label_indices "`label_indices' `best_idx'"
        }
    }

    foreach donor of varlist `donors_to_plot' {
        local donor_lines `"`donor_lines' (line `donor' Year, sort lcolor(gs8%80) lpattern(dash) lwidth(thin))"'
        local ndonors = `ndonors' + 1
    }

    local donor_leaders ""
    local donor_label_options ""
    local label_count = 0
    foreach donor of local label_donors {
        quietly summarize Year if !missing(`donor')
        local label_year = r(max)
        quietly summarize `donor' if Year == `label_year'
        local label_y = r(mean)
        local label_count = `label_count' + 1
        local label_donor`label_count' "`donor'"
        local label_year`label_count' = `label_year'
        local label_y`label_count' = `label_y'
    }

    local placed_labels ""
    forvalues k = 1/`label_count' {
        local best_idx = .
        local best_y = .
        forvalues j = 1/`label_count' {
            if strpos(" `placed_labels' ", " `j' ") == 0 {
                if missing(`best_y') | `label_y`j'' < `best_y' {
                    local best_y = `label_y`j''
                    local best_idx = `j'
                }
            }
        }
        if missing(`best_idx') continue
        local placed_labels "`placed_labels' `best_idx'"
        local donor "`label_donor`best_idx''"
        local label_year = `label_year`best_idx''
        local label_y = `label_y`best_idx''
        local min_gap = 0.095 * `yrange'
        local label_text_y = `label_y'
        if `k' > 1 {
            local previous_y = `last_label_y'
            if `label_text_y' < `previous_y' + `min_gap' {
                local label_text_y = `previous_y' + `min_gap'
            }
        }
        if `label_text_y' > `ymax' + 0.20 * `yrange' {
            local label_text_y = `ymax' + 0.20 * `yrange'
        }
        local last_label_y = `label_text_y'
        local lead_x = `label_year' + 0.35
        local text_x = `label_year' + 0.58
        local donor_label : variable label `donor'
        if "`donor_label'" == "" local donor_label "`donor'"
        if "`donor_label'" == "RUSSIAN FEDERATION" local donor_label "RUSSIA"
        if "`donor_label'" == "UNITED STATES" local donor_label "US"
        if "`donor_label'" == "UNITED KINGDOM" local donor_label "UK"
        if "`donor_label'" == "SLOVAK REPUBLIC" local donor_label "SLOVAKIA"
        local donor_leaders `"`donor_leaders' (pci `label_y' `label_year' `label_text_y' `lead_x', lcolor(gs5) lwidth(vthin))"'
        local donor_label_options `"`donor_label_options' text(`label_text_y' `text_x' "`donor_label'", size(vsmall) color(gs5) placement(e))"'
    }

    local t1order = `ndonors' + 1
    local treated_lines `"`treated_lines' (line `tr1' Year, sort lcolor("`color1'") lpattern(solid) lwidth(medthick))"'
    local legend_order `"`t1order' "`lab1'""'

    if "`tr2'" != "" {
        local t2order = `ndonors' + 2
        local treated_lines `"`treated_lines' (line `tr2' Year, sort lcolor("`color2'") lpattern(solid) lwidth(medthick))"'
        local legend_order `"`legend_order' `t2order' "`lab2'""'
    }

    if "`tr2'" != "" {
        local pvalue_text `"text(`ytext' `xtext' "`ptext1'" "`ptext2'", size(medsmall) placement(e) color(black))"'
    }
    else {
        local pvalue_text `"text(`ytext' `xtext' "`ptext1'", size(medsmall) placement(e) color(black))"'
    }

    twoway `donor_lines' `treated_lines' `donor_leaders', ///
        xline(`treatyear', lpattern(dot) lcolor(black) lwidth(thin)) ///
        yline(0, lcolor(black) lwidth(thin)) ///
        `pvalue_text' ///
        `donor_label_options' ///
        title("`title'", size(medsmall) justification(left) position(11)) ///
        xtitle("") ///
        ytitle("`ytitle'", size(small)) ///
        xlabel(`xlabel_spec', nogrid labsize(small) tposition(inside)) ///
        ylabel(, nogrid labsize(small) tposition(inside)) ///
        xscale(range(`xmin' `=`xmax'+1.8')) ///
        xmtick(, tposition(inside)) ///
        ymtick(, tposition(inside)) ///
        graphregion(color(white) margin(r=10 l=5 t=5 b=5)) ///
        plotregion(style(outline) lcolor(black) lwidth(thin)) ///
        bgcolor(white) ///
        note("Gray donor lines shown use pre-RMSPE <= `multiplier'x treated pre-RMSPE; p-values use all valid donor placebos.", size(vsmall)) ///
        legend(order(`legend_order') pos(6) ring(0) cols(1) region(style(none)) size(vsmall)) ///
        name(placebo_graph, replace)

    graph export "`outfile'", replace
end

capture program drop plot_total_case
program define plot_total_case
    syntax, DATA(string) Treatyear(integer) Xmin(integer) OUTfile(string) ///
        TITLE(string) Tr1(name) Lab1(string) Color1(string) ///
        [Tr2(name) Lab2(string) Color2(string)]

    use "`data'", clear
    keep if Year >= `xmin'
    quietly summarize Year
    local xmax = r(max)

    ds gap_pct_*
    local raw_vars `r(varlist)'
    local donors ""
    foreach var of local raw_vars {
        if substr("`var'", 1, 15) != "gap_pct_effect_" & ///
           substr("`var'", 1, 12) != "avg_gap_pct_" {
            local donor_label = subinstr("`var'", "gap_pct_", "", .)
            local donor_label = subinstr("`donor_label'", "_", " ", .)
            label variable `var' "`donor_label'"
            local donors "`donors' `var'"
        }
    }

    if "`tr2'" != "" {
        draw_placebo_graph, donors(`donors') tr1(`tr1') lab1("`lab1'") ///
            color1("`color1'") treatyear(`treatyear') outfile("`outfile'") ///
            title("`title'") ytitle("Treatment effect (%)") ///
            xmin(`xmin') xmax(`xmax') multiplier($rmspe_multiplier) ///
            tr2(`tr2') lab2("`lab2'") color2("`color2'")
    }
    else {
        draw_placebo_graph, donors(`donors') tr1(`tr1') lab1("`lab1'") ///
            color1("`color1'") treatyear(`treatyear') outfile("`outfile'") ///
            title("`title'") ytitle("Treatment effect (%)") ///
            xmin(`xmin') xmax(`xmax') multiplier($rmspe_multiplier)
    }
end

capture program drop plot_ratio_case
program define plot_ratio_case
    syntax, BASEdir(string) Treatyear(integer) Xmin(integer) OUTfile(string) ///
        TITLE(string) File1(string) Gap1(string) Lab1(string) Color1(string) ///
        [File2(string) Gap2(string) Lab2(string) Color2(string) EXclude(string)]

    tempfile master donor_tmp
    use "`basedir'/`file1'", clear
    keep Year `gap1'
    rename `gap1' treated1
    replace treated1 = treated1 * 100
    keep if Year >= `xmin'
    quietly summarize Year
    local xmax = r(max)
    save `master', replace

    if "`file2'" != "" {
        use "`basedir'/`file2'", clear
        keep Year `gap2'
        rename `gap2' treated2
        replace treated2 = treated2 * 100
        keep if Year >= `xmin'
        merge 1:1 Year using `master', nogenerate
        save `master', replace
    }

    local files : dir "`basedir'" files "gap_*.dta"
    local donors ""
    local i = 0
    foreach file of local files {
        local country = subinstr("`file'", "gap_", "", .)
        local country = subinstr("`country'", ".dta", "", .)

        local skip_country = 0
        foreach excluded of local exclude {
            if "`country'" == "`excluded'" local skip_country = 1
        }

        if !`skip_country' {
            use "`basedir'/`file'", clear
            quietly summarize Year
            if r(max) < `xmax' {
                continue
            }
            ds gap_*
            local gapvar : word 1 of `r(varlist)'
            keep Year `gapvar'
            local i = `i' + 1
            rename `gapvar' donor`i'
            local donor_label = subinstr("`country'", "_", " ", .)
            label variable donor`i' "`donor_label'"
            replace donor`i' = donor`i' * 100
            keep if Year >= `xmin'
            save `donor_tmp', replace

            use `master', clear
            merge 1:1 Year using `donor_tmp', nogenerate
            save `master', replace
            local donors "`donors' donor`i'"
        }
    }

    use `master', clear

    if "`file2'" != "" {
        draw_placebo_graph, donors(`donors') tr1(treated1) lab1("`lab1'") ///
            color1("`color1'") treatyear(`treatyear') outfile("`outfile'") ///
            title("`title'") ytitle("Treatment effect (percentage points)") ///
            xmin(`xmin') xmax(`xmax') multiplier($rmspe_multiplier) ///
            tr2(treated2) lab2("`lab2'") color2("`color2'")
    }
    else {
        draw_placebo_graph, donors(`donors') tr1(treated1) lab1("`lab1'") ///
            color1("`color1'") treatyear(`treatyear') outfile("`outfile'") ///
            title("`title'") ytitle("Treatment effect (percentage points)") ///
            xmin(`xmin') xmax(`xmax') multiplier($rmspe_multiplier)
    }
end

* Brexit: only the United Kingdom is treated.
plot_total_case, ///
    data("$root/code/Brexit-stata_external_try/total_publications/all_gaps_merged.dta") ///
    treatyear(2016) xmin(2005) ///
    outfile("$fig_dir/brexit_in_space_placebo_total.pdf") ///
    title("Brexit in-space placebo: total publications") ///
    tr1(uk_gap_pct) lab1("United Kingdom") color1("201 6 43")

plot_ratio_case, ///
    basedir("$root/code/Brexit-stata_external_try/intl_ratio") ///
    treatyear(2016) xmin(2005) ///
    outfile("$fig_dir/brexit_in_space_placebo_ratio.pdf") ///
    title("Brexit in-space placebo: international collaboration ratio") ///
    file1("uk_synth_results.dta") gap1("uk_gap") ///
    lab1("United Kingdom") color1("201 6 43") ///
    exclude("UNITED_KINGDOM EU")

* 2014 Crimean crisis: Russia and Ukraine are treated units.
plot_total_case, ///
    data("$root/code/crimes/total_publications/all_gaps_merged.dta") ///
    treatyear(2014) xmin(2005) ///
    outfile("$fig_dir/crimean_in_space_placebo_total.pdf") ///
    title("Crimean crisis in-space placebo: total publications") ///
    tr1(russia_gap_pct) lab1("Russia") color1("76 92 156") ///
    tr2(ukraine_gap_pct) lab2("Ukraine") color2("227 195 65")

plot_ratio_case, ///
    basedir("$root/code/crimes/intl_ratio") ///
    treatyear(2014) xmin(2005) ///
    outfile("$fig_dir/crimean_in_space_placebo_ratio.pdf") ///
    title("Crimean crisis in-space placebo: international collaboration ratio") ///
    file1("russia_synth_results.dta") gap1("russia_gap") ///
    lab1("Russia") color1("76 92 156") ///
    file2("ukraine_synth_results.dta") gap2("ukraine_gap") ///
    lab2("Ukraine") color2("227 195 65") ///
    exclude("RUSSIA RUSSIAN_FEDERATION UKRAINE")

* 2022 full-scale invasion: Russia and Ukraine are treated units.
plot_total_case, ///
    data("$root/code/crimes_2015_2022/total_publications/all_gaps_merged.dta") ///
    treatyear(2022) xmin(2015) ///
    outfile("$fig_dir/war_in_space_placebo_total.pdf") ///
    title("Full-scale invasion in-space placebo: total publications") ///
    tr1(russia_gap_pct) lab1("Russia") color1("76 92 156") ///
    tr2(ukraine_gap_pct) lab2("Ukraine") color2("227 195 65")

plot_ratio_case, ///
    basedir("$root/code/crimes_2015_2022/intl_ratio") ///
    treatyear(2022) xmin(2015) ///
    outfile("$fig_dir/war_in_space_placebo_ratio.pdf") ///
    title("Full-scale invasion in-space placebo: international collaboration ratio") ///
    file1("russia_synth_results.dta") gap1("russia_gap") ///
    lab1("Russia") color1("76 92 156") ///
    file2("ukraine_synth_results.dta") gap2("ukraine_gap") ///
    lab2("Ukraine") color2("227 195 65") ///
    exclude("RUSSIA RUSSIAN_FEDERATION UKRAINE")

display as text "In-space placebo figures exported to $fig_dir"
