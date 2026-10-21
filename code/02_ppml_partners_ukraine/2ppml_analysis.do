* =============================================================================
* PPML分析：乌克兰与合作伙伴国家合作变化（内部控制组方法）
* 模型：E[Count_jt] = exp(α_j + λ_t + β_j · Post_t + ln(Total_t^Intl) + γ · ln(Total_jt^Pub))
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

cd "$CODE/02_ppml_partners_ukraine"



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
* 检查是否存在ln_total_pub变量
capture confirm variable ln_total_pub
local has_ln_total_pub = (_rc == 0)

if `has_ln_total_pub' {
    destring year paper_count post_war ln_total_vol ln_total_pub, replace
    display "✅ 检测到ln_total_pub变量，将作为控制变量"
}
else {
    destring year paper_count post_war ln_total_vol, replace
    display "⚠️  未检测到ln_total_pub变量，将仅使用ln_total_vol作为offset"
}

encode partner_country, gen(partner_id)

* 检查数据
display _dup(80) "="
display "数据检查"
display _dup(80) "="
tab year
tab post_war
display ""
display "合作伙伴数量: " partner_id[_N]
display "年份范围: " year[1] " - " year[_N]
display ""
summarize paper_count ln_total_vol
if `has_ln_total_pub' {
    summarize ln_total_pub
}

* 检查是否有缺失值
count if missing(paper_count)
if r(N) > 0 {
    display "⚠️  警告: paper_count有 " r(N) " 个缺失值"
}

count if missing(ln_total_vol)
if r(N) > 0 {
    display "⚠️  警告: ln_total_vol有 " r(N) " 个缺失值"
}

if `has_ln_total_pub' {
    count if missing(ln_total_pub)
    if r(N) > 0 {
        display "⚠️  警告: ln_total_pub有 " r(N) " 个缺失值"
    }
}

count if missing(partner_id)
if r(N) > 0 {
    display "⚠️  警告: partner_id有 " r(N) " 个缺失值"
}

* =============================================================================
* Step 2: Run PPML Model (with Offset)
* 模型：E[Count_jt] = exp(α_j + λ_t + β_j · Post_t + ln(Total_t^Intl) + γ · ln(Total_jt^Pub))
* =============================================================================

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
if `has_ln_total_pub' {
    display "命令: ppmlhdfe paper_count i.post_war#i.partner_id ln_total_pub, absorb(partner_id year) offset(ln_total_vol) vce(cluster partner_id)"
}
else {
    display "命令: ppmlhdfe paper_count i.post_war#i.partner_id, absorb(partner_id year) offset(ln_total_vol) vce(cluster partner_id)"
}
display ""

* 根据是否存在ln_total_pub变量，选择不同的模型设定
if `has_ln_total_pub' {
    ppmlhdfe paper_count i.post_war#i.partner_id ln_total_pub, ///
        absorb(partner_id year) ///
        offset(ln_total_vol) ///
        vce(cluster partner_id) ///
        maxiter(10000) ///
        tolerance(1e-8)
}
else {
    ppmlhdfe paper_count i.post_war#i.partner_id, ///
        absorb(partner_id year) ///
        offset(ln_total_vol) ///
        vce(cluster partner_id) ///
        maxiter(10000) ///
        tolerance(1e-8)
}

* 保存结果
estimates store ppml_main
display ""
display "✅ PPML回归完成"
display ""

* 显示主要结果
display _dup(80) "="
display "主要结果摘要"
display _dup(80) "="
display ""
display "模型系数（部分显示，每个合作伙伴国家都有一个post_war系数）"
display "使用 'estimates replay ppml_main' 查看完整结果"
display ""

* 显示如何提取每个合作伙伴的系数
display ""
display _dup(80) "="
display "提取每个合作伙伴的系数"
display _dup(80) "="
display ""
display "主回归已完成，系数存储在 'ppml_main' 中"
display ""
display "要提取每个合作伙伴的post_war系数，有两种方法："
display ""
display "方法1（推荐）: 运行辅助脚本"
display "  do 3extract_partner_coefficients.do"
display "  这个脚本会对每个合作伙伴分别运行回归，提取系数"
display ""
display "方法2: 手动提取交互项系数"
display "  estimates restore ppml_main"
display "  matrix list e(b)"
display "  查找包含 'post_war#partner_id' 的系数"
display ""
display "方法3: 使用margins命令（如果支持）"
display "  estimates restore ppml_main"
display "  margins, dydx(post_war) over(partner_id)"
display ""
display "建议使用方法1，运行以下命令："
display "  do 3extract_partner_coefficients.do"
display ""

display ""
display _dup(80) "="
display "分析完成！"
display _dup(80) "="
display ""
display "主要结果文件:"
display "  - partner_coefficients.dta: 每个合作伙伴的系数"
display "  - partner_coefficients.xlsx: Excel格式结果"
display "  - partner_coefficients.csv: CSV格式结果"
display ""
display "查看完整回归结果:"
display "  estimates replay ppml_main"
display ""
