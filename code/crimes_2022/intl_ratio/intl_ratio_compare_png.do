clear all
set more off

* 1. 加载2014年的结果数据
local base_dir_2014 "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/crimes/intl_ratio"
local base_dir_2022 "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/crimes_2022/intl_ratio"
use "`base_dir_2014'/ukraine_synth_results.dta", clear
rename ukraine_synthetic ukraine_synthetic_2014  // 先重命名2014年的变量
rename ukraine_gap ukraine_gap_2014    // 重命名2014年的gap变量
merge 1:1 Year using "`base_dir_2014'/russia_synth_results.dta", nogenerate
rename russia_synthetic russia_synthetic_2014    // 重命名2014年的俄罗斯变量
rename russia_gap russia_gap_2014   // 重命名2014年的gap变量

* 保存2014年的效应值
sum ukraine_gap_2014 if Year >= 2014
local ukraine_effect_2014 = r(mean)*100
sum russia_gap_2014 if Year >= 2014
local russia_effect_2014 = r(mean)*100


* 2. 加载2022年的结果并合并
merge 1:1 Year using "`base_dir_2022'/ukraine_synth_results.dta", nogenerate
rename ukraine_synthetic ukraine_synthetic_2022  // 重命名2022年的变量
rename ukraine_gap ukraine_gap_2022    // 重命名2022年的gap变量
merge 1:1 Year using "`base_dir_2022'/russia_synth_results.dta", nogenerate
rename russia_synthetic russia_synthetic_2022    // 重命名2022年的变量
rename russia_gap russia_gap_2022  // 重命名2022年的gap变量

* 获取2022年效应值
sum ukraine_gap_2022 if Year >= 2022
local ukraine_effect_2022 = r(mean)*100
sum russia_gap_2022 if Year >= 2022
local russia_effect_2022 = r(mean)*100

graph set window fontface "Helvetica"
set scheme s2color
graph set eps fontface "Helvetica"  // 如果要导出eps格式
* 绘图
twoway (line ukraine_actual Year, lcolor("227 195 65") lwidth(medthick)) ///
       (line ukraine_synthetic_2014 Year, lcolor("227 195 65") lwidth(medthick) lpattern(dash_dot)) ///
       (line ukraine_synthetic_2022 Year, lcolor("227 195 65") lwidth(medthick) lpattern(dash)) ///
       (line russia_actual Year, lcolor("76 92 156") lwidth(medthick)) ///
	   (line russia_synthetic_2014 Year, lcolor("76 92 156") lwidth(medthick) lpattern(dash_dot)) ///
       (line russia_synthetic_2022 Year, lcolor("76 92 156") lwidth(medthick) lpattern(dash)), ///
       xline(2022, lpattern(dash) lcolor(gray)) ///
       xline(2014, lpattern(dash_dot) lcolor(gray)) ///
       text(0.8 2014.2 "Crimean", placement(east)) ///
       text(0.8 2022.2 "War", placement(east)) ///
	   text(0.7 2018 `"Ukraine (2014): `=string(`ukraine_effect_2014',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Ukraine (2022): `=string(`ukraine_effect_2022',"%5.2f")'%"' `"`=char(13)'"' , size(medium)) ///
       text(0.47 2018 `"Russia (2014) : `=string( `russia_effect_2014',"%5.2f")'%"' `"`=char(13)'"' ///
                `"Russia (2022) : `=string( `russia_effect_2022',"%5.2f")'%"', size(medium)) ///
		xtitle("") ///
       ytitle("The ratio of international publications", size(medium)) ///
       xlabel(2004(2)2024, nogrid tposition(inside)) ///
       ylabel(0.4(0.1)0.8, nogrid tposition(inside) format(%3.1f)) ///
       xmtick(2004(1)2024, tposition(inside)) ///
       ymtick(0.4(0.05)0.8, tposition(inside)) ///
       graphregion(color(white) margin(r=5 l=5 t=5 b=5)) ///
       plotregion(style(outline) lcolor(black) lwidth(thin)) ///
       bgcolor(white) ///
       legend(order(1 "Ukraine Actual" 2 "Ukraine Synthetic(2014)" 3 "Ukraine Synthetic(2022)" ///
                    4 "Russia Actual" 5 "Russia Synthetic(2014)" 6 "Russia Synthetic(2022)") ///
              pos(11) ring(0) cols(1) region(style(none)) size(vsmall)) ///
       name(combined_comparison_real, replace)

// graph export "/Users/sunmengge/Dropbox/crimes_2022/intl_ratio/1combined_actual_vs_synthetic.eps", replace

// graph export "`base_dir_2022'/1combined_actual_vs_synthetic.png", ///
//        width(1200) height(800) replace

graph export "`base_dir_2022'/1combined_actual_vs_synthetic.pdf", replace
