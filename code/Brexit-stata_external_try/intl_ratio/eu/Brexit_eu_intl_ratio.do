clear
* 导入Excel数据

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

import excel "$CODE/Brexit-stata_external_try/brexit_non_eu.xlsx", sheet("Sheet1") firstrow clear

encode Country, gen(id)
xtset id Year
gen log_pub_total = log(pub_total + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

* 保存处理后的数据集，以便后续使用
save "$CODE/Brexit-stata_external_try/intl_ratio/eu/processed_data.dta", replace	

* 对eu进行合成控制分析，处理年份为2016年
synth intl_ratio ///
    log_pub_total log_gdp_per_capita  log_rp RD /// 这些变量会使用xperiod限定范围内的变量数据
    intl_ratio(2015) intl_ratio(2013) intl_ratio(2012) intl_ratio(2010) intl_ratio(2010(1)2015), /// 结果变量的滞后值
    trunit(6) trperiod(2016) ///
    counit(1 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 20) ///
    xperiod(2008(1)2015) ///只对未指定具体时期的预测变量生效
    nested allopt ///
    keep(eu_synth_results, replace)

* 保存eu的结果
use eu_synth_results, clear
rename _time Year
rename _Y_treated eu_actual
rename _Y_synthetic eu_synthetic
gen eu_gap = eu_actual - eu_synthetic

* 计算处理前的RMSPE (2008-2015)
gen sq_gap = eu_gap^2 if Year <= 2015
sum sq_gap
local pre_mspe = r(mean)
local pre_rmspe = sqrt(`pre_mspe')

* 计算处理后的RMSPE (2016-2023)
replace sq_gap = eu_gap^2 if Year >= 2016 & Year <= 2023
sum sq_gap if Year >= 2016
local post_mspe = r(mean)
local post_rmspe = sqrt(`post_mspe')

* 计算比率
local rmspe_ratio = `post_rmspe' / `pre_rmspe'
local rmspe_ratio_display = string(`rmspe_ratio', "%9.3f")

* 计算处理后期的平均效应
sum eu_gap if Year >= 2016
local eu_avg_effect = r(mean)
local eu_avg_effect_display = string(`eu_avg_effect', "%9.3f")

* 添加W权重
matrix W = e(W_weights)

* 添加V矩阵
matrix V = e(V_matrix)
svmat V, names(v_weight)
* 重命名V矩阵的列名为实际变量名
rename v_weight1 log_gdp_per_capita
rename v_weight2 log_rp
rename v_weight3 RD

save "$CODE/Brexit-stata_external_try/intl_ratio/eu/eu_synth_results.dta", replace

* 绘制eu真实数据和合成数据对比图
twoway (line eu_actual Year, lcolor(blue) lwidth(medthick)) ///
       (line eu_synthetic Year, lcolor(red) lwidth(medthick) lpattern(dash)), ///
       xline(2016, lpattern(dash) lcolor(gray)) ///
       legend(order(1 "EU Actual" 2 "EU Synthetic") position(6) rows(1)) ///
       title("EU: Actual vs Synthetic Control", size(large)) ///
	   subtitle("Average Treatment Effect: `eu_avg_effect_display' Post-Pre Effect Ratio: `rmspe_ratio_display'") ///
       xtitle("Year", size(medium)) ytitle("the ratio of international pulications", size(medium)) ///
       xlabel(#10) ///
       graphregion(color(white)) bgcolor(white) ///
       name(eu_comparison, replace)
graph export "$CODE/Brexit-stata_external_try/intl_ratio/eu/eu_actual_vs_synthetic.png", width(1200) height(800) replace


	
* 假设每个控制组国家都是处理组，逐个遍历进行合成控制
foreach country_code of numlist 1 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 20 {
    * 显示进度
    di "Processing country code: `country_code'"
	
	* 使用保存的处理后数据集，而不是每次都重新导入
    use "$CODE/Brexit-stata_external_try/intl_ratio/eu/processed_data.dta", clear
    xtset id Year  // 确保面板数据结构设置正确
 
    * 创建控制组列表，排除当前处理单位和EU(6)
    local control_list ""
    foreach ctrl of numlist 1 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 20 {
        if `ctrl' != `country_code' & `ctrl' != 6 & `ctrl' != 19 {
            local control_list "`control_list' `ctrl'"
        }
    }
	
	* 对于问题国家，尝试使用更简单的拟合模型
	if `country_code' == 5 | `country_code' == 17 |`country_code' == 20 {
	  	di "Using simplified model for problematic country code `country_code'"
		capture noisily {
			synth intl_ratio log_pub_total log_gdp_per_capita log_rp RD, ///
				  trunit(`country_code') trperiod(2016) ///
				  counit(`control_list') ///
				  xperiod(2005(1)2015) ///
				  nested allopt ///
				  keep("$CODE/Brexit-stata_external_try/intl_ratio/eu/synth_`country_code'", replace)
		}
	}
	* 对其他国家进行合成控制分析
	else {
		capture noisily {
			synth intl_ratio log_pub_total log_gdp_per_capita log_rp RD intl_ratio(2015) intl_ratio(2013) intl_ratio(2012) intl_ratio(2010) intl_ratio(2010(1)2015), ///
				  trunit(`country_code') trperiod(2016) ///
				  counit(`control_list') ///
				  xperiod(2008(1)2015) 
				  nested ///
				  keep("$CODE/Brexit-stata_external_try/intl_ratio/eu/synth_`country_code'", replace)
		}
	}
	
	* 处理结果并创建gap文件
    capture {
        use "$CODE/Brexit-stata_external_try/intl_ratio/eu/synth_`country_code'", clear
        rename _time Year
        gen gap_`country_code' = _Y_treated - _Y_synthetic
        keep Year gap_`country_code'
        drop if missing(Year)
        save "$CODE/Brexit-stata_external_try/intl_ratio/eu/gap_`country_code'", replace
    }
}

* 合并所有gap文件和eu结果，计算RMSPE和比率
use "$CODE/Brexit-stata_external_try/intl_ratio/eu/gap_1", clear
foreach country_code of numlist 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 20 {
    capture {
        merge 1:1 Year using "$CODE/Brexit-stata_external_try/intl_ratio/eu/gap_`country_code'", nogenerate
    }
}
merge 1:1 Year using "$CODE/Brexit-stata_external_try/intl_ratio/eu/eu_synth_results.dta", nogenerate

* 计算eu的平均处理效应（2016年及以后）
sum eu_gap if Year >= 2016
local eu_avg_effect = r(mean)
local eu_avg_effect_display = string(`eu_avg_effect', "%5.3f")

* 检查变量是否已存在，如果存在则删除
capture drop pre_sq_error_* pre_mspe_* pre_rmspe_* post_sq_error_* post_mspe_* post_rmspe_* post_pre_ratio_*

* 计算eu的RMSPE
gen pre_sq_error_eu = eu_gap^2 if Year < 2016
egen pre_mspe_eu = mean(pre_sq_error_eu)
gen pre_rmspe_eu = sqrt(pre_mspe_eu)

gen post_sq_error_eu = eu_gap^2 if Year >= 2016
egen post_mspe_eu = mean(post_sq_error_eu)
gen post_rmspe_eu = sqrt(post_mspe_eu)

gen post_pre_ratio_eu = post_rmspe_eu / pre_rmspe_eu
sum post_pre_ratio_eu
local eu_ratio = r(mean)

* 创建一个变量来存储每个国家的比率值
gen country_id = .
gen ratio_value = .
gen country_name = ""

* 填充eu的数据
replace country_id = 6 in 1
replace ratio_value = `eu_ratio' in 1
replace country_name = "EU" in 1

* 计算每个国家的RMSPE和比率
local row = 2
foreach country_code of numlist 1 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 20 {
    capture {
        capture confirm variable gap_`country_code'
        if _rc == 0 {
            gen pre_sq_error_`country_code' = gap_`country_code'^2 if Year < 2016
            egen pre_mspe_`country_code' = mean(pre_sq_error_`country_code')
            gen pre_rmspe_`country_code' = sqrt(pre_mspe_`country_code')
         
            gen post_sq_error_`country_code' = gap_`country_code'^2 if Year >= 2016
            egen post_mspe_`country_code' = mean(post_sq_error_`country_code')
            gen post_rmspe_`country_code' = sqrt(post_mspe_`country_code')
         
            sum pre_rmspe_`country_code'
            if r(mean) > 0 {
                gen post_pre_ratio_`country_code' = post_rmspe_`country_code' / pre_rmspe_`country_code'
                sum post_pre_ratio_`country_code'
                if r(N) > 0 & !missing(r(mean)) {
                    * 存储比率值到变量中
                    replace country_id = `country_code' in `row'
                    replace ratio_value = r(mean) in `row'
                    * 获取国家名称（如果需要）
                    local row = `row' + 1
                    di "Country `country_code' ratio: " r(mean)
                }
            }
        }
    }
}

* 保存包含所有gap和比率的数据集
save "$CODE/Brexit-stata_external_try/intl_ratio/eu/all_results_with_rmspe.dta", replace

****************************************************************************************************************
* 绘图部分
use "$CODE/Brexit-stata_external_try/intl_ratio/eu/all_results_with_rmspe.dta", clear

* 第一个preserve块：计算p值和筛选国家
preserve
    * 只保留每个国家的第一个观测值
    bysort country_id: keep if _n == 1
    
    * 首先筛选pre-treatment拟合效果好的国家
    gen qualified = 0
    replace qualified = 1 if country_id == 6  // eu总是包括
    
    * 获取eu的pre-MSPE
    sum pre_mspe_eu
    local eu_pre_mspe = r(mean)
    
    * 筛选拟合效果好的国家
    foreach country_code of numlist 1 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 20 {
        sum pre_mspe_`country_code'
        if r(N) > 0 & !missing(r(mean)) {
            if r(mean) < 5*`eu_pre_mspe' {
                replace qualified = 1 if country_id == `country_code'
            }
        }
    }
    
    * 计算比率和extreme effect (双边检验)
    gen abs_ratio = abs(ratio_value)
    sum abs_ratio if country_id == 6
    local eu_abs_ratio = r(mean)
    
    gen more_extreme = 0
    replace more_extreme = 1 if qualified == 1 & abs_ratio >= `eu_abs_ratio'
    
    * 计算p值相关统计量
    count if country_id != 6
    local total_countries = r(N)
    
    count if qualified == 1 & more_extreme == 1
    local extreme_count = r(N)
    
    local p_value = `extreme_count' / `total_countries'
    local p_value_display = string(`p_value', "%9.3f")
    
    count if qualified == 1
    local total_qualified = r(N)
    
    * 保存qualified国家列表用于filtered_list
    levelsof country_id if qualified == 1 & country_id != 6, local(qualified_countries)
restore

* 1. 绘制所有国家的安慰剂效应图
twoway (line gap_* Year, lpattern(dash) lcolor(gs12)) ///
       (line eu_gap Year, lwidth(thick) lcolor(blue)), ///
       legend(order(2 "EU" 1 "Control Countries") pos(11) ring(0) rows(2) region(style(none)) size(small)) ///
       xline(2016, lpattern(dash) lcolor(gray)) ///
       yline(0, lcolor(black)) ///
       title("Placebo Test: Treatment Effects", size(large)) ///
       subtitle("All Countries (N=`total_countries', p-value=`p_value_display')") ///
       xtitle("Year", size(medium)) ytitle("Effect", size(medium)) ///
       xlabel(#10) ///
       graphregion(color(white)) bgcolor(white) ///
       name(placebo_effects, replace)

graph export "$CODE/Brexit-stata_external_try/intl_ratio/eu/placebo_effects_all.png", ///
       width(1200) height(800) replace

* 2. 创建filtered_list用于筛选后的图
local filtered_list ""
foreach country of local qualified_countries {
    local filtered_list "`filtered_list' (line gap_`country' Year, lpattern(dash) lcolor(gs12))"
}

* 绘制筛选后的安慰剂效应图
twoway (line eu_gap Year, lwidth(thick) lcolor(blue)) ///
       `filtered_list', ///
       legend(order(1 "EU" 2 "Control Countries (Filtered)") pos(11) ring(0) rows(2) region(style(none)) size(small)) ///
       xline(2016, lpattern(dash) lcolor(gray)) ///
       yline(0, lcolor(black)) ///
       title("Placebo Test: Treatment Effects (Filtered)", size(large)) ///
       subtitle("Filtered Countries (N=`total_qualified', p-value=`p_value_display')") ///
       xtitle("Year", size(medium)) ytitle("Effect", size(medium)) ///
       xlabel(#10) ///
       yscale(range(-0.1 0.1)) ///
       graphregion(color(white)) bgcolor(white) ///
       name(placebo_effects_filtered, replace)

graph export "$CODE/Brexit-stata_external_try/intl_ratio/eu/placebo_effects_filtered.png", ///
       width(1200) height(800) replace

* 3. 绘制比率图
preserve
    bysort country_id: keep if _n == 1
    
    * 重新生成qualified变量
    gen qualified = 0
    replace qualified = 1 if country_id == 6
    foreach country of local qualified_countries {
        replace qualified = 1 if country_id == `country'
    }
    
    * 排序和排名
    gsort -ratio_value
    gen rank = _n if qualified == 1
    count if qualified == 1
    local total_qualified = r(N)
    sum rank if country_id == 6
    local eu_rank = r(mean)
    
    * 绘制比率图
    twoway (bar ratio_value rank , barwidth(0.8) color(gs12)) ///
           (bar ratio_value rank if country_id == 6, barwidth(0.8) color(blue)), ///
           title("Post/Pre-Treatment RMSPE Ratio (Filtered Countries)", size(large)) ///
           subtitle("EU Rank: `extreme_count' of `total_countries' (p-value: `p_value_display')", size(medium)) ///
           xtitle("Country Rank", size(medium)) ytitle("Post/Pre RMSPE Ratio", size(medium)) ///
           xlabel(1(1)`total_qualified') ///
           graphregion(color(white)) bgcolor(white) ///
           name(rmspe_ratio_filtered, replace)
    
    graph export "$CODE/Brexit-stata_external_try/intl_ratio/eu/post_pre_rmspe_ratio_filtered.png", ///
           width(1200) height(800) replace
restore

