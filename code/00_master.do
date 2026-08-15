*===============================================================*
* 00_master.do — Figure 1 end-to-end build
*
* Runs the six synthetic-control analyses behind Figure 1 panels a-l,
* then combines them into the final figure.
*
*   Steps 1-2  Brexit          (2016)  panels a-d
*   Steps 3-4  Crimea          (2014)  panels e-h
*   Steps 5-6  Russia-Ukraine  (2022)  panels i-l
*   Step  7    combine 12 panels -> code/picutres/figure1.pdf
*
* Usage — from the repository root:
*     stata-mp -b do code/00_master.do
* or from inside Stata:
*     do "code/00_master.do"
*
* Requires: synth (SSC). config.do installs missing SSC packages.
* Runtime: several hours; each synth call runs hundreds of placebo
* permutations.
*===============================================================*
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

* The Okabe-Ito palette ($C_EU, $C_UK, $C_RU, $C_UA, $C_SHADE, $C_LINE)
* is defined in config.do and shared by every panel do-file.

* ── Run each panel's analysis + plotting do-file ─────────────────────────
di as result "=== Step 1/6: Brexit – Total Publications (panels a, c) ==="
do "$CODE/Brexit-stata_external_try/total_publications/compare.do"

di as result "=== Step 2/6: Brexit – Intl. Ratio (panels b, d) ==="
do "$CODE/Brexit-stata_external_try/intl_ratio/compare_intl_ratio.do"

di as result "=== Step 3/6: Crimea – Total Publications (panels e, g) ==="
do "$CODE/crimes/total_publications/compare_total.do"

di as result "=== Step 4/6: Crimea – Intl. Ratio (panels f, h) ==="
do "$CODE/crimes/intl_ratio/intl_ratio_compare.do"

di as result "=== Step 5/6: War – Total Publications (panels i, k) ==="
do "$CODE/crimes_2015_2022/total_publications/compare_total_2022.do"

di as result "=== Step 6/6: War – Intl. Ratio (panels j, l) ==="
do "$CODE/crimes_2015_2022/intl_ratio/intl_ratio_compare.do"

* ── Combine panels and export the final figure ───────────────────────────
di as result "=== Step 7/7: combining all 12 panels into Figure 1 ==="
do "$CODE/99_combine_figure1.do"

di as result "=== Done. Figure 1 written to code/picutres/figure1.pdf ==="
