* =============================================================================
* 俄罗斯 2022 全面入侵对学者迁入的因果效应: 合成控制法 (SCM) — WoS 版
* 数据: 本项目 WoS 复刻 MPIDR 算法 (7mpidr_migration_replication.py)
*        -> mpidr_country_measures.csv 的 inmig (迁入学者数), 2005-2024
* 供体池: 科研体量与俄罗斯可比 (pre 期 population 在 RUS 的 [1/5, 5x]),
*   |netmig| pre 年均 >=50, 排除 UKR/BLR. 共 31 个供体.
* 处理国: RUS, 处理年 T0=2022 (post=2022,2023,2024)
* 结果变量: inflow (= inmig)
* 预测变量 / MSPE: 2008-2021 (WoS 2005 全国 inflow=0, 2006-07 仍大量冷启动零值,
*   会导致 synth V 矩阵奇异; 故从 2008 起用完整可匹配年份)
* 推断: in-space placebo (synth2), 报告 RMSPE 比值排名 p 值
* 注: WoS 早期年份存在 padded population 冷启动; 与 OpenAlex 版对照时需注意量纲差异.
* =============================================================================
clear all
set more off
global DIR "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/4scm_russia_wos"
cap mkdir "$DIR/results"

import delimited "$DIR/scm_panel.csv", clear varnames(1)

encode country, gen(cid)
tsset cid year

gen inflow = number_of_inmigrations
gen ln_researchers = ln(researchers)

summarize cid if country=="RUS", meanonly
global TRT = r(min)

* -----------------------------------------------------------------------------
* 主分析: synth2 (含 in-space placebo)
*   预测/MSPE 窗口: 2008-2021 (避开 2005-07 冷启动零值)
* -----------------------------------------------------------------------------
cap frame drop scm_rus
synth2 inflow ///
    inflow(2008) inflow(2009) inflow(2010) inflow(2011) ///
    inflow(2012) inflow(2013) inflow(2014) inflow(2015) ///
    inflow(2016) inflow(2017) inflow(2018) inflow(2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2008(1)2021) mspeperiod(2008(1)2021) ///
    placebo(unit) frame(scm_rus) nofigure

frame scm_rus {
    export delimited "$DIR/results/scm_russia_frame.csv", replace
}
matrix W = e(W_weights)
matrix list W

display _n "✅ 俄罗斯 SCM WoS (inflow) 完成 -> results/scm_russia_frame.csv"
