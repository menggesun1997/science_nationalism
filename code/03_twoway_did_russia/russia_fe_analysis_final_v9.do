* =============================================================================
* 俄罗斯国际合作事件研究分析 - 时间窗口 (2017-2024，2022为事件年)
* =============================================================================

* 设置工作环境
clear all
set more off

* 关闭现有日志文件（如果存在）

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

cd "$CODE/03_twoway_did_russia"

capture log close

* 开始日志记录
log using "analysis_log_final_v9.txt", replace

* 1. 数据导入和基本检查
* =============================================================================

* 导入Excel数据：sheet "详细合作数据"；Y变量列名为 cooperation_ratio
import excel using "russia_cooperation_analysis_results.xlsx", sheet("详细合作数据") firstrow clear

* 统一变量命名与类型
capture confirm variable cooperation_ratio
if _rc == 0 {
    capture drop coop_ratio
    rename cooperation_ratio coop_ratio
}

* 创建国家编码（将字符串转换为数值）
capture confirm variable country_id
if _rc != 0 {
    encode country, gen(country_id)
}

* 尝试将关键变量转为数值
capture destring year coop_ratio, replace ignore(" ,%")

* 检查数据结构
display "Checking data structure before creating event study variables:"
describe
summarize year country coop_ratio

* 先确保存在比例因变量（全窗口）以供后续两个阶段使用
capture confirm variable coop_ratio
if _rc != 0 {
    capture drop total_coop_year
    bysort year: egen total_coop_year = sum(coop_articles)
    gen coop_ratio = coop_articles / total_coop_year
}

* 删除已存在的事件研究变量（如果存在）
capture drop event_year_rel
capture drop event_year_pos
capture drop post_war

* 创建事件研究变量（以2021年为基准年；窗口2017-2024 -> 相对年 -4..+2）
gen event_year_rel = year - 2021  // 2017=-4 ... 2021=0 ... 2024=2
gen post_war = (year >= 2022)

* 创建非负的事件研究变量（处理因子变量限制）
* 分步骤创建以避免解析问题
gen temp_offset = 5
gen event_year_pos = event_year_rel + temp_offset
drop temp_offset
* 这样：2017=1,2018=2,2019=3,2020=4,2021=5,2022=6,2023=7, 2024=8

* =============================================================================
* 2. 平行趋势检验（2017–2021，仅用于验证识别）
* =============================================================================

* 2.0 阶段一：仅战前窗口（2017-2021）用于平行趋势检验
preserve
keep if year >= 2017 & year <= 2021

* 调试：检查 event_year_pos 的值范围
tab event_year_pos
summarize event_year_pos

* 平行趋势（比例因变量）
reghdfe coop_ratio ib(5).event_year_pos, absorb(country_id) vce(robust)
estimates store pre_trends_ratio
esttab pre_trends_ratio using "pre_trends_ratio_results.txt", ///
    b(3) se(3) ///
    title("Pre-Trends Check (2017-2021), DV: coop_ratio, baseline 2021") ///
    addnotes("Robust SE" "Country FE only" "Coefficients are relative to 2021") ///
    replace

* 导出战前参数（供 Python 使用）
estimates restore pre_trends_ratio
* 调试：检查估计结果是否存在
estimates dir
* 调试：显示当前估计结果
ereturn list
capture which parmest
if _rc {
    ssc install parmest, replace
}
* 尝试不同的 parmest 选项
capture parmest, norestore
if _rc {
    display "parmest failed, trying alternative approach"
    * 如果 parmest 失败，直接从估计结果中提取
    matrix b = e(b)
    matrix V = e(V)
    local nparams = colsof(b)
    clear
    set obs `nparams'
    gen parm = ""
    gen estimate = .
    gen min95 = .
    gen max95 = .
    forvalues i = 1/`nparams' {
        local varname = el(e(b), 1, `i')
        replace parm = "`varname'" in `i'
        replace estimate = el(b, 1, `i') in `i'
        local se = sqrt(el(V, `i', `i'))
        replace min95 = estimate - 1.96*`se' in `i'
        replace max95 = estimate + 1.96*`se' in `i'
    }
}
* 调试：显示所有参数
count
if r(N) > 0 {
    list parm estimate min95 max95 in 1/`r(N)'
}
else {
    display "No parameters found"
}
* 简化匹配逻辑
keep if regexm(parm, "event_year") | regexm(parm, "event_ye")
* 再次调试：显示匹配后的结果
count
if r(N) > 0 {
    list parm estimate min95 max95
}
else {
    display "No event_year parameters found"
}
gen event_bin = .
quietly replace event_bin = real(regexs(1)) if regexm(parm, "^([0-9]+)[b]?\.")
* 调试：显示 event_bin 生成结果
list parm event_bin
* 调试：显示哪些参数被成功解析
count if !missing(event_bin)
display "Successfully parsed " r(N) " parameters"
* 调试：显示哪些参数没有被解析
count if missing(event_bin)
if r(N) > 0 {
    display "Failed to parse " r(N) " parameters:"
    list parm if missing(event_bin)
}
drop if missing(event_bin)
gen rel_year = event_bin - 5
keep estimate min95 max95 event_bin rel_year parm
* 最终调试：显示导出前的数据
count
if r(N) > 0 {
    list estimate min95 max95 event_bin rel_year parm
    export delimited using "pre_trends_params1.csv", replace
}
else {
    display "No data to export"
}


* （改为由 Python 绘图）不在 Stata 内作图



* 战前系数联合检验（2017-2020 vs 2021）
capture log close pretest
log using "pre_trends_test.txt", replace name(pretest)
display "=== Joint test of pre-war coefficients (2017-2020) ==="
capture test 1.event_year_pos 2.event_year_pos 3.event_year_pos 4.event_year_pos
if _rc == 0 {
    test 1.event_year_pos 2.event_year_pos 3.event_year_pos 4.event_year_pos
} 
else {
    display "Joint test failed; check factor coding."
}
log close pretest

restore

* =============================================================================
* 3. 主模型（2017–2024，包含战后动态）
* =============================================================================
display "=== Limiting Analysis to 2017-2024 (War in 2022) ==="
keep if year >= 2017 & year <= 2024
display "Data after time window restriction:"
describe
summarize year coop_ratio

* 设置面板数据结构（供后续 xtserial 与 xtdescribe 使用）
capture xtset country_id year

* 检查比例变量分布
summarize coop_ratio
describe coop_ratio

* 3.1 事件研究模型（使用比例形式）
reghdfe coop_ratio ib(5).event_year_pos, absorb(country_id) vce(robust)
estimates store ratio_event_study
* 输出比例形式事件研究结果
esttab ratio_event_study using "ratio_event_study_results.txt", ///
    b(3) se(3) ///
    title("Event Study: Dynamic Impact of Russia-Ukraine War on Cooperation (Ratio)") ///
    addnotes("Standard errors in parentheses" "Robust standard errors" "Country fixed effects only (no year FE)" "Baseline year: 2021" "Dependent variable: coop_ratio") ///
    replace

* 3.2（附）战前系数联合检验回显（基于2中的模型设置）

estimates restore ratio_event_study

display "--- Parallel Trends Test (Ratio: coop_ratio) ---"
capture test 1.event_year_pos 2.event_year_pos 3.event_year_pos 4.event_year_pos
if _rc == 0 {
    display "Pre-war coefficients test (2017-2020 vs 2021):"
    test 1.event_year_pos 2.event_year_pos 3.event_year_pos 4.event_year_pos
}

* =============================================================================
* 4. 异质性分析：按国家分析（与主模型一致：吸收国家固定效应）
* =============================================================================
reghdfe coop_ratio i.post_war##i.country_id, absorb(country_id) vce(cluster country_id)
estimates store hetero_country
esttab hetero_country using "heterogeneity_country.txt", ///
    b(3) se(3) ///
    title("Heterogeneity Analysis by Country (FE: country absorbed)") ///
    addnotes("Clustered by country" "Country FE absorbed via absorb(country_id)" "Coefficients: post_war and post_war#country_id") ///
    replace

* 导出每个国家的回归型战争效应（基于系数组合）供 Python 使用
* 注意：对每个国家 k，效应 = _b[1.post_war] + _b[1.post_war#k.country_id]（若交互不存在则为0）
tempname __pf
postfile `__pf' int country_id double war_effect using "war_effects_by_country.dta", replace
levelsof country_id, local(__cids)
foreach k of local __cids {
    local eff = _b[1.post_war]
    capture scalar __add = _b[1.post_war#`k'.country_id]
    if _rc == 0 {
        local eff = `eff' + __add
    }
    post `__pf' (`k') (`eff')
}
postclose `__pf'

* =============================================================================
* 5. 稳健性检验（精简为比例形式）：
* 同一设定 absorb(country_id)，报告主模型与聚类标准误版本
* =============================================================================
display "=== Robustness Checks (Ratio only) ==="

* 聚类标准误（按国家聚类）
reghdfe coop_ratio ib(5).event_year_pos, absorb(country_id) vce(cluster country_id)
estimates store ratio_clustered

* 输出稳健性检验结果（两列：主模型、聚类SE）
esttab ratio_event_study ratio_clustered, ///
    b(3) se(3) ///
    title("Robustness Checks for Event Study Model (Ratio)") ///
    mtitles("Main Model" "Clustered SE") ///
    addnotes("Standard errors in parentheses" "Robust/Clustered SE" "Country fixed effects only (no year FE)")

esttab ratio_event_study ratio_clustered using "robustness_checks.txt", ///
    b(3) se(3) ///
    title("Robustness Checks for Event Study Model (Ratio)") ///
    mtitles("Main Model" "Clustered SE") ///
    addnotes("Standard errors in parentheses" "Robust/Clustered SE" "Country fixed effects only (no year FE)") ///
    replace


* （改为由 Python 绘图）不在 Stata 内作图

* 导出主模型事件研究系数（供 Python 使用）
preserve
estimates restore ratio_event_study
* 调试：检查估计结果是否存在
estimates dir
* 调试：显示当前估计结果
ereturn list
capture which parmest
if _rc {
    ssc install parmest, replace
}
* 尝试不同的 parmest 选项
capture parmest, norestore
if _rc {
    display "parmest failed, trying alternative approach"
    * 如果 parmest 失败，直接从估计结果中提取
    matrix b = e(b)
    matrix V = e(V)
    local nparams = colsof(b)
    clear
    set obs `nparams'
    gen parm = ""
    gen estimate = .
    gen min95 = .
    gen max95 = .
    forvalues i = 1/`nparams' {
        local varname = el(e(b), 1, `i')
        replace parm = "`varname'" in `i'
        replace estimate = el(b, 1, `i') in `i'
        local se = sqrt(el(V, `i', `i'))
        replace min95 = estimate - 1.96*`se' in `i'
        replace max95 = estimate + 1.96*`se' in `i'
    }
}
* 调试：显示所有参数
count
if r(N) > 0 {
    list parm estimate min95 max95 in 1/`r(N)'
}
else {
    display "No parameters found"
}
* 简化匹配逻辑
keep if regexm(parm, "event_year") | regexm(parm, "event_ye")
* 再次调试：显示匹配后的结果
count
if r(N) > 0 {
    list parm estimate min95 max95
}
else {
    display "No event_year parameters found"
}
gen event_bin = .
quietly replace event_bin = real(regexs(1)) if regexm(parm, "^([0-9]+)[b]?\.")
* 调试：显示 event_bin 生成结果
list parm event_bin
* 调试：显示哪些参数被成功解析
count if !missing(event_bin)
display "Successfully parsed " r(N) " parameters"
* 调试：显示哪些参数没有被解析
count if missing(event_bin)
if r(N) > 0 {
    display "Failed to parse " r(N) " parameters:"
    list parm if missing(event_bin)
}
drop if missing(event_bin)
gen rel_year = event_bin - 5
keep estimate min95 max95 event_bin rel_year parm
* 最终调试：显示导出前的数据
count
if r(N) > 0 {
    list estimate min95 max95 event_bin rel_year parm
    export delimited using "event_study_params2.csv", replace
}
else {
    display "No data to export"
}
restore

* 导出聚类SE版本参数（供 Python 使用，仅保存 DTA）
preserve
estimates restore ratio_clustered
parmest, norestore
keep if regexm(parm, "event_ye") | regexm(parm, "event_year")
gen event_bin = .
quietly replace event_bin = real(regexs(1)) if regexm(parm, "^([0-9]+)[b]?\.")
* 调试：显示 event_bin 生成结果
list parm event_bin
* 调试：显示哪些参数被成功解析
count if !missing(event_bin)
display "Successfully parsed " r(N) " parameters"
* 调试：显示哪些参数没有被解析
count if missing(event_bin)
if r(N) > 0 {
    display "Failed to parse " r(N) " parameters:"
    list parm if missing(event_bin)
}
drop if missing(event_bin)
gen rel_year = event_bin - 5
keep estimate min95 max95 event_bin rel_year parm
save "event_study_params_clustered.dta", replace
restore


* 6. 使用Python进行高级可视化（比例因变量）
* =============================================================================

* 先保存面板数据以供Python脚本读取
save "russia_cooperation_panel_final.dta", replace

* 运行事件研究Python可视化脚本
shell python3 ./event_study_visualization.py

* 运行简化的异质性分析Python脚本，统一由 Python 输出 heterogeneity_country_diff.csv 与 heterogeneity_country_summary.txt
shell python3 ./simple_heterogeneity_analysis.py


* 7. 保存最终数据
* =============================================================================

save "russia_cooperation_panel_final.dta", replace

* 输出数据摘要
describe
summarize
xtdescribe


* 关闭日志文件
log close
