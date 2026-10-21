# dyad_ppml — 2022 战争对俄罗斯科研合作的影响（伙伴国视角，dyadic PPML）

与同级目录的 partner-level 设定（`../2ppml_analysis.do`，内部控制组）不同，
这里站在**每个伙伴国 i 的视角**问：战后俄罗斯在 i 的合作组合中的份额变不变？
对照是 i 与**控制组焦点国**的合作。结构与 `02_ppml_partners_uk/dyad_ppml` 的
"EU to UK" 方向同构，只是焦点与伙伴的角色互换。

## 设定

```
(1) pooled       P_ijt = exp( a_ij + mu_it + beta * Post_t x RU_j )
(2) by group     P_ijt = exp( a_ij + mu_it + sum_g beta_g * Post_t x RU_j x G_g(i) )
(3) event study  P_ijt = exp( a_ij + mu_it + sum_g sum_k beta_gk * 1[t=k] x RU_j x G_g(i) )
(4) per partner  P_ijt = exp( a_j  + mu_t  + beta_i * Post_t x RU_j )   逐个 i
```

- `i` 伙伴国，`j` 焦点国（俄罗斯或控制组国家），`RU_j = 1[j = RUSSIAN FEDERATION]`
- `G_g(i)` 伙伴 i 属于集团 g 的指示变量，集团按给定设定划分：
  `EU`（EU27 + UK，28 国）、`NORTH_AMERICA`（US + Canada）、
  `ASIA`（Japan, South Korea, Singapore）、`CHINA`、`OTHER`（其余 158 国）
- `a_ij` 伙伴-焦点对固定效应，吸收距离、语言、历史联系等时间不变基线
- `mu_it` **伙伴-年**固定效应，吸收 i 当年的整体科研与国际合作规模
- 因 `mu_it` 已吸收 i 的总体活跃度，`exp(beta_g)-1` 即集团 g 伙伴与俄罗斯
  合作量相对其与控制组焦点国合作量的百分比变化
- `Post_t = 1[t >= 2022]`（2022-02 全面入侵），event study 省略参照年 2021
- SE 聚类到 country pair（规格 4 的面板里 dyad 等于 focal，只有 4 个 cluster，
  故改用 robust SE）

## 控制组

焦点国 `j` 取俄罗斯 + 控制组。控制组沿用 `03_twoway_did_russia` 两阶段筛选
（斜率匹配 + RMSE 最小化）的结果：**SOUTH AFRICA / BRAZIL / GEORGIA**。
`--all-controls` 用全部 9 个候选国（+ ARGENTINA, ARMENIA, AZERBAIJAN,
BOSNIA & HERZEGOVINA, MOLDOVA, SERBIA）做稳健性检验，结论不变。

伙伴池剔除所有焦点国自身（俄罗斯与控制组彼此之间的合作不进 `i` 维度），
以保持 `j` 维度干净。

## 运行

```
python 1build_dyad_panel.py                 # -> dyad_panel.csv / .dta
python 2estimate_dyad_ppml.py               # 基线（3 个控制国）
python 2estimate_dyad_ppml.py --all-controls # 稳健性（9 个控制国）
python 3plot_results.py [--all-controls]
```

估计用 `pyfixest.fepois`（等同 Stata `ppmlhdfe`；本机未装 Stata，UK 目录下
两者已交叉验证过 pooled beta 一致）。

## 数据

输入为按焦点国分文件的原始论文清单（`OST_BK, Annee_Bibliographique,
countries`）：

- `00_data_processing/russia_articles/russia_articles.txt`
- `00_data_processing/countrol_countries_articles/*_articles.txt`

一篇俄-控制组合著论文会同时出现在两个文件里，按 `(focal, OST_BK)` 去重避免
重复计数。国名经别名表规范化（`KOREA, REP. -> SOUTH KOREA`、英国各地区合并、
`SERBIA AND MONTENEGRO -> REPUBLIC OF SERBIA` 等）；`countries` 字段里
`KOREA, REP.` / `IRAN, ISLAMIC REP.` 含逗号，解析时特殊处理。

面板：192 伙伴 × 4 焦点 × 20 年（2005–2024）= 15,360 obs（基线），
补零后 41% 为 0。

## 结果

![](russia_dyad_event.png)

**pooled**：`exp(beta)-1 = -39.6%`（95% CI −44.1% 到 −34.6%，p<0.001）。

**分集团**（规格 2，基线控制组）：

| 集团 | n | `exp(beta_g)-1` | 95% CI | p |
|---|---|---|---|---|
| ASIA (JP/KR/SG) | 3 | **−51.2%** | [−59.4, −41.4] | <0.001 |
| EU27 + UK | 28 | **−48.7%** | [−51.7, −45.5] | <0.001 |
| US + Canada | 2 | **−45.5%** | [−47.8, −43.0] | <0.001 |
| Rest of world | 158 | **−24.1%** | [−33.1, −13.9] | <0.001 |
| China | 1 | +3.2% | [−13.0, +22.4] | 0.72 |

西方集团（EU、北美）与东亚发达国家的撤出幅度几乎相同，约 −45% 到 −51%；
其余世界也下降但只有一半幅度（−24%）；**中国是唯一不显著、且点估计为正的
集团**。9 控制国版本（`*_allctrl.csv`）给出 −47.8% / −44.4% / −50.7% /
−23.5% / +5.6%，排序与显著性完全一致。

**事件研究**：2012–2021 各集团 `beta_gk` 基本在 ±5% 内波动（EU 2016–2020 的
点估计 −4.2% 到 +3.8%，多数不显著），平行趋势在战前十年成立；断点出现在
2022 并逐年加深——EU −15.2%（2022）→ −49.0%（2023）→ −57.7%（2024），ASIA
−16.7% → −34.5% → −45.8%，中国则是 +3.5% → −10.6% → −8.9%。

事件研究图的纵坐标直接用 `beta_gk`（log points），各集团战前是否平行可以
一眼读出：2012–2021 五条线都贴着 0 线、彼此交叠，2022 起同步下折且分离。

2005–2011 的 `beta_gk` 在 +0.5 到 +1.4 之间（即 +50% 到 +300%），这是控制组
国家（尤其南非、巴西、格鲁吉亚）早期体量小、增速远快于俄罗斯造成的基期
效应，不是俄罗斯的异常。主图默认从 2012 画起，完整窗口见
`russia_dyad_event_full.pdf` 与 `res_event.csv`。

**逐伙伴**（规格 4，80 个与俄年均合作 ≥ 20 篇的伙伴）：

![](russia_dyad_by_partner.png)

跌幅最大的是 MONGOLIA (−83%)、MONTENEGRO (−75%)、UKRAINE (−71%)、
PALESTINE (−70%)、IRELAND (−66%)；几乎所有 EU 国家与日韩新落在 −40% 到
−66%。**上升的只有中东/南亚/白俄一组**：BYELARUS (+147%)、IRAQ (+101%)、
NIGERIA (+52%)、JORDAN (+50%)、BANGLADESH (+43%)、EGYPT (+41%)、
SAUDI ARABIA (+39%)、LEBANON (+29%)。中国 (+3.2%)、印度 (−8.2%)、
土耳其 (−6.1%)、伊朗 (+12.6%) 均不显著——这几个大国既没撤出也没明显加码。

读法：战后俄罗斯的合作组合发生了方向明确的重构，西方与东亚发达国家同步
撤出约一半，中国持平，增量来自白俄与中东/南亚。

## 输出

| 文件 | 内容 |
|---|---|
| `dyad_panel.csv` / `.dta` | 伙伴 × 焦点 × 年面板（全部 10 个焦点国） |
| `res_pooled.csv` | 规格 (1) |
| `res_by_group.csv` | 规格 (2) 各集团 `beta_g` |
| `res_event.csv` | 规格 (3) 各集团逐年 `beta_gk` |
| `res_by_partner.csv` | 规格 (4) 逐伙伴 `beta_i` |
| `res_*_allctrl.csv` | 同上，9 控制国版本 |
| `russia_dyad_by_group.pdf` | 集团系数图 |
| `russia_dyad_event.pdf` | 事件研究路径（`beta_gk`，2012 起） |
| `russia_dyad_event_full.pdf` | 同上，完整 2005–2024 窗口 |
| `russia_dyad_by_partner.pdf` | 逐伙伴 lollipop |
