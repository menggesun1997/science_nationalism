* =============================================================================
* 乌克兰 2022 全面入侵对学者迁入的因果效应: 合成控制法 (SCM)
* 数据: OpenAlex 国家级 inflow (number_of_inmigrations, 迁入学者数), 2005-2024
* 供体池: 科研体量与乌克兰可比的国家 (pre 期研究者规模在 UKR 的 [1/5, 5x] 区间),
*   |netmigration| pre 年均>=50, 排除战争相关国 (RUS/BLR). 处理国 UKR.
* 处理年 T0=2022 (post=2022,2023,2024)
* 结果变量: inflow (迁入学者数).
* 预测变量 (与俄罗斯设定一致, Abadie 经典结构):
*   inflow 年段均值 2005-09 / 2010-14 / 2015-19, 再加处理前近两年 2020, 2021.
*   MSPE 窗口: 全 pre 期 2005-2021.
* 推断: in-space placebo (synth2), Post/Pre MSPE 比值排名 p 值
* =============================================================================
clear all
set more off

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

global DIR "$CODE/4scm_ukraine_openalex"
cap mkdir "$DIR/results"

import delimited "$DIR/scm_panel.csv", clear varnames(1)

* 面板设置: 国家数值 id + 年份
encode country, gen(cid)
tsset cid year

* 结果变量: 迁入学者数 (inflow)
gen inflow = number_of_inmigrations
gen ln_researchers = ln(researchers)

* 处理国 id
summarize cid if country=="UKR", meanonly
global TRT = r(min)

* -----------------------------------------------------------------------------
* 主分析: synth2 + nested
*   预测变量: 年段均值 + 近两年 lag
*   注: nested+placebo 可能不收敛, 故拆成两步
* -----------------------------------------------------------------------------
cap frame drop scm_ukr_main
synth2 inflow ///
    inflow(2005(1)2009) inflow(2010(1)2014) inflow(2015(1)2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2005(1)2021) mspeperiod(2005(1)2021) ///
    nested ///
    frame(scm_ukr_main) nofigure

display _n "=== nested 主估计完成 (period-avg predictors) ==="
matrix W = e(W_weights)
matrix list W

frame scm_ukr_main {
    export delimited "$DIR/results/scm_ukraine_nested_frame.csv", replace
}

* -----------------------------------------------------------------------------
* Placebo 推断: 不加 nested
* -----------------------------------------------------------------------------
cap frame drop scm_ukr
synth2 inflow ///
    inflow(2005(1)2009) inflow(2010(1)2014) inflow(2015(1)2019) ///
    inflow(2020) inflow(2021), ///
    trunit($TRT) trperiod(2022) ///
    xperiod(2005(1)2021) mspeperiod(2005(1)2021) ///
    placebo(unit) frame(scm_ukr) nofigure

frame scm_ukr {
    export delimited "$DIR/results/scm_ukraine_frame.csv", replace
}

display _n "✅ 乌克兰 SCM (inflow, period-avg predictors) 完成 -> results/scm_ukraine_frame.csv"
