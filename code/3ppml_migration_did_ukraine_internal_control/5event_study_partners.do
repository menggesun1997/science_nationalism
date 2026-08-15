* 乌克兰 — 四条关键走廊单边 event study
* 伙伴: DEU CHN USA RUS (欧盟 / 东方 / 西方 / 战争直接对手)
clear all
set more off
global FOCAL "UKR"
global T0 = 2022
global WDIR "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/3ppml_migration_did_ukraine_internal_control"
global THR_OUT = 1
global THR_IN  = 1
global PARTNERS "DEU CHN USA RUS"
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw data processing/_mig_es_partner_core.do"
