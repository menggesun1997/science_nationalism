* =============================================================================
* 俄罗斯 2022 全面入侵对学者迁入的因果效应: 合成控制法 (SCM)
* 数据: OpenAlex 国家级 inflow (number_of_inmigrations, 迁入学者数), 2005-2024
* 供体池: 科研体量与俄罗斯可比的国家 (pre 期研究者规模在 RUS 的 [1/5, 5x] 区间),
*   |netmigration| pre 年均>=50, 排除处理/战争相关国 (RUS/UKR/BLR). 共 29 个供体.
*   -> 合成体天然由规模同量级国 (日英德法印韩加意西等) 构成, 构成可解释.
* 处理国: RUS, 处理年 T0=2022 (post=2022,2023,2024)
* 结果变量: inflow (迁入学者数).
* 预测变量 (Abadie 经典结构, 替代逐年 lag):
*   inflow 年段均值 2005-09 / 2010-14 / 2015-19, 再加处理前近两年 2020, 2021.
*   MSPE 窗口仍为全 pre 期 2005-2021 (评估整段拟合).
* 推断: in-space placebo (synth2 自带), 报告 RMSPE 比值排名 p 值
* =============================================================================
clear all
set more off
global DIR "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/4scm_russia_openalex"
cap mkdir "$DIR/results"

import delimited "$DIR/scm_panel.csv", clear varnames(1)

* 面板设置: 国家数值 id + 年份
encode country, gen(cid)
tsset cid year

* 结果变量: 迁入学者数 (inflow). import delimited 会把 number_of_inmigrations 读入同名列.
gen inflow = number_of_inmigrations
* 协变量: 研究者规模 (对数, 备用)
gen ln_researchers = ln(researchers)

* 处理国 id
summarize cid if country=="RUS", meanonly
global TRT = r(min)

* -----------------------------------------------------------------------------
* 主分析: synth2 + nested (更彻底搜索 V)
*   预测变量: 年段均值 + 近两年 lag (经典 Abadie 结构).
*   MSPE 窗口: 2005-2021 (全 pre 期).
*   注: nested+placebo 会在部分供体国不收敛 (r430, 曾见于 GBR); 故拆成两步 ——
*     (1) 处理国主估计用 nested; (2) in-space placebo 用默认优化.
* -----------------------------------------------------------------------------
cap frame drop scm_rus_main
synth2 inflow ///
    inflow(2005(1)2009) inflow(2010(1)2014) inflow(2015(1)2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2005(1)2021) mspeperiod(2005(1)2021) ///
    nested ///
    frame(scm_rus_main) nofigure

display _n "=== nested 主估计完成 (period-avg predictors) ==="
matrix W = e(W_weights)
matrix list W

frame scm_rus_main {
    export delimited "$DIR/results/scm_russia_nested_frame.csv", replace
}

* -----------------------------------------------------------------------------
* Placebo 推断: 不加 nested (避免供体国不收敛中断)
* -----------------------------------------------------------------------------
cap frame drop scm_rus
synth2 inflow ///
    inflow(2005(1)2009) inflow(2010(1)2014) inflow(2015(1)2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2005(1)2021) mspeperiod(2005(1)2021) ///
    placebo(unit) frame(scm_rus) nofigure

frame scm_rus {
    export delimited "$DIR/results/scm_russia_frame.csv", replace
}

display _n "✅ 俄罗斯 SCM (inflow, period-avg predictors) 完成 -> results/scm_russia_frame.csv"
