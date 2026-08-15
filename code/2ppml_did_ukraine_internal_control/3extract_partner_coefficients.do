* =============================================================================
* 提取每个合作伙伴的post_war系数
* 方法：对每个合作伙伴分别运行PPML回归
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

cd "$CODE/2ppml_did_ukraine_internal_control"

* 导入数据
use ppml_data.dta, clear

* 确保变量类型正确
destring year paper_count post_war ln_total_vol ln_total_pub, replace
encode partner_country, gen(partner_id)

* 获取所有合作伙伴
levelsof partner_id, local(partners)

* 创建结果文件
tempname memhold
tempfile results
postfile `memhold' partner_id str50 partner_country double coef double se double tstat double pvalue int sig_10 int sig_05 int sig_01 using `results', replace

* 对每个合作伙伴分别运行回归
local n_partners : word count `partners'
local i = 0

foreach p of local partners {
    local i = `i' + 1
    if mod(`i', 20) == 0 {
        display "处理进度: `i' / `n_partners'"
    }
    
    * 保存当前数据状态
    preserve
    keep if partner_id == `p'
    
    * 获取合作伙伴名称（直接从数据中获取，避免特殊字符问题）
    local pname = partner_country[1]
    
    * 检查数据量
    count
    local total_obs = r(N)
    
    * 检查是否有足够的变异
    count if post_war == 1 & paper_count > 0
    local post_pos = r(N)
    count if post_war == 0 & paper_count > 0
    local pre_pos = r(N)
    
    * 初始化结果变量
    local coef = .
    local se = .
    local tstat = .
    local pval = .
    local sig_10 = 0
    local sig_05 = 0
    local sig_01 = 0
    
    * 如果有足够的变异和数据，进行回归
    if (`post_pos' > 0 & `pre_pos' > 0 & `total_obs' >= 4) {
        * 使用ppmlhdfe（包含年份固定效应）
        capture quietly ppmlhdfe paper_count post_war ln_total_pub, ///
            absorb(year) ///
            offset(ln_total_vol) ///
            vce(robust) ///
            maxiter(10000) ///
            tolerance(1e-8)
        
        * 如果ppmlhdfe失败，使用简单的poisson回归
        if _rc != 0 {
            capture quietly poisson paper_count post_war ln_total_pub, offset(ln_total_vol) vce(robust)
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
            local sig_10 = (`pval' < 0.10)
            local sig_05 = (`pval' < 0.05)
            local sig_01 = (`pval' < 0.01)
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
                local sig_10 = 0
                local sig_05 = 0
                local sig_01 = 0
            }
        }
    }
    
    * 保存结果到postfile（只有当有有效结果时才保存）
    if !missing(`coef') {
        * 使用compound quotes (`"..."') 来安全处理包含引号的字符串
        post `memhold' (`p') (`"`pname'"') (`coef') (`se') (`tstat') (`pval') (`sig_10') (`sig_05') (`sig_01')
    }
    
    restore
}

* 关闭postfile
postclose `memhold'

* 加载结果
use `results', clear

* 标记正负增长
gen direction = .
replace direction = 1 if coef > 0 & !missing(coef)   // 正向增长
replace direction = -1 if coef < 0 & !missing(coef)  // 负向增长
replace direction = 0 if coef == 0 | missing(coef)    // 无变化

* 保存结果
save partner_coefficients.dta, replace
export excel using partner_coefficients.xlsx, firstrow(variables) replace
export delimited using partner_coefficients.csv, replace

display _dup(80) "="
display "系数提取完成！"
display _dup(80) "="
display ""
display "结果摘要:"
display "总合作伙伴数: " _N
tab direction
display ""
count if sig_01 == 1
local n_sig_01 = r(N)
count if sig_05 == 1
local n_sig_05 = r(N)
count if sig_10 == 1
local n_sig_10 = r(N)
display "1%水平显著: `n_sig_01'"
display "5%水平显著: `n_sig_05'"
display "10%水平显著: `n_sig_10'"
display ""

* 显示前10名和后10名
display "正向变化最多的10个国家："
gsort -coef
list partner_country coef pvalue sig_10 sig_05 sig_01 in 1/10, noobs

display ""
display "负向变化最多的10个国家："
gsort coef
list partner_country coef pvalue sig_10 sig_05 sig_01 in 1/10, noobs

display ""
display "✅ 结果已保存到："
display "  - partner_coefficients.dta"
display "  - partner_coefficients.xlsx"
display "  - partner_coefficients.csv"
