clear all
set more off

local base_dir_2014 "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/crimes/total_publications"
local base_dir_2022 "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/crimes_2022/total_publications"

* 1. 加载2014年的结果数据
use "`base_dir_2014'/ukraine_synth_results.dta", clear
rename ukraine_synthetic_real ukraine_synthetic_real_2014
rename ukraine_gap_pct ukraine_gap_pct_2014
rename ukraine_actual_real ukraine_actual_real_2014
merge 1:1 Year using "`base_dir_2014'/russia_synth_results.dta", nogenerate
rename russia_synthetic_real russia_synthetic_real_2014
rename russia_gap_pct russia_gap_pct_2014
rename russia_actual_real russia_actual_real_2014

* 保存2014年的效应值
sum ukraine_gap_pct_2014 if Year >= 2014
local ukraine_effect_2014 = r(mean)
sum russia_gap_pct_2014 if Year >= 2014
local russia_effect_2014 = r(mean)

* 2. 加载2022年的结果并合并
* 使用临时变量来避免修改原始文件
tempfile temp_ukraine_2022 temp_russia_2022

* 复制2022年数据到临时文件
use "`base_dir_2022'/ukraine_synth_results.dta", clear
save "`temp_ukraine_2022'", replace

use "`base_dir_2022'/russia_synth_results.dta", clear
save "`temp_russia_2022'", replace

* 重新加载2014年数据
use "`base_dir_2014'/ukraine_synth_results.dta", clear
rename ukraine_synthetic_real ukraine_synthetic_real_2014
rename ukraine_gap_pct ukraine_gap_pct_2014
rename ukraine_actual_real ukraine_actual_real_2014
merge 1:1 Year using "`base_dir_2014'/russia_synth_results.dta", nogenerate
rename russia_synthetic_real russia_synthetic_real_2014
rename russia_gap_pct russia_gap_pct_2014
rename russia_actual_real russia_actual_real_2014

* 保存2014年的效应值
sum ukraine_gap_pct_2014 if Year >= 2014
local ukraine_effect_2014 = r(mean)
sum russia_gap_pct_2014 if Year >= 2014
local russia_effect_2014 = r(mean)

* 合并2022年的ukraine数据（使用临时文件）
merge 1:1 Year using "`temp_ukraine_2022'", nogenerate
rename ukraine_synthetic_real ukraine_synthetic_real_2022
rename ukraine_gap_pct ukraine_gap_pct_2022
rename ukraine_actual_real ukraine_actual_real_2022

* 合并2022年的russia数据（使用临时文件）
merge 1:1 Year using "`temp_russia_2022'", nogenerate
rename russia_synthetic_real russia_synthetic_real_2022
rename russia_gap_pct russia_gap_pct_2022
rename russia_actual_real russia_actual_real_2022

* 获取2022年效应值
sum ukraine_gap_pct_2022 if Year >= 2022
local ukraine_effect_2022 = r(mean)
sum russia_gap_pct_2022 if Year >= 2022
local russia_effect_2022 = r(mean)

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"
* 绘图
twoway (line ukraine_actual_real_2022 Year, lcolor("227 195 65") lwidth(medthick)) ///
       (line ukraine_synthetic_real_2014 Year, lcolor("227 195 65") lwidth(medthick) lpattern(dash_dot)) ///
	   (line ukraine_synthetic_real_2022 Year, lcolor("227 195 65") lwidth(medthick) lpattern(dash)) ///
	   (line russia_actual_real_2022 Year, lcolor("76 92 156") lwidth(medthick)) ///
	   (line russia_synthetic_real_2014 Year, lcolor("76 92 156") lwidth(medthick) lpattern(dash_dot)) ///
       (line russia_synthetic_real_2022 Year, lcolor("76 92 156") lwidth(medthick) lpattern(dash)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       xline(2014, lpattern(dash_dot) lcolor(gray)) ///
       text(60000 2014.2 "Crimean", placement(east)) ///
       text(60000 2022.2 "War", placement(east)) ///
	   text(20000 2018 `"Ukraine (2014): `=string(`ukraine_effect_2014',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Ukraine (2022): `=string(`ukraine_effect_2022',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Russia (2014) : `=string( `russia_effect_2014',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Russia (2022) : `=string( `russia_effect_2022',"%5.2f")'%"', size(medium)) ///
       xtitle("") ///
       ytitle("Total number of publications", size(medium)) ///
       xlabel(2004(2)2024, nogrid tposition(inside)) ///
       ylabel(0(20000)60000, nogrid tposition(inside) format(%9.0gc)) ///
       xmtick(2004(1)2024, tposition(inside)) ///
       ymtick(0(5000)60000, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Ukraine Actual" 2 "Ukraine Synthetic(2014)" 3 "Ukraine Synthetic(2022)" ///
                    4 "Russia Actual" 5 "Russia Synthetic(2014)" 6 "Russia Synthetic(2022)") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison_real, replace)

// graph export "`base_dir_2022'/1combined_actual_vs_synthetic.pdf", replace
graph export "`base_dir_2022'/1combined_actual_vs_synthetic.eps", replace
