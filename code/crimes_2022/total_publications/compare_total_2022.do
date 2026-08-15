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
local base_dir "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/crimes_2022"
import excel "`base_dir'/original_completed.xlsx", sheet("Sheet1") firstrow clear
local treated_year 2022
local before_treated_year 2021

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
gen log_pub_total = log(pub_total + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

gen log_gdp_per_capita_10 = log_gdp_per_capita /10
gen log_rp_10 = log_rp /10

global control_vars "log_gdp_per_capita_10 log_rp_10 RD"
global control_vars_russia "log_pub_total(2021) log_pub_total(2020) log_pub_total(2018) log_pub_total(2016) log_pub_total(2014) log_pub_total(2012) log_pub_total(2009)"
// global control_vars_ukraine "log_pub_total(2021) log_pub_total(2020) log_pub_total(2018) log_pub_total(2017) log_pub_total(2016) log_pub_total(2012) log_pub_total(2011)  log_pub_total(2008) log_pub_total(2007) log_pub_total(2006) "
global control_vars_ukraine "log_pub_total(2021) log_pub_total(2020) log_pub_total(2019) log_pub_total(2018) log_pub_total(2017) log_pub_total(2016) log_pub_total(2015) log_pub_total(2014) log_pub_total(2010) log_pub_total(2009) "

* 1.6 保存处理后的数据
save "`base_dir'/total_publications/processed_data.dta", replace


* 2. RUSSIAN_FEDERATION合成控制分析
* 2.1 运行RUSSIAN_FEDERATION的合成控制分析
synth log_pub_total ///
	$control_vars ///
    $control_vars_russia , ///
    trunit(`russia_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(2008(1)`before_treated_year') /// 
    nested allopt ///
    keep(russia_synth_results, replace)

* 2.2 处理RUSSIAN_FEDERATION结果
use russia_synth_results, clear
describe
rename _time Year
di "已将_time变量重命名为Year"
describe
rename _Y_treated russia_actual
rename _Y_synthetic russia_synthetic
gen russia_gap = russia_actual - russia_synthetic

* 2.3 计算RUSSIAN_FEDERATION效应
gen russia_actual_real = exp(russia_actual) - 1
gen russia_synthetic_real = exp(russia_synthetic) - 1
gen russia_gap_pct_effect = russia_actual_real - russia_synthetic_real
gen russia_gap_pct = (russia_actual_real - russia_synthetic_real) / russia_actual_real * 100

* 2.4 计算RUSSIAN_FEDERATION平均处理效应
egen russia_avg_effect = mean(russia_gap_pct) if Year >= `treated_year'
local russia_avg_effect : display %5.2f r(mean)

* 2.5 计算RUSSIAN_FEDERATION的RMSPE - 基于log尺度
gen log_gap_russia = russia_actual - russia_synthetic
gen pre_sq_error_russia = log_gap_russia^2 if Year <= `before_treated_year' & Year >= 2008
egen pre_mspe_russia = mean(pre_sq_error_russia)
gen pre_rmspe_russia = sqrt(pre_mspe_russia)

gen post_sq_error_russia = log_gap_russia^2 if Year >= `treated_year'
egen post_mspe_russia = mean(post_sq_error_russia)
gen post_rmspe_russia = sqrt(post_mspe_russia)

gen rmspe_ratio_russia = post_rmspe_russia / pre_rmspe_russia

drop if missing(Year)  // 删除Year缺失的观测值

* 确认Year变量存在
describe Year
list Year in 1/5

* 2.6 保存RUSSIAN_FEDERATION结果
save "`base_dir'/total_publications/russia_synth_results.dta", replace
di "已保存russia_synth_results.dta，包含Year变量"

* 2.7 输出控制组国家与权重对应表
use russia_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id
save temp_weights_russia.dta, replace

use "`base_dir'/total_publications/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_russia.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/total_publications/russia_weights_country.xlsx", firstrow(variables) replace


* 3. UKRAINE合成控制分析

* 3.0 准备UKRAINE分析数据
use "`base_dir'/total_publications/processed_data.dta", clear
* 3.1 运行UKRAINE的合成控制分析
synth log_pub_total ///
	$control_vars_ukraine , ///
    trunit(`ukraine_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(2008(1)`before_treated_year') /// 
    nested allopt ///
    keep(ukraine_synth_results, replace)
* 查看预测变量权重
matrix list e(V_matrix)

* 3.2 处理UKRAINE结果
use ukraine_synth_results, clear
describe
rename _time Year
di "已将_time变量重命名为Year"
describe
rename _Y_treated ukraine_actual
rename _Y_synthetic ukraine_synthetic
gen ukraine_gap = ukraine_actual - ukraine_synthetic

* 3.3 计算UKRAINE效应
gen ukraine_actual_real = exp(ukraine_actual) - 1
gen ukraine_synthetic_real = exp(ukraine_synthetic) - 1
gen ukraine_gap_pct_effect = ukraine_actual_real - ukraine_synthetic_real
gen ukraine_gap_pct = (ukraine_actual_real - ukraine_synthetic_real) / ukraine_actual_real * 100

* 3.4 计算UKRAINE平均处理效应
egen ukraine_avg_effect = mean(ukraine_gap_pct) if Year >= `treated_year'
local ukraine_avg_effect : display %5.2f r(mean)

* 3.5 计算UKRAINE的RMSPE - 基于log尺度
gen log_gap_ukraine = ukraine_actual - ukraine_synthetic
gen pre_sq_error_ukraine = log_gap_ukraine^2 if Year <= `before_treated_year' & Year >= 2008
egen pre_mspe_ukraine = mean(pre_sq_error_ukraine)
gen pre_rmspe_ukraine = sqrt(pre_mspe_ukraine)

gen post_sq_error_ukraine = log_gap_ukraine^2 if Year >= `treated_year'
egen post_mspe_ukraine = mean(post_sq_error_ukraine)
gen post_rmspe_ukraine = sqrt(post_mspe_ukraine)

gen rmspe_ratio_ukraine = post_rmspe_ukraine / pre_rmspe_ukraine

drop if missing(Year)  // 删除Year缺失的观测值

* 确认Year变量存在
describe Year
list Year in 1/5

* 3.6 保存UKRAINE结果
save "`base_dir'/total_publications/ukraine_synth_results.dta", replace
di "已保存ukraine_synth_results.dta，包含Year变量"

* 3.7 输出控制组国家与权重对应表
use ukraine_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id
save temp_weights_ukraine.dta, replace


use "`base_dir'/total_publications/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_ukraine.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/total_publications/ukraine_weights_country.xlsx", firstrow(variables) replace



* 3.8 合并UKRAINE和RUSSIAN_FEDERATION结果进行对比可视化
use "`base_dir'/total_publications/ukraine_synth_results.dta", clear
merge 1:1 Year using "`base_dir'/total_publications/russia_synth_results.dta", nogenerate

* 获取2022年效应值
sum ukraine_gap_pct if Year >= `treated_year'
local ukraine_effect_2022 = r(mean)
sum russia_gap_pct if Year >= `treated_year'
local russia_effect_2022 = r(mean)

* 获取效应值
sum ukraine_gap_pct if Year >= `treated_year'
local ukraine_effect = r(mean)
sum russia_gap_pct if Year >= `treated_year'
local russia_effect = r(mean)

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
twoway (line ukraine_actual_real Year, lcolor("227 195 65") lwidth(medthick) yaxis(2)) ///
       (line ukraine_synthetic_real Year, lcolor("227 195 65") lwidth(medthick) lpattern(dash) yaxis(2)) ///
       (line russia_actual_real Year, lcolor("76 92 156") lwidth(medthick) yaxis(1)) ///
       (line russia_synthetic_real Year, lcolor("76 92 156") lwidth(medthick) lpattern(dash) yaxis(1)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       text(60000 2022 "War", placement(east)) ///
	   text(20000 2020 "Russia Effect: `=string(`russia_effect',"%5.2f")'%", size(medium)) ///
       text(25000 2020 "Ukraine Effect: `=string(`ukraine_effect',"%5.2f")'%", size(medium)) ///
       xtitle("") ///
       ytitle("Total Publications", size(medium)) ///
       xlabel(2004(5)2024, nogrid tposition(inside)) ///
       ylabel(0(10000)60000, nogrid tposition(inside) format(%9.0gc) axis(1)) ///
       ylabel(0(2000)12000, nogrid tposition(inside) format(%9.0gc) axis(2)) ///
       xmtick(2004(1)2024, tposition(inside)) ///
       ymtick(0(5000)60000, tposition(inside) axis(1)) ///
	   ymtick(0(2000)12000, tposition(inside) axis(2)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Ukraine Actual" 2 "Ukraine Synthetic" 3 "Russia Actual" 4 "Russia Synthetic") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison_real, replace)

graph export "`base_dir'/total_publications/combined_actual_vs_synthetic.eps",replace
// graph export "`base_dir'/total_publications/combined_actual_vs_synthetic.png", ///
//        width(1200) height(800) replace

* 4. 安慰剂检验
* 4.1 对每个控制组国家进行合成控制分析
foreach country of local control_countries {
    di "Processing `country'"

    use "`base_dir'/total_publications/processed_data.dta", clear

    * 获取当前国家的ID
    qui sum country_id if Country == "`country'"
    local treat_id = r(mean)
    di "Treatment ID for `country': `treat_id'"
	* 跳过ID小于18的国家
    if `treat_id' < 50 {
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
        synth log_pub_total log_gdp_per_capita log_rp RD log_pub_total(2021), ///
              trunit(`=`treat_id'') trperiod(2022) ///
              counit(`placebo_controls') ///
              xperiod(2008(1)2021) ///
              nested allopt ///
              keep("`base_dir'/total_publications/synth_`country'.dta", replace)
    }

    * 如果标准模型失败，尝试简化模型
    if _rc != 0 {
        di "Standard model failed for `country', trying simplified model"
        capture noisily {
            synth log_pub_total log_gdp_per_capita log_rp, ///
                  trunit(`=`treat_id'') trperiod(2022) ///
                  counit(`placebo_controls') ///
                  xperiod(2008(1)2021) ///
                  nested allopt ///
                  keep("`base_dir'/total_publications/synth_`country'.dta", replace)
        }
    }

    * 处理结果
    capture {
        use "`base_dir'/total_publications/synth_`country'.dta", clear
        rename _time Year
        gen actual_real = exp(_Y_treated) - 1
        gen synthetic_real = exp(_Y_synthetic) - 1
		gen gap_pct_effect_`country' = actual_real - synthetic_real
        gen gap_pct_`country' = (actual_real - synthetic_real) / actual_real * 100

        * 计算平均处理效应
        egen avg_effect = mean(gap_pct_`country') if Year >= 2022
        gen avg_gap_pct_`country' = avg_effect
        drop avg_effect

        keep Year gap_pct_effect_`country' gap_pct_`country' avg_gap_pct_`country'
        drop if missing(Year)  // 删除Year缺失的观测值
        save "`base_dir'/total_publications/gap_`country'.dta", replace
    }
}

* 4.2 合并所有结果 - 直接从ARGENTINA开始
* 从ARGENTINA数据开始
use "`base_dir'/total_publications/gap_ARGENTINA.dta", clear
* 合并其他控制组国家
foreach country of local control_countries {
    if "`country'" != "ARGENTINA" {
        capture {
            merge 1:1 Year using "`base_dir'/total_publications/gap_`country'.dta", nogenerate
        }
    }
}
* 合并ukraine数据和russia数据
merge 1:1 Year using "`base_dir'/total_publications/ukraine_synth_results.dta",nogenerate
merge 1:1 Year using "`base_dir'/total_publications/russia_synth_results.dta", nogenerate

* 保存最终合并的数据
save "`base_dir'/total_publications/all_gaps_merged.dta", replace

* 4.4 计算控制组国家的RMSPE - 基于log尺度的差异
use "`base_dir'/total_publications/all_gaps_merged.dta", clear
foreach country of local control_countries {
    capture {
        * 重新加载原始合成控制结果来计算正确的RMSPE
        preserve
        use "`base_dir'/total_publications/synth_`country'.dta", clear
        rename _time Year
        
        * 计算log尺度上的差异（这是合成控制法实际拟合的尺度）
        gen log_gap_`country' = _Y_treated - _Y_synthetic
        
        * 基于log尺度计算RMSPE
        gen pre_sq_error_`country' = log_gap_`country'^2 if Year <= `before_treated_year' & Year > 2008
        egen pre_mspe_`country' = mean(pre_sq_error_`country')
        gen pre_rmspe_`country' = sqrt(pre_mspe_`country')
      
        gen post_sq_error_`country' = log_gap_`country'^2 if Year >= `treated_year'
        egen post_mspe_`country' = mean(post_sq_error_`country')
        gen post_rmspe_`country' = sqrt(post_mspe_`country')
      
        gen rmspe_ratio_`country' = post_rmspe_`country' / pre_rmspe_`country'
        
        * 保存RMSPE结果到临时文件
        keep Year pre_rmspe_`country' post_rmspe_`country' rmspe_ratio_`country'
        
        * 检查并处理重复值
        duplicates drop Year, force
        
        save "`base_dir'/total_publications/temp_rmspe_`country'.dta", replace
        restore
        
        * 合并RMSPE结果到主数据集
        merge 1:1 Year using "`base_dir'/total_publications/temp_rmspe_`country'.dta", nogenerate
    }
}

* 保存最终合并的数据（ukraine和russia的RMSPE已经在前面计算好了）
save "`base_dir'/total_publications/all_gaps_merged.dta", replace

* 5. 结果可视化和统计分析
* 5.1 基于effect计算p-value
// * 获取ukraine基准
// * pre_rmspe_russia(1285.02)；pre_rmspe_ukraine(508.5893)
// sum pre_rmspe_ukraine
// local ukraine_pre_rmspe = r(mean)
// local threshold = 1 // 设置阈值
//
// * 获取russia效应
// sum russia_gap_pct if Year >= 2022
// local russia_avg_effect = abs(r(mean))
// * 获取ukraine效应
// sum ukraine_gap_pct if Year >= 2022
// local ukraine_avg_effect = abs(r(mean))
//
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
// 		if "`country'" == "MALTA" {
// 			continue
// 		}
//      
//         * 检查pre_rmspe
//         sum `var'
//         if r(N) > 0 {
//             local pre_rmspe = r(mean)
//             * 检查gap_pct
//             capture confirm variable gap_pct_`country'
//             if !_rc {
//                 sum gap_pct_`country' if Year >= 2022
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
* 获取EU的RMSPE比率
sum rmspe_ratio_russia
local russia_rmspe_ratio = r(mean)
di "russia的RMSPE比率: `russia_rmspe_ratio'"

* 计算所有控制组国家的RMSPE比率
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

* 计算基于RMSPE比率的p值
local p_value_rmspe_russia = `rmspe_ratio_higher_count_russia' / `total_control_count_russia'
local p_value_rmspe_display_russia = string(`p_value_rmspe_russia', "%9.3f")

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
local p_value_rmspe_display_ukraine = string(`p_value_rmspe_ukraine', "%9.3f")

di "=== RMSPE比率p值计算结果 ==="
di "总控制组国家数: `total_control_count_ukraine'"
di "RMSPE比率大于ukraine的国家数: `rmspe_ratio_higher_ukraine'"
di "基于RMSPE比率的p值: `p_value_rmspe_display_ukraine'"
di "ukraine的RMSPE比率: `ukraine_rmspe_ratio'"


* 5.3 绘制筛选后的安慰剂效应图
sum pre_rmspe_russia // 获取russia基准
local russia_pre_rmspe = r(mean)
local qualified_countries ""  // 用来存储合格的国家列表
local threshold =2

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
                    if `pre_rmspe' < `threshold'*`russia_pre_rmspe' {
                        local qualified_count = `qualified_count' + 1
                        local qualified_countries `"`qualified_countries' "`country'""'
                        di "国家 `country' 合格: pre_rmspe = `pre_rmspe'"
                    }
                }
            }
        }
    }
}

* 绘制筛选后的安慰剂效应图
* 准备绘图命令
local filtered_control_lines ""
local filtered_legend_order ""
local j = 1

* 使用我们存储的合格国家列表
foreach country of local qualified_countries {
    capture confirm variable gap_pct_`country'
    if !_rc {
        local filtered_control_lines `"`filtered_control_lines' (line gap_pct_`country' Year, lpattern(dash) lcolor(gray))"'
        local filtered_legend_order `"`filtered_legend_order' `j' "`country'" "'
        local ++j
    }
}

* 添加russia和ukraine
local filtered_control_lines `"`filtered_control_lines' (line russia_gap_pct Year, lwidth(thick) lcolor("76 92 156"))"'
local filtered_control_lines `"`filtered_control_lines' (line ukraine_gap_pct Year, lwidth(thick) lcolor("227 195 65"))"'

* 绘制图形
twoway `filtered_control_lines', ///
       xline(`treated_year', lpattern(dot) lcolor(gray) lwidth(thick)) ///
       yline(0, lcolor(black)) ///
       xtitle("") ///
       ytitle("Treatment Effect", size(medium)) ///
       text(-20 2010 `"p-value(russia) : `p_value_rmspe_display_russia'"' `"`=char(13)'"' ///
                `"p-value(ukraine) : `p_value_rmspe_display_ukraine'"', size(medium)) ///
       xlabel(2005(2)2023, nogrid tposition(inside)) ///
       ylabel(, nogrid tposition(inside)) ///
       xmtick(2005(1)2023, tposition(inside)) ///
       ymtick(, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
	   legend(off) ///
       name(placebo_filtered, replace)
//        legend(order(`filtered_legend_order' `=`j'' "RUSSIA" `=`j'+1' "UKRAINE") /// 
//               pos(3) ring(1) cols(1) region(style(none)) size(vsmall)) ///
* 导出图形
graph export "`base_dir'/total_publications/placebo_filtered.pdf", replace
// graph export "`base_dir'/total_publications/placebo_filtered.png", ///
//        width(1200) height(800) replace

* 保存最终结果
save "`base_dir'/total_publications/final_results.dta", replace
