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
local base_dir "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/Brexit-stata_external_try"
import excel "`base_dir'/brexit_non_eu.xlsx", sheet("Sheet1") firstrow clear

local treated_year 2016
local before_treated_year 2015
local pre_period_start 2008

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
gen log_pub_total_10 = log_pub_total / 10
gen log_gdp_per_capita_10 = log_gdp_per_capita /10
gen log_rp_10 = log_rp /10

* 1.6 计算预处理期（2008-2015年）的均值变量，避免过拟合
* 计算每个国家在预处理期的平均GDP per capita
bysort country_id: egen gdp_pre_mean = mean(gdp_per_capita) if Year >= `pre_period_start' & Year <= `before_treated_year'
bysort country_id: egen log_gdp_pre_mean = mean(log_gdp_per_capita) if Year >= `pre_period_start' & Year <= `before_treated_year'

* 计算每个国家在预处理期的平均研究人员数量
bysort country_id: egen researchers_pre_mean = mean(ResearchersinRD) if Year >= `pre_period_start' & Year <= `before_treated_year'
bysort country_id: egen log_rp_pre_mean = mean(log_rp) if Year >= `pre_period_start' & Year <= `before_treated_year'

* 计算每个国家在预处理期的平均R&D投入
bysort country_id: egen rd_pre_mean = mean(RD) if Year >= `pre_period_start' & Year <= `before_treated_year'

* 计算每个国家的平均出版物总量（新的协变量）
bysort country_id: egen log_pub_pre_mean = mean(log_pub_total) if Year >= 2010 & Year <= 2015

* 计算每个国家在2010-2015年的平均国际合作比例（新的协变量）
bysort country_id: egen intl_ratio_mean = mean(intl_ratio) if Year >= 2005 & Year <= 2015

* 将预处理期均值扩展到所有年份
bysort country_id: egen gdp_pre_final = max(gdp_pre_mean)
bysort country_id: egen log_gdp_pre_final = max(log_gdp_pre_mean)
bysort country_id: egen researchers_pre_final = max(researchers_pre_mean)
bysort country_id: egen log_rp_pre_final = max(log_rp_pre_mean)
bysort country_id: egen rd_pre_final = max(rd_pre_mean)
bysort country_id: egen log_pub_pre_mean_final = max(log_pub_pre_mean)
bysort country_id: egen intl_ratio_mean_final = max(intl_ratio_mean)

* 清理临时变量
drop gdp_pre_mean log_gdp_pre_mean researchers_pre_mean log_rp_pre_mean rd_pre_mean
drop log_pub_pre_mean intl_ratio_mean

* 1.7 为UK和EU分别定义控制变量 - 使用预处理期均值避免过拟合
* 原变量（可能导致过拟合）
* global control_vars "log_gdp_per_capita log_rp RD"

global control_vars "intl_ratio_mean_final"

* UK专用控制变量
global uk_control_vars_1 "intl_ratio(2015) intl_ratio(2014) intl_ratio(2011) intl_ratio(2010)  "

* EU专用控制变量
global eu_control_vars_1 "intl_ratio(2015) intl_ratio(2010) "

* 1.6 保存处理后的数据
save "`base_dir'/intl_ratio/processed_data.dta", replace

* 2. UK合成控制分析
* 2.1 运行UK的合成控制分析
synth intl_ratio ///
	$control_vars ///
    $uk_control_vars_1 , ///
    trunit(`uk_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(2008(1)`before_treated_year') ///
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
egen uk_avg_effect = mean(uk_gap) if Year >= `treated_year'
local uk_avg_effect : display %5.4f r(mean)


* 2.5 计算UK的RMSPE
gen pre_sq_error_uk = uk_gap^2 if Year <= `before_treated_year' & Year > 2008
egen pre_mspe_uk = mean(pre_sq_error_uk)
gen pre_rmspe_uk = sqrt(pre_mspe_uk)

gen post_sq_error_uk = uk_gap^2 if Year >= `treated_year'
egen post_mspe_uk = mean(post_sq_error_uk)
gen post_rmspe_uk = sqrt(post_mspe_uk)

gen rmspe_ratio_uk = post_rmspe_uk / pre_rmspe_uk


* 2.6 保存UK结果
save "`base_dir'/intl_ratio/uk_synth_results.dta", replace
* 2.7 输出控制组国家与权重对应表
use uk_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id

* 检查并处理重复的 country_id
duplicates report country_id
duplicates tag country_id, gen(dup)
count if dup > 0
if r(N) > 0 {
    di "警告：发现重复的 country_id，将进行聚合处理"
    * 如果有重复，使用 collapse 对权重进行求和（或者可以改为 first、mean 等）
    collapse (sum) _W_Weight, by(country_id)
}
else {
    drop dup
}
drop if country_id == .

save temp_weights_uk_`treated_year'.dta, replace

use "`base_dir'/intl_ratio/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_uk_`treated_year'.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/intl_ratio/uk_weights_country.xlsx", firstrow(variables) replace

* 3. EU合成控制分析
* 3.1 准备EU分析数据
use "`base_dir'/intl_ratio/processed_data.dta", clear

* 3.2 运行EU的合成控制分析
synth intl_ratio ///
	$control_vars ///
    $eu_control_vars_1 , ///
    trunit(`eu_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(2008(1)`before_treated_year') ///
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
egen eu_avg_effect = mean(eu_gap) if Year >= `treated_year' 
local eu_avg_effect : display %5.4f r(mean)

* 3.6 计算EU的RMSPE
gen pre_sq_error_eu = eu_gap^2 if Year <= `before_treated_year' & Year > 2008
egen pre_mspe_eu = mean(pre_sq_error_eu)                                 
gen pre_rmspe_eu = sqrt(pre_mspe_eu)

gen post_sq_error_eu = eu_gap^2 if Year >= `treated_year'
egen post_mspe_eu = mean(post_sq_error_eu)
gen post_rmspe_eu = sqrt(post_mspe_eu)

gen rmspe_ratio_eu = post_rmspe_eu / pre_rmspe_eu


* 3.7 保存EU结果
save "`base_dir'/intl_ratio/eu_synth_results.dta", replace
* 3.7 输出控制组国家与权重对应表
use eu_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id

* 检查并处理重复的 country_id
duplicates report country_id
duplicates tag country_id, gen(dup)
count if dup > 0
if r(N) > 0 {
    di "警告：发现重复的 country_id，将进行聚合处理"
    * 如果有重复，使用 collapse 对权重进行求和（或者可以改为 first、mean 等）
    collapse (sum) _W_Weight, by(country_id)
}
else {
    drop dup
}
drop if country_id == .

save temp_weights_eu_`treated_year'.dta, replace

use "`base_dir'/intl_ratio/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_eu_`treated_year'.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/intl_ratio/eu_weights_country.xlsx", firstrow(variables) replace

* 3.9 合并EU和UK结果进行对比可视化
use "`base_dir'/intl_ratio/eu_synth_results.dta", clear
merge 1:1 Year using "`base_dir'/intl_ratio/uk_synth_results.dta", nogenerate
* 获取效应值
sum eu_gap if Year >= `treated_year'
local eu_effect = r(mean)*100
sum uk_gap if Year >= `treated_year'
local uk_effect = r(mean)*100

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
// 您的图形代码保持不变
twoway (connected eu_actual Year, lcolor("0 51 154") lwidth(medthick) mcolor("0 51 154")) ///
       (line eu_synthetic Year, lcolor("0 51 154") lwidth(medthick) lpattern(dash)) ///
       (connected uk_actual Year, lcolor("201 6 43") lwidth(medthick) mcolor("201 6 43")) ///
       (line uk_synthetic Year, lcolor("201 6 43") lwidth(medthick) lpattern(dash)), ///
       xline(`treated_year', lpattern(dot) lcolor(black)) ///
	   text(0.78 2015 "Brexit", size(medium)) ///
	   text(0.75 2021 `"UK : `=string(`uk_effect',"%5.2f")'%"' `"`=char(13)'"', size(medium)) ///
	   text(0.5 2021 `"EU : `=string( `eu_effect',"%5.2f")'%"' `"`=char(13)'"', size(medium)) ///
       xtitle("") ///
       ytitle("The ratio of international publications", size(medium)) ///
       xlabel(2005(2)2024, nogrid tposition(inside)) ///
       ylabel(0.4(0.1)0.8, nogrid tposition(inside) format(%3.1f)) ///
       xmtick(2005(1)2024, tposition(iside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "EU Actual" 2 "EU Synthetic" 3 "UK Actual" 4 "UK Synthetic") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison, replace)

graph export "`base_dir'/intl_ratio/combined_actual_vs_synthetic_`treated_year'.pdf", replace

* 4. 安慰剂检验
* 4.1 对每个控制组国家进行合成控制分析
foreach country of local control_countries {
    di "Processing `country'"

    use "`base_dir'/intl_ratio/processed_data.dta", clear

    * 获取当前国家的ID（改进版）
    qui sum country_id if Country == "`country'"
    local treat_id = r(mean)
    di "Treatment ID for `country': `treat_id'"
	* 跳过ID小于50的国家
    if `treat_id' < 50 {
        di "Skipping `country' (ID < 1)"
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

    
	di "Using STANDAR model for `country'"
	* 运行标准合成控制
	capture noisily {
		synth intl_ratio $control_vars ///
			  $uk_control_vars_1 , ///
			  trunit(`=`treat_id'') trperiod(2016) ///
			  counit(`placebo_controls') ///
			  xperiod(2008(1)2015) ///
			  nested allopt ///
			  keep("`base_dir'/intl_ratio/synth_`country'", replace)
	}
    

    * 处理结果
    capture {
        use "`base_dir'/intl_ratio/synth_`country'", clear
        rename _time Year
		rename _Y_treated cc_actual
		rename _Y_synthetic cc_synthetic
		gen gap_`country' = cc_actual - cc_synthetic
 
        * 计算平均处理效应
        egen avg_effect = mean(gap_`country') if Year >= 2016
        gen avg_gap_`country' = avg_effect
        drop avg_effect
 
        keep Year gap_`country' avg_gap_`country'
        drop if missing(Year)
        save "`base_dir'/intl_ratio/gap_`country'", replace
    }
}


* 4.2 合并所有结果
use "`base_dir'/intl_ratio/gap_ARGENTINA", clear
foreach country of local control_countries {
    if "`country'" != "ARGENTINA" {
        capture {
            merge 1:1 Year using "`base_dir'/intl_ratio/gap_`country'", nogenerate
        }
    }
}
merge 1:1 Year using "`base_dir'/intl_ratio/eu_synth_results.dta", nogenerate
merge 1:1 Year using "`base_dir'/intl_ratio/uk_synth_results.dta", nogenerate

* 4.3 计算每个国家的RMSPE
foreach country of local control_countries {
    capture {
        gen pre_sq_error_`country' = gap_`country'^2 if Year <= `before_treated_year' & Year > 2008
        egen pre_mspe_`country' = mean(pre_sq_error_`country')
        gen pre_rmspe_`country' = sqrt(pre_mspe_`country')
      
        gen post_sq_error_`country' = gap_`country'^2 if Year >= `treated_year'
        egen post_mspe_`country' = mean(post_sq_error_`country')
        gen post_rmspe_`country' = sqrt(post_mspe_`country')
      
        gen rmspe_ratio_`country' = post_rmspe_`country' / pre_rmspe_`country'
    }
}

* 5. 最直接的p值计算
* 5.1 基于effect计算p-value 
// * 获取UK基准
// sum pre_rmspe_eu
// local eu_pre_rmspe = r(mean)
// local threshold = 10  // 设置阈值
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

* 5.2 基于RMSPE比率的计算eu的p值
* 获取EU的RMSPE比率
sum rmspe_ratio_eu
local eu_rmspe_ratio = r(mean)
di "EU的RMSPE比率: `eu_rmspe_ratio'"

* 计算所有控制组国家的RMSPE比率
local total_control_count_eu = 2
local rmspe_ratio_higher_count_eu = 1

foreach country of local control_countries {
    capture confirm variable rmspe_ratio_`country'
    if !_rc {
        sum rmspe_ratio_`country'
        if r(N) > 0 {
            local total_control_count_eu = `total_control_count_eu' + 1
            local country_rmspe_ratio = r(mean)
            
            * 检查该国家的RMSPE比率是否大于EU
            if `country_rmspe_ratio' > `eu_rmspe_ratio' {
                local rmspe_ratio_higher_count_eu = `rmspe_ratio_higher_count_eu' + 1
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于EU)"
            }
            else {
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于EU)"
            }
        }
    }
}

* 计算基于RMSPE比率的p值
local p_value_rmspe_eu = `rmspe_ratio_higher_count_eu' / `total_control_count_eu'
local p_value_rmspe_display_eu = string(`p_value_rmspe_eu', "%9.2f")

di "=== RMSPE比率p值计算结果 ==="
di "总控制组国家数: `total_control_count_eu'"
di "RMSPE比率大于EU的国家数: `rmspe_ratio_higher_count_eu'"
di "基于RMSPE比率的p值: `p_value_rmspe_display_eu'"
di "EU的RMSPE比率: `eu_rmspe_ratio'"


* 5.3 基于RMSPE比率计算uk的p值
* 获取EU的RMSPE比率
sum rmspe_ratio_uk
local uk_rmspe_ratio = r(mean)
di "uk的RMSPE比率: `uk_rmspe_ratio'"

* 计算所有控制组国家的RMSPE比率
local total_control_count_uk = 2
local rmspe_ratio_higher_count_uk = 1

foreach country of local control_countries {
    capture confirm variable rmspe_ratio_`country'
    if !_rc {
        sum rmspe_ratio_`country'
        if r(N) > 0 {
            local total_control_count_uk = `total_control_count_uk' + 1
            local country_rmspe_ratio = r(mean)
            
            * 检查该国家的RMSPE比率是否大于uk
            if `country_rmspe_ratio' > `uk_rmspe_ratio' {
                local rmspe_ratio_higher_count_uk = `rmspe_ratio_higher_count_uk' + 1
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于uk)"
            }
            else {
                di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于uk)"
            }
        }
    }
}

* 计算基于RMSPE比率的p值
local p_value_rmspe_uk = `rmspe_ratio_higher_count_uk' / `total_control_count_uk'
local p_value_rmspe_display_uk = string(`p_value_rmspe_uk', "%9.2f")

di "=== RMSPE比率p值计算结果 ==="
di "总控制组国家数: `total_control_count_uk'"
di "RMSPE比率大于uk的国家数: `rmspe_ratio_higher_count_uk'"
di "基于RMSPE比率的p值: `p_value_rmspe_display_uk'"
di "uk的RMSPE比率: `uk_rmspe_ratio'"

* 5.4 绘制筛选后的安慰剂效应图
* 获取UK基准
sum pre_rmspe_eu
local eu_pre_rmspe = r(mean)
local threshold = 20  // 设置阈值
local qualified_count = 0

local qualified_countries ""  // 用来存储合格的国家列表
* 使用varlist自动遍历所有pre_rmspe变量
foreach var of varlist pre_rmspe_* {
    if "`var'" != "pre_rmspe_uk" & "`var'" != "pre_rmspe_eu" {
        * 提取国家名
        local country = substr("`var'", 11, .)
        * 检查pre_rmspe
        sum `var'
        if r(N) > 0 {
            local pre_rmspe = r(mean)
            if !_rc {
                if r(N) > 0 {
                    * 判断是否合格
                    if `pre_rmspe' < `threshold'*`eu_pre_rmspe' {
						local qualified_count = `qualified_count' + 1
                        local qualified_countries `"`qualified_countries' "`country'""'
                        di "国家 `country' 合格: pre_rmspe = `pre_rmspe'"
                    }
                }
            }
        }
    }
}

di "图中控制组国家的数量为:`qualified_count'"

* 准备绘图命令（为每个 control 国家分配不同颜色，便于区分哪条线对应哪国）
local filtered_control_lines ""
local filtered_legend_order ""
local j = 1
* 预定义一组可区分的颜色（与图例顺序一致，国家多时可追加 gs4 gs6 gs8 等）
local color_list "navy maroon forest_green dkorange brown cyan gold lime magenta orange_red purple teal red blue green orange sienna olive"

* 使用我们存储的合格国家列表
foreach country of local qualified_countries {
    capture confirm variable gap_`country'
    if !_rc {
		gen gap_100_`country' = gap_`country' * 100
        local ccolor : word `j' of `color_list'
        if "`ccolor'" == "" local ccolor gs10
        local filtered_control_lines `"`filtered_control_lines' (line gap_100_`country' Year, lpattern(dash) lcolor("`ccolor'"))"'
        local filtered_legend_order `"`filtered_legend_order' `j' "`country'" "'
        local ++j
    }
}

* 添加EU和UK
* 为EU和UK创建新变量
gen eu_gap100 = eu_gap * 100
gen uk_gap100 = uk_gap * 100
local filtered_control_lines `"`filtered_control_lines' (line eu_gap100 Year, lwidth(thick) lcolor("0 51 154"))"'
local filtered_control_lines `"`filtered_control_lines' (line uk_gap100 Year, lwidth(thick) lcolor("201 6 43"))"'

* 绘制图形
// twoway `filtered_control_lines', ///
//        xline(`treated_year', lpattern(dot) lcolor(black)) ///
//        yline(0, lcolor(black)) ///
//        xtitle("") ///
// 	   ytitle("Treatment Effect", size(medium)) ///
// 	   text(-10 2008 `"p-value(EU) : `p_value_rmspe_display_eu'"' ///
//                 `"p-value(UK) : `p_value_rmspe_display_uk'"', size(medium)) ///
//        xlabel(2005(2)2024, nogrid tposition(inside)) ///
//        ylabel(, nogrid tposition(inside)) ///
//        xmtick(2005(1)2024, tposition(inside)) ///
//        ymtick(, tposition(inside)) ///
//        graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
//        plotregion(style(outline) lcolor(black) lwidth(thin)) ///
//        bgcolor(white) ///
//        legend(off) ///
//        name(placebo_filtered, replace)
// // legend(order(`filtered_legend_order' `=`j'' "EU" `=`j'+1' "UK") pos(3) ring(1) cols(1) region(style(none)) size(vsmall)) ///

twoway `filtered_control_lines', ///
       xline(`treated_year', lpattern(dot) lcolor(black)) ///
       yline(0, lcolor(black)) ///
       xtitle("") ///
	   ytitle("Treatment Effect", size(medium)) ///
	   text(-10 2008 `"p-value(EU) : `p_value_rmspe_display_eu'"' ///
                `"p-value(UK) : `p_value_rmspe_display_uk'"', size(medium)) ///
       xlabel(2005(2)2024, nogrid tposition(inside)) ///
       ylabel(, nogrid tposition(inside)) ///
       xmtick(2005(1)2024, tposition(inside)) ///
       ymtick(, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(`filtered_legend_order' `j' "EU" `=`j'+1' "UK") pos(3) ring(1) cols(1) region(style(none)) size(vsmall)) ///
       name(placebo_filtered, replace)

* 导出图形
graph export "`base_dir'/intl_ratio/placebo_filtered_`treated_year'.pdf", replace
