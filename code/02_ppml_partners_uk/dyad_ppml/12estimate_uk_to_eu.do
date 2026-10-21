*==============================================================*
* 12estimate_uk_to_eu.do
*
* "UK to EU" 方向：对照组是英国自己的其他（非 EU）伙伴。
*
*   P_jt = exp( a_j + mu_t + beta_k * Post_t x 1[j=k] )
*
* a_j 伙伴固定效应；mu_t 年份固定效应，吸收英国整体科研增长与整体国际
* 合作变化。exp(beta_k)-1 即英国与 EU 国家 k 的合作量相对其与对照伙伴
* 合作量的百分比变化。SE 聚类到伙伴国。
*
* 与 11estimate_eu_to_uk.do 的区别只在参照组：同一个 pair 的计数 P_ij
* 是同一个数，但对照集不同，所以两个方向的 beta 不同。
*
* EU27 aggregate: 把 27 国合并成单一处理伙伴后再估计。
*
* 输入 uk_dyad_panel.csv（5build_uk_focal_panel.py 产出）
* 输出 st_uk_to_eu_by_country.csv / st_uk_to_eu_pooled.csv
*==============================================================*

clear all
do "`c(pwd)'/_setup.do"

*--------------------------------------------------------------*
* 面板准备
*--------------------------------------------------------------*
import delimited "$DYAD/uk_dyad_panel.csv", varnames(1) clear
replace partner_country = strupper(strtrim(partner_country))

gen byte is_eu = strpos("$EU27", ";" + partner_country + ";") > 0

* 体量门槛：年均 >= $MIN_AVG 才进样本（EU 国家全部保留为处理伙伴）
qui levelsof year
local nyear = r(r)
bysort partner_country: egen double _tot = total(paper_count)
keep if _tot / `nyear' >= $MIN_AVG | is_eu == 1
drop _tot

* 补零成平衡面板
egen long partner_id = group(partner_country)
preserve
    keep partner_id partner_country is_eu
    duplicates drop
    tempfile xwalk
    save `xwalk'
restore
keep partner_id year paper_count
fillin partner_id year
replace paper_count = 0 if _fillin == 1
drop _fillin
merge m:1 partner_id using `xwalk', assert(match) nogenerate

gen byte post = (year >= $POST_YEAR)
save "$DYAD/uk_dyad_panel.dta", replace

di as result _n _dup(70) "="
di as result "UK-focal panel"
di as result _dup(70) "="
di "obs        " _N
qui levelsof partner_country
di "partners   " r(r)
qui count if is_eu == 1
di "EU dyads   " r(N) / `nyear' " countries"

*--------------------------------------------------------------*
* EU27 aggregate: 27 国合并成单一处理伙伴
*--------------------------------------------------------------*
di as result _n _dup(70) "="
di as result "UK to EU  --  EU27 aggregate"
di as result _dup(70) "="

* 在 dyad 层面估计（不 collapse）：单一 EU 交互项在 27 个 EU 伙伴
* cluster 上变化，所以这里聚类到伙伴国是有效的。若先 collapse 成一个
* EU27 组，交互项只在一个 cluster 内非零，cluster-robust 方差会退化。
preserve
    gen byte treat_post = is_eu * post

    ppmlhdfe paper_count treat_post, ///
        absorb(partner_id year) vce(cluster partner_id) ///
        maxiter(10000) tolerance(1e-8)

    local b  = _b[treat_post]
    local se = _se[treat_post]
    clear
    set obs 1
    gen str24 focal_country = "EU27 aggregate"
    gen int n_partners = .
    gen double coef = `b'
    gen double se   = `se'
    gen double pvalue     = 2*normal(-abs(`b'/`se'))
    gen double pct_change = 100*(exp(`b')-1)
    gen double ci_lo_pct  = 100*(exp(`b'-1.96*`se')-1)
    gen double ci_hi_pct  = 100*(exp(`b'+1.96*`se')-1)
    export delimited "$DYAD/st_uk_to_eu_pooled.csv", replace
restore

*--------------------------------------------------------------*
* 逐个 EU 国家 —— 单次联合回归
*
*   P_jt = exp( a_j + mu_t + sum_k beta_k * Post_t x 1[j=k] )
*
* 27 个 EU 伙伴各带一个交互项，一次估完。好处是其他 EU 国家 post 期的
* 偏离由各自的 beta_k 吸收，不会通过年份固定效应污染对照基准。
*
* 推断说明：这个方向上 dyad 就等于 partner，每个 beta_k 只由一个 cluster
* 识别，是典型的 one-treated-unit 问题。聚类到 partner_id 会退化（27 国
* 得到完全相同的 SE），所以这里报告 robust SE，并用非 EU 伙伴做安慰剂
* 的置换检验给出 p 值（见 13placebo_uk_to_eu.do）。
*--------------------------------------------------------------*
di as result _n _dup(70) "="
di as result "UK to EU  --  per EU country (joint regression, robust SE)"
di as result _dup(70) "="

qui levelsof partner_id if is_eu == 1, local(euids)

local terms ""
foreach k of local euids {
    qui gen byte tp_`k' = (partner_id == `k') * post
    local terms "`terms' tp_`k'"
}

ppmlhdfe paper_count `terms', ///
    absorb(partner_id year) vce(robust) ///
    maxiter(10000) tolerance(1e-8)

qui levelsof partner_id
local npool = r(r)

tempname bc
postfile `bc' str24 focal_country int n_partners ///
    double coef se pvalue pct_change ci_lo_pct ci_hi_pct ///
    using "$DYAD/_st_uk_bc.dta", replace

foreach k of local euids {
    qui levelsof partner_country if partner_id == `k', local(pc) clean
    local b  = _b[tp_`k']
    local se = _se[tp_`k']
    post `bc' ("`pc'") (`npool') (`b') (`se') ///
        (2*normal(-abs(`b'/`se'))) (100*(exp(`b')-1)) ///
        (100*(exp(`b'-1.96*`se')-1)) (100*(exp(`b'+1.96*`se')-1))
}
postclose `bc'
drop tp_*

use "$DYAD/_st_uk_bc.dta", clear
gen byte sig_10 = pvalue < 0.10
gen byte sig_05 = pvalue < 0.05
gen byte sig_01 = pvalue < 0.01
sort pct_change
list focal_country coef se pvalue pct_change ci_lo_pct ci_hi_pct, ///
    noobs sep(0) abbrev(13)
export delimited "$DYAD/st_uk_to_eu_by_country.csv", replace
erase "$DYAD/_st_uk_bc.dta"

di _n as result "saved st_uk_to_eu_pooled.csv / st_uk_to_eu_by_country.csv"
