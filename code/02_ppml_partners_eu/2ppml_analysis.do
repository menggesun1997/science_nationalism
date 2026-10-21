* =============================================================================
* PPML分析：EU-27与合作伙伴国家合作变化（内部控制组方法）
* 模型：\begin{equation}
* \label{eq:gravity_ppml} 
* E[\text{Count}_{jt}] = \exp\left( \alpha_j + \lambda_t + \beta_j \cdot \text{Post}_t + \ln(\text{Total}^{\text{Intl}}_{t}) + \gamma \cdot \ln(\text{Total}^{\text{Pub}}_{jt}) \right) 
* \end{equation}
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

cd "$CODE/02_ppml_partners_eu"



* 导入数据
* 优先尝试Stata格式，如果不存在则使用Excel或CSV
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

* 数据检查
describe
summarize

* 确保变量类型正确
destring year paper_count post_brexit ln_total_vol ln_total_pub, replace
encode partner_country, gen(partner_id)

* 检查数据
display _dup(80) "="
display "数据检查"
display _dup(80) "="
tab year
tab post_brexit
display ""
display "合作伙伴数量: " partner_id[_N]
display "年份范围: " year[1] " - " year[_N]
display ""
summarize paper_count ln_total_vol ln_total_pub

* 检查是否有缺失值
count if missing(paper_count)
if r(N) > 0 {
    display "⚠️  警告: paper_count有 " r(N) " 个缺失值"
}

count if missing(ln_total_vol)
if r(N) > 0 {
    display "⚠️  警告: ln_total_vol有 " r(N) " 个缺失值"
}

count if missing(ln_total_pub)
if r(N) > 0 {
    display "⚠️  警告: ln_total_pub有 " r(N) " 个缺失值"
}

count if missing(partner_id)
if r(N) > 0 {
    display "⚠️  警告: partner_id有 " r(N) " 个缺失值"
}

* =============================================================================
* Step 2: Run PPML Model (with Offset)
* 模型：\begin{equation}
* \label{eq:gravity_ppml} 
* E[\text{Count}_{jt}] = \exp\left( \alpha_j + \lambda_t + \beta_j \cdot \text{Post}_t + \ln(\text{Total}^{\text{Intl}}_{t}) + \gamma \cdot \ln(\text{Total}^{\text{Pub}}_{jt}) \right) 
* \end{equation}
* =============================================================================
display _dup(80) "="
display "Step 2: Run PPML Model (with Offset)"
display _dup(80) "="
display ""
display "模型设定:"
display "  \begin{equation}"
display "  \label{eq:gravity_ppml} "
display "  E[\text{Count}_{jt}] = \exp\left( \alpha_j + \lambda_t + \beta_j \cdot \text{Post}_t + \ln(\text{Total}^{\text{Intl}}_{t}) + \gamma \cdot \ln(\text{Total}^{\text{Pub}}_{jt}) \right) "
display "  \end{equation}"
display ""
display "变量说明:"
display "  - paper_count: 双边合作计数（因变量，Count_{jt}）"
display "  - i.post_brexit#i.partner_id: 核心变量，衡量每个合作伙伴国家在Brexit后的变化（β_j · Post_t）"
display "  - partner_id: 合作伙伴国家固定效应（α_j）"
display "  - year: 年份固定效应（λ_t）"
display "  - ln_total_vol: offset变量，控制国际总规模（ln(Total^{Intl}_t)）"
display "  - ln_total_pub: 回归变量，控制合作伙伴发文量（γ · ln(Total^{Pub}_{jt})）"
display ""

* 检查ppmlhdfe是否已安装
capture which ppmlhdfe
if _rc {
    display "正在安装ppmlhdfe包..."
    ssc install ppmlhdfe, replace
    ssc install reghdfe, replace
    ssc install ftools, replace
}

* 运行PPML回归
display ""
display "运行PPML回归..."
display "命令: ppmlhdfe paper_count i.post_brexit#i.partner_id ln_total_pub, absorb(partner_id year) offset(ln_total_vol) vce(cluster partner_id)"
display ""

ppmlhdfe paper_count i.post_brexit#i.partner_id ln_total_pub, ///
    absorb(partner_id year) ///
    offset(ln_total_vol) ///
    vce(cluster partner_id) ///
    maxiter(10000) ///
    tolerance(1e-8)

* 保存结果
estimates store ppml_main
display ""
display "✅ PPML回归完成"
display ""

* =============================================================================
* Step 3: 提取每个合作伙伴的系数
* =============================================================================
display _dup(80) "="
display "Step 3: 提取每个合作伙伴的系数"
display _dup(80) "="
display ""

* 保存当前数据到临时文件（用于获取合作伙伴名称）
tempfile original_data
save `original_data'

* 获取所有合作伙伴
levelsof partner_id, local(partners)

* 创建结果文件
tempname memhold
tempfile results
postfile `memhold' partner_id str50 partner_country double coef double se double tstat double pvalue int sig_10 int sig_05 int sig_01 using `results', replace

* 从主回归结果中提取每个合作伙伴的系数
estimates restore ppml_main
matrix b = e(b)
matrix V = e(V)
local varnames : colnames b

display "正在提取各合作伙伴的系数..."
local extracted = 0

foreach p of local partners {
    * 查找该合作伙伴的交互项系数
    local colnum = 0
    foreach v of local varnames {
        local colnum = `colnum' + 1
        * 查找包含该合作伙伴ID的交互项
        if strpos("`v'", "post_brexit#partner_id") > 0 | strpos("`v'", "partner_id#post_brexit") > 0 {
            * 检查是否匹配当前合作伙伴ID（使用字符串匹配）
            local pid_str = "`p'"
            if strpos("`v'", "`pid_str'") > 0 {
                local coef = b[1, `colnum']
                local se = sqrt(V[`colnum', `colnum'])
                local tstat = `coef' / `se'
                local pval = 2 * (1 - normal(abs(`tstat')))
                local sig_10 = (`pval' < 0.10)
                local sig_05 = (`pval' < 0.05)
                local sig_01 = (`pval' < 0.01)
                
                * 获取合作伙伴名称
                quietly levelsof partner_country if partner_id == `p', local(pname) clean
                
                * 保存结果
                post `memhold' (`p') (`"`pname'"') (`coef') (`se') (`tstat') (`pval') (`sig_10') (`sig_05') (`sig_01')
                local extracted = `extracted' + 1
                continue, break
            }
        }
    }
}

* 关闭postfile
postclose `memhold'

* 加载结果
use `results', clear

* 检查是否提取到结果
count
if r(N) == 0 {
    display "⚠️  警告：未能从主回归结果中提取到任何系数"
    display "可能的原因："
    display "  1. 主回归结果中没有交互项系数"
    display "  2. 变量名不匹配"
    display ""
    * 恢复原始数据
    use `original_data', clear
}
else {
    display "✅ 成功提取 " r(N) " 个合作伙伴的系数"
    display ""
    
    * 标记正负增长
    gen direction = .
    replace direction = 1 if coef > 0 & !missing(coef)   // 正向增长
    replace direction = -1 if coef < 0 & !missing(coef)  // 负向增长
    replace direction = 0 if coef == 0 | missing(coef)    // 无变化
    
    * 保存结果
    save partner_coefficients.dta, replace
    export excel using partner_coefficients.xlsx, firstrow(variables) replace
    export delimited using partner_coefficients.csv, replace
    
    display "✅ 系数结果已保存到："
    display "  - partner_coefficients.dta"
    display "  - partner_coefficients.xlsx"
    display "  - partner_coefficients.csv"
    display ""
    
    * 显示结果摘要
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
    
    * 恢复原始数据
    use `original_data', clear
}

* 显示主要结果
display _dup(80) "="
display "主要结果摘要"
display _dup(80) "="
display ""
display "模型系数（部分显示，每个合作伙伴国家都有一个post_brexit系数）"
display "使用 'estimates replay ppml_main' 查看完整结果"
display ""

display ""
display _dup(80) "="
display "分析完成！"
display _dup(80) "="
display ""
display "主要结果文件:"
display "  - partner_coefficients.dta: 每个合作伙伴的系数（已生成）"
display "  - partner_coefficients.xlsx: Excel格式结果（已生成）"
display "  - partner_coefficients.csv: CSV格式结果（已生成）"
display ""
display "查看完整回归结果:"
display "  estimates replay ppml_main"
display ""

