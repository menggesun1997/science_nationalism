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
gen log_gdp_per_capita_10 = log_gdp_per_capita / 10

gen log_rp = log(ResearchersinRD + 1)
gen log_rp_10 = log_rp / 10

* 1.6 计算预处理期（2008-2015年）的均值变量，避免过拟合
* 计算每个国家在预处理期的平均GDP per capita
bysort country_id: egen gdp_pre_mean = mean(gdp_per_capita) if Year >= `pre_period_start' & Year <= `before_treated_year'
bysort country_id: egen log_gdp_pre_mean = mean(log_gdp_per_capita) if Year >= `pre_period_start' & Year <= `before_treated_year'

* 计算每个国家在预处理期的平均研究人员数量
bysort country_id: egen researchers_pre_mean = mean(ResearchersinRD) if Year >= `pre_period_start' & Year <= `before_treated_year'
bysort country_id: egen log_rp_pre_mean = mean(log_rp) if Year >= `pre_period_start' & Year <= `before_treated_year'

* 计算每个国家在预处理期的平均R&D投入
bysort country_id: egen rd_pre_mean = mean(RD) if Year >= `pre_period_start' & Year <= `before_treated_year'

* 计算每个国家在2010-2015年的平均出版物总量（新的协变量）
bysort country_id: egen log_pub_pre_mean_uk = mean(log_pub_total) if Year >= 2005 & Year <= 2012
bysort country_id: egen log_pub_pre_mean_eu = mean(log_pub_total) if Year >= 2005 & Year <= 2014

* 将预处理期均值扩展到所有年份
bysort country_id: egen gdp_pre_final = max(gdp_pre_mean)
bysort country_id: egen log_gdp_pre_final = max(log_gdp_pre_mean)
bysort country_id: egen researchers_pre_final = max(researchers_pre_mean)
bysort country_id: egen log_rp_pre_final = max(log_rp_pre_mean)
bysort country_id: egen rd_pre_final = max(rd_pre_mean)
bysort country_id: egen log_pub_pre_mean_uk_final = max(log_pub_pre_mean_uk)
bysort country_id: egen log_pub_pre_mean_eu_final = max(log_pub_pre_mean_eu)

* 清理临时变量
drop gdp_pre_mean log_gdp_pre_mean researchers_pre_mean log_rp_pre_mean rd_pre_mean
drop log_pub_pre_mean_uk log_pub_pre_mean_eu


* 1.7 为UK和EU分别定义控制变量 - 使用预处理期均值避免过拟合
* 原变量（可能导致过拟合）
global control_vars "log_gdp_per_capita log_rp RD"

* 基础协变量（所有模型都使用）
// global base_control_vars "log_gdp_pre_final log_rp_pre_final rd_pre_final log_pub_pre_final"

* UK专用控制变量（添加出版物均值）
global uk_control_vars "log_pub_pre_mean_uk_final"
global uk_control_vars_1 "log_pub_total(2013) "


* EU专用控制变量（添加出版物均值）
global eu_control_vars "log_pub_pre_mean_eu_final"
global eu_control_vars_1 "log_pub_total(2015) "


* 显示控制变量的描述统计
di "预处理期均值控制变量描述统计："
summarize log_pub_pre_mean_uk_final log_pub_pre_mean_eu_final

* 1.8 保存处理后的数据
save "`base_dir'/total_publications/processed_data.dta", replace

* 2. UK合成控制分析
* 2.1 运行UK的合成控制分析
capture noisily {
    synth log_pub_total ///
        $uk_control_vars ///
        $uk_control_vars_1 , ///
        trunit(`uk_id') trperiod(`treated_year') ///
        counit(`control_ids') ///
        xperiod(`pre_period_start'(1)`before_treated_year') ///
        nested allopt ///
        keep(uk_synth_results, replace)
}

* 2.2 处理UK结果
use uk_synth_results, clear
rename _time Year
rename _Y_treated uk_actual
rename _Y_synthetic uk_synthetic
gen uk_gap = uk_actual - uk_synthetic

* 2.3 计算UK效应
gen uk_actual_real = exp(uk_actual) - 1
gen uk_synthetic_real = exp(uk_synthetic) - 1
gen uk_gap_pct_effect = uk_actual_real - uk_synthetic_real
gen uk_gap_pct = (uk_actual_real - uk_synthetic_real) / uk_actual_real * 100

* 2.4 计算UK平均处理效应
egen uk_avg_effect = mean(uk_gap_pct) if Year >= `treated_year'
local uk_avg_effect : display %5.2f r(mean)

* 2.5 计算UK的RMSPE - 基于log尺度
gen log_gap_uk = uk_actual - uk_synthetic
gen pre_sq_error_uk = log_gap_uk^2 if Year <= `before_treated_year' & Year > 2008
egen pre_mspe_uk = mean(pre_sq_error_uk)
gen pre_rmspe_uk = sqrt(pre_mspe_uk)

gen post_sq_error_uk = log_gap_uk^2 if Year >= `treated_year'
egen post_mspe_uk = mean(post_sq_error_uk)
gen post_rmspe_uk = sqrt(post_mspe_uk)

gen rmspe_ratio_uk = post_rmspe_uk / pre_rmspe_uk

* 2.6 保存UK结果
save "`base_dir'/total_publications/uk_synth_results.dta", replace

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

use "`base_dir'/total_publications/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_uk_`treated_year'.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/total_publications/uk_weights_country.xlsx", firstrow(variables) replace

* 3. EU合成控制分析
* 3.1 准备EU分析数据
use "`base_dir'/total_publications/processed_data.dta", clear

* 3.2 运行EU的合成控制分析
capture noisily {
    synth log_pub_total /// 
        $eu_control_vars ///
        $eu_control_vars_1 , ///
        trunit(`eu_id') trperiod(`treated_year') ///
        counit(`control_ids') ///
        xperiod(`pre_period_start'(1)`before_treated_year') ///
        nested allopt ///
        keep(eu_synth_results, replace)
}


* 3.3 处理EU结果
use eu_synth_results, clear
rename _time Year
rename _Y_treated eu_actual
rename _Y_synthetic eu_synthetic
gen eu_gap = eu_actual - eu_synthetic

* 3.4 计算EU效应
gen eu_actual_real = exp(eu_actual) - 1
gen eu_synthetic_real = exp(eu_synthetic) - 1
gen eu_gap_pct_effect = eu_actual_real - eu_synthetic_real
gen eu_gap_pct = (eu_actual_real - eu_synthetic_real) / eu_actual_real * 100

* 3.5 计算EU平均处理效应
egen eu_avg_effect = mean(eu_gap_pct) if Year >= `treated_year'
local eu_avg_effect : display %5.2f r(mean)

* 3.6 计算EU的RMSPE - 基于log尺度
gen log_gap_eu = eu_actual - eu_synthetic
gen pre_sq_error_eu = log_gap_eu^2 if Year <= `before_treated_year' & Year > 2008
egen pre_mspe_eu = mean(pre_sq_error_eu)
gen pre_rmspe_eu = sqrt(pre_mspe_eu)

gen post_sq_error_eu = log_gap_eu^2 if Year >= `treated_year'
egen post_mspe_eu = mean(post_sq_error_eu)
gen post_rmspe_eu = sqrt(post_mspe_eu)

gen rmspe_ratio_eu = post_rmspe_eu / pre_rmspe_eu

* 3.7 保存EU结果
save "`base_dir'/total_publications/eu_synth_results.dta", replace

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

use "`base_dir'/total_publications/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_eu_`treated_year'.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/total_publications/eu_weights_country.xlsx", firstrow(variables) replace



* 3.9 合并EU和UK结果进行对比可视化
use "`base_dir'/total_publications/eu_synth_results.dta", clear
merge 1:1 Year using "`base_dir'/total_publications/uk_synth_results.dta", nogenerate

* 获取效应值
sum eu_gap_pct if Year >= `treated_year'
local eu_effect = r(mean)
local eu_effect_str = string(`eu_effect',"%5.2f")

sum uk_gap_pct if Year >= `treated_year'
local uk_effect = r(mean)
local uk_effect_str = string(`uk_effect',"%5.2f")

sum pre_rmspe_uk
local pre_rmspe_uk = r(mean)
local pre_rmspe_uk_str = string(`pre_rmspe_uk',"%5.4f")

sum pre_rmspe_eu
local pre_rmspe_eu = r(mean)
local pre_rmspe_eu_str = string(`pre_rmspe_eu',"%5.4f")

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式

twoway (connected eu_actual_real Year, ///
           lcolor("0 51 154") lwidth(medthick) ///
           mcolor("0 51 154") yaxis(1)) ///
       (line eu_synthetic_real Year, ///
           lcolor("0 51 154") lwidth(medthick) lpattern(dash) ///
           yaxis(1)) ///
       (connected uk_actual_real Year, ///
           lcolor("201 6 43") lwidth(medthick) ///
           mcolor("201 6 43") yaxis(2)) ///
       (line uk_synthetic_real Year, ///
           lcolor("201 6 43") lwidth(medthick) lpattern(dash) ///
           yaxis(2)), ///
	   xline(`treated_year', lpattern(dot) lcolor(black)) ///
       text(29000 2015 "Brexit", size(medium)) ///
       text(15000 2021 "EU : `eu_effect_str'%", size(medium)) ///
       text(28000 2021 "UK : `uk_effect_str'%", size(medium)) ///
      xtitle("") ///
      ytitle("Total publications of EU(average)", size(medium) axis(1) color("0 51 154")) ///
	   ytitle("Total publications of UK ", size(medium) axis(2) color("201 6 43")) ///
       xlabel(2005(2)2024, nogrid tposition(inside)) ///
       ylabel(0(10000)30000, nogrid tposition(inside) format(%9.0gc) axis(1)) ///
       ylabel(0(50000)200000, nogrid tposition(inside) format(%9.0gc) axis(2)) ///
       xmtick(2005(1)2024, tposition(inside)) ///
       ymtick(0(5000)30000, tposition(inside) axis(1)) ///
       ymtick(0(10000)200000, tposition(inside) axis(2)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "EU Actual" 2 "EU Synthetic" 3 "UK Actual" 4 "UK Synthetic") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison_real, replace)

graph export "`base_dir'/total_publications/combined_actual_vs_synthetic_`treated_year'.pdf", replace

* 4. 安慰剂检验
* 4.1 对每个控制组国家进行合成控制分析
foreach country of local control_countries {
    di "Processing `country'"

    use "`base_dir'/total_publications/processed_data.dta", clear

    * 获取当前国家的ID
    qui sum country_id if Country == "`country'"
    local treat_id = r(mean)
    di "Treatment ID for `country': `treat_id'"
	* 检查是否获取到有效的ID
    if missing(`treat_id') {
        di "Warning: No valid ID found for `country', skipping..."
        continue
    }
	
	* 跳过ID小于21的国家
    if `treat_id' < 60 {
        di "Skipping `country' (ID: `current_id') as it is less than 50"
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
	
	* 检查控制组是否为空
    if "`placebo_controls'" == "" {
        di "Warning: No valid control units for `country', skipping..."
        continue
    }
	
	
	* 运行标准合成控制（使用基础控制变量）
	capture noisily {
		synth log_pub_total ///
			$uk_control_vars ///
			$uk_control_vars_1 , ///
			trunit(`treat_id') trperiod(`treated_year') ///
			counit(`placebo_controls') ///
			xperiod(2008(1)`before_treated_year') ///
			nested allopt ///
			keep("`base_dir'/total_publications/synth_`country'", replace)
	}

   
    * 处理结果
    capture {
        use "`base_dir'/total_publications/synth_`country'", clear
        rename _time Year
		
		gen `country'_gap = _Y_treated - _Y_synthetic
        gen actual_real = exp(_Y_treated) - 1
        gen synthetic_real = exp(_Y_synthetic) - 1
		gen gap_pct_effect_`country' = actual_real - synthetic_real
        gen gap_pct_`country' = (actual_real - synthetic_real) / actual_real * 100

        * 计算平均处理效应
        egen avg_effect = mean(gap_pct_`country') if Year >= `treated_year'
        gen avg_gap_pct_`country' = avg_effect
        drop avg_effect

        keep Year `country'_gap gap_pct_effect_`country' gap_pct_`country' avg_gap_pct_`country'
        drop if missing(Year)
        save "`base_dir'/total_publications/gap_`country'", replace
    }
}

* 4.2 合并所有结果
use "`base_dir'/total_publications/gap_ARGENTINA", clear
foreach country of local control_countries {
    if "`country'" != "ARGENTINA" {
        capture {
            merge 1:1 Year using "`base_dir'/total_publications/gap_`country'", nogenerate
        }
    }
}
merge 1:1 Year using "`base_dir'/total_publications/eu_synth_results.dta", nogenerate
merge 1:1 Year using "`base_dir'/total_publications/uk_synth_results.dta", nogenerate

* 保存最终合并的数据
save "`base_dir'/total_publications/all_gaps_merged.dta", replace

* 4.3 为每个控制国生成 temp_rmspe 并合并（变量后缀用 id，避免变量名截断）
foreach country of local control_countries {
    quietly {
        preserve
        use "`base_dir'/total_publications/processed_data.dta", clear
        qui sum country_id if Country == "`country'"
        local cid = r(mean)
        restore
    }

    if missing(`cid') continue
    capture confirm file "`base_dir'/total_publications/synth_`country'.dta"
    if _rc continue

    capture {
        preserve
        use "`base_dir'/total_publications/synth_`country'.dta", clear
        rename _time Year
        keep Year _Y_treated _Y_synthetic
        drop if missing(Year)
        keep if inrange(Year, 2005, 2024)
        duplicates drop Year, force

        gen log_gap = _Y_treated - _Y_synthetic

        gen pre_sq_error  = log_gap^2 if Year <= `before_treated_year' & Year > 2008
        egen pre_mspe     = mean(pre_sq_error)
        gen pre_rmspe     = sqrt(pre_mspe)

        gen post_sq_error = log_gap^2 if Year >= `treated_year'
        egen post_mspe    = mean(post_sq_error)
        gen post_rmspe    = sqrt(post_mspe)

        gen rmspe_ratio   = post_rmspe / pre_rmspe

        rename pre_rmspe   pre_rmspe_id`cid'
        rename post_rmspe  post_rmspe_id`cid'
        rename rmspe_ratio rmspe_ratio_id`cid'

        keep Year pre_rmspe_id`cid' post_rmspe_id`cid' rmspe_ratio_id`cid'
        duplicates drop Year, force
        isid Year

        tempfile t_`cid'
        save `t_`cid'', replace
        restore

        * 合并至主表（右表 Year 唯一）
        merge m:1 Year using `t_`cid'', nogenerate

        * 合并后再贴标签（避免嵌套 preserve）
        label var pre_rmspe_id`cid'   "pre_rmspe: `country'"
        label var post_rmspe_id`cid'  "post_rmspe: `country'"
        label var rmspe_ratio_id`cid' "rmspe_ratio: `country'"
    }
}


* 保存最终合并的数据
save "`base_dir'/total_publications/all_gaps_merged.dta", replace

* 5. 最直接的p值计算
// * 5.1 基于effect计算p-value 
// * 获取EU基准
// sum pre_rmspe_eu
// local eu_pre_rmspe = r(mean)
// local threshold = 10 // 设置阈值
//
// * 获取EU效应
// sum eu_gap_pct if Year >= `treated_year'
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
//             * 检查gap_pct
//             capture confirm variable gap_pct_`country'
//             if !_rc {
//                 sum gap_pct_`country' if Year >= `treated_year'
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


* 5.2 基于RMSPE比率的计算EU的p值
* 获取EU的RMSPE比率
sum rmspe_ratio_eu
local eu_rmspe_ratio = r(mean)
di "EU的RMSPE比率: `eu_rmspe_ratio'"

* 计算所有控制组国家的RMSPE比率
local total_control_count_eu = 2
local rmspe_ratio_higher_count_eu = 1

ds rmspe_ratio_id*
local ratio_vars `r(varlist)'

foreach var of varlist `ratio_vars' {
    quietly sum `var'
    if r(N) > 0 {
        local total_control_count_eu = `total_control_count_eu' + 1
        local country_rmspe_ratio = r(mean)
        if `country_rmspe_ratio' > `eu_rmspe_ratio' {
            local rmspe_ratio_higher_count_eu = `rmspe_ratio_higher_count_eu' + 1
			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于eu)"
        }
		else {
			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于eu)"
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


* 5.2 基于RMSPE比率的计算uk的p值
* 获取uk的RMSPE比率
sum rmspe_ratio_uk
local uk_rmspe_ratio = r(mean)
di "uk的RMSPE比率: `uk_rmspe_ratio'"

* 计算所有控制组国家的RMSPE比率
local total_control_count_uk = 2
local rmspe_ratio_higher_count_uk = 1

ds rmspe_ratio_id*
local ratio_vars `r(varlist)'

foreach var of varlist `ratio_vars' {
    quietly sum `var'
    if r(N) > 0 {
        local total_control_count_uk = `total_control_count_uk' + 1
        local country_rmspe_ratio = r(mean)
        if `country_rmspe_ratio' > `uk_rmspe_ratio' {
            local rmspe_ratio_higher_count_uk = `rmspe_ratio_higher_count_uk' + 1
			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于uk)"
        }
		else {
			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于uk)"
		}
    }
}

* 计算基于RMSPE比率的p值
local p_value_rmspe_uk = `rmspe_ratio_higher_count_uk' / `total_control_count_uk'
local p_value_rmspe_display_uk = string(`p_value_rmspe_uk', "%9.2f")

di "=== RMSPE比率p值计算结果 ==="
di "总控制组国家数: `total_control_count'"
di "RMSPE比率大于uk的国家数: `rmspe_ratio_higher_count_uk'"
di "基于RMSPE比率的p值: `p_value_rmspe_display_uk'"
di "uk的RMSPE比率: `uk_rmspe_ratio'"

* 5.4 绘制筛选后的安慰剂效应图（用 pre_rmspe_id# 选国，再映射回国家名）
sum pre_rmspe_eu
local eu_pre_rmspe = r(mean)
local threshold = 20
local qualified_count = 0

* 载入 id->Country 映射
preserve
use "`base_dir'/total_publications/processed_data.dta", clear
keep country_id Country
duplicates drop
tempfile idmap
save `idmap'
restore

* 基于 pre_rmspe_id# 选出合格 id，并映射到国家名
local qualified_countries ""
ds pre_rmspe_id*
local prevars `r(varlist)'

foreach var of varlist `prevars' {
    quietly sum `var'
    if r(N) > 0 {
        local pre_r = r(mean)
        if `pre_r' < `threshold' * `eu_pre_rmspe' {
            * 提取 id 数字部分
            local vid = subinstr("`var'", "pre_rmspe_id", "", .)
            preserve
            use `idmap', clear
            keep if country_id == real("`vid'")
            if _N == 1 {
                local cname = Country[1]
            }
            restore
            if "`cname'" != "" {
				local qualified_count = `qualified_count' + 1
                local qualified_countries `"`qualified_countries' "`cname'""'
            }
            local cname
        }
    }
}

di "图中控制组国家的数量为:`qualified_count'"



* 准备绘图命令（为每个 control 国家分配不同颜色，图例显示国家名）
local filtered_control_lines ""
local filtered_legend_order ""
local j = 1
* 预定义一组可区分的颜色（与图例顺序一致，国家多时可追加 gs4 gs6 gs8 等）
local color_list "navy maroon forest_green dkorange brown cyan gold lime magenta orange_red purple teal red blue green orange sienna olive"
* 使用我们存储的合格国家列表
foreach country of local qualified_countries {
    capture confirm variable gap_pct_`country'
    if !_rc {
        local ccolor : word `j' of `color_list'
        if "`ccolor'" == "" local ccolor gs10
        local filtered_control_lines `"`filtered_control_lines' (line gap_pct_`country' Year, lpattern(dash) lcolor("`ccolor'"))"'
        local filtered_legend_order `"`filtered_legend_order' `j' "`country'" "'
        local ++j
    }
}

* 添加EU和UK
local filtered_control_lines `"`filtered_control_lines' (line eu_gap_pct Year, lwidth(thick) lcolor("0 51 154"))"'
local filtered_control_lines `"`filtered_control_lines' (line uk_gap_pct Year, lwidth(thick) lcolor("201 6 43"))"'

* 绘制图形（图例显示 control 国家名称 + EU / UK）
twoway `filtered_control_lines', ///
       xline(`treated_year', lpattern(dot) lcolor(black)) ///
       yline(0, lcolor(black)) ///
       xtitle("") ///
	   ytitle("Treatment Effect", size(medium)) ///
	   text(-4 2008 `"p-value(EU) : `p_value_rmspe_display_eu'"' `"`=char(13)'"' ///
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
graph export "`base_dir'/total_publications/placebo_filtered_`treated_year'.pdf", replace

* 保存最终结果
save "`base_dir'/total_publications/final_results.dta", replace

* 清理临时文件
capture erase temp_weights.dta
capture erase temp_country.dta
foreach country of local control_countries {
    capture erase "`base_dir'/total_publications/temp_rmspe_`country'.dta"
}




