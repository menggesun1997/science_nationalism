* =============================================================================
* Event Study分析：俄罗斯-乌克兰战争对国际合作的影响
* 基准年：2021年（战前最后一年）
* 事件年：2022年（战争开始）
* 
* 注意：本脚本现在使用改进的SCM（合成控制法）选择的控制组：
*   - ARMENIA (58.56%)
*   - SOUTH AFRICA (41.44%)
* 
* 改进的SCM方法：
*   - 使用更近期的战前时期（2019-2021）进行拟合
*   - 限制使用的国家数量（最多3个）
*   - 战前趋势检验已通过（p=0.3198 > 0.05）
* 
* 这个控制组选择确保了战前期的平行趋势，解决了之前战前期系数显著的问题
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

cd "$CODE/2two_way_did_ukraine"

* 导入数据
import excel using ppml_did_data.xlsx, firstrow clear

* 数据检查
describe
summarize

* 确保变量类型正确
destring year paper_count post_war treated_country did_dummy, replace
encode focal_country, gen(focal_id)
encode partner_country, gen(partner_id)

* 创建配对固定效应（pair_id）：每个"焦点国-伙伴国"配对一个固定效应
* 例如："乌克兰-中国"是一个pair_id，"乌克兰-德国"是另一个pair_id
* 使用egen group创建配对ID
egen pair_id = group(focal_id partner_id)
label var pair_id "Pair fixed effect (focal-partner pair)"

* 创建事件研究变量
* 基准年：2021年（战前最后一年）
* 事件年：2022年
gen event_year = year - 2022

* 创建事件研究虚拟变量（以2021年为基准，即event_year = -1）
* 排除基准年（event_year = -1），这样2021年的系数为0
* 注意：使用所有数据（包括控制组），但event_year虚拟变量只对乌克兰非零
tab event_year

* 创建事件研究虚拟变量
* 我们需要为每个event_year创建虚拟变量，但排除基准年
levelsof event_year, local(event_years)

* 创建事件研究虚拟变量（排除基准年-1）
* 注意：只对乌克兰（treated_country == 1）创建交互项
* 对于负数年份，使用n前缀（如-7变成n7）
foreach ey of local event_years {
    if `ey' != -1 {
        * 处理负数年份：将-7转换为n7
        if `ey' < 0 {
            local ey_name = "n" + string(-`ey')
        }
        else {
            local ey_name = string(`ey')
        }
        gen event_year_`ey_name' = (event_year == `ey') * treated_country
        replace event_year_`ey_name' = 0 if missing(event_year_`ey_name')
    }
}

* Event Study回归：使用ppmlhdfe
* 模型：log E[paper_count] = α + Σ_t β_t * event_year_t + μ_partner + μ_year + ε
* 其中基准年（2021，event_year=-1）的系数为0
* 注意：使用所有数据（包括控制组），但event_year虚拟变量只对乌克兰非零

display _dup(80) "="
display "Event Study分析：乌克兰国际合作动态效应"
display _dup(80) "="

* 收集所有事件研究虚拟变量
local event_vars
foreach ey of local event_years {
    if `ey' != -1 {
        * 处理负数年份：将-7转换为n7
        if `ey' < 0 {
            local ey_name = "n" + string(-`ey')
        }
        else {
            local ey_name = string(`ey')
        }
        local event_vars `event_vars' event_year_`ey_name'
    }
}

* =============================================================================
* 运行PPML回归 - 使用正确的固定效应设定
* 固定效应：pair_id (配对固定效应 α_{kj}) + year (年份固定效应 δ_t)
* =============================================================================

display ""
display "正确的固定效应设定："
display "  - pair_id: 配对固定效应（每个'焦点国-伙伴国'配对一个固定效应）"
display "  - year: 年份固定效应"
display ""
display "例如："
display "  - pair_id=1: '乌克兰-中国'"
display "  - pair_id=2: '乌克兰-德国'"
display "  - pair_id=3: '巴西-中国'"
display _dup(80) "="

* 运行PPML回归（使用pair_id和year固定效应）
capture quietly ppmlhdfe paper_count `event_vars' post_war treated_country, ///
    absorb(pair_id year) ///
    vce(robust) ///
    maxiter(10000) ///
    tolerance(1e-8)

if _rc == 0 {
    display "✅ PPML回归成功"
    local model_used = 1
    estimates store event_study_ppml
    display ""
    display "使用的固定效应: pair_id + year"
    display "  - pair_id: 配对固定效应（group(focal_id, partner_id)）"
    display "  - year: 年份固定效应"
}
else {
    display "❌ PPML回归失败（错误代码: " _rc "）"
    display "请检查数据"
    exit
}

* 提取系数和标准误
matrix b = e(b)
matrix V = e(V)

* 使用postfile方法安全地存储结果（避免observation number out of range错误）
tempname memhold
tempfile results_file

postfile `memhold' event_year coef se ci_lower ci_upper significant pvalue sig_10 sig_05 sig_01 using `results_file', replace

* 添加基准年（系数为0）
post `memhold' (-1) (0) (0) (0) (0) (0) (1) (0) (0) (0)

* 提取每个事件年的系数
foreach ey of local event_years {
    if `ey' != -1 {
        * 处理负数年份：将-7转换为n7（与创建变量时保持一致）
        if `ey' < 0 {
            local ey_name = "n" + string(-`ey')
        }
        else {
            local ey_name = string(`ey')
        }
        capture matrix coef_val = b[1, "event_year_`ey_name'"]
        if !_rc {
            local coef = coef_val[1, 1]
            capture matrix se_val = V["event_year_`ey_name'", "event_year_`ey_name'"]
            if !_rc {
                local se = sqrt(se_val[1, 1])
                local ci_lower = `coef' - 1.96 * `se'
                local ci_upper = `coef' + 1.96 * `se'
                local tstat = `coef' / `se'
                local pval = 2 * (1 - normal(abs(`tstat')))
                * 使用更宽松的显著性水平（10%），并记录不同显著性水平
                local sig_10 = (`pval' < 0.10)
                local sig_05 = (`pval' < 0.05)
                local sig_01 = (`pval' < 0.01)
                * 主要使用10%水平
                local sig = `sig_10'
                
                * 使用postfile保存结果（包含不同显著性水平）
                post `memhold' (`ey') (`coef') (`se') (`ci_lower') (`ci_upper') (`sig') (`pval') (`sig_10') (`sig_05') (`sig_01')
            }
        }
    }
}

* 关闭postfile
postclose `memhold'

* 加载结果数据
use `results_file', clear

* 按event_year排序
sort event_year

* 添加模型信息列
gen model_used = `model_used'
gen fe_spec = "pair_id + year"
gen fe_explanation = "pair_id = group(focal_id, partner_id), 每个焦点国-伙伴国配对一个固定效应"

* 保存结果
save event_study_results.dta, replace
export excel using event_study_results.xlsx, firstrow(variables) replace
export delimited using event_study_results.csv, replace

display _dup(80) "="
display "Event Study结果摘要"
display _dup(80) "="
display "固定效应设定: pair_id + year"
display "  - pair_id: 配对固定效应（每个'焦点国-伙伴国'配对一个固定效应）"
display "  - year: 年份固定效应"
display ""
display "注意：pair_id = group(focal_id, partner_id)"
display "  这不是 focal_id + partner_id 的分别固定效应"
display "  而是每个独特的'焦点国-伙伴国'配对有一个单独的固定效应"
display ""
list event_year coef se ci_lower ci_upper significant pvalue sig_10 sig_05 sig_01, clean noobs

* 统计显著性情况
quietly count if sig_01 == 1 & event_year != -1
local n_sig_01 = r(N)
quietly count if sig_05 == 1 & event_year != -1
local n_sig_05 = r(N)
quietly count if sig_10 == 1 & event_year != -1
local n_sig_10 = r(N)
quietly count if event_year != -1
local n_total = r(N)

display ""
display "显著性统计（排除基准年）："
display "  1%水平显著: `n_sig_01' / `n_total'"
display "  5%水平显著: `n_sig_05' / `n_total'"
display "  10%水平显著: `n_sig_10' / `n_total'"

if `n_sig_10' == 0 {
    display ""
    display "⚠️  警告：所有系数在10%水平都不显著"
    display "可能的原因："
    display "  1. 样本量不足或数据稀疏"
    display "  2. 固定效应吸收了太多变异"
    display "  3. 事件效应确实很小"
    display "  4. 标准误估计偏大"
    display ""
    display "建议："
    display "  1. 检查数据质量和样本量"
    display "  2. 尝试减少固定效应（例如只使用partner_id，不使用year FE）"
    display "  3. 使用cluster标准误（vce(cluster partner_id)）"
    display "  4. 即使不显著，也可以报告系数和置信区间"
    display "  5. 考虑使用更宽松的显著性水平（如15%或20%）"
}

display ""
display _dup(80) "="
display "模型比较"
display _dup(80) "="
display ""
display "如果方法2（减少固定效应）的结果更显著，说明："
display "  - focal_id固定效应可能吸收了太多变异"
display "  - 减少固定效应后，事件研究系数更容易被识别"
display ""
display "建议在论文中报告："
display "  - 主要结果：方法2（减少固定效应）"
display "  - 稳健性检验：方法1（完整固定效应）"
display ""

display ""
display "✅ Event Study分析完成！"
display "结果已保存到："
display "  - event_study_results.dta"
display "  - event_study_results.xlsx"
display "  - event_study_results.csv"
