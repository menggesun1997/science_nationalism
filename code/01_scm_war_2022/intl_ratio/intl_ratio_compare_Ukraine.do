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

cd "$CODE/01_scm_war_2022/intl_ratio"

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


* 2. UKRAINE合成控制分析
* 2.1 准备UKRAINE分析数据
use "$CODE/crimes_2022/intl_ratio/processed_data.dta", clear

* 2.2 运行UKRAINE的合成控制分析
synth intl_ratio ///
    log_pub_total log_gdp_per_capita  log_rp RD /// 这些变量会使用xperiod限定范围内的变量数据
    intl_ratio(2021)  intl_ratio(2020) intl_ratio(2019) intl_ratio(2018) intl_ratio(2014) intl_ratio(2008(1)2013), /// 结果变量的滞后值
    trunit(`ukraine_id') trperiod(2022) ///
    counit(`control_ids') ///
    xperiod(2008(1)2021) ///
    nested allopt ///
    keep(ukraine_synth_results, replace)

* 3.3 处理UKRAINE结果
use ukraine_synth_results, clear
rename _time Year
rename _Y_treated ukraine_actual
rename _Y_synthetic ukraine_synthetic

* 3.4 计算UKRAINE效应
gen ukraine_gap = ukraine_actual - ukraine_synthetic

* 3.5 计算UKRAINE平均处理效应
egen ukraine_avg_effect = mean(ukraine_gap) if Year >= 2022
local ukraine_avg_effect : display %5.4f r(mean)

* 3.6 计算UKRAINE的RMSPE
gen pre_sq_error_ukraine = ukraine_gap^2 if Year <= 2021
egen pre_mspe_ukraine = mean(pre_sq_error_ukraine)
gen pre_rmspe_ukraine = sqrt(pre_mspe_ukraine)
local pre_rmspe_ukraine : display %5.4f r(mean)

gen post_sq_error_ukraine = ukraine_gap^2 if Year >= 2022
egen post_mspe_ukraine = mean(post_sq_error_ukraine)
gen post_rmspe_ukraine = sqrt(post_mspe_ukraine)

gen rmspe_ratio_ukraine = post_rmspe_ukraine / pre_rmspe_ukraine

* 3.7 保存UKRAINE结果
drop if missing(Year)  // 删除Year缺失的观测值
save "$CODE/crimes_2022/intl_ratio/ukraine_synth_results.dta", replace


sum ukraine_gap if Year >= 2022
local ukraine_effect = r(mean)


twoway (line ukraine_actual Year, lcolor(pink) lwidth(medthick)) ///
       (line ukraine_synthetic Year, lcolor(pink) lwidth(medthick) lpattern(dash)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       text(0.8 2022 "War", placement(east)) ///
       text(0.55 2020 "Ukraine Effect: `=string(`ukraine_effect',"%5.4f")'", size(medium)) ///
       text(0.50 2020 "PRE-RMSPE: `=string(`pre_rmspe_ukraine',"%5.4f")'", size(medium)) ///
       xtitle("") ///
       ytitle("the ratio of international publications", size(medium)) ///
       xlabel(2004(5)2024, nogrid tposition(inside)) ///
       ylabel(0.4(0.1)0.8, nogrid tposition(inside) format(%3.1f)) ///
       xmtick(2004(1)2024, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Ukraine Actual" 2 "Ukraine Synthetic") ///
              pos(3) ring(1) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison, replace)

graph export "$CODE/crimes_2022/intl_ratio/UKRAINE_combined_actual_vs_synthetic.png", ///
       width(1200) height(800) replace
