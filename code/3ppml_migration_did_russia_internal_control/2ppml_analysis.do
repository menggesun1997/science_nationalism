* =============================================================================
* 机制二 迁移流 - 俄罗斯 (2022 全面入侵)   净流入总量口径
* -----------------------------------------------------------------------------
* 口径变更: 由"逐伙伴双边 PPML DiD" 改为 "focal 层净流入总量" 断点分析。
* 结果变量 (按年汇总所有伙伴):
*   inflow_t  = Σ_j 流入人数 (partner -> RUS)
*   outflow_t = Σ_j 流出人数 (RUS -> partner)
*   net_t     = inflow_t - outflow_t   (净流入; 正=净流入, 负=净流出)
* 说明:
*   (1) 净流入含负值, 不适用 PPML; 故改用水平量时间序列。
*   (2) 总量加总后无 partner 内部对照组, 故用聚合时间序列的
*       前后对比 (pre/post) + 中断时间序列回归 (ITS: post 断点 + 线性趋势)。
*   (3) 总量口径纳入全部伙伴, 不施加 avg_pre 阈值 (阈值仅用于逐伙伴去噪)。
* 输出: results/net_inflow_timeseries.csv
* =============================================================================
clear all
set more off
global FOCAL "RUS"
global T0 = 2022
global WDIR "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/3ppml_migration_did_russia_internal_control"

* ---- 总流入 (in: partner -> focal) 按年汇总 ----
import delimited "$WDIR/ppml_data_in.csv", clear varnames(1)
collapse (sum) inflow=paper_count, by(year rel_year)
tempfile fin
save `fin'

* ---- 总流出 (out: focal -> partner) 按年汇总 ----
import delimited "$WDIR/ppml_data_out.csv", clear varnames(1)
collapse (sum) outflow=paper_count, by(year)
merge 1:1 year using `fin', nogen
sort year

* ---- 净流入 ----
gen net_inflow = inflow - outflow
gen post = year >= $T0
label var inflow     "总流入 partner->RUS"
label var outflow    "总流出 RUS->partner"
label var net_inflow "净流入 (in - out)"

display _dup(80) "="
display "$FOCAL  净流入总量  Post>=$T0"
display _dup(80) "="

* ---- 逐年时间序列 ----
list year rel_year inflow outflow net_inflow post, clean noobs

* ---- pre/post 前后对比 ----
display _n "---- pre/post 均值对比 (每年量) ----"
foreach v in inflow outflow net_inflow {
    quietly summarize `v' if post==0
    local pre = r(mean)
    quietly summarize `v' if post==1
    local pos = r(mean)
    local chg = `pos' - `pre'
    local pct = cond(`pre'!=0, 100*`chg'/abs(`pre'), .)
    display %-12s "`v'" ": pre=" %9.2f `pre' "  post=" %9.2f `pos' ///
        "  Δ=" %9.2f `chg' "  (" %7.1f `pct' "%)"
}

* ---- 中断时间序列 (ITS): post 水平断点 + 事件时间线性趋势 ----
* 诊断结论: 逐年序列 post 点数极少 (RUS/UKR 仅 3), 且残差自相关.
* 故: (1) 主回归改用 Newey-West HAC 标准误 (lag 1) 处理自相关;
*     (2) 增二次趋势稳健性 (rel_year^2), 检验 pre 是否线性可外推.
tsset year
capture drop rel_year2
gen rel_year2 = rel_year^2
display _n "---- ITS 中断回归 (post 断点, t=rel_year 趋势) ----"
foreach v in inflow outflow net_inflow {
    display _n "== ITS: `v'  [OLS] =="
    regress `v' post rel_year
    display _n "== ITS: `v'  [Newey-West HAC lag(1)] =="
    newey `v' post rel_year, lag(1)
    display _n "== ITS: `v'  [+二次趋势稳健性] =="
    regress `v' post rel_year rel_year2
    test rel_year2
}

* ---- 导出逐年序列 ----
gen focal = "$FOCAL"
order focal year rel_year inflow outflow net_inflow post
export delimited using "$WDIR/results/net_inflow_timeseries.csv", replace

display _n "✅ $FOCAL 净流入总量分析完成 -> results/net_inflow_timeseries.csv"
