*==============================================================*
* 00_master.do — 按顺序跑完 dyad_ppml 的全部 Stata 估计
*
* 前置（Python，只负责解析原始论文清单，不做估计）：
*     python 1build_dyad_panel.py      -> dyad_panel.csv
*     python 5build_uk_focal_panel.py  -> uk_dyad_panel.csv
*
* 用法（在本目录下）：
*     stata-mp -e do 00_master.do
*
* 收尾（Python 画图）：
*     python 14plot_two_panel.py
*==============================================================*

clear all
do "`c(pwd)'/_setup.do"

local here "$DYAD"

di as result _n _dup(70) "#"
di as result "# 10prepare_panel.do"
di as result _dup(70) "#"
do "`here'/10prepare_panel.do"

di as result _n _dup(70) "#"
di as result "# 11estimate_eu_to_uk.do"
di as result _dup(70) "#"
do "`here'/11estimate_eu_to_uk.do"

di as result _n _dup(70) "#"
di as result "# 12estimate_uk_to_eu.do"
di as result _dup(70) "#"
do "`here'/12estimate_uk_to_eu.do"

di as result _n _dup(70) "#"
di as result "# 13placebo_uk_to_eu.do"
di as result _dup(70) "#"
do "`here'/13placebo_uk_to_eu.do"

di as result _n _dup(70) "="
di as result "All Stata estimation finished."
di as result "Next:  python 14plot_two_panel.py"
di as result _dup(70) "="
