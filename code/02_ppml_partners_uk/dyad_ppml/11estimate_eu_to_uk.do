*==============================================================*
* 11estimate_eu_to_uk.do
*
* "EU to UK" 方向：对照组是每个 EU 国家自己的其他伙伴。
*
* 规格 1（pooled）
*   P_ijt = exp( a_ij + mu_it + beta * Post_t x UK_j )
* 规格 2（event study）
*   P_ijt = exp( a_ij + mu_it + sum_k beta_k * 1[t=k] x UK_j )
* 规格 3（逐国）
*   P_jt  = exp( a_j  + mu_t  + beta * Post_t x UK_j )
*
* a_ij 国家对固定效应，mu_it 为 EU 国家-年固定效应。因 mu_it 已吸收 i 的
* 总体活跃度，exp(beta)-1 即 i 与 UK 合作量相对其与对照伙伴的百分比变化。
* SE 聚类到 country pair。估计量 ppmlhdfe。
*
* 输出 st_eu_to_uk_pooled.csv / _event.csv / _by_country.csv
*==============================================================*

clear all
do "`c(pwd)'/_setup.do"

use "$DYAD/dyad_panel.dta", clear

*--------------------------------------------------------------*
* 时点覆盖：把处理时点移到 2021（脱欧后首个完整年），参照年 2020。
* 仅在本文件内局部生效，不改动共用的 _setup.do。
* 需据新 POST_YEAR 重建 post / post_uk。
*--------------------------------------------------------------*
global POST_YEAR 2021
global REF_YEAR  2020

capture drop post post_uk
gen byte post    = (year >= $POST_YEAR)
gen byte post_uk = post * uk

di as result _n "时点覆盖: POST_YEAR = $POST_YEAR, REF_YEAR = $REF_YEAR"

*--------------------------------------------------------------*
* 规格 1: pooled
*--------------------------------------------------------------*
di as result _n _dup(70) "="
di as result "Spec 1  pooled:  a_ij + mu_it + beta * Post x UK"
di as result _dup(70) "="

ppmlhdfe paper_count post_uk, ///
    absorb(pair focal_year) vce(cluster pair) ///
    maxiter(10000) tolerance(1e-8)

local b  = _b[post_uk]
local se = _se[post_uk]
local p  = 2 * normal(-abs(`b' / `se'))
local pct    = 100 * (exp(`b') - 1)
local pct_lo = 100 * (exp(`b' - 1.96 * `se') - 1)
local pct_hi = 100 * (exp(`b' + 1.96 * `se') - 1)

di as result _n "beta        " %9.4f `b' "  (se " %6.4f `se' ", p " %6.4f `p' ")"
di as result    "exp(beta)-1 " %8.2f `pct' "%  [" %7.2f `pct_lo' "%, " ///
                %7.2f `pct_hi' "%]"

preserve
    clear
    set obs 1
    gen str20 spec = "pooled"
    gen double coef = `b'
    gen double se   = `se'
    gen double pvalue = `p'
    gen double pct_change = `pct'
    gen double ci_lo_pct  = `pct_lo'
    gen double ci_hi_pct  = `pct_hi'
    export delimited "$DYAD/st_eu_to_uk_pooled.csv", replace
restore

*--------------------------------------------------------------*
* 规格 1b: 两段 beta（公投期 + 脱欧期）
*   P_ijt = exp( a_ij + mu_it + b1 * PostRef_t x UK_j
*                             + b2 * Brexit_t  x UK_j )
* PostRef_t = 1[t >= $REF_START]（含 2021 之后），Brexit_t = 1[t >= $POST_YEAR]
* 两个 dummy 嵌套，故：
*   b1      = 公投期效应（相对 PostRef 之前的年份）
*   b2      = 脱欧后相对公投期的增量效应
*   b1 + b2 = 脱欧后的累计效应
*--------------------------------------------------------------*
global REF_START 2016

di as result _n _dup(70) "="
di as result "Spec 1b  two-period: b1*PostRef x UK + b2*Brexit x UK"
di as result _dup(70) "="

capture drop postref_uk brexit_uk
gen byte postref_uk = (year >= $REF_START)  * uk
gen byte brexit_uk  = (year >= $POST_YEAR)  * uk

ppmlhdfe paper_count postref_uk brexit_uk, ///
    absorb(pair focal_year) vce(cluster pair) ///
    maxiter(10000) tolerance(1e-8)

* b1、b2 以及累计效应 b1+b2（用 lincom 取正确的组合 SE）
local b1  = _b[postref_uk]
local se1 = _se[postref_uk]
local b2  = _b[brexit_uk]
local se2 = _se[brexit_uk]

qui lincom postref_uk + brexit_uk
local b3  = r(estimate)
local se3 = r(se)

di as result _n "{hline 72}"
di as result %-26s "term" %9s "beta" %9s "se" %9s "p" %10s "pct" %18s "95% CI (pct)"
di as result "{hline 72}"

forvalues k = 1/3 {
    if `k' == 1 local lab "b1  PostRef x UK (2016-)"
    if `k' == 2 local lab "b2  Brexit  x UK (2021-)"
    if `k' == 3 local lab "b1+b2  cumulative 2021-"
    local b  = `b`k''
    local se = `se`k''
    local p  = 2 * normal(-abs(`b' / `se'))
    di as result %-26s "`lab'" %9.4f `b' %9.4f `se' %9.4f `p' ///
        %9.2f 100*(exp(`b')-1) "%" ///
        %9.2f 100*(exp(`b'-1.96*`se')-1) "%," ///
        %8.2f 100*(exp(`b'+1.96*`se')-1) "%"
}
di as result "{hline 72}"

preserve
    clear
    set obs 3
    gen str26 term = ""
    replace term = "postref_uk"  in 1
    replace term = "brexit_uk"   in 2
    replace term = "cumulative"  in 3
    gen double coef = .
    gen double se   = .
    foreach k of numlist 1/3 {
        replace coef = `b`k''  in `k'
        replace se   = `se`k'' in `k'
    }
    gen double pvalue     = 2 * normal(-abs(coef / se))
    gen double pct_change = 100 * (exp(coef) - 1)
    gen double ci_lo_pct  = 100 * (exp(coef - 1.96 * se) - 1)
    gen double ci_hi_pct  = 100 * (exp(coef + 1.96 * se) - 1)
    export delimited "$DYAD/st_eu_to_uk_twoperiod.csv", replace
restore
drop postref_uk brexit_uk

*--------------------------------------------------------------*
* 规格 2: event study（省略参照年 $REF_YEAR）
*--------------------------------------------------------------*
di as result _n _dup(70) "="
di as result "Spec 2  event study (reference year $REF_YEAR)"
di as result _dup(70) "="

qui levelsof year, local(yrs)
local terms ""
foreach y of local yrs {
    if `y' != $REF_YEAR {
        qui gen byte uk_`y' = uk * (year == `y')
        local terms "`terms' uk_`y'"
    }
}

ppmlhdfe paper_count `terms', ///
    absorb(pair focal_year) vce(cluster pair) ///
    maxiter(10000) tolerance(1e-8)

tempname es
postfile `es' int year double coef se pvalue pct_change ci_lo_pct ci_hi_pct ///
    using "$DYAD/_st_es.dta", replace
post `es' ($REF_YEAR) (0) (0) (.) (0) (0) (0)
foreach y of local yrs {
    if `y' != $REF_YEAR {
        local b  = _b[uk_`y']
        local se = _se[uk_`y']
        post `es' (`y') (`b') (`se') (2*normal(-abs(`b'/`se'))) ///
            (100*(exp(`b')-1)) (100*(exp(`b'-1.96*`se')-1)) ///
            (100*(exp(`b'+1.96*`se')-1))
    }
}
postclose `es'

preserve
    use "$DYAD/_st_es.dta", clear
    sort year
    list year coef se pvalue pct_change ci_lo_pct ci_hi_pct, ///
        noobs sep(0) abbrev(12)
    export delimited "$DYAD/st_eu_to_uk_event.csv", replace
restore
erase "$DYAD/_st_es.dta"
drop uk_*

*--------------------------------------------------------------*
* 规格 3: 逐个 EU 国家
*--------------------------------------------------------------*
di as result _n _dup(70) "="
di as result "Spec 3  per-country:  a_j + mu_t + beta * Post x UK"
di as result _dup(70) "="

tempname bc
postfile `bc' str24 focal_country int n_partners ///
    double coef se pvalue pct_change ci_lo_pct ci_hi_pct ///
    using "$DYAD/_st_bc.dta", replace

qui levelsof focal_id, local(ids)
foreach i of local ids {
    qui levelsof focal_country if focal_id == `i', local(fc) clean
    qui count if focal_id == `i' & uk == 1
    qui levelsof partner_id if focal_id == `i'
    local np = r(r)

    capture qui ppmlhdfe paper_count post_uk if focal_id == `i', ///
        absorb(partner_id year) vce(cluster partner_id) ///
        maxiter(10000) tolerance(1e-8)
    if _rc {
        di as error "  !! `fc': ppmlhdfe failed (rc = " _rc ")"
        continue
    }
    local b  = _b[post_uk]
    local se = _se[post_uk]
    post `bc' ("`fc'") (`np') (`b') (`se') (2*normal(-abs(`b'/`se'))) ///
        (100*(exp(`b')-1)) (100*(exp(`b'-1.96*`se')-1)) ///
        (100*(exp(`b'+1.96*`se')-1))
}
postclose `bc'

use "$DYAD/_st_bc.dta", clear
gen byte sig_10 = pvalue < 0.10
gen byte sig_05 = pvalue < 0.05
gen byte sig_01 = pvalue < 0.01
sort pct_change
list focal_country n_partners coef se pvalue pct_change ///
    ci_lo_pct ci_hi_pct, noobs sep(0) abbrev(13)
export delimited "$DYAD/st_eu_to_uk_by_country.csv", replace
erase "$DYAD/_st_bc.dta"

di _n as result "saved st_eu_to_uk_pooled.csv / _event.csv / _by_country.csv"
