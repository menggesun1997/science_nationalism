* =============================================================================
* Event Study: 动态效应分析
* 为多个国家生成动态效应图
* =============================================================================

clear all
set more off

* 设置工作目录
cd "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/2ppml_did_uk_internal_control"

* 导入数据
capture confirm file "ppml_data.dta"
if _rc == 0 {
    use ppml_data.dta, clear
    display "✅ 使用Stata格式数据"
}
else {
    capture confirm file "ppml_data.xlsx"
    if _rc == 0 {
        import excel using ppml_data.xlsx, firstrow clear
        display "✅ 使用Excel格式数据"
    }
    else {
        import delimited using ppml_data.csv, clear
        display "✅ 使用CSV格式数据"
    }
}

* 确保变量类型正确
destring year paper_count post_war ln_total_vol ln_total_pub, replace
encode partner_country, gen(partner_id)

* 定义关注的国家列表（使用引号包裹每个国家名称，避免空格分割问题）
local target_countries `" "UNITED ARAB EMIRATES" "SAUDI ARABIA" "INDONESIA" "NIGERIA" "PAKISTAN" "EGYPT" "INDIA" "CHINA" "TURKIYE" "QATAR" "RUSSIAN FEDERATION" "NEW ZEALAND" "FRANCE" "UNITED STATES" "'

* 创建国家名称到ID的映射
preserve
keep partner_id partner_country
duplicates drop
sort partner_id
tempfile partner_map
save `partner_map'
restore

* 显示目标国家的ID映射
display ""
display _dup(80) "="
display "目标国家的Partner ID映射"
display _dup(80) "="
display ""
preserve
use `partner_map', clear
foreach country of local target_countries {
    * 去除引号（如果有）
    local country_clean = subinstr(`"`country'"', `"""', "", .)
    count if upper(trim(partner_country)) == upper(trim(`"`country_clean'"'))
    if r(N) > 0 {
        local country_id = partner_id[1]
        display "  `country_clean': partner_id = `country_id'"
    }
    else {
        display "  ⚠️  `country_clean': 未找到"
    }
}
restore

* 定义基准年（2021年，战前最后一年）
local base_year = 2021

display ""
display _dup(80) "="
display "Event Study回归：动态效应分析"
display _dup(80) "="
display ""
display "模型设定:"
display "  E[Count_jt] = exp(α_j + λ_t + β_jt • Year_t + ln(Total_t^Intl) + γ • ln(Total_jt^Pub))"
display ""
display "基准年: `base_year'"
display ""

* 检查ppmlhdfe是否已安装
capture which ppmlhdfe
if _rc {
    display "正在安装ppmlhdfe包..."
    ssc install ppmlhdfe, replace
    ssc install reghdfe, replace
    ssc install ftools, replace
}

* 检查coefplot是否已安装
capture which coefplot
if _rc {
    display "正在安装coefplot包..."
    ssc install coefplot, replace
}

* 运行Event Study回归
display ""
display "运行Event Study回归..."
display "命令: ppmlhdfe paper_count ib`base_year'.year#i.partner_id ln_total_pub, absorb(partner_id year) offset(ln_total_vol) vce(cluster partner_id)"
display ""

ppmlhdfe paper_count ib`base_year'.year#i.partner_id ln_total_pub, ///
    absorb(partner_id year) ///
    offset(ln_total_vol) ///
    vce(cluster partner_id) ///
    maxiter(10000) ///
    tolerance(1e-8)

* 保存结果
estimates store event_study_main
display ""
display "✅ Event Study回归完成"
display ""

* =============================================================================
* 为每个目标国家生成动态效应图
* =============================================================================

display ""
display _dup(80) "="
display "生成各国家的动态效应图"
display _dup(80) "="
display ""

* 创建输出目录
capture mkdir "event_study_results"

* 为每个国家生成单独的图
foreach country of local target_countries {
    * 获取该国家的partner_id
    preserve
    keep partner_id partner_country
    duplicates drop
    count if upper(trim(partner_country)) == "`country'"
    if r(N) == 0 {
        restore
        display "⚠️  跳过 `country'：未找到该国家"
        continue
    }
    local country_id = partner_id[1]
    restore
    
    * 去除引号（如果有）
    local country_clean = subinstr(`"`country'"', `"""', "", .)
    display ""
    display "正在为 `country_clean' (partner_id=`country_id') 生成动态效应图..."
    
    * 生成图
    * 生成文件名（去除空格和特殊字符）
    local country_file = subinstr(`"`country_clean'"', " ", "_", .)
    local country_file = subinstr(`"`country_file'"', ",", "", .)
    
    capture coefplot, ///
        keep(*.year#`country_id'.partner_id) ///
        coeflabels(*.year#`country_id'.partner_id = "") ///
        vertical ///
        yline(0, lcolor(black) lwidth(0.8)) ///
        xline(2021.5, lpattern(dash) lcolor(red) lwidth(1.2)) ///
        title("Event Study: UK-`country_clean' Collaboration Dynamics", size(medium)) ///
        ytitle("Relative Change in Collaboration (Log Scale)", size(small)) ///
        xtitle("Year", size(small)) ///
        addplot(line @b @at, lcolor(blue) lwidth(1.5)) ///
        ciopts(recast(rcap) lcolor(blue) mcolor(blue)) ///
        note("Base year: `base_year'. Controls include partner's scientific mass (ln_total_pub).", size(vsmall)) ///
        graphregion(color(white)) ///
        plotregion(color(white)) ///
        saving("event_study_results/event_study_`country_file'.gph", replace)
    
    if _rc == 0 {
        * 导出为PNG
        graph export "event_study_results/event_study_`country_file'.png", replace width(2000) height(1200)
        * 导出为PDF
        graph export "event_study_results/event_study_`country_file'.pdf", replace
        display "  ✅ 已保存: event_study_results/event_study_`country_file'.png"
    }
    else {
        display "  ⚠️  生成图表时出错"
    }
}

* =============================================================================
* 生成综合图：所有国家在一个图中（使用子图）
* =============================================================================

display ""
display _dup(80) "="
display "生成综合图：所有国家在一个图中"
display _dup(80) "="
display ""

* 准备数据用于综合图
display ""
display "提取系数数据用于Python可视化..."
preserve
estimates restore event_study_main

* 使用parmest提取系数（需要安装parmest: ssc install parmest）
capture which parmest
if _rc {
    display "正在安装parmest包..."
    ssc install parmest, replace
}

* 提取所有系数
parmest, saving("event_study_results/event_study_coefficients.dta", replace)

* 加载系数数据
use "event_study_results/event_study_coefficients.dta", clear

* 解析系数名称，提取年份和partner_id
gen year = .
gen partner_id_coef = .
gen country = ""

* 解析系数名称（格式：year#partner_id.partner_id）
gen coef_name = parm

* 为每个目标国家提取数据
tempfile all_countries_data
clear
save `all_countries_data', emptyok

foreach country of local target_countries {
    * 获取该国家的partner_id
    preserve
    use `partner_map', clear
    * 去除引号（如果有）
    local country_clean = subinstr(`"`country'"', `"""', "", .)
    count if upper(trim(partner_country)) == upper(trim(`"`country_clean'"'))
    if r(N) == 0 {
        restore
        continue
    }
    local country_id = partner_id[1]
    restore
    
    preserve
    use "event_study_results/event_study_coefficients.dta", clear
    
    * 筛选该国家的系数（包含该partner_id的交互项）
    keep if strpos(parm, "#`country_id'.partner_id") > 0
    
    if _N == 0 {
        restore
        continue
    }
    
    * 提取年份
    gen year_str = substr(parm, 1, strpos(parm, ".") - 1)
    gen year_part = substr(year_str, 1, strpos(year_str, "#") - 1)
    destring year_part, replace
    rename year_part year
    
    * 添加国家信息（使用清理后的国家名称）
    gen country = "`country_clean'"
    gen country_id = `country_id'
    
    * 重命名列以匹配Python脚本期望的格式
    rename estimate coef
    rename stderr se
    
    * 计算置信区间
    gen ci_lower = coef - 1.96 * se
    gen ci_upper = coef + 1.96 * se
    
    * 只保留需要的列
    keep year coef se ci_lower ci_upper country country_id
    
    * 添加到总数据
    append using `all_countries_data'
    save `all_countries_data', replace
    
    restore
}

* 加载所有国家数据
use `all_countries_data', clear

* 保存为CSV以便后续使用
export delimited using "event_study_results/event_study_all_countries_data.csv", replace
display "✅ 已保存数据: event_study_results/event_study_all_countries_data.csv"
display "  共 " _N " 条记录，涵盖 " country[_N] " 个国家"

* 生成综合图（使用Python会更灵活，但这里先用Stata的简单方法）
* 由于Stata的coefplot对多国家支持有限，我们生成一个包含所有国家的数据文件
* 用户可以使用Python或其他工具进一步可视化

display ""
display "✅ Event Study分析完成！"
display ""
display "输出文件："
display "  - 各国家的单独图表: event_study_results/event_study_*.png"
display "  - 所有国家的数据: event_study_results/event_study_all_countries_data.csv"
display ""
display "建议：使用Python脚本（6visualize_event_study.py）生成更美观的综合图"

restore

* =============================================================================
* 显示主要结果摘要
* =============================================================================

display ""
display _dup(80) "="
display "主要结果摘要"
display _dup(80) "="
display ""
display "查看完整回归结果:"
display "  estimates replay event_study_main"
display ""
display "查看特定国家的系数:"
display "  estimates restore event_study_main"
display "  matrix list e(b)"
display "  查找包含 'year#partner_id' 的系数"
display ""

