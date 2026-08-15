* =============================================================================
* 机制二 迁移流 - 俄罗斯 (2022 全面入侵)   净流入总量口径  [MPIDR 数据版]
* -----------------------------------------------------------------------------
* 数据来源: MPIDR Scholarly Migration Database 2.0 (2026 V2) 国家级文件,
*           gender=all, field=all, in/out=number_of_in/outmigrations, 2008-2024。
* 复刻 3ppml_migration_did_russia_internal_control/2ppml_analysis.do 的
* "focal 层净流入总量" 中断时间序列 (ITS) 分析, 分别对 openalex / scopus 两库跑。
* 结果变量 (按年汇总所有伙伴):
*   inflow_t  = Σ_j 流入人数 (partner -> RUS)
*   outflow_t = Σ_j 流出人数 (RUS -> partner)
*   net_t     = inflow_t - outflow_t   (净流入; 正=净流入, 负=净流出)
* 模型 (ITS): Y_t = b0 + b1*post + b2*rel_year + e
* 输出: results/net_inflow_timeseries_<prov>.csv, results/its_coef_<prov>.csv
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

global FOCAL "RUS"
global T0 = 2022
global WDIR "$CODE/3ppml_migration_did_russia_internal_control_mpidr"

do "$CODE/0raw_publiations_process/raw data processing/_mig_its_mpidr_core.do"
