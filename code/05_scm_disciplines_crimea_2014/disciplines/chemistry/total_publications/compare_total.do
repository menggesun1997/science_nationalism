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

cd "$CODE/05_scm_disciplines_crimea_2014/disciplines/chemistry/total_publications"

local discipline "chemistry"
local base_dir "../.."
import excel "`base_dir'/`discipline'/discipline_`discipline'.xlsx", sheet("Sheet1") firstrow clear

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
    if !inlist("`country'", "RUSSIAN_FEDERATION", "UKRAINE") {
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
gen log_pub_total = log(Chemistry_total + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

* 1.6 保存处理后的数据
save "`base_dir'/`discipline'/total_publications/processed_data.dta", replace


* 2. RUSSIAN_FEDERATION合成控制分析
* 2.1 运行RUSSIAN_FEDERATION的合成控制分析
synth log_pub_total ///
    log_gdp_per_capita  log_rp RD /// 这些变量会使用xperiod限定范围内的变量数据
    log_pub_total(2013) log_pub_total(2012) log_pub_total(2011) log_pub_total(2010) log_pub_total(2008) log_pub_total(2010(1)2013), /// 
    trunit(`russia_id') trperiod(2014) ///
    counit(`control_ids') ///
    xperiod(2008(1)2013) ///
    nested allopt ///
    keep(russia_synth_results, replace)

* 2.2 处理RUSSIAN_FEDERATION结果
use russia_synth_results, clear
rename _time Year
rename _Y_treated russia_actual
rename _Y_synthetic russia_synthetic
gen russia_gap = russia_actual - russia_synthetic

* 2.3 计算RUSSIAN_FEDERATION效应
gen russia_actual_real = exp(russia_actual) - 1
gen russia_synthetic_real = exp(russia_synthetic) - 1
gen russia_gap_pct_effect = russia_actual_real - russia_synthetic_real
gen russia_gap_pct = (russia_actual_real - russia_synthetic_real) / russia_actual_real * 100

* 2.4 计算RUSSIAN_FEDERATION平均处理效应
egen russia_avg_effect = mean(russia_gap_pct) if Year >= 2014
local russia_avg_effect : display %5.2f r(mean)

* 2.5 计算RUSSIAN_FEDERATION的RMSPE
gen pre_sq_error_russia = russia_gap_pct_effect^2 if Year <= 2013
egen pre_mspe_russia = mean(pre_sq_error_russia)
gen pre_rmspe_russia = sqrt(pre_mspe_russia)

gen post_sq_error_russia = russia_gap_pct_effect^2 if Year >= 2014
egen post_mspe_russia = mean(post_sq_error_russia)
gen post_rmspe_russia = sqrt(post_mspe_russia)

gen rmspe_ratio_russia = post_rmspe_russia / pre_rmspe_russia

drop if missing(Year)  // 删除Year缺失的观测值

* 2.6 保存RUSSIAN_FEDERATION结果
save "`base_dir'/`discipline'/total_publications/russia_synth_results.dta", replace

* 3. UKRAINE合成控制分析
* 3.1 准备UKRAINE分析数据
use "`base_dir'/`discipline'/total_publications/processed_data.dta", clear

* 3.2 运行UKRAINE的合成控制分析
synth log_pub_total ///
    log_gdp_per_capita log_rp RD ///
    log_pub_total(2013)  log_pub_total(2012) log_pub_total(2011) log_pub_total(2010) log_pub_total(2008) log_pub_total(2008(1)2013), /// 结果变量的滞后值
    trunit(`ukraine_id') trperiod(2014) ///
    counit(`control_ids') ///
    xperiod(2008(1)2013) ///
    nested allopt ///
    keep(ukraine_synth_results, replace)

* 3.3 处理UKRAINE结果
use ukraine_synth_results, clear
rename _time Year
rename _Y_treated ukraine_actual
rename _Y_synthetic ukraine_synthetic
gen ukraine_gap = ukraine_actual - ukraine_synthetic

* 3.4 计算UKRAINE效应
gen ukraine_actual_real = exp(ukraine_actual) - 1
gen ukraine_synthetic_real = exp(ukraine_synthetic) - 1
gen ukraine_gap_pct_effect = ukraine_actual_real - ukraine_synthetic_real
gen ukraine_gap_pct = (ukraine_actual_real - ukraine_synthetic_real) / ukraine_actual_real * 100

* 3.5 计算UKRAINE平均处理效应
egen ukraine_avg_effect = mean(ukraine_gap_pct) if Year >= 2014
local ukraine_avg_effect : display %5.2f r(mean)

* 3.6 计算UKRAINE的RMSPE
gen pre_sq_error_ukraine = ukraine_gap_pct_effect^2 if Year <= 2013
egen pre_mspe_ukraine = mean(pre_sq_error_ukraine)
gen pre_rmspe_ukraine = sqrt(pre_mspe_ukraine)

gen post_sq_error_ukraine = ukraine_gap_pct_effect^2 if Year >= 2014
egen post_mspe_ukraine = mean(post_sq_error_ukraine)
gen post_rmspe_ukraine = sqrt(post_mspe_ukraine)

gen rmspe_ratio_ukraine = post_rmspe_ukraine / pre_rmspe_ukraine

drop if missing(Year)  // 删除Year缺失的观测值
* 3.7 保存UKRAINE结果
save "`base_dir'/`discipline'/total_publications/ukraine_synth_results.dta", replace


* 3.8 合并UKRAINE和RUSSIAN_FEDERATION结果进行对比可视化
use "`base_dir'/`discipline'/total_publications/ukraine_synth_results.dta", clear
merge 1:1 Year using "`base_dir'/`discipline'/total_publications/russia_synth_results.dta", nogenerate

* 获取效应值
sum ukraine_gap_pct if Year >= 2014
local ukraine_effect = r(mean)
sum russia_gap_pct if Year >= 2014
local russia_effect = r(mean)

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式

twoway (line russia_actual_real Year, lcolor("76 92 156") lwidth(medthick) yaxis(1)) ///
       (line russia_synthetic_real Year, lcolor("76 92 156") lwidth(medthick) lpattern(dash) yaxis(1)) ///
	   (line ukraine_actual_real Year, lcolor("227 195 65") lwidth(medthick) yaxis(2)) ///
       (line ukraine_synthetic_real Year, lcolor("227 195 65") lwidth(medthick) lpattern(dash) yaxis(2)), ///
       xline(2014, lpattern(dot) lcolor(black)) ///
       text(2600 2019 "Russia Effect: `=string(`russia_effect',"%5.2f")'%", size(medium)) ///
	   text(600 2019 "Ukraine Effect: `=string(`ukraine_effect',"%5.2f")'%", size(medium)) ///
       xtitle("") ///
	   title("`discipline'") ///
       ytitle("Total publications of Russia", size(medium) axis(1)) ///
	   ytitle("Total publications of Ukraine", size(medium) axis(2)) ///
       xlabel(2005(2)2024, nogrid tposition(inside)) ///
	   ylabel(0(2000)8000, nogrid tposition(inside) format(%9.0gc) axis(1)) ///
	   ylabel(0(500)2000, nogrid tposition(inside) format(%9.0gc) axis(2)) ///
       xmtick(2005(1)2024, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(off) ///
       name(combined_comparison_real, replace)	   


graph export "`base_dir'/`discipline'/total_publications/crimean_`discipline'_total.pdf", replace

* 4. 安慰剂检验
* 4.1 对每个控制组国家进行合成控制分析
// foreach country of local control_countries {
//     di "Processing `country'"
//
//     use "$CODE/01_scm_crimea_2014/total_publications/processed_data.dta", clear
//
//     * 获取当前国家的ID
//     qui sum country_id if Country == "`country'"
//     local treat_id = r(mean)
//     di "Treatment ID for `country': `treat_id'"
// 	* 跳过ID小于18的国家
//     if `treat_id' < 18 {
//         di "Skipping `country' (ID < 18)"
//         continue
//     }
//
//     * 构建placebo控制组
//     local placebo_controls
//     foreach ctrl of local control_countries {
//         if "`ctrl'" != "`country'" {
//             qui sum country_id if Country == "`ctrl'"
//             local placebo_controls "`placebo_controls' `=r(mean)'"
//         }
//     }
//
//     * 尝试标准模型，如果失败则使用简化模型
//     capture noisily {
//         synth log_pub_total log_gdp_per_capita log_rp RD, ///
//               trunit(`=`treat_id'') trperiod(2014) ///
//               counit(`placebo_controls') ///
//               xperiod(2008(1)2013) ///
//               nested allopt ///
//               keep("$CODE/01_scm_crimea_2014/total_publications/synth_`country'.dta", replace)
//     }
//  
//     * 如果标准模型失败，尝试简化模型
//     if _rc != 0 {
//         di "Standard model failed for `country', trying simplified model"
//         capture noisily {
//             synth log_pub_total log_gdp_per_capita log_rp, ///
//                   trunit(`=`treat_id'') trperiod(2014) ///
//                   counit(`placebo_controls') ///
//                   xperiod(2005(1)2013) ///
//                   nested allopt ///
//                   keep("$CODE/01_scm_crimea_2014/total_publications/synth_`country'.dta", replace)
//         }
//     }
//
//     * 处理结果
//     capture {
//         use "$CODE/01_scm_crimea_2014/total_publications/synth_`country'.dta", clear
//         rename _time Year
//         gen actual_real = exp(_Y_treated) - 1
//         gen synthetic_real = exp(_Y_synthetic) - 1
// 		gen gap_pct_effect_`country' = actual_real - synthetic_real
//         gen gap_pct_`country' = (actual_real - synthetic_real) / actual_real * 100
//   
//         * 计算平均处理效应
//         egen avg_effect = mean(gap_pct_`country') if Year >= 2014
//         gen avg_gap_pct_`country' = avg_effect
//         drop avg_effect
//   
//         keep Year gap_pct_effect_`country' gap_pct_`country' avg_gap_pct_`country'
//         drop if missing(Year)  // 删除Year缺失的观测值
//         save "$CODE/01_scm_crimea_2014/total_publications/gap_`country'.dta", replace
//     }
// }

* 4.2 合并所有结果 - 直接从ARGENTINA开始
* 从ARGENTINA数据开始
// use "$CODE/01_scm_crimea_2014/total_publications/gap_ARGENTINA.dta", clear
// * 合并其他控制组国家
// foreach country of local control_countries {
//     if "`country'" != "ARGENTINA" {
//         capture {
//             merge 1:1 Year using "$CODE/01_scm_crimea_2014/total_publications/gap_`country'.dta", nogenerate
//         }
//     }
// }
// * 合并ukraine数据和russia数据
// merge 1:1 Year using "$CODE/01_scm_crimea_2014/total_publications/ukraine_synth_results.dta",nogenerate
// merge 1:1 Year using "$CODE/01_scm_crimea_2014/total_publications/russia_synth_results.dta", nogenerate
//
// * 保存最终合并的数据
// save "$CODE/01_scm_crimea_2014/total_publications/all_gaps_merged.dta", replace
//
// * 4.3 计算每个国家的RMSPE
// foreach country of local control_countries {
//     capture {
//         gen pre_sq_error_`country' = gap_pct_effect_`country'^2 if Year <= 2013
//         egen pre_mspe_`country' = mean(pre_sq_error_`country')
//         gen pre_rmspe_`country' = sqrt(pre_mspe_`country')
//        
//         gen post_sq_error_`country' = gap_pct_effect_`country'^2 if Year >= 2014
//         egen post_mspe_`country' = mean(post_sq_error_`country')
//         gen post_rmspe_`country' = sqrt(post_mspe_`country')
//        
//         gen rmspe_ratio_`country' = post_rmspe_`country' / pre_rmspe_`country'
//     }
// }
//
// * 5. 结果可视化和统计分析
// * 获取russia基准
// * pre_rmspe_russia(584.0948)；pre_rmspe_ukraine(145.699)
// sum pre_rmspe_russia
// local russia_pre_rmspe = r(mean)
// local threshold = 2 // 设置阈值
//
// * 获取russia效应
// sum russia_gap_pct if Year >= 2014
// local russia_avg_effect = abs(r(mean))
//
// * 自动获取所有控制组变量（不穷举）
// local qualified_count = 0
// local extreme_count = 0
// local quali
// * 使用varlist自动遍历所有pre_rmspe变量
// foreach var of varlist pre_rmspe_* {
//     if "`var'" != "pre_rmspe_russia" & "`var'" != "pre_rmspe_russia" {
//         * 提取国家名
//         local country = substr("`var'", 11, .)
//        
//         * 检查pre_rmspe
//         sum `var'
//         if r(N) > 0 {
//             local pre_rmspe = r(mean)
//             * 检查gap_pct
//             capture confirm variable gap_pct_`country'
//             if !_rc {
//                 sum gap_pct_`country' if Year >= 2014
//                 if r(N) > 0 {
//                     local effect = abs(r(mean))
//                     * 判断是否合格
//                     if `pre_rmspe' < `threshold'*`russia_pre_rmspe' {
//                         local qualified_count = `qualified_count' + 1
//                         local qualified_countries `"`qualified_countries' "`country'""'
//                         di "国家 `country' 合格: pre_rmspe = `pre_rmspe'"
//                        
//                         * 判断是否效应更极端
//                         if `effect' >= `russia_avg_effect' {
//                             local extreme_count = `extreme_count' + 1
//                             di "  效应更极端: effect = `effect'"
//                         }
//                     }
//                 }
//             }
//         }
//     }
// }
//
// * 计算p值
// local p_value = (`extreme_count' + 1) / (`qualified_count' + 1)
// local p_value_display = string(`p_value', "%9.3f")
// di "合格国家数: `qualified_count', 效应极端国家数: `extreme_count'"
// di "p值: `p_value_display'"
//
//
//
// * 5.4 绘制筛选后的安慰剂效应图
// * 准备绘图命令
// local filtered_control_lines ""
// local filtered_legend_order ""
// local j = 1
//
// * 使用我们存储的合格国家列表
// foreach country of local qualified_countries {
//     capture confirm variable gap_pct_`country'
//     if !_rc {
//         local filtered_control_lines `"`filtered_control_lines' (line gap_pct_`country' Year, lpattern(dash))"'
//         local filtered_legend_order `"`filtered_legend_order' `j' "`country'" "'
//         local ++j
//     }
// }
//
// * 添加russia和ukraine
// local filtered_control_lines `"`filtered_control_lines' (line russia_gap_pct Year, lwidth(thick) lcolor("137 202 229"))"'
// local filtered_control_lines `"`filtered_control_lines' (line ukraine_gap_pct Year, lwidth(thick) lcolor(orange_red))"'
//
// * 绘制图形
// twoway `filtered_control_lines', ///
//        xline(2014, lpattern(dash) lcolor(gray)) ///
//        text(20 2010 "Crimean", placement(east)) ///
//        yline(0, lcolor(black)) ///
//        xtitle("") ///
//        ytitle("Filtered Countries:`qualified_count', p-value:`p_value_display',threshold :`threshold'", size(medium)) ///
//        xlabel(2004(5)2024, nogrid tposition(inside)) ///
//        ylabel(, nogrid tposition(inside)) ///
//        xmtick(2004(1)2024, tposition(inside)) ///
//        ymtick(, tposition(inside)) ///
//        graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
//        plotregion(style(outline) lcolor(black) lwidth(thin)) ///
//        bgcolor(white) ///
//        legend(order(`filtered_legend_order' `=`j'' "RUSSIA" `=`j'+1' "UKRAINE") /// 
//               pos(3) ring(1) cols(1) region(style(none)) size(vsmall)) ///
//        name(placebo_filtered, replace)
//
// * 导出图形
// graph export "$CODE/01_scm_crimea_2014/total_publications/placebo_filtered.png", ///
//        width(1200) height(800) replace
//
// * 5.5 保存最终结果
// save "$CODE/01_scm_crimea_2014/total_publications/final_results.dta", replace
