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
local base_dir "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/crimes_2015_2022"
import excel "`base_dir'/original_completed_new.xlsx", sheet("Sheet1") firstrow clear

local treated_year = 2022
local before_treated_year = 2021
local fit_start_year 2015  // 新增变量

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

gen log_pub_total_10 = log_pub_total / 10
gen log_gdp_per_capita_10 = log_gdp_per_capita /10
gen log_rp_10 = log_rp /10

global control_vars "log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD"

global control_vars_russia "intl_ratio(2021) intl_ratio(2019) intl_ratio(2017) intl_ratio(2015) " //2022
global control_vars_ukraine "intl_ratio(2021) intl_ratio(2020) intl_ratio(2019) intl_ratio(2018) intl_ratio(2017)  " //2022

// global control_vars_russia "intl_ratio(2020) intl_ratio(2019) intl_ratio(2017) intl_ratio(2015) " //2021
// global control_vars_ukraine "intl_ratio(2020) intl_ratio(2019) intl_ratio(2018) intl_ratio(2017) intl_ratio(2016) intl_ratio(2015) " //2021

// global control_vars_russia "intl_ratio(2019) intl_ratio(2018) intl_ratio(2017) intl_ratio(2016) " //2020
// global control_vars_ukraine "intl_ratio(2019) intl_ratio(2018) intl_ratio(2017) intl_ratio(2016) intl_ratio(2015) " //2020  (only this one variable)


// global control_vars_russia "intl_ratio(2018) intl_ratio(2017) intl_ratio(2016) intl_ratio(2015) " //2019
// global control_vars_ukraine "intl_ratio(2018) intl_ratio(2017) intl_ratio(2016) intl_ratio(2015) " //2019 (only this one variable)


* 1.6 保存处理后的数据
save "`base_dir'/intl_ratio_new/processed_data.dta", replace


* 2. RUSSIAN_FEDERATION合成控制分析
* 2.1 运行RUSSIAN_FEDERATION的合成控制分析
synth intl_ratio  ///
	$control_vars ///
    $control_vars_russia , ///
    trunit(`russia_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(`fit_start_year'(1)`before_treated_year') ///
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
egen russia_avg_effect = mean(russia_gap) if Year >= `treated_year'
local russia_avg_effect : display %5.2f r(mean)


* 2.5 计算RUSSIAN_FEDERATION的RMSPE
gen pre_sq_error_russia = russia_gap^2 if Year <= `before_treated_year'
egen pre_mspe_russia = mean(pre_sq_error_russia)
gen pre_rmspe_russia = sqrt(pre_mspe_russia)
local pre_rmspe_russia : display %5.4f r(mean)

gen post_sq_error_russia = russia_gap^2 if Year >= `treated_year' & Year >= `fit_start_year'
egen post_mspe_russia = mean(post_sq_error_russia)
gen post_rmspe_russia = sqrt(post_mspe_russia)

gen rmspe_ratio_russia = post_rmspe_russia / pre_rmspe_russia

drop if missing(Year)  // 删除Year缺失的观测值

* 2.6 保存RUSSIAN_FEDERATION结果
save "`base_dir'/intl_ratio_new/russia_synth_results.dta", replace

* 2.7 输出控制组国家与权重对应表
use russia_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id
save temp_weights_russia_`treated_year'.dta, replace


* 3. UKRAINE合成控制分析
* 3.0 准备UKRAINE分析数据
use "`base_dir'/intl_ratio_new/processed_data.dta", clear

* 3.1 运行UKRAINE的合成控制分析
synth intl_ratio ///
	$control_vars ///
    $control_vars_ukraine , ///
    trunit(`ukraine_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(`fit_start_year'(1)`before_treated_year') ///
    nested allopt ///
    keep(ukraine_synth_results, replace)

* 3.2 处理UKRAINE结果
use ukraine_synth_results, clear
rename _time Year
rename _Y_treated ukraine_actual
rename _Y_synthetic ukraine_synthetic

* 3.3 计算UKRAINE效应
gen ukraine_gap = ukraine_actual - ukraine_synthetic

* 3.4 计算UKRAINE平均处理效应
egen ukraine_avg_effect = mean(ukraine_gap) if Year >= `treated_year'
local ukraine_avg_effect : display %5.2f r(mean)

* 3.5 计算UKRAINE的RMSPE
gen pre_sq_error_ukraine = ukraine_gap^2 if Year <= `before_treated_year' & Year >= `fit_start_year'
egen pre_mspe_ukraine = mean(pre_sq_error_ukraine)
gen pre_rmspe_ukraine = sqrt(pre_mspe_ukraine)
local pre_rmspe_ukraine : display %5.4f r(mean)

gen post_sq_error_ukraine = ukraine_gap^2 if Year >= `treated_year'
egen post_mspe_ukraine = mean(post_sq_error_ukraine)
gen post_rmspe_ukraine = sqrt(post_mspe_ukraine)

gen rmspe_ratio_ukraine = post_rmspe_ukraine / pre_rmspe_ukraine

* 3.6 保存UKRAINE结果
drop if missing(Year)  // 删除Year缺失的观测值
save "`base_dir'/intl_ratio_new/ukraine_synth_results.dta", replace


* 3.7 输出控制组国家与权重对应表
use ukraine_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id
save temp_weights_ukraine_`treated_year'.dta, replace


* 3.8 合并UKRAINE和RUSSIAN_FEDERATION结果进行对比可视化
use "`base_dir'/intl_ratio_new/ukraine_synth_results.dta", clear
merge 1:1 Year using "`base_dir'/intl_ratio_new/russia_synth_results.dta", nogenerate
* 获取效应值
sum ukraine_gap if Year >= `treated_year'
local ukraine_effect = r(mean)*100
sum russia_gap if Year >= `treated_year'
local russia_effect = r(mean)*100

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
twoway (line ukraine_actual Year, lcolor("227 195 65") lwidth(medthick)) ///
       (line ukraine_synthetic Year, lcolor("227 195 65") lwidth(medthick) lpattern(dash)) ///
       (line russia_actual Year, lcolor("76 92 156") lwidth(medthick)) ///
       (line russia_synthetic Year, lcolor("76 92 156") lwidth(medthick) lpattern(dash)) ///
	   if Year >= `fit_start_year', ///
       xline(`treated_year', lpattern(dot) lcolor(black)) ///
       text(0.50 2019 "Russia Effect: `=string(`russia_effect',"%5.2f")'%", size(medium)) ///
	   text(0.55 2019 "Ukraine Effect: `=string(`ukraine_effect',"%5.2f")'%", size(medium)) ///
       xtitle("") ///
       ytitle("The ratio of international publications", size(medium)) ///
       xlabel(`fit_start_year'(2)2024, nogrid tposition(inside)) ///
       ylabel(0.4(0.1)0.8, nogrid tposition(inside) format(%3.1f)) ///
       xmtick(`fit_start_year'(1)2024, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Ukraine Actual" 2 "Ukraine Synthetic" 3 "Russia Actual" 4 "Russia Synthetic") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison, replace)

graph export "`base_dir'/intl_ratio_new/combined_actual_vs_synthetic_`treated_year'.pdf", replace

* 4. 安慰剂检验
* 4.1 对每个控制组国家进行合成控制分析
foreach country of local control_countries {
    di "Processing `country'"

    use "`base_dir'/intl_ratio_new/processed_data.dta", clear

    * 获取当前国家的ID
    qui sum country_id if Country == "`country'"
    local treat_id = r(mean)
    di "Treatment ID for `country': `treat_id'"
	* 跳过ID小于18的国家
    if `treat_id' < 60 {
        di "Skipping `country' (ID < 18)"
        continue
    }

    * 构建placebo控制组
    local placebo_controls
    foreach ctrl of local control_countries {
        if "`ctrl'" != "`country'" {
            qui sum country_id if Country == "`ctrl'"
            local placebo_controls "`placebo_controls' `=r(mean)'"
        }
    }
   
    * 尝试标准模型，如果失败则使用简化模型
    capture noisily {
        synth intl_ratio ///
			  $control_vars ///
			  $control_vars_russia , ///
              trunit(`=`treat_id'') trperiod(`treated_year') ///
              counit(`placebo_controls') ///
              xperiod(`fit_start_year'(1)`before_treated_year') ///
              nested allopt ///
              keep("`base_dir'/intl_ratio_new/synth_`country'.dta", replace)
    }
   
    * 如果标准模型失败，尝试简化模型
    if _rc != 0 {
        di "Standard model failed for `country', trying simplified model"
        capture noisily {
            synth intl_ratio $control_vars $control_vars_ukraine , ///
                  trunit(`=`treat_id'') trperiod(`treated_year') ///
                  counit(`placebo_controls') ///
                  xperiod(`fit_start_year'(1)`before_treated_year') ///
                  nested allopt ///
                  keep("`base_dir'/intl_ratio_new/synth_`country'.dta", replace)
        }
    }
   
    * 保存结果
	capture {
		use "`base_dir'/intl_ratio_new/synth_`country'.dta", clear
		rename _time Year
		rename _Y_treated cc_actual
		rename _Y_synthetic cc_synthetic
		gen gap_`country' = cc_actual - cc_synthetic

		* 计算平均处理效应
		egen avg_effect = mean(gap_`country') if Year >= `treated_year'
		gen avg_gap_`country' = avg_effect
		drop avg_effect

		keep Year gap_`country' avg_gap_`country'
		drop if missing(Year)
		save "`base_dir'/intl_ratio_new/gap_`country'.dta", replace
	}
}

* 4.2 合并所有结果
use "`base_dir'/intl_ratio_new/gap_ARGENTINA.dta", clear
foreach country of local control_countries {
    if "`country'" != "ARGENTINA" {
        capture {
            merge 1:1 Year using "`base_dir'/intl_ratio_new/gap_`country'.dta", nogenerate
        }
    }
}
merge 1:1 Year using "`base_dir'/intl_ratio_new/ukraine_synth_results.dta", nogenerate
merge 1:1 Year using "`base_dir'/intl_ratio_new/russia_synth_results.dta", nogenerate

* 4.3 计算每个国家的RMSPE
foreach country of local control_countries {
    capture {
        gen pre_sq_error_`country' = gap_`country'^2 if Year <= `before_treated_year' & Year >= `fit_start_year'
        egen pre_mspe_`country' = mean(pre_sq_error_`country')
        gen pre_rmspe_`country' = sqrt(pre_mspe_`country')
       
        gen post_sq_error_`country' = gap_`country'^2 if Year >= `treated_year'
        egen post_mspe_`country' = mean(post_sq_error_`country')
        gen post_rmspe_`country' = sqrt(post_mspe_`country')
       
        gen rmspe_ratio_`country' = post_rmspe_`country' / pre_rmspe_`country'
    }
}

* 5. 结果可视化和统计分析
// * 获取russia基准
// * pre_rmspe_russia(0.003571)；pre_rmspe_ukraine(0.0298)
// sum pre_rmspe_ukraine
// local ukraine_pre_rmspe = r(mean)
// local threshold = 2 // 设置阈值
//
// * 获取russia效应
// sum ukraine_gap if Year >= `treated_year'
// local ukraine_avg_effect = abs(r(mean))
//
// * 自动获取所有控制组变量（不穷举）
// local qualified_count = 0
// local extreme_count = 0
// local quali
// * 使用varlist自动遍历所有pre_rmspe变量
// foreach var of varlist pre_rmspe_* {
//     if "`var'" != "pre_rmspe_russia" & "`var'" != "pre_rmspe_ukraine" {
//         * 提取国家名
//         local country = substr("`var'", 11, .)
//        
//         * 检查pre_rmspe
//         sum `var'
//         if r(N) > 0 {
//             local pre_rmspe = r(mean)
//             * 检查gap
//             capture confirm variable gap_`country'
//             if !_rc {
//                 sum gap_`country' if Year >= 2014
//                 if r(N) > 0 {
//                     local effect = abs(r(mean))
//                     * 判断是否合格
//                     if `pre_rmspe' < `threshold'*`ukraine_pre_rmspe' {
//                         local qualified_count = `qualified_count' + 1
//                         local qualified_countries `"`qualified_countries' "`country'""'
//                         di "国家 `country' 合格: pre_rmspe = `pre_rmspe'"
//                        
//                         * 判断是否效应更极端
//                         if `effect' >= `ukraine_avg_effect' {
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


* 5.2 基于RMSPE比率的计算russia的p值
* 获取russia的RMSPE比率
sum rmspe_ratio_russia
local russia_rmspe_ratio = r(mean)
di "russia的RMSPE比率: `russia_rmspe_ratio'"

* 计算所有控制组国家的RMSPE比率,total_control_count_russia=2因为一开始的国家中不包括russia和ukraine,rmspe_ratio_higher_count_russia=1是因为至少russia是相等的
local total_control_count_russia = 2
local rmspe_ratio_higher_count_russia = 1

foreach country of local control_countries {
    capture confirm variable rmspe_ratio_`country'
    if !_rc {
        sum rmspe_ratio_`country'
        if r(N) > 0 {
            local total_control_count_russia = `total_control_count_russia' + 1
            local country_rmspe_ratio = r(mean)
            
            * 检查该国家的RMSPE比率是否大于russia
            if `country_rmspe_ratio' > `russia_rmspe_ratio' {
                local rmspe_ratio_higher_count_russia = `rmspe_ratio_higher_count_russia' + 1
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于russia)"
            }
            else {
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于russia)"
            }
        }
    }
}

* 计算基于RMSPE比率的russia的p值
local p_value_rmspe_russia = `rmspe_ratio_higher_count_russia' / `total_control_count_russia'
local p_value_rmspe_display_russia = string(`p_value_rmspe_russia', "%9.2f")

di "=== RMSPE比率p值计算结果 ==="
di "总控制组国家数: `total_control_count_russia'"
di "RMSPE比率大于russia的国家数: `rmspe_ratio_higher_count_russia'"
di "基于RMSPE比率的p值: `p_value_rmspe_display_russia'"
di "russia的RMSPE比率: `russia_rmspe_ratio'"


* 5.3 基于RMSPE比率的计算ukraine的p值
* 获取ukraine的RMSPE比率
sum rmspe_ratio_ukraine
local ukraine_rmspe_ratio = r(mean)
di "ukraine的RMSPE比率: `ukraine_rmspe_ratio'"

* 计算所有控制组国家的RMSPE比率
local total_control_count_ukraine = 2
local rmspe_ratio_higher_ukraine = 1

foreach country of local control_countries {
    capture confirm variable rmspe_ratio_`country'
    if !_rc {
        sum rmspe_ratio_`country'
        if r(N) > 0 {
            local total_control_count_ukraine = `total_control_count_ukraine' + 1
            local country_rmspe_ratio = r(mean)
            
            * 检查该国家的RMSPE比率是否大于ukraine
            if `country_rmspe_ratio' > `ukraine_rmspe_ratio' {
                local rmspe_ratio_higher_ukraine = `rmspe_ratio_higher_ukraine' + 1
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于ukraine)"
            }
            else {
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于ukraine)"
            }
        }
    }
}

* 计算基于RMSPE比率的p值
local p_value_rmspe_ukraine = `rmspe_ratio_higher_ukraine' / `total_control_count_ukraine'
local p_value_rmspe_display_ukraine = string(`p_value_rmspe_ukraine', "%9.2f")

di "=== RMSPE比率p值计算结果 ==="
di "总控制组国家数: `total_control_count_ukraine'"
di "RMSPE比率大于ukraine的国家数: `rmspe_ratio_higher_ukraine'"
di "基于RMSPE比率的p值: `p_value_rmspe_display_ukraine'"
di "ukraine的RMSPE比率: `ukraine_rmspe_ratio'"
di "ukraine的pre-rmspe value:`pre_rmspe_ukraine'"

* 5.4 绘制筛选后的安慰剂效应图
sum pre_rmspe_ukraine // 获取russia基准
local ukraine_pre_rmspe = r(mean)
local qualified_countries ""  // 用来存储合格的国家列表
local threshold = 2

* 使用varlist自动遍历所有pre_rmspe变量
foreach var of varlist pre_rmspe_* {
    if "`var'" != "pre_rmspe_ukraine" & "`var'" != "pre_rmspe_russia" {
        * 提取国家名
        local country = substr("`var'", 11, .)
        * 检查pre_rmspe
        sum `var'
        if r(N) > 0 {
            local pre_rmspe = r(mean)
            if !_rc {
                if r(N) > 0 {
                    * 判断是否合格
                    if `pre_rmspe' < `threshold'*`ukraine_pre_rmspe' {
                        local qualified_count = `qualified_count' + 1
                        local qualified_countries `"`qualified_countries' "`country'""'
                        di "国家 `country' 合格: pre_rmspe = `pre_rmspe'"
                    }
                }
            }
        }
    }
}
* 准备绘图命令
local filtered_control_lines ""
local filtered_legend_order ""
local j = 1

* 使用我们存储的合格国家列表
foreach country of local control_countries {
    capture confirm variable gap_`country'
    if !_rc {
		gen gap_100_`country' = gap_`country' * 100
        local filtered_control_lines `"`filtered_control_lines' (line gap_100_`country' Year, lcolor(gs12) lpattern(dash))"'
        local filtered_legend_order `"`filtered_legend_order' `j' "`country'" "'
        local ++j
    }
}

* 添加russia和ukraine
gen russia_gap100 = russia_gap * 100
gen ukraine_gap100 = ukraine_gap * 100
local filtered_control_lines `"`filtered_control_lines' (line russia_gap100 Year, lwidth(thick) lcolor("76 92 156"))"'
local filtered_control_lines `"`filtered_control_lines' (line ukraine_gap100 Year, lwidth(thick) lcolor("227 195 65"))"'

* 绘制图形
twoway `filtered_control_lines' ///
	   if Year >= `fit_start_year', ///
       xline(`treated_year', lpattern(dot) lcolor(black)) ///
       yline(0, lcolor(black)) ///
       xtitle("") ///
	   ytitle("Treatment Effect", size(medium)) ///
	   text(-5 2017 `"p-value(Russia)  : `p_value_rmspe_display_russia'"' `"`=char(13)'"' ///
                `"p-value(Ukraine) : `p_value_rmspe_display_ukraine'"', size(medium)) ///
       xlabel(`fit_start_year'(2)2024, nogrid tposition(inside)) ///
       ylabel(, nogrid tposition(inside)) ///
       xmtick(`fit_start_year'(1)2024, tposition(inside)) ///
       ymtick(, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(off) ///
       name(placebo_filtered, replace)

* 导出图形
graph export "`base_dir'/intl_ratio_new/placebo_filtered_`treated_year'.pdf", replace

* 5.5 保存最终结果
save "`base_dir'/intl_ratio_new/final_results.dta", replace


