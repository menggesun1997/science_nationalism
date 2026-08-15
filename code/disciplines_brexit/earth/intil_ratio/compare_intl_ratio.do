clear all
set more off

********************************************************************************
* 程序结构：
* 1. 数据准备和变量定义
* 2. UK合成控制分析
* 3. EU合成控制分析
* 4. 安慰剂检验
* 5. 结果可视化和统计分析
********************************************************************************

* 1. 数据准备和变量定义
* 1.1 导入数据

local base_dir "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/disciplines_brexit"
local discipline "earth"
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
    if !inlist("`country'", "EU", "UNITED_KINGDOM") {
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
qui sum country_id if Country == "UNITED_KINGDOM"
local uk_id = r(mean)
qui sum country_id if Country == "EU"
local eu_id = r(mean)

* 1.5 生成分析所需变量
gen log_pub_total = log(pub_total + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

* 1.6 保存处理后的数据

save "`base_dir'/`discipline'/intil_ratio/processed_data.dta", replace

* 2. UK合成控制分析
* 2.1 运行UK的合成控制分析
synth intl_ratio ///
    intl_ratio(2015) intl_ratio(2014) intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2009) intl_ratio(2008) , /// 结果变量的滞后值
    trunit(`uk_id') trperiod(2016) ///
    counit(`control_ids') ///
    xperiod(2008(1)2015) ///
    nested allopt ///
    keep(uk_synth_results, replace)

* 2.2 处理UK结果
use uk_synth_results, clear
rename _time Year
rename _Y_treated uk_actual
rename _Y_synthetic uk_synthetic


* 2.3 计算UK效应（对于比例，直接计算差异，不是百分比变化）
* 假设uk_actual和uk_synthetic已经是比例值（0-1之间）
gen uk_gap = uk_actual - uk_synthetic

* 2.4 计算UK平均处理效应（对于比例，计算后期均值差异）
egen uk_avg_effect = mean(uk_gap) if Year >= 2016
local uk_avg_effect : display %5.4f r(mean)


* 2.5 计算UK的RMSPE
gen pre_sq_error_uk = uk_gap^2 if Year <= 2015
egen pre_mspe_uk = mean(pre_sq_error_uk)
gen pre_rmspe_uk = sqrt(pre_mspe_uk)

gen post_sq_error_uk = uk_gap^2 if Year >= 2016
egen post_mspe_uk = mean(post_sq_error_uk)
gen post_rmspe_uk = sqrt(post_mspe_uk)

gen rmspe_ratio_uk = post_rmspe_uk / pre_rmspe_uk


* 2.6 保存UK结果

save "`base_dir'/`discipline'/intil_ratio/uk_synth_results.dta", replace

* 3. EU合成控制分析
* 3.1 准备EU分析数据
use "`base_dir'/`discipline'/intil_ratio/processed_data.dta", clear

* 3.2 运行EU的合成控制分析
synth intl_ratio ///
    intl_ratio(2015) intl_ratio(2014) intl_ratio(2013) intl_ratio(2012) intl_ratio(2011) intl_ratio(2010) intl_ratio(2009) intl_ratio(2008) , /// 结果变量的滞后值
    trunit(`eu_id') trperiod(2016) ///
    counit(`control_ids') ///
    xperiod(2008(1)2015) ///
    nested allopt ///
    keep(eu_synth_results, replace)

* 3.3 处理EU结果
use eu_synth_results, clear
rename _time Year
rename _Y_treated eu_actual
rename _Y_synthetic eu_synthetic

* 3.4 计算EU效应
gen eu_gap = eu_actual - eu_synthetic

* 3.5 计算EU平均处理效应
egen eu_avg_effect = mean(eu_gap) if Year >= 2016
local eu_avg_effect : display %5.4f r(mean)

* 3.6 计算EU的RMSPE
gen pre_sq_error_eu = eu_gap^2 if Year <= 2015
egen pre_mspe_eu = mean(pre_sq_error_eu)
gen pre_rmspe_eu = sqrt(pre_mspe_eu)

gen post_sq_error_eu = eu_gap^2 if Year >= 2016
egen post_mspe_eu = mean(post_sq_error_eu)
gen post_rmspe_eu = sqrt(post_mspe_eu)

gen rmspe_ratio_eu = post_rmspe_eu / pre_rmspe_eu


* 3.7 保存EU结果
save "`base_dir'/`discipline'/intil_ratio/eu_synth_results.dta", replace


* 3.8 合并EU和UK结果进行对比可视化
use "`base_dir'/`discipline'/intil_ratio/eu_synth_results.dta", clear
merge 1:1 Year using "`base_dir'/`discipline'/intil_ratio/uk_synth_results.dta", nogenerate
* 获取效应值
sum eu_gap if Year >= 2016
local eu_effect = r(mean)*100
sum uk_gap if Year >= 2016
local uk_effect = r(mean)*100

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
twoway (line eu_actual Year, lcolor("0 51 154") lwidth(medthick)) ///
       (line eu_synthetic Year, lcolor("0 51 154") lwidth(medthick) lpattern(dash)) ///
       (line uk_actual Year, lcolor("201 6 43") lwidth(medthick)) ///
       (line uk_synthetic Year, lcolor("201 6 43") lwidth(medthick) lpattern(dash)), ///
	   xline(2016, lpattern(dot) lcolor(black)) ///
       text(0.7 2020 `"EU : `=string( `eu_effect',"%5.2f")'%"' `"`=char(13)'"' ///
                `"UK : `=string(`uk_effect',"%5.2f")'%"', size(medium)) ///
       xtitle("") ///
	   title("`discipline'") ///
       ytitle("the ratio of international publications", size(medium)) ///
       xlabel(2005(2)2024, nogrid tposition(inside)) ///
       ylabel(0(0.1)1, nogrid tposition(inside) format(%9.0gc)) ///
       xmtick(2005(1)2024, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(off) ///
       name(combined_comparison_real, replace)	 

graph export "`base_dir'/`discipline'/intil_ratio/brexit_`discipline'_ratio.pdf", replace

* 4. 安慰剂检验
* 4.1 对每个控制组国家进行合成控制分析
// foreach country of local control_countries {
//     di "Processing `country'"
//
//     use "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/processed_data.dta", clear
//
//     * 获取当前国家的ID（改进版）
//     qui sum country_id if Country == "`country'"
//     local treat_id = r(mean)
//     di "Treatment ID for `country': `treat_id'"
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
//     * 对于特定国家使用简化模型
//     if inlist("`country'", "COSTA_RICA", "UNITED_STATES", "TURKIYE") {
//         di "Using simplified model for `country'"
//         capture noisily {
//             synth intl_ratio log_pub_total log_gdp_per_capita log_rp RD, ///
//                   trunit(`=`treat_id'') trperiod(2016) ///
//                   counit(`placebo_controls') ///
//                   xperiod(2008(1)2015) ///
//                   nested allopt ///
//                   keep("/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/synth_`country'", replace)
//         }
//     }
//     else {
// 		di "Using STANDAR model for `country'"
//         * 运行标准合成控制
//         capture noisily {
// 			synth intl_ratio log_pub_total log_gdp_per_capita  log_rp RD ///
//                   intl_ratio(2015) intl_ratio(2013) intl_ratio(2012) intl_ratio(2010) intl_ratio(2010(1)2015), ///
//                   trunit(`=`treat_id'') trperiod(2016) ///
//                   counit(`placebo_controls') ///
//                   xperiod(2008(1)2015) ///
//                   nested allopt ///
//                   keep("/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/synth_`country'", replace)
//         }
//     }
//
//     * 处理结果
//     capture {
//         use "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/synth_`country'", clear
//         rename _time Year
// 		rename _Y_treated cc_actual
// 		rename _Y_synthetic cc_synthetic
// 		gen gap_`country' = cc_actual - cc_synthetic
//  
//         * 计算平均处理效应
//         egen avg_effect = mean(gap_`country') if Year >= 2016
//         gen avg_gap_`country' = avg_effect
//         drop avg_effect
//  
//         keep Year gap_`country' avg_gap_`country'
//         drop if missing(Year)
//         save "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/gap_`country'", replace
//     }
// }
//
//
// * 4.2 合并所有结果
// use "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/gap_ARGENTINA", clear
// foreach country of local control_countries {
//     if "`country'" != "ARGENTINA" {
//         capture {
//             merge 1:1 Year using "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/gap_`country'", nogenerate
//         }
//     }
// }
// merge 1:1 Year using "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/eu_synth_results.dta", nogenerate
// merge 1:1 Year using "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/uk_synth_results.dta", nogenerate
//
// * 4.3 计算每个国家的RMSPE
// foreach country of local control_countries {
//     capture {
//         gen pre_sq_error_`country' = gap_`country'^2 if Year <= 2015
//         egen pre_mspe_`country' = mean(pre_sq_error_`country')
//         gen pre_rmspe_`country' = sqrt(pre_mspe_`country')
//       
//         gen post_sq_error_`country' = gap_`country'^2 if Year >= 2016
//         egen post_mspe_`country' = mean(post_sq_error_`country')
//         gen post_rmspe_`country' = sqrt(post_mspe_`country')
//       
//         gen rmspe_ratio_`country' = post_rmspe_`country' / pre_rmspe_`country'
//     }
// }
//
// * 5. 最直接的p值计算
// * 获取UK基准
// sum pre_rmspe_eu
// local eu_pre_rmspe = r(mean)
// local threshold = 2  // 设置阈值
//
// * 获取UK效应
// sum eu_gap if Year >= 2016
// local eu_avg_effect = abs(r(mean))
//
// * 自动获取所有控制组变量（不穷举）
// local qualified_count = 0
// local extreme_count = 0
// local qualified_countries ""  // 用来存储合格的国家列表
//
// * 使用varlist自动遍历所有pre_rmspe变量
// foreach var of varlist pre_rmspe_* {
//     if "`var'" != "pre_rmspe_uk" & "`var'" != "pre_rmspe_eu" {
//         * 提取国家名
//         local country = substr("`var'", 11, .)
//        
//         * 检查pre_rmspe
//         sum `var'
//         if r(N) > 0 {
//             local pre_rmspe = r(mean)
//            
//             * 检查gap
//             capture confirm variable gap_`country'
//             if !_rc {
//                 sum gap_`country' if Year >= 2016
//                 if r(N) > 0 {
//                     local effect = abs(r(mean))
//                    
//                     * 判断是否合格
//                     if `pre_rmspe' < `threshold'*`eu_pre_rmspe' {
//                         local qualified_count = `qualified_count' + 1
//                         local qualified_countries `"`qualified_countries' "`country'""'
//                         di "国家 `country' 合格: pre_rmspe = `pre_rmspe'"
//                        
//                         * 判断是否效应更极端
//                         if `effect' >= `eu_avg_effect' {
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
// * 5.4 绘制筛选后的安慰剂效应图
// * 准备绘图命令
// local filtered_control_lines ""
// local filtered_legend_order ""
// local j = 1
//
// * 使用我们存储的合格国家列表
// foreach country of local qualified_countries {
//     capture confirm variable gap_`country'
//     if !_rc {
// 		gen gap_100_`country' = gap_`country' * 100
//         local filtered_control_lines `"`filtered_control_lines' (line gap_100_`country' Year, lpattern(dash))"'
//         local filtered_legend_order `"`filtered_legend_order' `j' "`country'" "'
//         local ++j
//     }
// }
//
// * 添加EU和UK
// * 为EU和UK创建新变量
// gen eu_gap100 = eu_gap * 100
// gen uk_gap100 = uk_gap * 100
// local filtered_control_lines `"`filtered_control_lines' (line eu_gap100 Year, lwidth(thick) lcolor("137 202 229"))"'
// local filtered_control_lines `"`filtered_control_lines' (line uk_gap100 Year, lwidth(thick) lcolor(orange_red))"'
//
// * 绘制图形
// twoway `filtered_control_lines', ///
//        xline(2016, lpattern(dash) lcolor(gray)) ///
//        text(6 2016 "Brexit", placement(east)) ///
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
//        legend(order(`filtered_legend_order' `=`j'' "EU" `=`j'+1' "UK") /// 
//               pos(3) ring(1) cols(1) region(style(none)) size(vsmall)) ///
//        name(placebo_filtered, replace)
//
// * 导出图形
// graph export "/Users/sunmengge/Dropbox/Brexit-stata/intl_ratio/placebo_filtered.png", ///
//        width(1200) height(800) replace
