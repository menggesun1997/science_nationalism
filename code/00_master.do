*===========================================================*
* 00_master.do
* 主运行文件：按顺序跑完 6 个分析 do，然后合并出图
* 在 Stata 中直接 do 这个文件即可一键生成 Figure 1
*===========================================================*
clear all
set more off

* ── 全局配色（所有子 do 通过全局宏共享颜色定义）─────────────────────────
global C_EU    "0 114 178"      // #0072B2  深蓝（EU）
global C_UK    "213 94 0"       // #D55E00  橙红（UK）
global C_RU    "86 180 233"     // #56B4E9  浅蓝（Russia）
global C_UA    "230 159 0"      // #E69F00  金黄（Ukraine）
global C_SHADE "238 238 238"    // #EEEEEE  后处理期阴影
global C_LINE  "68 68 68"       // #444444  干预线

* ── 运行各子图分析 + 绘图 do ─────────────────────────────────────────────
di as result "=== Step 1/6: Brexit – Total Publications (panels a, c) ==="
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/Brexit-stata_external_try/total_publications/compare.do"

di as result "=== Step 2/6: Brexit – Intl. Ratio (panels b, d) ==="
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/Brexit-stata_external_try/intl_ratio/compare_intl_ratio.do"

di as result "=== Step 3/6: Crimea – Total Publications (panels e, g) ==="
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/crimes/total_publications/compare_total.do"

di as result "=== Step 4/6: Crimea – Intl. Ratio (panels f, h) ==="
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/crimes/intl_ratio/intl_ratio_compare.do"

di as result "=== Step 5/6: War – Total Publications (panels i, k) ==="
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/crimes_2015_2022/total_publications/compare_total_2022.do"

di as result "=== Step 6/6: War – Intl. Ratio (panels j, l) ==="
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/crimes_2015_2022/intl_ratio/intl_ratio_compare.do"

* ── 合并并导出最终图 ─────────────────────────────────────────────────────
di as result "=== Combining all 12 panels → Figure 1 ==="
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/99_combine_figure1.do"

di as result "=== 完成！Figure 1 已保存至 code/picutres/figure1.pdf ==="
