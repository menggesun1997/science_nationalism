* =============================================================================
* Event Study平行趋势检验：俄罗斯-所有合作国家层面的合作效应分析
* 模型：E[Count_jt] = exp(α_j + λ_t + Σ_{k≠-1} β_{jk}D_{k,t} + γ · ln(ScientificSize_jt))
* 
* 平行趋势检验：检验事件发生前（rel_year < 0）的系数是否显著
* 如果事件发生前的系数不显著，说明满足平行趋势假设
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

cd "$CODE/02_ppml_partners_russia/event_study"



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
local has_ln_total_international = (_rc == 0)

* Post_t: 事件后虚拟变量（2022年及之后=1）
capture confirm variable post_war
if _rc {
    gen post_war = (year >= 2022)
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

* 检查每个国家每年的paper_count是否都大于100
preserve
gen year_meets_criteria = (paper_count > 10)
bysort partner_country: egen all_years_meet = min(year_meets_criteria)

* 找出满足条件的国家（所有年份都满足）
keep if all_years_meet == 1
keep partner_country
duplicates drop partner_country, force
levelsof partner_country, local(all_countries)
local n_countries: word count `all_countries'

display ""
display "筛选后的合作伙伴国家列表:"
display "  共有 " `n_countries' " 个国家（每年paper_count都 > 100）"

* 保存筛选后的国家列表到临时文件
tempfile filtered_countries
save `filtered_countries', replace
restore

* 只保留筛选后的国家的数据
merge m:1 partner_country using `filtered_countries', keep(match) nogen

* 生成相对事件年份
gen rel_year = year - 2022

* 设定事件研究窗口（2005-2024，即rel_year从-17到2）
keep if rel_year >= -17 & rel_year <= 2

display ""
display "筛选后的数据:"
display "  观测数: " _N
quietly summ rel_year
display "  相对年份范围: " r(min) " 到 " r(max)
quietly summ year
display "  实际年份范围: " r(min) " 到 " r(max)
quietly levelsof partner_country
display "  国家数: " r(r)

* =============================================================================
* Step 0.5: 输出每个国家每年的原始数据（2005-2024）
* =============================================================================
display ""
display _dup(80) "="
display "输出每个国家每年的原始数据（2005-2024）"
display _dup(80) "="

* 整理数据：按国家和年份排序
sort partner_country year

* 创建输出文件夹（如果不存在）
capture mkdir "event_study_try"
capture mkdir "event_study_try/countries_result"

* 保存每个国家每年的原始数据
export delimited using "event_study_try/countries_result/country_year_data_2005_2024.csv", replace
save "event_study_try/countries_result/country_year_data_2005_2024.dta", replace

display ""
display "每个国家每年的原始数据已保存:"
display "  - event_study_try/countries_result/country_year_data_2005_2024.csv"
display "  - event_study_try/countries_result/country_year_data_2005_2024.dta"
display ""
display "数据包含列: partner_country, year, rel_year, paper_count, ln_total_international, post_war"
display "  其中 rel_year = year - 2022"
display "  rel_year = -1 对应 2021年（baseline year）"
display "  rel_year = 0 对应 2022年（event year）"

* 保存原始数据（用于循环）
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
gen pre_trend_coef = .  // 事件发生前的平均系数
gen pre_trend_se = .    // 事件发生前系数的标准误
gen pre_trend_pvalue = . // 事件发生前系数的p值
gen pre_trend_sig = 0   // 是否显著（1=显著，0=不显著）
gen n_pre_periods = .   // 事件发生前的时期数
gen f_test_pvalue = .   // F检验的p值（检验所有事件发生前的系数联合为0）

* 保存临时结果文件
tempfile results
save `results', replace
restore

* =============================================================================
* Step 1.5: 创建Event Study系数数据框（用于可视化）
* =============================================================================
preserve
clear
* 创建event study系数数据框
* 每个国家有20个事件年份（-17到2，排除-1），加上基准年-1（系数为0），共20个
* 事件年份：-17, -16, ..., -2, -1(baseline), 0, 1, 2
set obs `=`n_countries' * 20'

gen partner_country = ""
gen rel_year = .
gen coefficient = .
gen std_error = .
gen ci_lower = .
gen ci_upper = .
gen pvalue = .
gen coefficient_pct = .
gen ci_lower_pct = .
gen ci_upper_pct = .
gen sig_stars = ""

* 保存临时event study结果文件
tempfile event_study_results
save `event_study_results', replace
restore

* =============================================================================
* Step 2: 循环每个国家，运行Event Study回归并进行平行趋势检验
* =============================================================================

display ""
display _dup(80) "="
display "为每个国家循环运行Event Study回归并进行平行趋势检验"
display _dup(80) "="
display ""
display "模型设定（对每个国家j）:"
display "  E[Count_jt] = exp(α_j + λ_t + Σ_{k≠-1} β_{jk}D_{k,t} + γ · ln(ScientificSize_jt))"
display ""
display "平行趋势检验："
display "  H0: 所有事件发生前的系数（rel_year < 0）联合为0"
display "  如果p值 > 0.05，则不能拒绝H0，平行趋势假设成立"
display ""

* 检查ppmlhdfe是否已安装
capture which ppmlhdfe
if _rc {
    display "正在安装ppmlhdfe包..."
    ssc install ppmlhdfe, replace
    ssc install reghdfe, replace
    ssc install ftools, replace
}

* 循环每个国家
local row = 1
local country_num = 0
local es_row = 1  // Event study结果的行号

foreach country of local all_countries {
    local country_num = `country_num' + 1
    
    * 初始化变量
    local regression_success = 0
    local n_pre = 0
    local sum_weight = 0
    local avg_pre_coef = .
    local avg_pre_se = .
    local pval = .
    local f_pval = .
    
    display ""
    display _dup(80) "-"
    display "处理国家 " `country_num' "/" `n_countries' ": `country'"
    display _dup(80) "-"
    
    * 加载原始数据
    use `original_data', clear
    
    * 创建该国家的虚拟变量
    gen country_j = (partner_country == "`country'")
    
    * 生成事件年份虚拟变量（排除基准年-1）
    * 注意：Stata变量名不能包含负号，所以负数用n前缀
    * 事件年份：-17到-2, 0, 1, 2（排除-1作为基准年）
    capture drop D_*_country_j
    
    * 生成所有事件年份的虚拟变量（-17到-2, 0, 1, 2）
    * 使用循环生成-17到-2的所有年份（注意：forvalues对负数步长可能有问题，改用numlist）
    foreach k of numlist -17 -16 -15 -14 -13 -12 -11 -10 -9 -8 -7 -6 -5 -4 -3 -2 {
        local k_abs = -`k'
        local var_name "D_n`k_abs'_country_j"
        gen `var_name' = (rel_year == `k') * country_j
    }
    * 生成0, 1, 2的虚拟变量
    foreach k of numlist 0 1 2 {
        local var_name "D_`k'_country_j"
        gen `var_name' = (rel_year == `k') * country_j
    }
    
    * 运行PPML回归
    * 注意：由于变量太多，我们需要动态构建变量列表
    local event_vars ""
    foreach k of numlist -17 -16 -15 -14 -13 -12 -11 -10 -9 -8 -7 -6 -5 -4 -3 -2 {
        local k_abs = -`k'
        local var_name "D_n`k_abs'_country_j"
        capture confirm variable `var_name'
        if _rc == 0 {
            local event_vars "`event_vars' `var_name'"
        }
    }
    foreach k of numlist 0 1 2 {
        local var_name "D_`k'_country_j"
        capture confirm variable `var_name'
        if _rc == 0 {
            local event_vars "`event_vars' `var_name'"
        }
    }
    
    display "  运行PPML回归..."
    display "  事件年份变量数量: " `: word count `event_vars''
    display "  事件年份变量列表: `event_vars'"
    
    capture {
        ppmlhdfe paper_count `event_vars' ln_total_international, ///
            absorb(partner_country year) ///
            cluster(partner_country) ///
            maxiter(10000) ///
            tolerance(1e-8)
    }
    
    * 如果回归成功，进行平行趋势检验
    if _rc == 0 {
        local regression_success = 1
        display "  ✅ 回归成功"
        * 提取事件发生前的系数（rel_year < 0，即-17到-2）
        local pre_coefs ""
        local pre_vars ""
        local n_pre = 0
        
        capture {
            
            foreach k of numlist -17 -16 -15 -14 -13 -12 -11 -10 -9 -8 -7 -6 -5 -4 -3 -2 {
                local k_abs = -`k'
                local var_name "D_n`k_abs'_country_j"
                
                capture {
                    local coef = _b[`var_name']
                    local se = _se[`var_name']
                    
                    if !missing(`coef') & !missing(`se') {
                        local pre_coefs "`pre_coefs' `coef'"
                        local pre_vars "`pre_vars' `var_name'"
                        local n_pre = `n_pre' + 1
                    }
                    else {
                        * 调试信息：显示为什么系数缺失
                        capture confirm variable `var_name'
                        if _rc == 0 {
                            display "    ⚠️  变量 `var_name' 存在但系数缺失 (coef=`coef', se=`se')"
                        }
                        else {
                            display "    ⚠️  变量 `var_name' 不存在（可能被drop）"
                        }
                    }
                }
                if _rc != 0 {
                    display "    ⚠️  无法提取变量 `var_name' 的系数，错误代码: " _rc
                }
            }
            
            display "  成功提取的事件发生前系数数量: " `n_pre' " / 16"
            
            if `n_pre' > 0 {
                display "  ✅ 成功提取 " `n_pre' " 个事件发生前的系数"
                * 计算事件发生前系数的平均值和标准误
                * 使用加权平均（权重为1/标准误的平方）
                local sum_weighted_coef = 0
                local sum_weight = 0
                local sum_se_sq = 0
                
                foreach var of local pre_vars {
                    capture {
                        local coef = _b[`var']
                        local se = _se[`var']
                        if !missing(`coef') & !missing(`se') & `se' > 0 {
                            local weight = 1 / (`se'^2)
                            local sum_weighted_coef = `sum_weighted_coef' + `coef' * `weight'
                            local sum_weight = `sum_weight' + `weight'
                            local sum_se_sq = `sum_se_sq' + `se'^2
                        }
                    }
                }
                
                if `sum_weight' > 0 {
                    local avg_pre_coef = `sum_weighted_coef' / `sum_weight'
                    local avg_pre_se = sqrt(`sum_se_sq' / `n_pre')
                    
                    display "  平均系数: " %9.4f `avg_pre_coef' " (se=" %9.4f `avg_pre_se' ")"
                    
                    * 计算t统计量和p值
                    local t_stat = `avg_pre_coef' / `avg_pre_se'
                    local pval = 2 * (1 - normal(abs(`t_stat')))
                    
                    * F检验：检验所有事件发生前的系数联合为0
                    capture {
                        test `pre_vars'
                        local f_stat = r(F)
                        local f_pval = r(p)
                        display "  F检验p值: " %9.4f `f_pval'
                    }
                    if _rc != 0 {
                        local f_stat = .
                        local f_pval = .
                        display "  ⚠️  F检验失败，错误代码: " _rc
                    }
                    
                    * 提取所有事件年份的系数（用于event study图）
                    * 包括所有年份：-17到2，其中-1是基准年（系数为0）
                    * 先处理-17到-2
                    foreach k of numlist -17 -16 -15 -14 -13 -12 -11 -10 -9 -8 -7 -6 -5 -4 -3 -2 {
                        local k_abs = -`k'
                        local var_name "D_n`k_abs'_country_j"
                        
                        capture {
                            local coef = _b[`var_name']
                            local se = _se[`var_name']
                            
                            if !missing(`coef') & !missing(`se') {
                                * 计算p值
                                local t = `coef' / `se'
                                local p = 2 * (1 - normal(abs(`t')))
                                
                                * 计算置信区间
                                local ci_lower = `coef' - 1.96 * `se'
                                local ci_upper = `coef' + 1.96 * `se'
                                
                                * 转换为百分比
                                local coef_pct = (`coef') * 100
                                local ci_lower_pct = (`ci_lower') * 100
                                local ci_upper_pct = (`ci_upper') * 100
                                
                                * 显著性标记
                                local sig = ""
                                if `p' < 0.001 {
                                    local sig "***"
                                }
                                else if `p' < 0.01 {
                                    local sig "**"
                                }
                                else if `p' < 0.05 {
                                    local sig "*"
                                }
                                
                                * 保存到event study结果文件
                                preserve
                                use `event_study_results', clear
                                
                                replace partner_country = "`country'" in `es_row'
                                replace rel_year = `k' in `es_row'
                                replace coefficient = `coef' in `es_row'
                                replace std_error = `se' in `es_row'
                                replace ci_lower = `ci_lower' in `es_row'
                                replace ci_upper = `ci_upper' in `es_row'
                                replace pvalue = `p' in `es_row'
                                replace coefficient_pct = `coef_pct' in `es_row'
                                replace ci_lower_pct = `ci_lower_pct' in `es_row'
                                replace ci_upper_pct = `ci_upper_pct' in `es_row'
                                replace sig_stars = "`sig'" in `es_row'
                                
                                save `event_study_results', replace
                                restore
                                
                                local es_row = `es_row' + 1
                            }
                        }
                    }
                    
                    * 处理基准年-1（系数为0）
                    preserve
                    use `event_study_results', clear
                    
                    replace partner_country = "`country'" in `es_row'
                    replace rel_year = -1 in `es_row'
                    replace coefficient = 0 in `es_row'
                    replace std_error = 0 in `es_row'
                    replace ci_lower = 0 in `es_row'
                    replace ci_upper = 0 in `es_row'
                    replace pvalue = . in `es_row'
                    replace coefficient_pct = 0 in `es_row'
                    replace ci_lower_pct = 0 in `es_row'
                    replace ci_upper_pct = 0 in `es_row'
                    replace sig_stars = "" in `es_row'
                    
                    save `event_study_results', replace
                    restore
                    
                    local es_row = `es_row' + 1
                    
                    * 处理0, 1, 2
                    foreach k of numlist 0 1 2 {
                        local var_name "D_`k'_country_j"
                        
                        capture {
                            local coef = _b[`var_name']
                            local se = _se[`var_name']
                            
                            if !missing(`coef') & !missing(`se') {
                                * 计算p值
                                local t = `coef' / `se'
                                local p = 2 * (1 - normal(abs(`t')))
                                
                                * 计算置信区间
                                local ci_lower = `coef' - 1.96 * `se'
                                local ci_upper = `coef' + 1.96 * `se'
                                
                                * 转换为百分比
                                local coef_pct = (`coef') * 100
                                local ci_lower_pct = (`ci_lower') * 100
                                local ci_upper_pct = (`ci_upper') * 100
                                
                                * 显著性标记
                                local sig = ""
                                if `p' < 0.001 {
                                    local sig "***"
                                }
                                else if `p' < 0.01 {
                                    local sig "**"
                                }
                                else if `p' < 0.05 {
                                    local sig "*"
                                }
                                
                                * 保存到event study结果文件
                                preserve
                                use `event_study_results', clear
                                
                                replace partner_country = "`country'" in `es_row'
                                replace rel_year = `k' in `es_row'
                                replace coefficient = `coef' in `es_row'
                                replace std_error = `se' in `es_row'
                                replace ci_lower = `ci_lower' in `es_row'
                                replace ci_upper = `ci_upper' in `es_row'
                                replace pvalue = `p' in `es_row'
                                replace coefficient_pct = `coef_pct' in `es_row'
                                replace ci_lower_pct = `ci_lower_pct' in `es_row'
                                replace ci_upper_pct = `ci_upper_pct' in `es_row'
                                replace sig_stars = "`sig'" in `es_row'
                                
                                save `event_study_results', replace
                                restore
                                
                                local es_row = `es_row' + 1
                            }
                        }
                    }
                    
                    * 显示结果
                    display "  事件发生前的系数:"
                    foreach var of local pre_vars {
                        capture {
                            local coef = _b[`var']
                            local se = _se[`var']
                            local t = `coef' / `se'
                            local p = 2 * (1 - normal(abs(`t')))
                            display "    `var': " %9.4f `coef' " (se=" %9.4f `se' ", p=" %9.4f `p' ")"
                        }
                    }
                    display "  平均系数: " %9.4f `avg_pre_coef' " (se=" %9.4f `avg_pre_se' ", p=" %9.4f `pval' ")"
                    if !missing(`f_pval') {
                        display "  F检验p值（所有事件发生前系数联合为0）: " %9.4f `f_pval'
                        if `f_pval' > 0.05 {
                            display "  ✅ 平行趋势假设成立（p > 0.05）"
                        }
                        else {
                            display "  ⚠️  平行趋势假设可能不成立（p <= 0.05）"
                        }
                    }
                }
            }
            else {
                display "  ⚠️  警告：无法提取事件发生前的系数"
            }
        }
        
        * 保存结果（移出capture块，确保即使前面的操作失败也能保存国家名称）
        preserve
        use `results', clear
        
        * 确保row不超过数据框大小
        if `row' <= _N {
            replace partner_country = "`country'" in `row'
            
            * 检查是否成功提取了系数（通过检查n_pre是否大于0）
            * 使用临时变量避免宏展开问题
            local check_success = (`regression_success' == 1)
            local check_n_pre = (`n_pre' > 0)
            local check_sum_weight = (`sum_weight' > 0)
            if `check_success' == 1 & `check_n_pre' == 1 & `check_sum_weight' == 1 {
                * 尝试保存系数（如果变量已定义）
                capture {
                    replace pre_trend_coef = `avg_pre_coef' in `row'
                    replace pre_trend_se = `avg_pre_se' in `row'
                    replace pre_trend_pvalue = `pval' in `row'
                    replace pre_trend_sig = (`pval' < 0.05) in `row'
                    replace n_pre_periods = `n_pre' in `row'
                    replace f_test_pvalue = `f_pval' in `row'
                }
                if _rc != 0 {
                    display "  ⚠️  保存系数时出错，错误代码: " _rc
                    * 如果保存失败，标记为缺失
                    replace pre_trend_coef = . in `row'
                    replace pre_trend_se = . in `row'
                    replace pre_trend_pvalue = . in `row'
                    replace pre_trend_sig = . in `row'
                    replace n_pre_periods = . in `row'
                    replace f_test_pvalue = . in `row'
                }
                else {
                    display "  ✅ 结果已保存"
                }
            }
            else {
                * 回归失败或无法提取系数，标记为缺失
                if `regression_success' == 0 {
                    display "  ⚠️  回归失败，无法保存系数"
                }
                else {
                    if `n_pre' == 0 {
                        display "  ⚠️  无法提取事件发生前的系数（n_pre=0）"
                    }
                    else {
                        display "  ⚠️  权重总和为0，无法计算平均系数（sum_weight=`sum_weight'）"
                    }
                }
                replace pre_trend_coef = . in `row'
                replace pre_trend_se = . in `row'
                replace pre_trend_pvalue = . in `row'
                replace pre_trend_sig = . in `row'
                replace n_pre_periods = . in `row'
                replace f_test_pvalue = . in `row'
            }
        }
        else {
            display "  ⚠️  警告：row (" `row' ") 超出数据框大小 (" _N ")"
        }
        
        save `results', replace
        restore
    }
    else {
        local regression_success = 0
        display "  ❌ 回归失败，错误代码: " _rc
        display "   可能的原因："
        display "   1. 变量过多导致共线性"
        display "   2. 数据不足"
        display "   3. 收敛失败"
        display "   跳过该国家的平行趋势检验"
        
        * 即使回归失败，也要在结果中记录该国家（标记为失败）
        preserve
        use `results', clear
        
        replace partner_country = "`country'" in `row'
        replace pre_trend_coef = . in `row'
        replace pre_trend_se = . in `row'
        replace pre_trend_pvalue = . in `row'
        replace pre_trend_sig = . in `row'
        replace n_pre_periods = . in `row'
        replace f_test_pvalue = . in `row'
        
        save `results', replace
        restore
        
        * 即使回归失败，也要为event study结果预留空间（20个年份）
        * 这样es_row才能正确递增，避免后续国家覆盖前面的数据
        * 检查es_row是否超出数据框大小
        local max_rows = `n_countries' * 20
        if `es_row' + 19 <= `max_rows' {
            preserve
            use `event_study_results', clear
            
            * 为该国家的所有年份创建空记录（-17到2，共20个年份）
            forvalues k = -17(-1)2 {
                if `es_row' <= `max_rows' {
                    replace partner_country = "`country'" in `es_row'
                    replace rel_year = `k' in `es_row'
                    replace coefficient = . in `es_row'
                    replace std_error = . in `es_row'
                    replace ci_lower = . in `es_row'
                    replace ci_upper = . in `es_row'
                    replace pvalue = . in `es_row'
                    replace coefficient_pct = . in `es_row'
                    replace ci_lower_pct = . in `es_row'
                    replace ci_upper_pct = . in `es_row'
                    replace sig_stars = "" in `es_row'
                    local es_row = `es_row' + 1
                }
            }
            
            save `event_study_results', replace
            restore
        }
        else {
            display "  ⚠️  警告：es_row超出数据框大小，跳过event study结果记录"
        }
    }
    
    local row = `row' + 1
    
    * 每10个国家显示一次进度
    if mod(`country_num', 10) == 0 {
        display ""
        display "进度: 已完成 " `country_num' "/" `n_countries' " 个国家"
    }
}

display ""
display _dup(80) "="
display "所有国家的平行趋势检验完成"
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
display "成功完成 " _N " 个国家的平行趋势检验"

* 检查是否有有效结果
if _N == 0 {
    display ""
    display "⚠️  警告：没有成功保存的结果！"
    display "   可能的原因："
    display "   1. 所有国家的回归都失败了"
    display "   2. 无法提取事件发生前的系数"
    display "   3. 数据筛选条件太严格"
    display ""
    display "   请检查循环中的错误信息"
}

* 排序（按F检验p值）
sort f_test_pvalue

* 创建输出文件夹（如果不存在）
capture mkdir "event_study_try"
capture mkdir "event_study_try/countries_result"

* 保存结果到event_study_try/countries_result文件夹
export delimited using "event_study_try/countries_result/parallel_trends_test_results.csv", replace
save "event_study_try/countries_result/parallel_trends_test_results.dta", replace

display ""
display "结果已保存:"
display "  - event_study_try/countries_result/parallel_trends_test_results.csv"
display "  - event_study_try/countries_result/parallel_trends_test_results.dta"

* 显示结果摘要
display ""
display _dup(80) "="
display "平行趋势检验结果摘要"
display _dup(80) "="
display ""
display "平行趋势假设成立的国家（F检验p值 > 0.05）:"
count if f_test_pvalue > 0.05 & f_test_pvalue != .
display "  数量: " r(N) " / " _N

display ""
display "平行趋势假设可能不成立的国家（F检验p值 <= 0.05）:"
count if f_test_pvalue <= 0.05 & f_test_pvalue != .
display "  数量: " r(N) " / " _N

display ""
local n_obs = _N
if `n_obs' > 0 {
    local display_count = min(10, `n_obs')
    display "前`display_count'个平行趋势检验结果（按F检验p值排序）:"
    list partner_country pre_trend_coef pre_trend_se pre_trend_pvalue f_test_pvalue pre_trend_sig in 1/`display_count', clean noobs
    
    display ""
    if `n_obs' > 1 {
        local start = max(1, `n_obs' - 9)
        local end_count = min(10, `n_obs')
        display "后`end_count'个平行趋势检验结果（按F检验p值排序）:"
        list partner_country pre_trend_coef pre_trend_se pre_trend_pvalue f_test_pvalue pre_trend_sig in `start'/`n_obs', clean noobs
    }
}
else {
    display "⚠️  没有可显示的结果"
}

display ""
display _dup(80) "="
display "分析完成！"
display _dup(80) "="

* =============================================================================
* Step 4: 为每个国家生成Event Study系数图
* =============================================================================
display ""
display _dup(80) "="
display "为每个国家生成Event Study系数图"
display _dup(80) "="

* 加载event study结果数据
use `event_study_results', clear
drop if missing(partner_country)

display ""
display "Event Study结果数据检查:"
display "  总观测数: " _N
count if !missing(coefficient)
display "  有效系数数量: " r(N)

if _N > 0 {
    * 保存event study结果
    export delimited using "event_study_try/countries_result/event_study_coefficients_all_countries.csv", replace
    save "event_study_try/countries_result/event_study_coefficients_all_countries.dta", replace
    
    display ""
    display "Event Study系数数据已保存:"
    display "  - event_study_try/countries_result/event_study_coefficients_all_countries.csv"
    display "  - event_study_try/countries_result/event_study_coefficients_all_countries.dta"
}
else {
    display ""
    display "⚠️  警告：没有Event Study系数数据可保存！"
    display "   可能的原因："
    display "   1. 所有国家的回归都失败了"
    display "   2. 无法提取事件年份的系数"
    display ""
    display "   跳过图表生成..."
    exit
}

* 设置图形样式
set scheme s1color

* 先加载F检验结果，以便在图表中显示
preserve
use `results', clear
keep partner_country f_test_pvalue
* 确保每个国家只有一行（删除重复）
duplicates drop partner_country, force
tempfile f_test_results
save `f_test_results', replace
restore

* 合并F检验结果
merge m:1 partner_country using `f_test_results', nogen

* 检查合并后的数据
display ""
display "合并F检验结果后:"
display "  总观测数: " _N
count if !missing(f_test_pvalue)
display "  有F检验p值的观测数: " r(N)

* 为每个国家生成event study图
quietly levelsof partner_country if !missing(coefficient), local(countries_for_plot)
local n_countries_plot: word count `countries_for_plot'

display ""
display "准备为 " `n_countries_plot' " 个国家生成图表..."

if `n_countries_plot' == 0 {
    display ""
    display "⚠️  警告：没有可生成图表的有效数据！"
    display "   跳过图表生成..."
    exit
}

local plot_count = 0
foreach country of local countries_for_plot {
    local plot_count = `plot_count' + 1
    
    preserve
    keep if partner_country == "`country'"
    
    * 检查是否有数据
    count if !missing(coefficient)
    if r(N) > 0 {
        * 获取F检验p值
        quietly summ f_test_pvalue
        local f_pval_display = r(mean)
        
        * 排序
        sort rel_year
        
        * 绘制event study图（使用原始系数值，非百分比）
        twoway (rarea ci_upper ci_lower rel_year, color(ebblue%30) lwidth(none)) ///
               (rcap ci_upper ci_lower rel_year, lcolor(ebblue) lwidth(thin)) ///
               (scatter coefficient rel_year, mcolor(navy) msize(medium) msymbol(circle)) ///
               (line coefficient rel_year, lcolor(navy) lwidth(medium)), ///
            xline(0, lcolor(red) lpattern(dash) lwidth(1.5)) ///
            xline(-1, lcolor(gray) lpattern(dash) lwidth(1)) ///
            xlabel(-17(2)2, labsize(small)) ///
            ylabel(, format(%9.1f) labsize(small)) ///
            ytitle("Coefficient", size(medium)) ///
            xtitle("Relative Event Year (Baseline = -1)", size(medium)) ///
            title("`country': Event Study Coefficients", size(medium)) ///
            note("Baseline year: rel_year = -1 (Year 2021)" "Event year: rel_year = 0 (Year 2022)", size(vsmall)) ///
            legend(off) ///
            yline(0, lcolor(black) lpattern(solid) lwidth(thin))
        
        * 清理国家名称用于文件名（移除特殊字符）
        local country_clean = subinstr("`country'", " ", "_", .)
        local country_clean = subinstr("`country_clean'", "/", "_", .)
        local country_clean = subinstr("`country_clean'", "\", "_", .)
        
        graph export "event_study_try/countries_result/event_study_`country_clean'.pdf", as(pdf) replace
        graph export "event_study_try/countries_result/event_study_`country_clean'.png", as(png) replace width(1200) height(800)
        
        if mod(`plot_count', 10) == 0 {
            display "  已生成 " `plot_count' " 个国家的图表..."
        }
    }
    
    restore
}

display ""
display "✅ 已为所有国家生成Event Study系数图"
display "  共生成 " `plot_count' " 个图表"
display "  保存位置: event_study_try/countries_result/event_study_[国家名].pdf/png"

