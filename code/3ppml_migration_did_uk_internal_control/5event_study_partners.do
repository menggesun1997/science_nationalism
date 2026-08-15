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
global FOCAL "GBR"
global T0 = 2016
global WDIR "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/3ppml_migration_did_uk_internal_control"
global THR_OUT = 3
global THR_IN  = 3
global PARTNERS "DEU CHN USA RUS"
do "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw data processing/_mig_es_partner_core.do"
