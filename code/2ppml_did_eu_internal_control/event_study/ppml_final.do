

clear all
set more off

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

cd "$CODE/2ppml_did_eu_internal_control"

* 导入数据（只使用xlsx格式）
capture confirm file "ppml_data.xlsx"
if _rc == 0 {
    import excel using ppml_data.xlsx, firstrow clear
    display "✅ 使用Excel格式数据"
}
else {
    display "❌ 错误：找不到ppml_data.xlsx文件"
    display "   请确保文件存在于工作目录中"
    exit
}


* 确保变量类型正确
capture confirm variable ln_total_international
local ln_total_international = (_rc == 0)

* Post_t: 事件后虚拟变量（2016年及之后=1）
* 如果数据中没有post_war变量，则生成
capture confirm variable post_war
if _rc {
    gen post_war = (year >= 2016)
    display "✅ 生成post_war变量"
}

* 确保partner_country是字符串类型
capture confirm string variable partner_country
if _rc {
    tostring partner_country, replace
    display "✅ 将partner_country转换为字符串类型"
}

* =============================================================================
* Step 0: 筛选合作伙伴国家（只保留每年paper_count > 100的国家）
* =============================================================================

* 检查每个国家每年的paper_count是否都大于10
preserve
gen year_meets_criteria = (paper_count > 30)

* 按国家统计：每年是否都满足条件
bysort partner_country: egen all_years_meet = min(year_meets_criteria)

* 统计信息
count if all_years_meet == 1
local n_qualified = r(N)
count if all_years_meet == 0
local n_not_qualified = r(N)

* 找出满足条件的国家（所有年份都满足）
keep if all_years_meet == 1
* 获取唯一的国家列表
keep partner_country
duplicates drop partner_country, force
levelsof partner_country, local(all_countries)
local n_countries: word count `all_countries'

display ""
display "筛选后的合作伙伴国家列表:"
* 显示这些国家
if `n_countries' > 0 {
    display ""
    display "这些国家:"
    list partner_country, clean noobs
}

* 保存筛选后的国家列表到临时文件
tempfile filtered_countries
save `filtered_countries', replace
restore

* 只保留筛选后的国家的数据
merge m:1 partner_country using `filtered_countries', keep(match) nogen

display ""
display "筛选后的数据:"
display "  观测数: " _N
quietly levelsof partner_country
display "  国家数: " r(r)

* 保存原始数据（用于循环）- 在创建结果数据框之前保存
tempfile original_data
save `original_data', replace

* =============================================================================
* Step 1: 创建结果数据框
* =============================================================================
preserve
clear
set obs `n_countries'

* 创建变量
gen partner_country = ""
gen coefficient_log = .
gen std_error = .
gen ci_lower_log = .
gen ci_upper_log = .
gen coefficient = .
gen ci_lower = .
gen ci_upper = .
gen pvalue = .
gen coefficient_pct = .
gen ci_lower_pct = .
gen ci_upper_pct = .
gen sig_stars = ""

* 保存临时结果文件
tempfile results
save `results', replace
restore

* =============================================================================
* Step 2: 循环每个国家，运行PPML回归
* =============================================================================

display "为每个国家循环运行PPML回归"
display "Cluster标准误: partner_country"
display ""

* 加载原始数据（确保数据已加载）
use `original_data', clear

* 循环每个国家
local row = 1
local country_num = 0

foreach country of local all_countries {
    local country_num = `country_num' + 1
    
    display ""
    display _dup(80) "-"
    display "处理国家 " `country_num' "/" `n_countries' ": `country'"
    display _dup(80) "-"
    
    * 删除可能存在的旧变量（如果存在）
    capture drop country_j_post
    
    * 创建该国家的交互项变量：Country_j × Post_t
    * 只有该国家在2016年之后的观测为1，其他全为0
    gen country_j_post = (partner_country == "`country'") * post_war
    
    * 验证交互项计算
    count if partner_country == "`country'" & year >= 2016 & country_j_post == 1
    local n_treated = r(N)
    count if partner_country == "`country'" & year < 2016 & country_j_post == 0
    local n_pre = r(N)
    count if partner_country != "`country'" & country_j_post == 0
    local n_control = r(N)
    
    display "  交互项验证:"
    display "    - `country'在2016年之后的观测（应为1）: " `n_treated'
    display "    - `country'2016年之前的观测（应为0）: " `n_pre'
    display "    - 其他国家的所有观测（应为0）: " `n_control'
    
    * 运行PPML回归
    capture {
        ppmlhdfe paper_count ///
            country_j_post ///
            ln_total_international, ///
            absorb(partner_country year) ///
            cluster(partner_country) ///
            maxiter(10000) ///
            tolerance(1e-8)
    }
    
    * 如果回归成功，提取系数和标准误
    if _rc == 0 {
        capture {
            local coef_log = _b[country_j_post]
            local se = _se[country_j_post]
            
            if !missing(`coef_log') & !missing(`se') {
                * 计算p值（双尾检验）
                local z_score = `coef_log' / `se'
                local pval = 2 * (1 - normal(abs(`z_score')))
                
                * 计算置信区间（对数尺度）
                local ci_lower_log = `coef_log' - 1.96 * `se'
                local ci_upper_log = `coef_log' + 1.96 * `se'
                
                * 转换为相对份额的变化: e^δ_j - 1
                local coefficient = exp(`coef_log') - 1
                local ci_lower = exp(`ci_lower_log') - 1
                local ci_upper = exp(`ci_upper_log') - 1
                
                * 转换为百分比
                local coefficient_pct = `coefficient' * 100
                local ci_lower_pct = `ci_lower' * 100
                local ci_upper_pct = `ci_upper' * 100
                
                * 显著性标记
                local sig_stars = ""
                if `pval' < 0.001 {
                    local sig_stars "***"
                }
                else if `pval' < 0.01 {
                    local sig_stars "**"
                }
                else if `pval' < 0.05 {
                    local sig_stars "*"
                }
                
                * 保存结果到结果文件
                preserve
                use `results', clear
                
                replace partner_country = "`country'" in `row'
                replace coefficient_log = `coef_log' in `row'
                replace std_error = `se' in `row'
                replace ci_lower_log = `ci_lower_log' in `row'
                replace ci_upper_log = `ci_upper_log' in `row'
                replace coefficient = `coefficient' in `row'
                replace ci_lower = `ci_lower' in `row'
                replace ci_upper = `ci_upper' in `row'
                replace pvalue = `pval' in `row'
                replace coefficient_pct = `coefficient_pct' in `row'
                replace ci_lower_pct = `ci_lower_pct' in `row'
                replace ci_upper_pct = `ci_upper_pct' in `row'
                replace sig_stars = "`sig_stars'" in `row'
                
                save `results', replace
                restore
                
                display "  ✅ 成功：系数 = " %9.4f `coef_log' " (p = " %9.4f `pval' ")"
            }
            else {
                display "  ⚠️  警告：无法提取系数"
            }
        }
    }
    else {
        display "  ⚠️  警告：回归失败，错误代码: " _rc
    }
    
    * 恢复原始数据（删除临时变量，准备下一个国家）
    use `original_data', clear
    
    local row = `row' + 1
}

display ""
display _dup(80) "="
display "所有国家的回归完成"
display _dup(80) "="

* =============================================================================
* Step 3: 整理和保存结果
* =============================================================================
display ""
display _dup(80) "="
display "整理和保存结果"
display _dup(80) "="

* 加载结果数据
use `results', clear

* 删除空行
drop if missing(partner_country)

display ""
display "成功提取 " _N " 个国家的系数"

* 删除空行
drop if missing(partner_country)

* 排序（按系数大小）
sort coefficient_log

* 创建输出文件夹（如果不存在）
capture mkdir "event_study_try"

* 保存结果到event_study_try文件夹
export delimited using "event_study_try/did_all_countries_results_stata.csv", replace
save "event_study_try/did_all_countries_results_stata.dta", replace

display ""
display "结果已保存:"


* 显示结果摘要（前10个和后10个）
display ""
display _dup(80) "="
display "DID系数结果摘要（按系数大小排序）"
display _dup(80) "="
display ""
display "系数最大的10个国家:"
list partner_country coefficient_log coefficient_pct pvalue sig_stars in 1/10, clean noobs

display ""
display "系数最小的10个国家:"
local n_obs = _N
local start = max(1, `n_obs' - 9)
list partner_country coefficient_log coefficient_pct pvalue sig_stars in `start'/`n_obs', clean noobs

display ""
display "所有国家统计:"
display "  总国家数: " _N
count if pvalue < 0.05 & pvalue != .
display "  显著国家数 (p<0.05): " r(N)
count if coefficient_log > 0 & coefficient_log != .
display "  正系数国家数: " r(N)
count if coefficient_log < 0 & coefficient_log != .
display "  负系数国家数: " r(N)

