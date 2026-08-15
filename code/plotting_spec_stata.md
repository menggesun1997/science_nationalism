# Figure 1 绘图规格（Stata）

## 架构

```
analysis/*.do  →  results/*.dta  →  plot/*.do  →  output/gph/*.gph  →  99_combine_figure1.do
```

- **analysis**：只跑 SCM，结果存 `.dta`，不重复运行
- **plot**：只读 `.dta` 画图，可反复修改
- **`00_master.do`**：一键运行全流程（分析层默认注释掉）

---

## 一、文件结构

```
/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/
├── 00_master.do
├── 99_combine_figure1.do
├── analysis/
│   ├── 01_brexit_total.do        # EU & UK 总发文量 SCM
│   ├── 02_brexit_ratio.do        # EU & UK 国际合作比率 SCM
│   ├── 03_crimea_total.do        # Russia & Ukraine 总发文量 SCM（Crimea）
│   ├── 04_crimea_ratio.do        # Russia & Ukraine 国际合作比率 SCM（Crimea）
│   ├── 05_war_total.do           # Russia & Ukraine 总发文量 SCM（War）
│   └── 06_war_ratio.do           # Russia & Ukraine 国际合作比率 SCM（War）
├── plot/
│   ├── p01_brexit_total.do       # panel a（EU）& panel c（UK）
│   ├── p02_brexit_ratio.do       # panel b（EU）& panel d（UK）
│   ├── p03_crimea_total.do       # panel e（Russia）& panel g（Ukraine）
│   ├── p04_crimea_ratio.do       # panel f（Russia）& panel h（Ukraine）
│   ├── p05_war_total.do          # panel i（Russia）& panel k（Ukraine）
│   └── p06_war_ratio.do          # panel j（Russia）& panel l（Ukraine）
├── results/                      # 分析层中间产物
│   ├── brexit_total.dta
│   ├── brexit_ratio.dta
│   ├── crimea_total.dta
│   ├── crimea_ratio.dta
│   ├── war_total.dta
│   └── war_ratio.dta
├── output/gph/                   # panel_a.gph … panel_l.gph + legend_only.gph
└── picutres/                     # figure1.pdf, figure1.png
```

---

## 二、尺寸规格

### 目标视觉效果

以 `figure1_redrawn.pdf`（Python 示意图）作为**比例和尺寸的参照**：
- 3 行 × 4 列，每个 panel 接近正方形
- 左侧行标签文字清晰可读，不被压缩
- 底部图例为单行，高度约为主图区的 10%

该示意图的**以下内容不要照搬**，内容以本文档规格为准：
- ❌ 置信区间阴影带（SCM 无传统 CI）
- ❌ Treatment effect 标注在左下角（应在左上角）
- ❌ 无数据点 marker（应加 `connected`）
- ❌ 有主标题（不要）

### 整体图（`graph combine` 最终输出）

| 参数 | 值 | 说明 |
|---|---|---|
| `xsize` | 11 英寸 | ≈ 180 mm，Nature 双栏宽度 |
| `ysize` | 8 英寸 | ≈ 200 mm，含底部图例行 |
| 输出分辨率 | 300 DPI（PNG）+ 矢量（PDF） | 投稿标准 |
| 布局 | 3 行 × 4 列 | 共 12 个 panel |

> `ysize(8)` 中主图区约占 7.5 英寸、图例行约占 0.5 英寸，对应参照图的比例。

### 单个 panel 尺寸

**单个 panel 不需要也不应该在 `twoway` 里单独设 `xsize`/`ysize`**，其显示尺寸完全由最终 `graph combine` / `grc1leg` 自动计算：

```
单个 panel 宽度 ≈ xsize(11) ÷ cols(4) ≈ 2.75 英寸 ≈ 70 mm
单个 panel 高度 ≈ ysize(8)  ÷ rows(3) ≈ 2.67 英寸 ≈ 68 mm
（实际绘图区再减去 imargin 和 margin 占用，约 60×60 mm，接近正方形）
```

想调整子图大小，只改合并文件里的以下三个参数：

| 想要的效果 | 改哪里 |
|---|---|
| 子图整体更大/更小 | 调大/小 `xsize` 和 `ysize` |
| 子图内文字/线条更大 | 调高 `iscale`（如 0.5 → 0.55） |
| 子图比例变宽/变高 | 调整 `xsize` 与 `ysize` 的比值 |

> 如需单独预览某个 panel 的效果，可在 `twoway` 内**临时**加 `xsize(2.75) ysize(2.67)`，预览后删去，不影响 `graph combine` 最终布局。

### `iscale` 对字号的影响

`iscale(0.5)` 会将子图内所有元素缩放至 50%，因此 **`twoway` 内的字号需要按约 2 倍设置**，最终视觉效果才符合规范：

| 元素 | `twoway` 中设置 | 合并后视觉效果 |
|---|---|---|
| 子图标题 | `medium`（≈ 10 pt） | ≈ 8 pt |
| 轴刻度 | `medsmall`（≈ 9 pt） | ≈ 7.5 pt |
| 事件标注 / Treatment effect 框 | `small`（≈ 8 pt） | ≈ 7 pt |
| 行标签（ytitle 事件名） | `large`（≈ 12 pt） | ≈ 10 pt |

> 若合并后文字偏小，可将 `iscale` 从 `0.5` 调高至 `0.55`，或将各 `twoway` 内字号上调一档。

> ⚠️ **常见错误**：`xsize`/`ysize` 只能在**最终那次** `graph combine` 或 `grc1leg` 里设置，且只设一次。如果先 combine 成 `panels_only.gph` 再套一层 combine，第一层已经锁死了各 panel 的内部比例，第二层的 `xsize`/`ysize` 只缩放整体画布，导致 panel 变扁、图例行过高。参见第六节。

---

## 三、分析层（`analysis/*.do`）

SCM 代码不变，末尾追加以下代码，将结果标准化后存 `.dta`：

```stata
* ── 追加在现有 SCM 代码末尾 ──────────────────────────────
rename <actual_var>  actual          // 替换为实际变量名
rename _Y_synthetic  synthetic

gen gap     = actual - synthetic
gen is_post = (year >= `treat_year')

* RMSPE
gen gap_sq = gap^2
sum gap_sq if !is_post, meanonly  ;  local rmspe_pre  = sqrt(r(mean))
sum gap_sq if  is_post, meanonly  ;  local rmspe_post = sqrt(r(mean))
drop gap_sq

* ATT（相对于 pre-treatment 均值的百分比）
sum gap    if  is_post, meanonly  ;  local gap_mean = r(mean)
sum actual if !is_post, meanonly
local att = (`gap_mean' / r(mean)) * 100

gen country     = "<CountryName>"              // 替换
gen att         = `att'
gen rmspe_ratio = `rmspe_post' / `rmspe_pre'
gen placebo_p   = .                            // 跑完 placebo 后手动填入

keep year country actual synthetic gap is_post att rmspe_ratio placebo_p
save "results/brexit_total.dta", replace       // 替换为对应文件名
```

> `placebo_p` 需对每个 donor 循环跑 `synth`，统计 treated unit 的 RMSPE ratio 排名后手动填入。

**每个 `.dta` 的变量说明：**

| 变量 | 说明 |
|---|---|
| `year` | 年份 |
| `country` | 国家名（"EU" / "UK" / "Russia" / "Ukraine"） |
| `actual` / `synthetic` | 原始单位（不除以 1000，由可视化层处理） |
| `gap` | actual − synthetic |
| `is_post` | 1 = post-treatment |
| `att` | ATT 百分比 |
| `rmspe_ratio` | post/pre RMSPE 比值 |
| `placebo_p` | In-space placebo p 值 |

---

## 四、可视化层（`plot/*.do`）

每个文件读一个 `.dta`，分两段分别画 2 个 panel。

### 配色（在 `00_master.do` 定义，所有 do 文件继承）

```stata
global C_EU    "31 78 121"     // #1F4E79 Navy
global C_UK    "181 72 42"     // #B5482A Rust
global C_RU    "91 117 83"     // #5B7553 Olive
global C_UA    "210 162 76"    // #D2A24C Mustard
global C_SHADE "238 238 238"   // #EEEEEE 阴影区
global C_LINE  "68 68 68"      // #444444 干预线
global C_GREY  "85 85 85"      // #555555 图例
```

### 每个子图必须包含

| 元素 | 规格 |
|---|---|
| Post-treatment 阴影区 | `rarea`，`color("${C_SHADE}%60")` |
| Synthetic 虚线+点 | `connected`，`lpattern(dash) lwidth(thick) msymbol(Oh) msize(small) mfcolor(white) mlcolor("${C_xx}")` |
| Actual 实线+点 | `connected`，`lpattern(solid) lwidth(vthick) msymbol(O) msize(small) mcolor("${C_xx}")` |
| Intervention 垂直线 | `xline()`，`lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)` |
| 事件标注 | 虚线右侧，`size(small) color("${C_LINE}")` |
| Treatment effect 信息框 | **左上角**，含 `Treatment effect = x%`、`RMSPE ratio = x`、`p = x` |
| 子图字母+标题 | `subtitle("a   EU · Total publications", size(medium) justification(left) position(11))` |
| 轴刻度字号 | `labsize(medsmall)` |
| Y 轴（total） | 数据 ÷ 1000，`ytitle("Publications (×1,000)", size(small))` |
| Y 轴（ratio） | 保留两位小数，`ytitle("Intl. publication ratio", size(small))` |
| 禁用 | 置信区间、子图图例（`legend(off)`）、主标题 |

### 行标签（panel a / e / i 专用 ytitle）

只有每行第一个 panel 的 ytitle 包含事件名，字号 `medlarge`，事件名与指标名之间插入空行制造距离：

```stata
* panel a
ytitle("Brexit referendum" " " " " " " "Publications (×1,000)", size(large))
* panel e
ytitle("Crimea crisis" " " " " " " "Publications (×1,000)", size(large))
* panel i
ytitle("Russia–Ukraine war" " " " " " " "Publications (×1,000)", size(large))
* 其余 panel
ytitle("Publications (×1,000)", size(medsmall))   // 或 "Intl. publication ratio"
```

### 完整模板（`p01_brexit_total.do`）

```stata
local treat_year = 2016
local event_label "Brexit (2016)"
local xmin = 2005
local xmax = 2024

* ── Panel a: EU ──────────────────────────────────────────
use "results/brexit_total.dta", clear
keep if country == "EU"

gen actual_k    = actual    / 1000
gen synthetic_k = synthetic / 1000

local att_val     : display %4.2f att[1]
local rmspe_r     : display %4.2f rmspe_ratio[1]
local p_val       : display %4.3f placebo_p[1]
local info `""Treatment effect = `att_val'%" "RMSPE ratio = `rmspe_r', p = `p_val'""'

sum actual_k synthetic_k, meanonly
local ymin = r(min) * 0.92
local ymax = r(max) * 1.05
gen ylo = `ymin'  ;  gen yhi = `ymax'

twoway ///
    (rarea ylo yhi year if year >= `treat_year', color("${C_SHADE}%60") lwidth(none)) ///
    (connected synthetic_k year, lpattern(dash)  lcolor("${C_EU}") lwidth(thick) ///
        msymbol(Oh) msize(small) mfcolor(white) mlcolor("${C_EU}") mlwidth(thin)) ///
    (connected actual_k    year, lpattern(solid) lcolor("${C_EU}") lwidth(vthick) ///
        msymbol(O)  msize(small) mcolor("${C_EU}")) ///
    , ///
    xline(`treat_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`ymax'*0.97' `=`treat_year'+0.3' "`event_label'", ///
        size(small) color("${C_LINE}") placement(e)) ///
    text(`=`ymax'*0.95' `=`xmin'+0.5' `info', ///
        size(small) box bcolor(white) bmargin(small) justification(left) placement(e)) ///
    subtitle("a   EU · Total publications", ///
        size(medium) justification(left) position(11) margin(b=2)) ///
    ytitle("Brexit referendum" " " " " " " "Publications (×1,000)", size(large)) ///
    xtitle("") xlabel(`xmin'(5)`xmax', labsize(medsmall)) ///
    ylabel(, angle(0) format(%4.0f) labsize(medsmall)) ///
    legend(off) graphregion(color(white)) plotregion(margin(zero)) ///
    name(panel_a, replace)

graph save panel_a "output/gph/panel_a.gph", replace
drop actual_k synthetic_k ylo yhi

* ── Panel c: UK ──────────────────────────────────────────
use "results/brexit_total.dta", clear
keep if country == "UK"

gen actual_k    = actual    / 1000
gen synthetic_k = synthetic / 1000

local att_val : display %4.2f att[1]
local rmspe_r : display %4.2f rmspe_ratio[1]
local p_val   : display %4.3f placebo_p[1]
local info `""Treatment effect = `att_val'%" "RMSPE ratio = `rmspe_r', p = `p_val'""'

sum actual_k synthetic_k, meanonly
local ymin = r(min) * 0.92
local ymax = r(max) * 1.05
gen ylo = `ymin'  ;  gen yhi = `ymax'

twoway ///
    (rarea ylo yhi year if year >= `treat_year', color("${C_SHADE}%60") lwidth(none)) ///
    (connected synthetic_k year, lpattern(dash)  lcolor("${C_UK}") lwidth(thick) ///
        msymbol(Oh) msize(small) mfcolor(white) mlcolor("${C_UK}") mlwidth(thin)) ///
    (connected actual_k    year, lpattern(solid) lcolor("${C_UK}") lwidth(vthick) ///
        msymbol(O)  msize(small) mcolor("${C_UK}")) ///
    , ///
    xline(`treat_year', lpattern(shortdash) lcolor("${C_LINE}") lwidth(medthick)) ///
    text(`=`ymax'*0.97' `=`treat_year'+0.3' "`event_label'", ///
        size(small) color("${C_LINE}") placement(e)) ///
    text(`=`ymax'*0.95' `=`xmin'+0.5' `info', ///
        size(small) box bcolor(white) bmargin(small) justification(left) placement(e)) ///
    subtitle("c   UK · Total publications", ///
        size(medium) justification(left) position(11) margin(b=2)) ///
    ytitle("Publications (×1,000)", size(medsmall)) ///
    xtitle("") xlabel(`xmin'(5)`xmax', labsize(medsmall)) ///
    ylabel(, angle(0) format(%4.0f) labsize(medsmall)) ///
    legend(off) graphregion(color(white)) plotregion(margin(zero)) ///
    name(panel_c, replace)

graph save panel_c "output/gph/panel_c.gph", replace
drop actual_k synthetic_k ylo yhi
```

---

## 五、`00_master.do`

```stata
clear all
set more off
set scheme white_tableau
graph set window fontface "Helvetica"

global C_EU "31 78 121"  ;  global C_UK "181 72 42"
global C_RU "91 117 83"  ;  global C_UA "210 162 76"
global C_SHADE "238 238 238"  ;  global C_LINE "68 68 68"  ;  global C_GREY "85 85 85"

global root "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code"
cd "$root"

* 分析层（结果已有时保持注释）
* do "analysis/01_brexit_total.do"
* do "analysis/02_brexit_ratio.do"
* do "analysis/03_crimea_total.do"
* do "analysis/04_crimea_ratio.do"
* do "analysis/05_war_total.do"
* do "analysis/06_war_ratio.do"

* 可视化层
do "plot/p01_brexit_total.do"
do "plot/p02_brexit_ratio.do"
do "plot/p03_crimea_total.do"
do "plot/p04_crimea_ratio.do"
do "plot/p05_war_total.do"
do "plot/p06_war_ratio.do"

* 合并
do "99_combine_figure1.do"
```

---

## 六、`99_combine_figure1.do`

> **核心原则**：`xsize`/`ysize` 只在最终那次 `graph combine` 设置，且只设一次。不要先合 `panels_only` 再套一层 combine——第一次 combine 会锁死每个 panel 的内部比例，第二次缩放整体画布无法修正，导致 panel 变扁、图例行过高。

### 方案 A：`grc1leg`（推荐）

一步完成合并+图例，`xsize`/`ysize` 只出现一次。

```stata
* 需先安装：ssc install grc1leg
* 前提：plot/*.do 里的 twoway 正常写 legend()，不写 legend(off)
*       grc1leg 自动从 legendfrom 指定的 panel 提取图例并去重

clear all
set scheme white_tableau
graph set window fontface "Helvetica"
global root "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code"

grc1leg ///
    "output/gph/panel_a.gph" "output/gph/panel_b.gph" ///
    "output/gph/panel_c.gph" "output/gph/panel_d.gph" ///
    "output/gph/panel_e.gph" "output/gph/panel_f.gph" ///
    "output/gph/panel_g.gph" "output/gph/panel_h.gph" ///
    "output/gph/panel_i.gph" "output/gph/panel_j.gph" ///
    "output/gph/panel_k.gph" "output/gph/panel_l.gph" ///
    , ///
    cols(4) rows(3) ///
    legendfrom("output/gph/panel_a.gph") ///
    position(6) ring(0) ///
    iscale(0.5) imargin(small) ///
    xsize(11) ysize(8) ///
    graphregion(color(white) margin(l=10 r=2 t=2 b=2)) ///
    name(figure1, replace)

graph export "$root/picutres/figure1.pdf", replace
graph export "$root/picutres/figure1.png", replace width(3300)
graph close _all
```

### 方案 B：原生 `graph combine`（无需额外安装）

把图例做成第 13 个 panel，和 12 个数据 panel 在**同一次** `graph combine` 里完成。

```stata
clear all
set scheme white_tableau
graph set window fontface "Helvetica"
global C_SHADE "238 238 238"  ;  global C_GREY "85 85 85"
global root "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code"

* Step 1: 做图例 panel（中性灰）
clear  ;  set obs 5  ;  gen year = 2010 + _n  ;  gen v1 = .  ;  gen v2 = .

twoway ///
    (rarea v1 v2 year, color("${C_SHADE}%60") lwidth(none)) ///
    (connected v1 year, lpattern(solid) lcolor("${C_GREY}") lwidth(thick) ///
        msymbol(O)  msize(small) mcolor("${C_GREY}")) ///
    (connected v2 year, lpattern(dash)  lcolor("${C_GREY}") lwidth(medthick) ///
        msymbol(Oh) msize(small) mfcolor(white) mlcolor("${C_GREY}") mlwidth(thin)) ///
    , legend(order(2 "Actual (treated unit)" 3 "Synthetic counterfactual" ///
                   1 "Post-treatment period") ///
             rows(1) size(medsmall) region(lstyle(none)) symxsize(10)) ///
    xscale(off) yscale(off) ///
    graphregion(color(white)) plotregion(margin(zero) lstyle(none)) ///
    name(legend_panel, replace)
graph save legend_panel "output/gph/legend_panel.gph", replace

* Step 2: 一次性合并（xsize/ysize 只在这里出现）
* 共 13 个 panel，cols(4) 自动排 4 行，第 4 行只有 legend_panel
* holes(14 15 16) 让第 4 行后三格留空，legend_panel 居左
graph combine ///
    "output/gph/panel_a.gph" "output/gph/panel_b.gph" ///
    "output/gph/panel_c.gph" "output/gph/panel_d.gph" ///
    "output/gph/panel_e.gph" "output/gph/panel_f.gph" ///
    "output/gph/panel_g.gph" "output/gph/panel_h.gph" ///
    "output/gph/panel_i.gph" "output/gph/panel_j.gph" ///
    "output/gph/panel_k.gph" "output/gph/panel_l.gph" ///
    "output/gph/legend_panel.gph" ///
    , ///
    cols(4) holes(14 15 16) ///
    iscale(0.5) imargin(small) ///
    xsize(11) ysize(8) ///
    graphregion(color(white) margin(l=10 r=2 t=2 b=2)) ///
    name(figure1, replace)

graph export "$root/picutres/figure1.pdf", replace
graph export "$root/picutres/figure1.png", replace width(3300)
graph close _all
```

---

## 七、质量控制清单

**分析层**
- [ ] 6 个 `results/*.dta` 已生成，含所有标准变量
- [ ] `att`、`rmspe_ratio`、`placebo_p` 均已填入（非 `.`）

**可视化层**
- [ ] 12 个 `.gph` 已生成，配色为 Navy / Rust / Olive / Mustard
- [ ] Total publications y 轴用 k（÷ 1000，ytitle 含 "×1,000"）
- [ ] panel a/e/i 的 ytitle 含较大事件名且与指标名有间距
- [ ] 每个子图有阴影区、垂直干预线、**左上角** Treatment effect 信息框
- [ ] `legend(off)`，无 CI；实线用实心圆 `O`，虚线用空心圆 `Oh`（`mfcolor(white)`）
- [ ] 如果合并后数据点消失，检查是否被 scheme 覆盖：在 `twoway` 内显式写全 `msymbol() msize() mfcolor() mlcolor()`

**合并层**
- [ ] 底部有 3 项中性灰图例（单行）
- [ ] 无主标题，PDF 为矢量格式

---

## 八、给 Claude Code 的指令

> 请对我的 Stata 项目做完整重构，项目根目录：`/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/`，Stata 18，macOS。
>
> **重构范围：** 将以下 6 个"分析+可视化混合"do 文件拆分为 `analysis/` 和 `plot/` 两层：
> - `Brexit-stata_external_try/total_publications/compare.do` → `analysis/01` + `plot/p01`
> - `Brexit-stata_external_try/intl_ratio/compare_intl_ratio.do` → `analysis/02` + `plot/p02`
> - `crimes/total_publications/compare_total.do` → `analysis/03` + `plot/p03`
> - `crimes/intl_ratio/intl_ratio_compare.do` → `analysis/04` + `plot/p04`
> - `crimes_2015_2022/total_publications/compare_total_2022.do` → `analysis/05` + `plot/p05`
> - `crimes_2015_2022/intl_ratio/intl_ratio_compare.do` → `analysis/06` + `plot/p06`
>
> **分析层：** 保留所有 SCM 代码，末尾按第二节模板提取结果存为 `results/*.dta`。
>
> **可视化层：** `use results/*.dta` 读取数据，按第三节规范画图。
>
> **新建：** 按第四、五节新建 `00_master.do` 和 `99_combine_figure1.do`。
