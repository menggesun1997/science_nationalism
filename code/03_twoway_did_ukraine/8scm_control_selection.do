* ============================================================================
* 合成控制法（Synthetic Control Method, SCM）控制组选择
* 为乌克兰构建合成控制组，使用多个控制国家的加权组合
* ============================================================================

clear all
set more off
set matsize 10000

* 设置工作目录

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

cd "$CODE/03_twoway_did_ukraine"

global base_dir "."
cd "$base_dir"

* 输出文件
global scm_output_file "scm_control_selection_results.dta"
global scm_output_excel "scm_control_selection_results.xlsx"

* ============================================================================
* 步骤1: 加载数据
* ============================================================================

display _dup(80) "="
display "步骤1: 加载Y_{k,t}数据"
display _dup(80) "="

* 读取控制组国家与集合P的合作数据
import excel using "control_group_cooperation_data.xlsx", ///
    sheet("控制组与集合P合作汇总") firstrow clear

* 保留需要的变量
keep year country coop_articles_with_P
rename coop_articles_with_P Y_kt
gen log_Y_kt = log(Y_kt + 1)

* 保存临时文件
tempfile control_data
save `control_data', replace

* 读取乌克兰与集合P的合作数据
import excel using "control_group_cooperation_data.xlsx", ///
    sheet("乌克兰与集合P合作") firstrow clear

* 保留需要的变量
keep year ukraine_coop_with_P
rename ukraine_coop_with_P Y_kt
gen country = "UKRAINE"
gen log_Y_kt = log(Y_kt + 1)
keep year country Y_kt log_Y_kt

* 合并数据
append using `control_data'
sort country year

display "✅ 数据加载完成"
display "  数据形状: " _N " 行"
display "  包含国家: "
tab country

* ============================================================================
* 步骤2: 准备SCM数据结构
* ============================================================================

display _dup(80) "="
display "步骤2: 准备SCM数据结构"
display _dup(80) "="

* 定义战前时期
local pre_start = 2015
local pre_end = 2021
local treatment_year = 2022

* 创建国家ID
encode country, gen(country_id)
tab country_id, gen(country_dummy)

* 找到乌克兰的ID
summarize country_id if country == "UKRAINE"
local ukraine_id = r(mean)

* 找到控制国家的ID（排除乌克兰）
levelsof country_id if country != "UKRAINE", local(control_ids)

display "战前时期: `pre_start'-`pre_end'"
display "乌克兰ID: `ukraine_id'"
display "控制国家ID: `control_ids'"

* ============================================================================
* 步骤3: 运行合成控制分析
* ============================================================================

display _dup(80) "="
display "步骤3: 运行合成控制分析"
display _dup(80) "="

* 准备数据：只保留战前时期用于拟合
preserve
keep if year >= `pre_start' & year <= `pre_end'

* 使用synth命令（如果已安装synth包）
* 注意：需要先安装synth包，运行: ssc install synth

capture confirm file "synth.ado"
if _rc == 0 {
    display "使用synth命令进行合成控制分析..."
    
    * 运行合成控制
    synth log_Y_kt ///
        log_Y_kt(2015) log_Y_kt(2016) log_Y_kt(2017) log_Y_kt(2018) ///
        log_Y_kt(2019) log_Y_kt(2020) log_Y_kt(2021), ///
        trunit(`ukraine_id') trperiod(`treatment_year') ///
        counit(`control_ids') ///
        xperiod(`pre_start'(1)`pre_end') ///
        nested allopt ///
        keep(scm_results_temp, replace)
    
    * 加载结果
    use scm_results_temp, clear
    
    * 重命名变量
    rename _time year
    rename _Y_treated ukraine_actual
    rename _Y_synthetic ukraine_synthetic
    gen gap = ukraine_actual - ukraine_synthetic
    
    * 保存权重信息
    preserve
    keep _Co_Number _W_Weight
    rename _Co_Number country_id
    rename _W_Weight weight
    save scm_weights_temp, replace
    restore
    
    * 保存结果
    save "$scm_output_file", replace
    
    display "✅ 合成控制分析完成"
}
else {
    display "⚠️ 未找到synth命令"
    display "请先安装synth包: ssc install synth"
    display "或者使用Python脚本进行SCM分析"
    
    restore
    exit
}

restore

* ============================================================================
* 步骤4: 计算RMSPE统计
* ============================================================================

display _dup(80) "="
display "步骤4: 计算RMSPE统计"
display _dup(80) "="

use "$scm_output_file", clear

* 计算战前RMSPE
gen pre_period = (year <= `pre_end')
gen gap_sq = gap^2

* 战前RMSPE
summarize gap_sq if pre_period == 1
local pre_mspe = r(mean)
local pre_rmspe = sqrt(`pre_mspe')

* 战后RMSPE
summarize gap_sq if pre_period == 0
local post_mspe = r(mean)
local post_rmspe = sqrt(`post_mspe')

* RMSPE比率
local rmspe_ratio = `post_rmspe' / `pre_rmspe'

display "战前RMSPE: `pre_rmspe'"
display "战后RMSPE: `post_rmspe'"
display "RMSPE比率: `rmspe_ratio'"

* 保存RMSPE统计
preserve
clear
set obs 1
gen pre_rmspe = `pre_rmspe'
gen post_rmspe = `post_rmspe'
gen rmspe_ratio = `rmspe_ratio'
save scm_rmspe_stats, replace
restore

* ============================================================================
* 步骤5: 显示权重结果
* ============================================================================

display _dup(80) "="
display "步骤5: 合成控制组权重结果"
display _dup(80) "="

use scm_weights_temp, clear

* 合并国家名称
merge 1:1 country_id using `control_data', keepusing(country) nogen
keep country_id country weight
sort weight, descending

display "权重分配:"
list country weight, clean noobs

* 显示主要贡献国家（权重 > 1%）
display ""
display "主要贡献国家（权重 > 1%）:"
list country weight if weight > 0.01, clean noobs

* ============================================================================
* 步骤6: 保存结果
* ============================================================================

display _dup(80) "="
display "步骤6: 保存结果"
display _dup(80) "="

* 保存到Excel
use "$scm_output_file", clear
export excel using "$scm_output_excel", sheet("SCM_Results") firstrow(variables) replace

* 保存权重
use scm_weights_temp, clear
merge 1:1 country_id using `control_data', keepusing(country) nogen
keep country weight
sort weight, descending
export excel using "$scm_output_excel", sheet("SCM_Weights") firstrow(variables) sheetreplace

* 保存RMSPE统计
use scm_rmspe_stats, clear
export excel using "$scm_output_excel", sheet("RMSPE_Statistics") firstrow(variables) sheetreplace

display "✅ 结果已保存到: $scm_output_excel"

* ============================================================================
* 步骤7: 创建可视化（可选，需要graph命令）
* ============================================================================

display _dup(80) "="
display "步骤7: 创建可视化"
display _dup(80) "="

use "$scm_output_file", clear

* 图表1: 乌克兰 vs 合成控制组
twoway ///
    (line ukraine_actual year, lcolor(227 195 65) lwidth(thick) lpattern(solid) ///
        mcolor(227 195 65) msize(medium) msymbol(circle)) ///
    (line ukraine_synthetic year, lcolor(gray) lwidth(medthick) lpattern(dash) ///
        mcolor(gray) msize(medium) msymbol(square)), ///
    xline(2022, lcolor(red) lpattern(dash)) ///
    xline(2021, lcolor(gray) lpattern(dot)) ///
    xlabel(2015(2)2024) ///
    ytitle("log(Y_{{k,t}})") ///
    xtitle("Year") ///
    title("Synthetic Control Method: Ukraine vs Synthetic Control", size(medium)) ///
    legend(order(1 "Ukraine (Actual)" 2 "Synthetic Control") position(6) cols(2)) ///
    graphregion(color(white)) plotregion(color(white))

graph export "scm_plots/scm_ukraine_synthetic.png", replace width(2000) height(1200)
graph export "scm_plots/scm_ukraine_synthetic.pdf", replace

* 图表2: 处理效应（Gap）
twoway ///
    (line gap year, lcolor(227 195 65) lwidth(thick) lpattern(solid) ///
        mcolor(227 195 65) msize(medium) msymbol(circle)) ///
    (line zero = 0, lcolor(black) lpattern(solid) lwidth(thin)), ///
    xline(2022, lcolor(red) lpattern(dash)) ///
    xlabel(2015(2)2024) ///
    ytitle("Treatment Effect (Gap)") ///
    xtitle("Year") ///
    title("Treatment Effect: Ukraine vs Synthetic Control", size(medium)) ///
    legend(order(1 "Treatment Effect" 2 "Zero Line") position(6) cols(2)) ///
    graphregion(color(white)) plotregion(color(white))

graph export "scm_plots/scm_treatment_effect.png", replace width(2000) height(1200)
graph export "scm_plots/scm_treatment_effect.pdf", replace

display "✅ 图表已保存到: scm_plots/"

* ============================================================================
* 完成
* ============================================================================

display _dup(80) "="
display "SCM控制组选择完成！"
display _dup(80) "="

* 显示建议使用的控制组国家
use scm_weights_temp, clear
merge 1:1 country_id using `control_data', keepusing(country) nogen
keep country weight
sort weight, descending

display ""
display "建议使用的控制组国家（按权重排序）:"
local i = 1
foreach country in `=country[1]' `=country[2]' `=country[3]' `=country[4]' `=country[5]' {
    if weight[`i'] > 0.01 {
        display "  `i'. `country' (权重: " %5.2f weight[`i']*100 "%)"
        local i = `i' + 1
    }
}

* 清理临时文件
capture erase scm_results_temp.dta
capture erase scm_weights_temp.dta
capture erase scm_rmspe_stats.dta

display ""
display "✅ 分析完成！"






