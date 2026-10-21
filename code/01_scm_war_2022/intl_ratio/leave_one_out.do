clear all
set more off

********************************************************************************
* 程序结构：
* 1. 数据准备和变量定义
* 2. russia合成控制分析
* 4. 安慰剂检验
* 5. 结果可视化和统计分析
********************************************************************************
* 定义基础路径

* 1. 数据准备和变量定义
* 1.1 导入数据

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

cd "$CODE/01_scm_war_2022/intl_ratio"

local base_path ".."
local base_path_1 "leave_one_russia"
import excel "`base_path'/original_completed.xlsx", sheet("Sheet1") firstrow clear

local treated_year 2022
local before_treated_year 2021

* 1.2 标准化国家名称
* 保存原始国家名称
gen country_original = Country

* 标准化国家名称（用于文件操作）
* 1. 替换特殊字符为下划线
replace Country = subinstr(Country, " ", "_", .)
replace Country = subinstr(Country, ".", "_", .)
replace Country = subinstr(Country, ",", "_", .)
replace Country = subinstr(Country, "(", "_", .)
replace Country = subinstr(Country, ")", "_", .)
replace Country = subinstr(Country, "-", "_", .)
replace Country = subinstr(Country, "__", "_", .)  // 处理可能出现的双下划线

* 2. 转换为大写
replace Country = upper(Country)
* 显示所有标准化后的国家名称
di "标准化后的国家名称列表："
sort Country
list Country country_original, noobs sepby(Country)

* 3. 处理特殊情况，确保生成有效的变量名
replace Country = "IRAN" if Country == "IRAN_ISLAMIC_REP_"
replace Country = "KOREA" if Country == "KOREA_REP_"
replace Country = "SLOVAK" if Country == "SLOVAK_REPUBLIC"


* 保存国家名称映射
preserve
    keep Country country_original
    duplicates drop
    save "`base_path_1'/country_name_mapping.dta", replace
restore

* 1.3 自动获取国家列表
levelsof Country, local(countries) clean

* 验证获取的国家列表
di "获取到的国家列表："
foreach country of local countries {
    di "`country'"
}
di "共计 `: word count `countries'' 个国家"

* 1.4 生成国家ID和分组
gen country_id = .
local i = 1
foreach country of local countries {
    replace country_id = `i' if Country == "`country'"
    local ++i
}

* 检查未匹配的国家
list Country if missing(country_id)
* 设置面板数据结构
xtset country_id Year


* 1.5 创建处理组和控制组
* 创建控制组国家列表
local control_countries
foreach country of local countries {
    if !inlist("`country'", "RUSSIAN_FEDERATION") {
        local control_countries `"`control_countries' "`country'""'
    }
}

* 获取控制组ID列表
local control_ids
foreach country of local control_countries {
    qui sum country_id if Country == "`country'"
    local control_ids "`control_ids' `r(mean)'"
}

* 获取处理组ID
qui sum country_id if Country == "RUSSIAN_FEDERATION"
local russia_id = r(mean)

* 1.6 生成分析所需变量
gen log_pub_total = log(pub_total + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

gen log_pub_total_10 = log_pub_total / 10
gen log_gdp_per_capita_10 = log_gdp_per_capita /10
gen log_rp_10 = log_rp /10

global control_vars "log_pub_total_10 log_gdp_per_capita_10 log_rp_10 RD"

global control_vars_1 "intl_ratio(2021) intl_ratio(2019) intl_ratio(2017) intl_ratio(2015) " //2022

* 1.7 保存处理后的数据
save "`base_path_1'/processed_data.dta", replace

* 2. russia合成控制分析
* 2.1 运行russia的合成控制分析
synth intl_ratio ///
    $control_vars ///
    $control_vars_1 , ///
    trunit(`russia_id') trperiod(2022) ///
    counit(`control_ids') ///
    xperiod(2015(1)2021) ///
    nested allopt ///
    keep("`base_path_1'/russia_synth_results.dta", replace)

* 2.2 处理russia结果
use "`base_path_1'/russia_synth_results.dta", clear
rename _time Year
rename _Y_treated russia_actual
rename _Y_synthetic russia_synthetic
gen russia_gap = russia_actual - russia_synthetic


* 2.4 计算russia平均处理效应
egen russia_avg_effect = mean(russia_gap) if Year >= 2022
local russia_avg_effect : display %5.4f r(mean)

* 2.5 计算RUSSIAN_FEDERATION的RMSPE
gen pre_sq_error_russia = russia_gap^2 if Year <= 2021
egen pre_mspe_russia = mean(pre_sq_error_russia)
gen pre_rmspe_russia = sqrt(pre_mspe_russia)
local pre_rmspe_russia : display %5.4f r(mean)

gen post_sq_error_russia = russia_gap^2 if Year >= 2022
egen post_mspe_russia = mean(post_sq_error_russia)
gen post_rmspe_russia = sqrt(post_mspe_russia)

gen rmspe_ratio_russia = post_rmspe_russia / pre_rmspe_russia

drop if missing(Year)  // 删除Year缺失的观测值

* 2.7 保存russia结果
save "`base_path_1'/russia_synth_results.dta", replace

* 2.8 输出控制组国家与权重对应表
use "`base_path_1'/russia_synth_results.dta", clear
keep _Co_Number _W_Weight
rename _Co_Number country_id
save "`base_path_1'/temp_weights.dta", replace

use "`base_path_1'/processed_data.dta", clear
keep country_id Country country_original
duplicates drop
save "`base_path_1'/temp_country.dta", replace

use "`base_path_1'/temp_weights.dta", clear
merge 1:1 country_id using "`base_path_1'/temp_country.dta"
keep if _W_Weight > 0
list country_id country_original _W_Weight, noobs
export excel using "`base_path_1'/russia_weights_country.xlsx", firstrow(variables) replace

* 2.9 对RUSSIAN_FEDERATION结果可视化
use "`base_path_1'/russia_synth_results.dta", clear
* 获取平均效应值
sum russia_gap if Year >= 2022
local russia_avg_effect = r(mean)*100

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
twoway (line russia_actual Year, lcolor("137 202 229") lwidth(medthick)) ///
       (line russia_synthetic Year, lcolor("137 202 229") lwidth(medthick) lpattern(dash)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       text(0.8 2022 "War", placement(east)) ///
       text(0.55 2019 "Russia Effect: `=string(`russia_avg_effect',"%5.2f")'%", size(medium)) ///
       xtitle("") ///
       ytitle("the ratio of international publications", size(medium)) ///
       xlabel(2015(2)2024, nogrid tposition(inside)) ///
       ylabel(0.4(0.1)0.8, nogrid tposition(inside) format(%3.1f)) ///
       xmtick(2015(1)2024, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Russia Actual" 2 "Russia Synthetic") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison, replace)

graph export "`base_path_1'/russia_actual_vs_synthetic.png", ///
       width(1200) height(800) replace
	   
* 2.10 留一检查 (Leave-one-out analysis)
* 2.10.1 准备数据
use "`base_path_1'/processed_data.dta", clear

* 保存country_id映射
preserve
    keep Country country_id
    duplicates drop
    save "`base_path_1'/country_id_map.dta", replace
restore

* 2.10.2 创建留一检查的循环
foreach country of local control_countries {
    * 获取当前国家的ID
	di "==== 当前国家: `country' ===="
    preserve
        use "`base_path_1'/country_id_map.dta", clear
        qui sum country_id if Country == "`country'"
        local current_id = r(mean)
    restore
   
    * 获取原始国家名称（用于显示）
    preserve
        use "`base_path_1'/country_name_mapping.dta", clear
        qui sum country_original if Country == "`country'"
        local display_name = r(mean)
    restore
	di "get country_name_mapping"
   
    * 创建新的控制组列表（排除当前国家）
    local new_control_ids
    foreach c of local control_countries {
        if "`c'" != "`country'" {
            preserve
                use "`base_path_1'/country_id_map.dta", clear
                qui sum country_id if Country == "`c'"
                local new_control_ids "`new_control_ids' `r(mean)'"
            restore
        }
    }
    di "get new_control_ids"
	
	
	* 运行合成控制分析
	* 重新加载主数据集，确保有country_id
    use "`base_path_1'/processed_data.dta", clear
    xtset country_id Year
    synth intl_ratio ///
        $control_vars ///
        $control_vars_1 , ///
        trunit(`russia_id') trperiod(`treated_year') ///
        counit(`new_control_ids') ///
        xperiod(2015(1)`before_treated_year') ///
        nested allopt ///
        keep("`base_path_1'/loo_`country'.dta", replace)
   
	di "synthetic finished!"
    * 处理结果
    use "`base_path_1'/loo_`country'.dta", clear
    capture confirm variable _time
    if _rc == 0 {
        rename _time Year
    }
    tsset Year
	di "step1"
    rename _Y_treated russia_actual
    rename _Y_synthetic russia_synthetic_`country'
    gen russia_gap_`country' = russia_actual - russia_synthetic_`country'
	di "step2"
   
    * 计算效应（intl_ratio已经是比例，直接使用差值）
    gen russia_gap_pct_`country' = russia_gap_`country' * 100
	di "step3"
   
    * 计算当前留一检查的平均效应
    qui sum russia_gap_pct_`country' if Year >= `treated_year'
    local current_avg_effect = r(mean)
    local current_avg_effect_str = string(`current_avg_effect',"%5.2f")
	di "step4"
   
    * 计算当前留一检查的RMSPE
    gen pre_sq_error = russia_gap_`country'^2 if Year <= `before_treated_year'
    egen pre_mspe = mean(pre_sq_error)
    gen pre_rmspe = sqrt(pre_mspe)
    qui sum pre_rmspe
    local current_rmspe = r(mean)
    local current_rmspe_str = string(`current_rmspe',"%5.4f")
	di "step5"
   
    * 为当前留一检查生成可视化图
    graph set window fontface "Helvetica"
    set scheme s2color
   
    twoway (line russia_actual Year, lcolor(orange_red) lwidth(medthick)) ///
           (line russia_synthetic_`country' Year, lcolor(blue) lwidth(medthick) lpattern(dash)), ///
           xline(2022, lpattern(dash) lcolor(gray)) ///
           text(0.8 2022.2 "Russia-Ukraine War", placement(east)) ///
           text(0.6 2020 "Avg Effect: `current_avg_effect_str'%", size(medium)) ///
           text(0.4 2020 "RMSPE: `current_rmspe_str'", size(medium)) ///
           title("Leave-one-out: Excluding `country'", size(medium)) ///
           xtitle("") ///
           ytitle("International Publication Ratio", size(medium)) ///
           xlabel(2015(2)2024, nogrid tposition(inside)) ///
           ylabel(0(0.1)1, nogrid tposition(inside) format(%9.2f)) ///
           xmtick(2015(1)2024, tposition(inside)) ///
           ymtick(0(0.05)1, tposition(inside)) ///
           graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
           plotregion(style(outline) lcolor(black) lwidth(thin)) ///
           bgcolor(white) ///
           legend(order(1 "Russia Actual" 2 "Russia Synthetic") ///
                  pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
           name(loo_`country', replace)
    di "step6"
    * 保存当前留一检查的图
    graph export "`base_path_1'/loo_`country'.png", ///
           width(1200) height(800) replace
    di "step7"
    * 保存结果
    save "`base_path_1'/loo_`country'_results.dta", replace
	di "step8"
}

* 2.10.3 合并所有留一检查结果
* 批量去重所有国家的结果文件
foreach country of local control_countries {
   use "`base_path_1'/loo_`country'_results.dta", clear
   drop if missing(Year)
   duplicates drop Year, force
   save "`base_path_1'/loo_`country'_results.dta", replace
}
* 使用第一个国家的结果作为基础
local first_country : word 1 of `control_countries'
use "`base_path_1'/loo_`first_country'_results.dta", clear
keep Year russia_actual russia_synthetic_`first_country' russia_gap_pct_`first_country'

* 合并其他国家的结果
foreach country of local control_countries {
   if "`first_country'" != "`country'" {
	   merge 1:1 Year using "`base_path'/loo_`country'_results.dta", ///
		   keepusing(russia_synthetic_`country' russia_gap_pct_`country') nogen
   }
}

* 2.10.4 计算平均效应和置信区间
egen mean_synthetic = rowmean(russia_synthetic_*)
egen sd_synthetic = rowsd(russia_synthetic_*)
gen ci_lower = mean_synthetic - 1.96*sd_synthetic
gen ci_upper = mean_synthetic + 1.96*sd_synthetic
di "ci_upper"

* 2.10.5 可视化留一检查结果
graph set window fontface "Helvetica"
set scheme s2color

twoway (line russia_actual Year, lcolor(orange_red) lwidth(medthick)) ///
       (line mean_synthetic Year, lcolor(blue) lwidth(medthick)) ///
       (rarea ci_lower ci_upper Year, fcolor(blue%20) lcolor(gray)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       text(0.6 2018.2 "Russia-Ukraine War", placement(east)) ///
       xtitle("") ///
       ytitle("International Publication Ratio", size(medium)) ///
       xlabel(2015(2)2024, nogrid tposition(inside)) ///
       ylabel(0(0.1)0.6, nogrid tposition(inside) format(%9.2f)) ///
       xmtick(2015(1)2024, tposition(inside)) ///
       ymtick(0(0.05)0.6, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Russia Actual" 2 "Mean Synthetic" 3 "95% CI") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(loo_analysis, replace)

graph export "`base_path_1'/loo_analysis.png", ///
       width(1200) height(800) replace

* 2.10.6 计算并输出每个控制组国家的平均效应
foreach country of local control_countries {
    qui sum russia_gap_pct_`country' if Year >= `treated_year'
    local country_avg_effect = r(mean)
    di "`country' 平均效应: " %5.2f `country_avg_effect' "%"
}


