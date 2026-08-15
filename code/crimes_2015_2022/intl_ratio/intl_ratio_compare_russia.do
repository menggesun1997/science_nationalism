clear all
set more off

********************************************************************************
* 程序结构：
* 1. 数据准备和变量定义
* 2. RUSSIAN_FEDERATION合成控制分析
* 3. UKRAINE合成控制分析
* 4. 安慰剂检验
* 5. 结果可视化和统计分析
********************************************************************************

* 1. 数据准备和变量定义
* 1.1 导入数据

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

import excel "$CODE/crimes_2022/original_completed.xlsx", sheet("Sheet1") firstrow clear

* 替换国家名称中的空格为下划线
replace Country = subinstr(Country, " ", "_", .)

* 1.2 自动获取国家列表
levelsof Country, local(countries) clean


* 验证获取的国家列表
di "获取到的国家列表："
foreach country of local countries {
    di "`country'"
}
di "共计 `: word count `countries'' 个国家"

* 1.3 生成国家ID和分组
gen country_id = .
local i = 1
foreach country of local countries {
    replace country_id = `i' if Country == "`country'"  // 使用完全匹配
    local ++i
}


* 检查未匹配的国家
list Country if missing(country_id)

* 设置面板数据结构
xtset country_id Year

* 1.4 创建处理组和控制组
* 创建控制组国家列表
local control_countries
foreach country of local countries {
    if !inlist("`country'", "UKRAINE", "RUSSIAN_FEDERATION") {
        local control_countries `"`control_countries' "`country'""'
    }
}

* 获取控制组ID列表
local control_ids
foreach country of local control_countries {
    qui sum country_id if Country == "`country'"
    local control_ids "`control_ids' `r(mean)'"
}

* 获取处理组ID
qui sum country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)
qui sum country_id if Country == "UKRAINE"
local ukraine_id = r(mean)

* 1.5 生成分析所需变量
gen log_pub_total = log(pub_total + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

* 1.6 保存处理后的数据
save "$CODE/crimes_2022/intl_ratio/processed_data.dta", replace


* 2. RUSSIAN_FEDERATION合成控制分析
* 2.1 运行RUSSIAN_FEDERATION的合成控制分析
synth intl_ratio ///
    log_pub_total log_gdp_per_capita  log_rp RD /// 这些变量会使用xperiod限定范围内的变量数据
    intl_ratio(2021)  intl_ratio(2020) intl_ratio(2019) intl_ratio(2018) intl_ratio(2014) intl_ratio(2008(1)2013), /// 结果变量的滞后值
    trunit(`russia_id') trperiod(2022) ///
    counit(`control_ids') ///
    xperiod(2008(1)2021) ///
    nested allopt ///
    keep(russia_synth_results, replace)

* 2.2 处理RUSSIAN_FEDERATION结果
use russia_synth_results, clear
rename _time Year
rename _Y_treated russia_actual
rename _Y_synthetic russia_synthetic


* 2.3 计算RUSSIAN_FEDERATION效应（对于比例，直接计算差异，不是百分比变化）
* 假设russia_actual和russia_synthetic已经是比例值（0-1之间）
gen russia_gap = russia_actual - russia_synthetic

* 2.4 计算RUSSIAN_FEDERATION平均处理效应（对于比例，计算后期均值差异）
egen russia_avg_effect = mean(russia_gap) if Year >= 2022
local russia_avg_effect : display %5.4f r(mean)


* 2.5 计算RUSSIAN_FEDERATION的RMSPE
gen pre_sq_error_russia = russia_gap^2 if Year <= 2021
egen pre_mspe_russia = mean(pre_sq_error_russia)
gen pre_rmspe_russia = sqrt(pre_mspe_russia)
local pre_rmspe_russia : display %5.4f r(mean)

gen post_sq_error_russia = russia_gap^2 if Year >= 2022
egen post_mspe_russia = mean(post_sq_error_russia)
gen post_rmspe_russia = sqrt(post_mspe_russia)

gen rmspe_ratio_russia = post_rmspe_russia / pre_rmspe_russia

drop if missing(Year)  // 删除Year缺失的观测值

* 2.6 保存RUSSIAN_FEDERATION结果
save "$CODE/crimes_2022/intl_ratio/russia_synth_results.dta", replace



sum russia_gap if Year >= 2022
local russia_effect = r(mean)

twoway (line russia_actual Year, lcolor(cyan) lwidth(medthick)) ///
       (line russia_synthetic Year, lcolor(cyan) lwidth(medthick) lpattern(dash)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       text(0.8 2022.5 "War", placement(east)) ///
       text(0.55 2020 "PRE-RMSPE: `=string(`pre_rmspe_russia',"%5.4f")'", size(medium)) ///
       text(0.50 2020 "Russia Effect: `=string(`russia_effect',"%5.4f")'", size(medium)) ///
       xtitle("") ///
       ytitle("the ratio of international publications", size(medium)) ///
       xlabel(2004(5)2024, nogrid tposition(inside)) ///
       ylabel(0.4(0.1)0.8, nogrid tposition(inside) format(%3.1f)) ///
       xmtick(2004(1)2024, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Russia Actual" 2 "Russia Synthetic") ///
              pos(3) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison, replace)

graph export "$CODE/crimes_2022/intl_ratio/russia_combined_actual_vs_synthetic.png", ///
       width(1200) height(800) replace
