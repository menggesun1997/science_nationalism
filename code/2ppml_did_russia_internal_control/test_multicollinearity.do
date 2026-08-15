* =============================================================================
* 测试：ppmlhdfe在完全多重共线性情况下的行为
* 测试问题：post_war和absorb(year)完全共线时会发生什么？
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

cd "$CODE/2ppml_did_russia_internal_control"

* 导入数据
use ppml_data.dta, clear

* 确保变量类型正确
destring year paper_count post_war ln_total_vol ln_total_pub, replace
encode partner_country, gen(partner_id)

* 选择一个合作伙伴进行测试（比如第一个）
quietly levelsof partner_id, local(partners)
local test_partner : word 1 of `partners'

display _dup(80) "="
display "测试：ppmlhdfe在完全多重共线性情况下的行为"
display _dup(80) "="
display ""
display "测试合作伙伴ID: `test_partner'"
display ""

* 筛选出测试合作伙伴的数据
keep if partner_id == `test_partner'

display "数据摘要："
tab year post_war
display ""

* =============================================================================
* 测试1：同时使用post_war和absorb(year)
* =============================================================================
display _dup(80) "-"
display "测试1：同时使用post_war和absorb(year)"
display _dup(80) "-"
display ""

capture quietly ppmlhdfe paper_count post_war ln_total_pub, ///
    absorb(year) ///
    offset(ln_total_vol) ///
    vce(robust) ///
    maxiter(10000) ///
    tolerance(1e-8)

if _rc == 0 {
    display "✅ 回归成功（返回码: " _rc "）"
    display ""
    display "系数矩阵："
    matrix list e(b)
    display ""
    display "注意：检查post_war是否被删除（标记为omitted）"
    
    * 检查post_war系数是否存在
    capture matrix b = e(b)
    capture local post_war_coef = b[1, colnumb(b, "post_war")]
    
    if _rc == 0 & !missing(`post_war_coef') {
        display "✅ post_war系数存在: " `post_war_coef'
    }
    else {
        display "⚠️  post_war系数不存在或被删除"
    }
}
else {
    display "❌ 回归失败（返回码: " _rc "）"
    display "错误信息："
    display "  " _rc
}

display ""
display ""

* =============================================================================
* 测试2：只使用post_war（无年份固定效应）
* =============================================================================
display _dup(80) "-"
display "测试2：只使用post_war（无年份固定效应）"
display _dup(80) "-"
display ""

capture quietly ppmlhdfe paper_count post_war ln_total_pub, ///
    offset(ln_total_vol) ///
    vce(robust) ///
    maxiter(10000) ///
    tolerance(1e-8)

if _rc == 0 {
    display "✅ 回归成功（返回码: " _rc "）"
    display ""
    display "系数矩阵："
    matrix list e(b)
    display ""
    
    * 提取post_war系数
    matrix b = e(b)
    local post_war_coef = b[1, colnumb(b, "post_war")]
    display "✅ post_war系数: " `post_war_coef'
}
else {
    display "❌ 回归失败（返回码: " _rc "）"
}

display ""
display ""

* =============================================================================
* 测试3：只使用年份固定效应（无post_war）
* =============================================================================
display _dup(80) "-"
display "测试3：只使用年份固定效应（无post_war）"
display _dup(80) "-"
display ""

capture quietly ppmlhdfe paper_count ln_total_pub, ///
    absorb(year) ///
    offset(ln_total_vol) ///
    vce(robust) ///
    maxiter(10000) ///
    tolerance(1e-8)

if _rc == 0 {
    display "✅ 回归成功（返回码: " _rc "）"
    display ""
    display "系数矩阵："
    matrix list e(b)
    display ""
    display "注意：这里没有post_war系数，因为我们没有包含它"
}
else {
    display "❌ 回归失败（返回码: " _rc "）"
}

display ""
display _dup(80) "="
display "测试完成"
display _dup(80) "="
display ""
display "结论："
display "1. 如果ppmlhdfe自动删除了post_war，你将无法得到post_war的系数"
display "2. 即使回归成功，被删除的变量的系数也无法解释"
display "3. 建议：明确移除absorb(year)，只保留post_war"
















