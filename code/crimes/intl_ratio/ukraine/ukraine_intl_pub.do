// clear
// * 导入Excel数据
// import excel "/Users/sunmengge/Desktop/SCM_STATA/crimes/original_completed.xlsx", sheet("Sheet1") firstrow clear
//
// encode Country, gen(id)
// xtset id Year
// gen log_pub_total = log(pub_total + 1)
// gen log_gdp_per_capita = log(gdp_per_capita + 1)
// gen log_rp = log(ResearchersinRD + 1)
// * 保存处理后的数据集，以便后续使用
// save "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/processed_data.dta", replace	
//
// * 对ukraine进行合成控制分析，处理年份为2014年
// synth log_pub_total log_gdp_per_capita log_rp RD log_pub_total(2013) log_pub_total(2012) log_pub_total(2011) log_pub_total(2010) log_pub_total(2009) log_pub_total(2008) log_pub_total(2007) , trunit(44) trperiod(2014) counit(1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 36 37 38 39 40 41 42 43 45 46) xperiod(2010(1)2013)  nested keep(ukraine_synth_results, replace)
//
//
// * 保存ukraine的结果
// use ukraine_synth_results, clear
// rename _time Year
// rename _Y_treated ukraine_actual
// rename _Y_synthetic ukraine_synthetic
// gen ukraine_gap = ukraine_actual - ukraine_synthetic
// keep Year ukraine_actual ukraine_synthetic ukraine_gap
// save "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/ukraine_synth_results.dta", replace
//
// * 绘制ukraine真实数据和合成数据对比图
// twoway (line ukraine_actual Year, lcolor(blue) lwidth(medthick)) ///
//        (line ukraine_synthetic Year, lcolor(red) lwidth(medthick) lpattern(dash)), ///
//        xline(2014, lpattern(dash) lcolor(gray)) ///
//        legend(order(1 "ukraine Actual" 2 "ukraine Synthetic") position(6) rows(1)) ///
//        title("ukraine: Actual vs Synthetic Control", size(large)) ///
//        subtitle("Synthetic Control Analysis") ///
//        xtitle("Year", size(medium)) ytitle("log_pub_total", size(medium)) ///
//        xlabel(#10) ///
//        graphregion(color(white)) bgcolor(white) ///
//        name(ukraine_comparison, replace)
// graph export "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/ukraine_actual_vs_synthetic.png", width(1200) height(800) replace


	
// * 假设每个控制组国家都是处理组，逐个遍历进行合成控制
// foreach country_code of numlist 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 36 37 38 39 40 41 42 43 45 46 {
//     * 显示进度
//     di "Processing country code: `country_code'"
//	
// 	* 使用保存的处理后数据集，而不是每次都重新导入
//     use "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/processed_data.dta", clear
//     xtset id Year  // 确保面板数据结构设置正确
// 
//     * 创建控制组列表，排除当前处理单位和ukraine(44)
//     local control_list ""
//     foreach ctrl of numlist  1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 36 37 38 39 40 41 42 43 45 46 {
//         if `ctrl' != `country_code' & `ctrl' != 35 & `ctrl' != 44 {
//             local control_list "`control_list' `ctrl'"
//         }
//     }
//	
// 	* 对于问题国家，尝试使用更简单的拟合模型
// 	if `country_code' == 26 | `country_code' == 46 {
// 	  	di "Using simplified model for problematic country code `country_code'"
// 		capture noisily {
// 			synth log_pub_total log_gdp_per_capita log_rp RD, ///
// 				  trunit(`country_code') trperiod(2014) ///
// 				  counit(`control_list') ///
// 				  nested allopt ///
// 				  keep("/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/synth_`country_code'", replace)
// 		}
// 	}
// 	* 对其他国家进行合成控制分析
// 	else {
// 		capture noisily {
// 			synth log_pub_total log_gdp_per_capita log_rp RD log_pub_total(2013) log_pub_total(2012) log_pub_total(2011) log_pub_total(2010) log_pub_total(2009) log_pub_total(2008) log_pub_total(2007), ///
// 				  trunit(`country_code') trperiod(2014) ///
// 				  counit(`control_list') ///
// 				  nested ///
// 				  keep("/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/synth_`country_code'", replace)
// 		}
// 	}
//	
// 	* 处理结果并创建gap文件
//     capture {
//         use "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/synth_`country_code'", clear
//         rename _time Year
//         gen gap_`country_code' = _Y_treated - _Y_synthetic
//         keep Year gap_`country_code'
//         drop if missing(Year)
//         save "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/gap_`country_code'", replace
//     }
// }

* 1. 先处理 ukraine_synth_results.dta 的重复值
use "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/ukraine_synth_results.dta", clear
* 检查重复值
duplicates list Year
* 保留每个年份的第一个观察值
bysort Year: keep if _n == 1
* 保存处理后的数据
save "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/ukraine_synth_results_clean.dta", replace



* 合并所有gap文件和ukraine结果，计算RMSPE和比率
use "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/gap_1", clear

* 合并其他gap文件
foreach country_code of numlist 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 36 37 38 39 40 41 42 43 45 46{
    capture {
        merge 1:1 Year using "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/gap_`country_code'", nogenerate
    }
}

* 合并ukraine的结果
merge 1:1 Year using "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/ukraine_synth_results_clean.dta", nogenerate

* 计算ukraine的平均处理效应（2014年及以后）
sum ukraine_gap if Year >= 2014
local ukraine_avg_effect = r(mean)
local ukraine_avg_effect_display = string(`ukraine_avg_effect', "%5.3f")

* 检查变量是否已存在，如果存在则删除
capture drop pre_sq_error_* pre_mspe_* pre_rmspe_* post_sq_error_* post_mspe_* post_rmspe_* post_pre_ratio_*

* 计算ukraine的RMSPE
gen pre_sq_error_ukraine = ukraine_gap^2 if Year < 2014
egen pre_mspe_ukraine = mean(pre_sq_error_ukraine)
gen pre_rmspe_ukraine = sqrt(pre_mspe_ukraine)

gen post_sq_error_ukraine = ukraine_gap^2 if Year >= 2014
egen post_mspe_ukraine = mean(post_sq_error_ukraine)
gen post_rmspe_ukraine = sqrt(post_mspe_ukraine)

gen post_pre_ratio_ukraine = post_rmspe_ukraine / pre_rmspe_ukraine
sum post_pre_ratio_ukraine
local ukraine_ratio = r(mean)

* 创建一个变量来存储每个国家的比率值
gen country_id = .
gen ratio_value = .
gen country_name = ""

* 填充ukraine的数据
replace country_id = 44 in 1
replace ratio_value = `ukraine_ratio' in 1
replace country_name = "ukraine" in 1

* 计算每个国家的RMSPE和比率
local row = 2
foreach country_code of numlist 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 36 37 38 39 40 41 42 43 45 46 {
    capture {
        capture confirm variable gap_`country_code'
        if _rc == 0 {
            gen pre_sq_error_`country_code' = gap_`country_code'^2 if Year < 2014
            egen pre_mspe_`country_code' = mean(pre_sq_error_`country_code')
            gen pre_rmspe_`country_code' = sqrt(pre_mspe_`country_code')
         
            gen post_sq_error_`country_code' = gap_`country_code'^2 if Year >= 2014
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
save "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/all_results_with_rmspe.dta", replace

****************************************************************************************************************
* 绘图部分
use "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/all_results_with_rmspe.dta", clear

* 1. 绘制所有国家的安慰剂效应图
tempvar ukraine_line control_lines
twoway (line gap_* Year, lpattern(dash) lcolor(gs12)) ///
       (line ukraine_gap Year, lwidth(thick) lcolor(blue)), ///
       legend(order(2 "ukraine" 1 "Control Countries") pos(11) ring(0) rows(2) region(style(none)) size(small)) ///
       xline(2014, lpattern(dash) lcolor(gray)) ///
       yline(0, lcolor(black)) ///
       title("Placebo Test: Treatment Effects", size(large)) ///
       subtitle("ukraine vs Control Countries") ///
       xtitle("Year", size(medium)) ytitle("Effect", size(medium)) ///
       xlabel(#10) ///
       graphregion(color(white)) bgcolor(white) ///
       name(placebo_effects, replace)

graph export "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/placebo_effects_all.png", ///
       width(1200) height(800) replace

* 2&3. 首先创建筛选国家的列表
sum pre_mspe_ukraine
local ukraine_pre_mspe = r(mean)

* 创建一个标记变量来存储筛选结果
gen filtered = 0
replace filtered = 1 if country_id == 44  // ukraine总是包括

* 创建一个字符串来存储被筛选的国家列表（用于绘图）
local filtered_list ""

* 筛选国家（只执行一次）
foreach country_code of numlist 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 36 37 38 39 40 41 42 43 45 46{
    capture {
        sum pre_mspe_`country_code'
        if r(N) > 0 & !missing(r(mean)) {
            local country_pre_mspe = r(mean)
            if `country_pre_mspe' < 5*`ukraine_pre_mspe' {
                sum post_pre_ratio_`country_code'
                if r(N) > 0 & !missing(r(mean)) & r(mean) < 15 {
                    * 为绘制安慰剂效应图添加命令
                    local filtered_list "`filtered_list' (line gap_`country_code' Year, lpattern(dash) lcolor(gs12))"
                    * 为比率图标记国家
                    replace filtered = 1 if country_id == `country_code'
                    di "Country `country_code' included with pre_mspe = " `country_pre_mspe' " and ratio = " r(mean)
                }
            }
        }
    }
}

* 绘制筛选后的安慰剂效应图
	twoway (line ukraine_gap Year, lwidth(thick) lcolor(blue)) ///
		   `filtered_list', ///
		   legend(order(1 "ukraine" 2 "Control Countries (Filtered)") pos(11) ring(0) rows(2) region(style(none)) size(small)) ///
		   xline(2014, lpattern(dash) lcolor(gray)) ///
		   yline(0, lcolor(black)) ///
		   title("Placebo Test: Treatment Effects (Filtered)", size(large)) ///
		   subtitle("ukraine vs Filtered Control Countries") ///
		   xtitle("Year", size(medium)) ytitle("Effect", size(medium)) ///
		   xlabel(#10) ///
		   yscale(range(-0.1 0.1)) ///
		   graphregion(color(white)) bgcolor(white) ///
		   name(placebo_effects_filtered, replace)
graph export "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/placebo_effects_filtered.png", width(1200) height(800) replace

* 创建比率图（使用已经筛选好的国家）
preserve
    * 使用之前创建的 filtered 变量筛选国家
    keep if filtered == 1
    
    * 只保留每个国家的第一个观测值
    bysort country_id: keep if _n == 1
	
	* 计算每个国家ratio_value的绝对值
    gen abs_ratio = abs(ratio_value)
    
    * 排序并计算排名
    gsort -ratio_value
    gen rank = _n
    gen ukraine_dummy = (country_id == 44)
    
    * 计算ukraine的排名和p值
    sum rank if ukraine_dummy == 1
    local ukraine_rank = r(mean)
    count if ratio_value != .
    local total_filtered = r(N)
    * 计算双尾p值
    local p_value = 2 * min(`ukraine_rank' / `total_filtered', 1 - (`ukraine_rank' - 1) / `total_filtered')
    
	* 绘制比率图（仍然使用原始的ratio_value，而不是绝对值）
    gsort -ratio_value  // 恢复原始排序用于显示
    replace rank = _n   // 重新生成用于显示的排名
    
    twoway (bar ratio_value rank, barwidth(0.8) color(gs12)) ///
           (bar ratio_value rank if ukraine_dummy == 1, barwidth(0.8) color(blue)), ///
           title("Post/Pre-Treatment RMSPE Ratio (Filtered Countries)", size(large)) ///
           subtitle("ukraine Rank: `ukraine_rank' of `total_filtered' (p-value: `p_value')", size(medium)) ///
           xtitle("Country Rank", size(medium)) ytitle("Post/Pre RMSPE Ratio", size(medium)) ///
           xlabel(1(1)`total_filtered') ///
           graphregion(color(white)) bgcolor(white) ///
           name(rmspe_ratio_filtered, replace)
    
    * 保存比率图
    graph export "/Users/sunmengge/Desktop/SCM_STATA/crimes/total_publications/ukraine/post_pre_rmspe_ratio_filtered.png", ///
           width(1200) height(800) replace
restore
