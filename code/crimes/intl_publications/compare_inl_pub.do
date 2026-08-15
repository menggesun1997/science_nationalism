* 首先加载russia数据

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

use "$CODE/crimes/intl_publications/russia/russia_synth_results.dta", clear

* 生成russia的gap
// gen russia_gap = russia_actual - russia_synthetic

* 检查重复值并保留每个年份的第一个观察值
duplicates list Year
bysort Year: keep if _n == 1

* 将russia数据暂时保存
tempfile russia_data
save `russia_data'

* 加载ukraine数据
use "$CODE/crimes/intl_publications/ukraine/ukraine_synth_results.dta", clear

* 生成ukraine的gap
// gen ukraine_gap = ukraine_actual - ukraine_synthetic

* 检查重复值并保留每个年份的第一个观察值
duplicates list Year
bysort Year: keep if _n == 1

* 合并数据
merge 1:1 Year using `russia_data'
drop _merge

* 计算处理后期的平均效应
sum ukraine_gap if Year >= 2014
local ukraine_avg_effect = r(mean)
local ukraine_avg_effect_display = string(`ukraine_avg_effect', "%9.3f")

sum russia_gap if Year >= 2014
local russia_avg_effect = r(mean)
local russia_avg_effect_display = string(`russia_avg_effect', "%9.3f")

* 绘制四条线的图
twoway (line russia_actual Year, lcolor(blue) lwidth(thick)) ///
       (line russia_synthetic Year, lcolor(blue) lpattern(dash)) ///
       (line ukraine_actual Year, lcolor(red) lwidth(thick)) ///
       (line ukraine_synthetic Year, lcolor(red) lpattern(dash)), ///
       xline(2014, lpattern(dash) lcolor(gray)) ///
	   legend(order(5 `"Russia Effect: `russia_avg_effect_display'"' ///
                   6 `"Ukraine Effect: `ukraine_avg_effect_display'"') ///
              pos(3) ring(0) rows(2) region(style(none)) size(small)) ///
       title("Synthetic Control Results: Russia(blue) vs Ukraine(red)", size(large)) ///
       subtitle("Average Effect - Russia: `russia_avg_effect_display', Ukraine: `ukraine_avg_effect_display'", size(medium)) ///
       xtitle("Year", size(medium)) ///
       ytitle("International Publications (log)", size(medium)) ///
       xlabel(2005(2)2023) ///
       graphregion(color(white)) bgcolor(white) ///
       name(synth_comparison, replace)

* 保存图形
graph export "$CODE/crimes/intl_publications/russia_ukraine_comparison.png", ///
       width(1200) height(800) replace

// * 如果您也想看差距图
// gen uk_gap = uk_actual - uk_synthetic
// gen eu_gap = eu_actual - eu_synthetic
//
// twoway (line uk_gap Year, lcolor(blue) lwidth(thick)) ///
//        (line eu_gap Year, lcolor(red) lwidth(thick)), ///
//        xline(2016, lpattern(dash) lcolor(gray)) ///
//        yline(0, lcolor(black)) ///
//        legend(order(1 "UK Gap" 2 "EU Gap") pos(6)) ///
//        title("Gap Plot: UK vs EU", size(large)) ///
//        xtitle("Year", size(medium)) ///
//        ytitle("Gap (Actual - Synthetic)", size(medium)) ///
//        xlabel(#10, angle(45)) ///
//        graphregion(color(white)) bgcolor(white) ///
//        name(gap_comparison, replace)
//
// * 保存差距图
// graph export "$CODE/Brexit-stata_external_try/total_publications/uk_eu_gaps.png", ///
//        width(1200) height(800) replace
