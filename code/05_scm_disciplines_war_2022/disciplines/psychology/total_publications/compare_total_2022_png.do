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

cd "$CODE/05_scm_disciplines_war_2022/disciplines/psychology/total_publications"

local discipline psychology


* 1. 加载2014年的结果数据
use "$CODE/05_scm_disciplines_crimea_2014/disciplines/`discipline'/total_publications/ukraine_synth_results.dta", clear
rename ukraine_synthetic_real ukraine_synthetic_real_2014  // 先重命名2014年的变量
rename ukraine_gap_pct ukraine_gap_pct_2014  // 重命名2014年的gap变量

merge 1:1 Year using "$CODE/05_scm_disciplines_crimea_2014/disciplines/`discipline'/total_publications/russia_synth_results.dta", nogenerate
rename russia_synthetic_real russia_synthetic_real_2014    // 重命名2014年的俄罗斯变量
rename russia_gap_pct russia_gap_pct_2014    // 重命名2014年的gap变量

* 保存2014年的效应值
sum ukraine_gap_pct_2014 if Year >= 2014
local ukraine_effect_2014 = r(mean)
sum russia_gap_pct_2014 if Year >= 2014
local russia_effect_2014 = r(mean)

* 2. 加载2022年的结果并合并
merge 1:1 Year using "../../`discipline'/total_publications/ukraine_synth_results.dta", nogenerate
rename ukraine_synthetic_real ukraine_synthetic_real_2022  // 重命名2022年的变量
rename ukraine_gap_pct ukraine_gap_pct_2022  // 重命名2022年的gap变量
merge 1:1 Year using "../../`discipline'/total_publications/russia_synth_results.dta", nogenerate
rename russia_synthetic_real russia_synthetic_real_2022    // 重命名2022年的变量
rename russia_gap_pct russia_gap_pct_2022    // 重命名2022年的gap变量

* 获取2022年效应值
sum ukraine_gap_pct_2022 if Year >= 2022
local ukraine_effect_2022 = r(mean)
sum russia_gap_pct_2022 if Year >= 2022
local russia_effect_2022 = r(mean)

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
* 绘图
twoway (line ukraine_actual_real Year, lcolor("137 202 229") lwidth(medthick)) ///
       (line ukraine_synthetic_real_2014 Year, lcolor("137 202 229") lwidth(medthick) lpattern(dash_dot)) ///
	   (line ukraine_synthetic_real_2022 Year, lcolor("137 202 229") lwidth(medthick) lpattern(dash)) ///
	   (line russia_actual_real Year, lcolor(orange_red) lwidth(medthick)) ///
	   (line russia_synthetic_real_2014 Year, lcolor(orange_red) lwidth(medthick) lpattern(dash_dot)) ///
       (line russia_synthetic_real_2022 Year, lcolor(orange_red) lwidth(medthick) lpattern(dash)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       xline(2014, lpattern(dash_dot) lcolor(gray)) ///
       text(1000 2014.2 "Crimean", placement(east)) ///
       text(1000 2022.2 "War", placement(east)) ///
	   text(700 2018 `"Ukraine (2014): `=string(`ukraine_effect_2014',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Ukraine (2022): `=string(`ukraine_effect_2022',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Russia (2014) : `=string( `russia_effect_2014',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Russia (2022) : `=string( `russia_effect_2022',"%5.2f")'%"', size(medium)) ///
       xtitle("") ///
       ytitle("total number of publications", size(medium)) ///
       xlabel(2004(2)2024, nogrid tposition(inside)) ///
       ylabel(0(200)1000, nogrid tposition(inside) format(%9.0gc)) ///
       xmtick(2004(1)2024, tposition(inside)) ///
       ymtick(0(100)1000, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Ukraine Actual" 2 "Ukraine Synthetic(2014)" 3 "Ukraine Synthetic(2022)" ///
                    4 "Russia Actual" 5 "Russia Synthetic(2014)" 6 "Russia Synthetic(2022)") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison_real, replace)

// graph export "$CODE/crimes_2022/total_publications/1combined_actual_vs_synthetic.eps", replace
graph export "../../`discipline'/total_publications/1combined_actual_vs_synthetic.png", ///
       width(1200) height(800) replace
