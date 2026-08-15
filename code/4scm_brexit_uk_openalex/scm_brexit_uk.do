* =============================================================================
* 英国 2016 Brexit 公投对学者迁入的因果效应: 合成控制法 (SCM)
* 数据: OpenAlex 国家级 inflow (number_of_inmigrations), 2005-2024
* 处理国: GBR, 处理年 T0=2016 (post=2016,...,2024)
* 供体池: pre (2005-2015) 研究者规模在 GBR 的 [1/5, 5x];
*   |netmigration| pre 年均>=50; 排除 RUS/UKR/BLR (后期战争冲击).
* 预测变量 (Abadie 结构, 适配 T0=2016):
*   inflow 年段均值 2005-08 / 2009-12 / 2013-14, 再加 2015.
*   MSPE 窗口: 全 pre 期 2005-2015.
* 推断: in-space placebo, Post/Pre MSPE 比值排名 p
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

global DIR "$CODE/4scm_brexit_uk_openalex"
cap mkdir "$DIR/results"

import delimited "$DIR/scm_panel.csv", clear varnames(1)

encode country, gen(cid)
tsset cid year

gen inflow = number_of_inmigrations
gen ln_researchers = ln(researchers)

summarize cid if country=="GBR", meanonly
global TRT = r(min)

* -----------------------------------------------------------------------------
* 主分析: synth2 + nested
* -----------------------------------------------------------------------------
cap frame drop scm_gbr_main
synth2 inflow ///
    inflow(2005(1)2008) inflow(2009(1)2012) inflow(2013(1)2014) ///
    inflow(2015), ///
    trunit($TRT) trperiod(2016) ///
    xperiod(2005(1)2015) mspeperiod(2005(1)2015) ///
    nested ///
    frame(scm_gbr_main) nofigure

display _n "=== nested 主估计完成 (Brexit GBR) ==="
matrix W = e(W_weights)
matrix list W

frame scm_gbr_main {
    export delimited "$DIR/results/scm_brexit_uk_nested_frame.csv", replace
}

* -----------------------------------------------------------------------------
* Placebo 推断: 不加 nested
* -----------------------------------------------------------------------------
cap frame drop scm_gbr
synth2 inflow ///
    inflow(2005(1)2008) inflow(2009(1)2012) inflow(2013(1)2014) ///
    inflow(2015), ///
    trunit($TRT) trperiod(2016) ///
    xperiod(2005(1)2015) mspeperiod(2005(1)2015) ///
    placebo(unit) frame(scm_gbr) nofigure

frame scm_gbr {
    export delimited "$DIR/results/scm_brexit_uk_frame.csv", replace
}

display _n "✅ 英国 Brexit SCM (inflow) 完成 -> results/scm_brexit_uk_frame.csv"
