*==============================================================*
* 16exclude_china_us.do
*
* 检验：event study 的系数持续下行，是否由对照池里高速增长的伙伴
* （尤其中国、美国）推动？
*
* 机制：mu_it 是 EU 国家-年固定效应，吸收 i 整个伙伴组合的平均增长。
* 若中美在 i 的组合里增速远高于英国，mu_it 被推高，UK dyad 相对就
* 越来越差——即便英国的绝对合作量在涨。把中美移出对照池即可检验。
*
* 对照池设定：
*   A  baseline            全部非 EU 伙伴
*   B  drop CHINA + US
*   C  drop 增速前四分位的伙伴（数据驱动版）
*
* 输出 st_pool_sensitivity.csv   三种对照池的 pooled beta
*       st_event_dropcnus.csv     B 的 event study
*       st_pool_shares.csv        中美在对照池中的份额演变
*==============================================================*

clear all
do "`c(pwd)'/_setup.do"

*--------------------------------------------------------------*
* 0  先看中美在对照池里的份额怎么变
*    如果份额明显上升，机制就成立
*--------------------------------------------------------------*
use "$DYAD/dyad_panel.dta", clear

gen byte cn_us = inlist(partner_country, "CHINA", "UNITED STATES")

preserve
    gen byte grp = 1 if uk
    replace  grp = 2 if cn_us
    replace  grp = 3 if missing(grp)

    collapse (sum) paper_count, by(year grp)
    reshape wide paper_count, i(year) j(grp)
    rename paper_count1 n_uk
    rename paper_count2 n_cnus
    rename paper_count3 n_other

    egen double tot = rowtotal(n_uk n_cnus n_other)
    gen double sh_uk   = 100 * n_uk   / tot
    gen double sh_cnus = 100 * n_cnus / tot

    di as result _n _dup(70) "="
    di as result "Shares in EU-27 partner portfolio (%)"
    di as result _dup(70) "="
    list year n_uk n_cnus n_other sh_uk sh_cnus, noobs sep(0) abbrev(10)
    export delimited "$DYAD/st_pool_shares.csv", replace
restore

*--------------------------------------------------------------*
* 1  标记高增长伙伴（数据驱动的 C 方案）
*    用 2005-2016 的对数增长率，避免用 post 期信息做筛选
*--------------------------------------------------------------*
preserve
    keep if year <= 2016 & uk == 0
    collapse (sum) paper_count, by(partner_country year)
    bysort partner_country (year): gen double g = ///
        (ln(paper_count[_N] + 1) - ln(paper_count[1] + 1)) / (year[_N] - year[1])
    bysort partner_country: keep if _n == 1
    keep partner_country g
    tempfile growth
    save `growth'
restore

merge m:1 partner_country using `growth', keep(master match) nogenerate
qui sum g if uk == 0, detail
local g75 = r(p75)
gen byte fast = (g >= `g75') & !missing(g) & uk == 0
di as txt _n "pre-period growth p75 = " %6.4f `g75'
qui levelsof partner_country if fast == 1
di as txt "fast-growing partners dropped in spec C: " r(r)

*--------------------------------------------------------------*
* 2  三种对照池下的 pooled beta
*--------------------------------------------------------------*
tempname ps
postfile `ps' str28 pool int n_obs int n_partners ///
    double coef se pvalue pct_change ci_lo_pct ci_hi_pct ///
    using "$DYAD/_st_ps.dta", replace

* 宏：跑一次并记录
capture program drop _runpool
program define _runpool
    args tag cond handle
    qui ppmlhdfe paper_count post_uk if `cond', ///
        absorb(pair focal_year) vce(cluster pair) ///
        maxiter(10000) tolerance(1e-8)
    local b  = _b[post_uk]
    local se = _se[post_uk]
    qui count if `cond'
    local n = r(N)
    qui levelsof partner_country if `cond'
    local np = r(r)
    di as result "`tag'" _col(30) %8.2f 100*(exp(`b')-1) "%   [" ///
        %7.2f 100*(exp(`b'-1.96*`se')-1) ", " ///
        %7.2f 100*(exp(`b'+1.96*`se')-1) "]   p = " ///
        %6.4f 2*normal(-abs(`b'/`se')) "   n = " `n'
    post `handle' ("`tag'") (`n') (`np') (`b') (`se') ///
        (2*normal(-abs(`b'/`se'))) (100*(exp(`b')-1)) ///
        (100*(exp(`b'-1.96*`se')-1)) (100*(exp(`b'+1.96*`se')-1))
end

di as result _n _dup(78) "="
di as result "Pooled beta under different control pools"
di as result _dup(78) "="

_runpool "A baseline"            "1"                  `ps'
_runpool "B drop CHINA + US"     "cn_us == 0"         `ps'
_runpool "C drop fast-growing"   "fast == 0"          `ps'
_runpool "B+C drop both"         "cn_us == 0 & fast == 0" `ps'

postclose `ps'

preserve
    use "$DYAD/_st_ps.dta", clear
    export delimited "$DYAD/st_pool_sensitivity.csv", replace
restore
erase "$DYAD/_st_ps.dta"

*--------------------------------------------------------------*
* 3  B 方案（剔除中美）的 event study
*    与 baseline 的逐年系数并排输出，看预趋势是否被压平
*--------------------------------------------------------------*
di as result _n _dup(70) "="
di as result "Event study, control pool excludes CHINA + US"
di as result _dup(70) "="

qui levelsof year, local(yrs)
local terms ""
foreach y of local yrs {
    if `y' != $REF_YEAR {
        qui gen byte uk_`y' = uk * (year == `y')
        local terms "`terms' uk_`y'"
    }
}

qui ppmlhdfe paper_count `terms' if cn_us == 0, ///
    absorb(pair focal_year) vce(cluster pair) ///
    maxiter(10000) tolerance(1e-8)

tempname es
postfile `es' int year double coef se pvalue pct_change ///
    ci_lo_pct ci_hi_pct using "$DYAD/_st_es2.dta", replace
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

use "$DYAD/_st_es2.dta", clear
sort year
list year coef se pvalue pct_change ci_lo_pct ci_hi_pct, ///
    noobs sep(0) abbrev(12)
export delimited "$DYAD/st_event_dropcnus.csv", replace
erase "$DYAD/_st_es2.dta"

di _n as result "saved st_pool_shares.csv / st_pool_sensitivity.csv"
di as result "      st_event_dropcnus.csv"
