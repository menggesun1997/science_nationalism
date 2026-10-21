*==============================================================*
* 13placebo_uk_to_eu.do
*
* UK->EU 方向的置换检验。
*
* 该方向每个 beta_k 只由一个 dyad 识别（UK-focal 面板里 dyad 就等于
* partner），cluster-robust 推断不可用。这里把每个非 EU 伙伴轮流当作
* "假处理"跑同一个规格，得到 beta 在无处理情形下的分布，再看真实的
* beta_k 落在分布的哪个位置：
*
*   p_k = Pr( |beta_placebo| >= |beta_k| )
*
* 这是 SCM 文献标准的 in-space placebo 推断，不依赖渐近方差。
*
* 输出 st_uk_to_eu_placebo.csv（安慰剂分布）
*       更新 st_uk_to_eu_by_country.csv 加入 p_placebo 列
*==============================================================*

clear all
do "`c(pwd)'/_setup.do"

use "$DYAD/uk_dyad_panel.dta", clear

* 安慰剂只用体量可比的非 EU 伙伴，避免极小国的噪声主导分布
bysort partner_id: egen double _tot = total(paper_count)
qui sum _tot if is_eu == 1, detail
local eu_p10 = r(p10)
di as txt "EU 伙伴总量的 10 分位: " %12.0f `eu_p10'

qui levelsof partner_id if is_eu == 0 & _tot >= `eu_p10', local(placebos)
di as txt "安慰剂伙伴数: " `: word count `placebos''

tempname pb
postfile `pb' str24 partner_country double coef se using ///
    "$DYAD/_st_pb.dta", replace

foreach k of local placebos {
    qui levelsof partner_country if partner_id == `k', local(pc) clean

    * 对照池 = 其他非 EU 伙伴 + 当前假处理国 k（EU 国家全部排除，
    * 因为它们是真实被处理的，不能当对照）
    qui gen byte _in = (is_eu == 0)
    qui gen byte tp  = (partner_id == `k') * post

    capture qui ppmlhdfe paper_count tp if _in, ///
        absorb(partner_id year) vce(robust) ///
        maxiter(10000) tolerance(1e-8)
    if !_rc {
        post `pb' ("`pc'") (_b[tp]) (_se[tp])
    }
    else {
        di as error "  !! `pc': rc = " _rc
    }
    drop _in tp
}
postclose `pb'

*--------------------------------------------------------------*
* 安慰剂分布摘要
*--------------------------------------------------------------*
use "$DYAD/_st_pb.dta", clear
gen double abs_coef = abs(coef)
gen double pct_change = 100*(exp(coef)-1)

di as result _n _dup(70) "="
di as result "Placebo distribution of beta (non-EU partners)"
di as result _dup(70) "="
sum coef, detail
di as txt _n "|beta| 分位数:"
_pctile abs_coef, percentiles(50 75 90 95 99)
di "  p50 = " %7.4f r(r1) "   p75 = " %7.4f r(r2) ///
   "   p90 = " %7.4f r(r3) "   p95 = " %7.4f r(r4) "   p99 = " %7.4f r(r5)

local npb = _N
export delimited "$DYAD/st_uk_to_eu_placebo.csv", replace

* 把 |beta_placebo| 存进 local，供下面算经验 p 值
forvalues i = 1/`npb' {
    local pb`i' = abs_coef[`i']
}

*--------------------------------------------------------------*
* 经验 p 值：p_k = Pr(|beta_placebo| >= |beta_k|)
*--------------------------------------------------------------*
import delimited "$DYAD/st_uk_to_eu_by_country.csv", varnames(1) clear

gen double p_placebo = .
gen int n_placebo = `npb'

forvalues r = 1/`=_N' {
    local bk = abs(coef[`r'])
    local cnt = 0
    forvalues i = 1/`npb' {
        if `pb`i'' >= `bk' local ++cnt
    }
    qui replace p_placebo = `cnt' / `npb' in `r'
}

gen byte sigp_10 = p_placebo <= 0.10
gen byte sigp_05 = p_placebo <= 0.05

sort pct_change
di as result _n _dup(78) "="
di as result "UK to EU: robust SE vs placebo-based p-value"
di as result _dup(78) "="
list focal_country pct_change ci_lo_pct ci_hi_pct pvalue p_placebo, ///
    noobs sep(0) abbrev(12)

export delimited "$DYAD/st_uk_to_eu_by_country.csv", replace
erase "$DYAD/_st_pb.dta"

di _n as result "saved st_uk_to_eu_placebo.csv"
di as result "updated st_uk_to_eu_by_country.csv (+ p_placebo)"
