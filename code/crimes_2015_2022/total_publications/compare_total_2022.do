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
local base_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/crimes_2015_2022"
import excel "`base_dir'/original_completed.xlsx", sheet("Sheet1") firstrow clear
save "`base_dir'/total_publications/processed_data.dta", replace
local treated_year 2022
local before_treated_year 2021
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

global control_vars_russia "log_pub_total(2021) log_pub_total(2020) log_pub_total(2018)  log_pub_total(2017) log_pub_total(2015) " // 2022
global control_vars_ukraine "log_pub_total(2021) log_pub_total(2020) log_pub_total(2019) log_pub_total(2018) log_pub_total(2017) " // 2022


// global control_vars_russia "log_pub_total(2020) log_pub_total(2019) log_pub_total(2018)  log_pub_total(2017) log_pub_total(2015) " // 2021
// global control_vars_ukraine "log_pub_total(2019) log_pub_total(2018) log_pub_total(2016) log_pub_total(2015) " // 2021


// global control_vars_russia "log_pub_total(2019) log_pub_total(2018)  log_pub_total(2017) log_pub_total(2015) " // 2020
// global control_vars_ukraine "log_pub_total(2019) log_pub_total(2017) log_pub_total(2016) log_pub_total(2015) " // 2020

// global control_vars_russia "log_pub_total(2018)  log_pub_total(2017) log_pub_total(2016) log_pub_total(2015) " // 2019
// global control_vars_ukraine "log_pub_total(2018) log_pub_total(2017) log_pub_total(2016) log_pub_total(2015) " // 2019(no other variables)

* 1.6 保存处理后的数据
save "`base_dir'/total_publications/processed_data.dta", replace


* 2. RUSSIAN_FEDERATION合成控制分析
* 2.1 运行RUSSIAN_FEDERATION的合成控制分析
synth log_pub_total ///
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
keep if Year >= `fit_start_year'
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
gen pre_sq_error_russia = log_gap_russia^2 if Year <= `before_treated_year' & Year >=`fit_start_year'
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

* 2.7 输出控制组国家与权重对应表
use russia_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id
save temp_weights_russia_`treated_year'.dta, replace

use "`base_dir'/total_publications/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_russia_`treated_year'.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/total_publications/russia_weights_country.xlsx", firstrow(variables) replace


* 3. UKRAINE合成控制分析

* 3.0 准备UKRAINE分析数据
use "`base_dir'/total_publications/processed_data.dta", clear
* 3.1 运行UKRAINE的合成控制分析
synth log_pub_total ///
	$control_vars ///
    $control_vars_ukraine , ///
    trunit(`ukraine_id') trperiod(`treated_year') ///
    counit(`control_ids') ///
    xperiod(`fit_start_year'(1)`before_treated_year') /// 
    nested allopt ///
    keep(ukraine_synth_results, replace)
* 查看预测变量权重
matrix list e(V_matrix)

* 3.2 处理UKRAINE结果
use ukraine_synth_results, clear
rename _time Year
keep if Year >= `fit_start_year'
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
gen pre_sq_error_ukraine = log_gap_ukraine^2 if Year <= `before_treated_year' & Year >=`fit_start_year'
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

* 3.7 输出控制组国家与权重对应表
use ukraine_synth_results, clear
keep _Co_Number _W_Weight
rename _Co_Number country_id
save temp_weights_ukraine_`treated_year'.dta, replace


use "`base_dir'/total_publications/processed_data.dta", clear
keep country_id Country
duplicates drop
save temp_country.dta, replace

use temp_weights_ukraine_`treated_year'.dta, clear
merge 1:1 country_id using temp_country.dta
keep if _W_Weight > 0
list country_id Country _W_Weight, noobs
export excel using "`base_dir'/total_publications/ukraine_weights_country.xlsx", firstrow(variables) replace


* 3.8 合并UKRAINE和RUSSIAN_FEDERATION结果进行对比可视化
use "`base_dir'/total_publications/ukraine_synth_results.dta", clear
merge 1:1 Year using "`base_dir'/total_publications/russia_synth_results.dta", nogenerate


* 获取效应值
sum ukraine_gap_pct if Year >= `treated_year'
local ukraine_effect = r(mean)
sum russia_gap_pct if Year >= `treated_year'
local russia_effect = r(mean)

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
qui sum Year
local max_year = r(max)
local x_start_year 2015

* 统一 effect 文本格式
local russia_effect_str  : di %5.2f `russia_effect'
local ukraine_effect_str : di %5.2f `ukraine_effect'

* 纵轴尺度（改这里即可）：阴影 rarea 与 ylabel、yscale(range) 三处一致
local y_lo_russia 0
local y_hi_russia 60000
local y_step_russia 10000

local y_lo_ukraine 0
local y_hi_ukraine 12000
local y_step_ukraine 3000

*===========================================================*
* 可视化规格：Nature/Science 风格，遵循 plotting_spec_stata.md
*===========================================================*
graph set window fontface "Helvetica"
set scheme s1color
graph set eps fontface "Helvetica"

gen _shade_lo_russia = `y_lo_russia'
gen _shade_hi_russia = `y_hi_russia'
gen _shade_lo_ukraine = `y_lo_ukraine'
gen _shade_hi_ukraine = `y_hi_ukraine'

local gph_dir "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/picutres/gph"
capture mkdir "`gph_dir'"

* ── Panel i: War – Russia Total Publications ─────────────────────────────────
sum rmspe_ratio_russia
local rmspe_russia : display %4.2f r(mean)
sum russia_gap_pct if Year >= `treated_year'
local ru_att_abs : display %4.2f abs(r(mean))
if r(mean) >= 0 local ru_att_sign "+"
else local ru_att_sign "-"

twoway ///
    (rarea _shade_lo_russia _shade_hi_russia Year if Year >= `treated_year' & Year <= `max_year', ///
        sort color("238 238 238%60") lwidth(none)) ///
    (line russia_synthetic_real Year if Year >= `x_start_year', lpattern(dash) ///
        lcolor("86 180 233") lwidth(medthick)) ///
    (line russia_actual_real Year if Year >= `x_start_year', lpattern(solid) ///
        lcolor("86 180 233") lwidth(thick)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("68 68 68") lwidth(thin)) ///
    text(`=`y_hi_russia'*0.97' `=`treated_year'+0.3' "War (2022)", ///
        size(vsmall) color("68 68 68") placement(e)) ///
    text(`=`y_hi_russia'*0.08' `=`x_start_year'+0.5' ///
        "ATT = `ru_att_sign'`ru_att_abs'%" ///
        "RMSPE ratio = `rmspe_russia'", ///
        size(vsmall) box bcolor(white) bmargin(small) ///
        justification(left) placement(e)) ///
    subtitle("{bf:i}  Russia · Total publications", ///
        size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Russia-Ukraine war" "Publications", size(small)) ///
    xtitle("") ///
    xlabel(`x_start_year'(2)`max_year', labsize(small) nogrid tposition(inside)) ///
    xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_russia'(`y_step_russia')`y_hi_russia', angle(0) format(%9.0gc) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_russia' `y_hi_russia') noextend) ///
    xscale(lcolor(black) lwidth(thin)) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    legend(off) ///
    name(panel_i, replace)

graph save "`gph_dir'/panel_i.gph", replace

* ── Panel k: War – Ukraine Total Publications ────────────────────────────────
sum rmspe_ratio_ukraine
local rmspe_ukraine : display %4.2f r(mean)
sum ukraine_gap_pct if Year >= `treated_year'
local ua_att_abs : display %4.2f abs(r(mean))
if r(mean) >= 0 local ua_att_sign "+"
else local ua_att_sign "-"

twoway ///
    (rarea _shade_lo_ukraine _shade_hi_ukraine Year if Year >= `treated_year' & Year <= `max_year', ///
        sort color("238 238 238%60") lwidth(none)) ///
    (line ukraine_synthetic_real Year if Year >= `x_start_year', lpattern(dash) ///
        lcolor("230 159 0") lwidth(medthick)) ///
    (line ukraine_actual_real Year if Year >= `x_start_year', lpattern(solid) ///
        lcolor("230 159 0") lwidth(thick)) ///
    , ///
    xline(`treated_year', lpattern(shortdash) lcolor("68 68 68") lwidth(thin)) ///
    text(`=`y_hi_ukraine'*0.97' `=`treated_year'+0.3' "War (2022)", ///
        size(vsmall) color("68 68 68") placement(e)) ///
    text(`=`y_hi_ukraine'*0.08' `=`x_start_year'+0.5' ///
        "ATT = `ua_att_sign'`ua_att_abs'%" ///
        "RMSPE ratio = `rmspe_ukraine'", ///
        size(vsmall) box bcolor(white) bmargin(small) ///
        justification(left) placement(e)) ///
    subtitle("{bf:k}  Ukraine · Total publications", ///
        size(medsmall) justification(left) position(11) margin(b=2)) ///
    ytitle("Publications", size(small)) ///
    xtitle("") ///
    xlabel(`x_start_year'(2)`max_year', labsize(small) nogrid tposition(inside)) ///
    xmtick(`x_start_year'(1)`max_year', tposition(inside)) ///
    ylabel(`y_lo_ukraine'(`y_step_ukraine')`y_hi_ukraine', angle(0) format(%9.0gc) labsize(small) nogrid tposition(inside)) ///
    yscale(lcolor(black) lwidth(thin) range(`y_lo_ukraine' `y_hi_ukraine') noextend) ///
    xscale(lcolor(black) lwidth(thin)) ///
    graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
    plotregion(margin(zero) lcolor(black) lwidth(thin)) ///
    legend(off) ///
    name(panel_k, replace)

graph save "`gph_dir'/panel_k.gph", replace

drop _shade_lo_russia _shade_hi_russia _shade_lo_ukraine _shade_hi_ukraine

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
        synth log_pub_total $control_vars $control_vars_ukraine , ///
              trunit(`=`treat_id'') trperiod(`treated_year') ///
              counit(`placebo_controls') ///
              xperiod(`fit_start_year'(1)`before_treated_year') ///
              nested allopt ///
              keep("`base_dir'/total_publications/synth_`country'.dta", replace)
    }
 
    * 如果标准模型失败，尝试简化模型
    if _rc != 0 {
        di "Standard model failed for `country', trying simplified model"
        capture noisily {
            synth log_pub_total $control_vars , ///
                  trunit(`=`treat_id'') trperiod(`treated_year') ///
                  counit(`placebo_controls') ///
                  xperiod(`fit_start_year'(1)`before_treated_year') ///
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
        egen avg_effect = mean(gap_pct_`country') if Year >= `treated_year' 	
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
        keep if inrange(Year, 2015, 2024)
        duplicates drop Year, force

        gen log_gap = _Y_treated - _Y_synthetic

        gen pre_sq_error  = log_gap^2 if Year <= `before_treated_year' & Year >= `fit_start_year'
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


* 保存最终合并的数据（ukraine和russia的RMSPE已经在前面计算好了）
save "`base_dir'/total_publications/all_gaps_merged.dta", replace

* 5. 结果可视化和统计分析
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


// * 5.2 基于RMSPE比率的计算russia的p值
// * 获取EU的RMSPE比率
// sum rmspe_ratio_russia
// local russia_rmspe_ratio = r(mean)
// di "russia的RMSPE比率: `russia_rmspe_ratio'"

// * 计算所有控制组国家的RMSPE比率
// local total_control_count_russia = 2
// local rmspe_ratio_higher_count_russia = 1

// foreach country of local control_countries {
//     quietly sum `var'
// 	if r(N) > 0 {
// 		local total_control_count_russia = `total_control_count_russia' + 1
// 		local country_rmspe_ratio = r(mean)
// 		* 检查该国家的RMSPE比率是否大于russia
// 		if `country_rmspe_ratio' > `russia_rmspe_ratio' {
// 			local rmspe_ratio_higher_count_russia = `rmspe_ratio_higher_count_russia' + 1
// 			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于russia)"
// 		}
// 		else {
// 			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于russia)"
// 		}
// 	}
// }

// * 计算基于RMSPE比率的p值
// local p_value_rmspe_russia = `rmspe_ratio_higher_count_russia' / `total_control_count_russia'
// local p_value_rmspe_display_russia = string(`p_value_rmspe_russia', "%9.2f")

// di "=== RMSPE比率p值计算结果 ==="
// di "总控制组国家数: `total_control_count_russia'"
// di "RMSPE比率大于russia的国家数: `rmspe_ratio_higher_count_russia'"
// di "基于RMSPE比率的p值: `p_value_rmspe_display_russia'"
// di "russia的RMSPE比率: `russia_rmspe_ratio'"


// * 5.3 基于RMSPE比率的计算ukraine的p值（id后缀变量）
// sum rmspe_ratio_ukraine
// local ukraine_rmspe_ratio = r(mean)

// local total_control_count_ukraine = 2
// local rmspe_ratio_higher_ukraine = 1

// ds rmspe_ratio_id*
// local ratio_vars `r(varlist)'

// foreach var of varlist `ratio_vars' {
//     quietly sum `var'
//     if r(N) > 0 {
//         local total_control_count_ukraine = `total_control_count_ukraine' + 1
//         local country_rmspe_ratio = r(mean)
//         if `country_rmspe_ratio' > `ukraine_rmspe_ratio' {
//             local rmspe_ratio_higher_ukraine = `rmspe_ratio_higher_ukraine' + 1
// 			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (大于ukraine)"
//         }
// 		else {
// 			di "国家 `country' RMSPE比率: `country_rmspe_ratio' (小于等于ukraine)"
// 		}
//     }
// }

// local p_value_rmspe_ukraine = `rmspe_ratio_higher_ukraine' / `total_control_count_ukraine'
// di "=== RMSPE比率p值计算结果（Ukraine） ==="
// di "总控制组国家数: `total_control_count_ukraine'"
// di "RMSPE比率大于ukraine的国家数: `rmspe_ratio_higher_ukraine'"
// di "基于RMSPE比率的p值: " %9.3f `p_value_rmspe_ukraine'
// di "ukraine的RMSPE比率: " %9.3f `ukraine_rmspe_ratio'


// * 5.4 绘制筛选后的安慰剂效应图（用 pre_rmspe_id# 选国，再映射回国家名）
// sum pre_rmspe_russia
// local russia_pre_rmspe = r(mean)
// local threshold = 20
// local qualified_count = 0

// * 载入 id->Country 映射
// preserve
// use "`base_dir'/total_publications/processed_data.dta", clear
// keep country_id Country
// duplicates drop
// tempfile idmap
// save `idmap'
// restore

// * 基于 pre_rmspe_id# 选出合格 id，并映射到国家名
// local qualified_countries ""
// ds pre_rmspe_id*
// local prevars `r(varlist)'

// foreach var of varlist `prevars' {
//     quietly sum `var'
//     if r(N) > 0 {
//         local pre_r = r(mean)
//         if `pre_r' < `threshold' * `russia_pre_rmspe' {
//             * 提取 id 数字部分
//             local vid = subinstr("`var'", "pre_rmspe_id", "", .)
//             preserve
//             use `idmap', clear
//             keep if country_id == real("`vid'")
//             if _N == 1 {
//                 local cname = Country[1]
//             }
//             restore
//             if "`cname'" != "" {
//                 local qualified_countries `"`qualified_countries' "`cname'""'
//             }
//             local cname
// 			local qualified_count = `qualified_count' + 1
//         }
//     }
// }
// di "图中控制组国家的数量为:`qualified_count'"

// * 组装绘图命令（gap_pct_国家名 变量已在4.2合并里存在）
// local filtered_control_lines ""
// local j = 1
// foreach country of local qualified_countries {
//     capture confirm variable gap_pct_`country'
//     if !_rc {
//         local filtered_control_lines `"`filtered_control_lines' (line gap_pct_`country' Year, lcolor(gs12) lpattern(dash))"'
//         local ++j
//     }
// }
// * 添加 Russia 与 Ukraine 的主线
// local filtered_control_lines `"`filtered_control_lines' (line russia_gap_pct Year, lwidth(thick) lcolor("76 92 156"))"'
// local filtered_control_lines `"`filtered_control_lines' (line ukraine_gap_pct Year, lwidth(thick) lcolor("227 195 65"))"'

// twoway `filtered_control_lines' ///
// 	   if Year >= `fit_start_year', ///
//        xline(`treated_year', lpattern(dot) lcolor(black)) ///
//        yline(0, lcolor(black)) ///
//        xtitle("") ///
//        ytitle("Treatment Effect", size(medium)) ///
//        text(-5 2017 `"p-value(Russia)  : `=string(`p_value_rmspe_russia',"%5.3f")'"' `"`=char(13)'"' ///
//                     `"p-value(Ukraine) : `=string(`p_value_rmspe_ukraine',"%5.3f")'"', size(medium)) ///
//        xlabel(`fit_start_year'(2)2024, nogrid tposition(inside)) ///
//        ylabel(, nogrid tposition(inside)) ///
//        xmtick(`fit_start_year'(1)2024, tposition(inside)) ///
//        ymtick(, tposition(inside)) ///
//        graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
//        plotregion(style(outline) lcolor(black) lwidth(thin)) ///
//        bgcolor(white) ///
//        legend(off) ///
//        name(placebo_filtered, replace)

// * 导出图形
// graph export "`base_dir'/total_publications/placebo_filtered_`treated_year'.pdf", replace

// * 5.5 保存最终结果
// save "`base_dir'/total_publications/final_results.dta", replace
