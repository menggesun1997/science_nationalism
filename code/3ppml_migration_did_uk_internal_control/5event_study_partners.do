* =============================================================================
* 英国 (Brexit) 迁移流 — 四条关键走廊的单边 event study
*
* 伙伴国 (ISO3): DEU CHN USA RUS
*
* 选取理由 (论文可引):
*   DEU — 欧盟最大科研伙伴; Brexit 直接冲击英欧人员流动
*   CHN — 最大非西方伙伴; 合作升但迁移模式分化, 地缘政治对照
*   USA — 最大双边走廊; 英语圈/跨大西洋替代欧盟的参照
*   RUS — 地缘政治 "East" 代表; 地图上呈净流入倾斜, 与欧盟故事形成对照
*
* 运行 (二选一):
*   stata-mp -b do 5event_study_partners.do
*   python3 .../13migration_partner_eventstudy.py   (已验证可出图)
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

global FOCAL "GBR"
global T0 = 2016
global WDIR "$CODE/3ppml_migration_did_uk_internal_control"
global THR_OUT = 3
global THR_IN  = 3
global PARTNERS "DEU CHN USA RUS"
do "$CODE/0raw_publiations_process/raw data processing/_mig_es_partner_core.do"
