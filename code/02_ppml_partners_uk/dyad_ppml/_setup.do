*==============================================================*
* _setup.do — 路径解析 + 共享设定，dyad_ppml 下每个 do-file 都先跑它
*
* 定义 $DYAD（本目录）以及 code/config.do 的全部全局量（$ROOT/$CODE/...）。
* 解析顺序与 config.do 一致，但同时处理 Windows 的反斜杠分隔符。
*==============================================================*

set more off

* ── 定位仓库根目录 ─────────────────────────────────────────────
capture confirm file "$ROOT/code/paths.py"
if _rc {
    global ROOT ""
}

if "$ROOT" == "" {
    local envroot : environment SCIENCE_NATIONALISM_ROOT
    if "`envroot'" != "" {
        capture confirm file "`envroot'/code/paths.py"
        if !_rc global ROOT "`envroot'"
    }
}

* 从工作目录向上找 code/paths.py。regexr 的两种分隔符都试，
* 以兼容 Windows 下 c(pwd) 返回反斜杠的情况。
if "$ROOT" == "" {
    local cand "`c(pwd)'"
    forvalues up = 1/12 {
        capture confirm file "`cand'/code/paths.py"
        if !_rc {
            global ROOT "`cand'"
            continue, break
        }
        local shorter = regexr("`cand'", "[/\\][^/\\]+$", "")
        if "`shorter'" == "`cand'" | "`shorter'" == "" continue, break
        local cand "`shorter'"
    }
}

if "$ROOT" == "" {
    di as error "{hline 70}"
    di as error "_setup.do could not locate the repository root."
    di as error `"Set it once per session, then rerun:"'
    di as error `"    global ROOT "/path/to/sicence nationism""'
    di as error "{hline 70}"
    exit 601
}

do "$ROOT/code/config.do"

global DYAD "$CODE/02_ppml_partners_uk/dyad_ppml"

* ── 共享设定 ───────────────────────────────────────────────────
* Post_t = 1[t >= 2017]；event study 省略参照年 2016（公投年）
global POST_YEAR  2017
global REF_YEAR   2016

* 伙伴体量门槛：年均合作少于该值的伙伴不进对照池
global MIN_AVG    5

* 对照池是否包含其他 EU-27 成员。
* 1 = 保留（基线）。EU 内部合作占 EU-27 对外合作约 45%，是组合里最大的
*     一块，也是英国脱欧后最自然的替代对象。剔除它会让 mu_it 只由第三国
*     合作定义，严重扭曲"i 的整体活跃度"这一参照基准。
* 0 = 剔除，仅作稳健性检验（若担心 EU 内部合作本身被 Brexit 间接影响）。
global INCL_EU    1

global UK "UNITED KINGDOM"

* EU-27 名单，分号分隔便于用 strpos 做成员判断
* （避免 foreach 对含空格国名的引号处理问题）
global EU27 ";AUSTRIA;BELGIUM;BULGARIA;CROATIA;CYPRUS;CZECHIA;DENMARK;ESTONIA;FINLAND;FRANCE;GERMANY;GREECE;HUNGARY;IRELAND;ITALY;LATVIA;LITHUANIA;LUXEMBOURG;MALTA;NETHERLANDS;POLAND;PORTUGAL;ROMANIA;SLOVAK REPUBLIC;SLOVENIA;SPAIN;SWEDEN;"

di as result "_setup.do: DYAD = $DYAD"
