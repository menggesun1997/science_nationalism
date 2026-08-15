* =============================================================================
* PPML-DiD分析：俄罗斯国际合作变化
* 分析俄罗斯与各合作伙伴国家在战争前后的合作变化
* 使用ppmlhdfe进行估计
* =============================================================================

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

cd "$CODE/2two_way_did_russia"

* 导入数据
import excel using ppml_did_data.xlsx, firstrow clear

* 数据检查
describe
summarize

* 确保变量类型正确
destring year paper_count post_war treated_country did_dummy, replace
encode focal_country, gen(focal_id)
encode partner_country, gen(partner_id)

* 检查数据
tab focal_country
tab post_war
tab treated_country
tab did_dummy

* =============================================================================
* 1. 基础PPML-DiD回归（所有数据）
* =============================================================================
display _dup(80) "="
display "基础PPML-DiD回归（所有数据）"
display _dup(80) "="

* 检查ppmlhdfe是否已安装
capture which ppmlhdfe
if _rc {
    display "正在安装ppmlhdfe包..."
    ssc install ppmlhdfe, replace
    ssc install reghdfe, replace
    ssc install ftools, replace
}

* 基础回归：所有合作伙伴
ppmlhdfe paper_count did_dummy post_war treated_country, ///
    absorb(focal_country partner_country year) ///
    vce(robust) ///
    maxiter(10000) ///
    tolerance(1e-8)

* 保存结果
estimates store baseline
display "基础回归完成，DID系数 = " _b[did_dummy]

* =============================================================================
* 2. 按合作伙伴国家分别估计（获取每个国家的系数）
* =============================================================================
display _dup(80) "="
display "按合作伙伴国家分别估计"
display _dup(80) "="

* 只保留俄罗斯的数据（因为只有俄罗斯是处理组）
keep if treated_country == 1

* 获取所有合作伙伴国家
levelsof partner_country, local(partners)

* 创建结果文件（使用postfile方法，更安全）
tempname memhold
tempfile results
postfile `memhold' str50 partner_country double coef double se double tstat double pvalue int significant using `results', replace

* 对每个合作伙伴国家分别回归
foreach partner of local partners {
    display "正在估计: `partner'"
    
    * 保存当前数据状态
    preserve
    keep if partner_country == "`partner'"
    
    * 检查数据量
    count
    local total_obs = r(N)
    
    * 检查是否有足够的变异
    count if post_war == 1 & paper_count > 0
    local post_pos = r(N)
    count if post_war == 0 & paper_count > 0
    local pre_pos = r(N)
    
    * 检查年份数量（需要至少2个不同的年份）
    quietly tab year
    local n_years = r(r)
    
    * 检查是否有足够的非零观测值
    count if paper_count > 0
    local nonzero_obs = r(N)
    
    * 初始化结果变量
    local coef = .
    local se = .
    local tstat = .
    local pval = .
    local sig = 0
    
    * 如果有足够的变异和数据，进行回归
    if (`post_pos' > 0 & `pre_pos' > 0 & `n_years' >= 2 & `nonzero_obs' >= 2 & `total_obs' >= 4) {
        * 方法1：尝试使用ppmlhdfe（如果数据量足够）
        * 如果年份数较少，不使用year固定效应
        if (`n_years' >= 5) {
            capture quietly ppmlhdfe paper_count post_war, ///
                absorb(year) ///
                vce(robust) ///
                maxiter(10000) ///
                tolerance(1e-8)
        }
        else {
            * 如果年份数较少，不使用固定效应
            capture quietly ppmlhdfe paper_count post_war, ///
                vce(robust) ///
                maxiter(10000) ///
                tolerance(1e-8)
        }
        
        * 如果ppmlhdfe失败，使用简单的poisson回归
        if _rc != 0 {
            capture quietly poisson paper_count post_war, vce(robust)
        }
        
        * 检查回归是否成功
        if _rc == 0 {
            * 提取系数
            matrix b = e(b)
            local coef = b[1, 1]
            matrix V = e(V)
            local se = sqrt(V[1, 1])
            local tstat = `coef' / `se'
            local pval = 2 * (1 - normal(abs(`tstat')))
            local sig = (`pval' < 0.05)
            
            display "  `partner': 系数 = " %9.6f `coef' ", 标准误 = " %9.6f `se' ", p值 = " %9.4f `pval'
        }
        else {
            * 如果回归失败，使用简单的log差异方法
            quietly summarize paper_count if post_war == 0
            local pre_mean = r(mean)
            quietly summarize paper_count if post_war == 1
            local post_mean = r(mean)
            
            * 计算log差异（避免log(0)）
            if (`pre_mean' > 0 & `post_mean' > 0) {
                local coef = log(`post_mean') - log(`pre_mean')
                local se = .
                local tstat = .
                local pval = .
                local sig = 0
                
                display "  `partner': log差异 = " %9.6f `coef' " (使用简单方法，无标准误)"
            }
            else {
                display "  `partner': 回归失败且无法计算log差异（错误代码: " _rc "），跳过"
                restore
                continue
            }
        }
    }
    else {
        display "  `partner': 数据不足（总观测数: `total_obs', 非零观测数: `nonzero_obs', 年份数: `n_years', 战前有数据: `pre_pos', 战后有数据: `post_pos'），跳过"
        restore
        continue
    }
    
    * 保存结果到postfile（只有当有有效结果时才保存）
    if !missing(`coef') {
        post `memhold' ("`partner'") (`coef') (`se') (`tstat') (`pval') (`sig')
    }
    
    restore
}

* 关闭postfile
postclose `memhold'

* 加载结果
use `results', clear

* 标记正负增长
gen direction = .
replace direction = 1 if coef > 0 & !missing(coef)   // 正向增长（红色）
replace direction = -1 if coef < 0 & !missing(coef)  // 负向增长（蓝色）
replace direction = 0 if coef == 0 | missing(coef)   // 无变化

* 保存结果
save partner_coefficients.dta, replace
export excel using partner_coefficients.xlsx, firstrow(variables) replace
export delimited using partner_coefficients.csv, replace

display _dup(80) "="
display "结果摘要"
display _dup(80) "="
display "总合作伙伴数: " _N
tab direction
display ""
display "正向增长国家数: " (direction == 1)
display "负向增长国家数: " (direction == -1)
display "无变化国家数: " (direction == 0)
display ""
summarize coef if direction == 1, detail
summarize coef if direction == -1, detail

* 显示前10名和后10名
display ""
display "正向增长最多的10个国家："
gsort -coef
list partner_country coef pvalue significant in 1/10, noobs

display ""
display "负向增长最多的10个国家："
gsort coef
list partner_country coef pvalue significant in 1/10, noobs

display ""
display "✅ 分析完成！"
display "结果已保存到："
display "  - partner_coefficients.dta"
display "  - partner_coefficients.xlsx"
display "  - partner_coefficients.csv"
