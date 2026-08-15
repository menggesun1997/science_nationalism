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
global FOCAL "RUS"
global T0 = 2022
global WDIR "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/3ppml_migration_did_russia_internal_control_mpidr"

do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw data processing/_mig_its_mpidr_core.do"
