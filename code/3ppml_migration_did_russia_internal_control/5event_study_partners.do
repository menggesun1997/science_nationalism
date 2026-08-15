* 俄罗斯 — 四条关键走廊单边 event study
* 伙伴: DEU CHN USA UKR (欧盟 / 东方 / 西方 / 战争直接对手)
clear all
set more off
global FOCAL "RUS"
global T0 = 2022
global WDIR "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/3ppml_migration_did_russia_internal_control"
global THR_OUT = 2
global THR_IN  = 2
global PARTNERS "DEU CHN USA UKR"
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw data processing/_mig_es_partner_core.do"
