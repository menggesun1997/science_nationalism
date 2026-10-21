# dyad_ppml — Brexit on UK–EU collaboration (dyadic PPML, Stata)

与同级目录的 partner-level 设定不同，这里的被解释变量是国家对的共同发表数
`P_ijt`。估计全部用 Stata `ppmlhdfe`；Python 只负责解析原始论文清单和画图。

## 两个方向的区别

合著没有方向性（`P_ij = P_ji`，原始数据只有每篇论文的国家列表，无通讯作者
信息），所以两栏**分子是同一个数，区别只在用谁的伙伴组合做参照**：

| | EU to UK | UK to EU |
|---|---|---|
| 焦点 | 每个 EU 国家 i | 英国 |
| 面板 | i × i 的伙伴 × 年 | UK × UK 的伙伴 × 年 |
| 固定效应 | `a_ij + mu_it` | `a_j + mu_t` |
| 对照组 | 国家 i 的其他非 EU 伙伴 | 英国的非 EU 伙伴 |
| 归一化掉的 | EU 国家 i 自身的整体增长 | 英国自身的整体增长 |
| 问的问题 | EU 国家有没有把合作移出英国 | 英国有没有把合作移出 EU |

两方向的符号/幅度差异本身就是信息：它能区分"是英国在转向"还是"是 EU 在转向"。

## 设定

```
EU to UK (1) pooled       P_ijt = exp( a_ij + mu_it + beta * Post_t x UK_j )
EU to UK (2) event study  P_ijt = exp( a_ij + mu_it + sum_k beta_k * 1[t=k] x UK_j )
EU to UK (3) per country  P_jt  = exp( a_j  + mu_t  + beta * Post_t x UK_j )
UK to EU     per country  P_jt  = exp( a_j  + mu_t  + sum_k beta_k * Post_t x 1[j=k] )
```

- `a_ij` 国家对固定效应，吸收距离、语言、历史联系等时间不变基线
- `mu_it` EU 国家-年固定效应，吸收 i 的整体科研增长、整体国际合作变化与国别冲击
- 因 `mu_it` 已吸收 i 的总体活跃度，`exp(beta)-1` 即为相对于对照伙伴的百分比变化
- 识别假设：若无 Brexit，与 UK 的合作会与同对照伙伴的合作以相同比例增长
- `Post_t = 1[t >= 2017]`，event study 省略年 `k0 = 2016`

### 推断

EU to UK 聚类到 country pair（2,258 个 pair，处理跨 27 个 pair 变化）。

UK to EU **不能**聚类到伙伴国：该面板里 dyad 就等于 partner，每个 `beta_k`
只由一个 cluster 识别，Poisson 的一阶条件令该 cluster 的 score 和为零，
cluster-robust 方差退化——27 个国家会得到完全相同的 SE（实测 0.0983）。
因此该方向报告 robust SE，并用 50 个体量可比的非 EU 伙伴做安慰剂置换检验，
给出经验 p 值 `p_k = Pr(|beta_placebo| >= |beta_k|)`（`13placebo_uk_to_eu.do`）。

## 运行顺序

```
python 1build_dyad_panel.py        # EU 焦点面板 -> dyad_panel.csv
python 5build_uk_focal_panel.py    # UK 焦点面板 -> uk_dyad_panel.csv
stata-mp -e do 00_master.do        # 10 -> 11 -> 12 -> 13
python 14plot_two_panel.py         # 双栏图
```

`_setup.do` 做路径解析并定义共享参数（`$POST_YEAR`、`$REF_YEAR`、
`$MIN_AVG`、`$INCL_EU`、`$EU27`），每个 do-file 开头都先跑它。

输入为 `00_data_processing/` 下的 `eu_articles.txt` 和 `uk_articles.txt`。

## 样本构造

- 焦点国：EU-27；对照伙伴**纳入**其他 EU-27 成员（`$INCL_EU = 1`），并要求
  年均合作 >= 5 篇
- EU 内部合作占 EU-27 对外合作约 45%（2005 年 47.3%，2024 年 44.7%），是伙伴
  组合里最大的一块，也是英国脱欧后最自然的替代对象。剔除它会让 `mu_it` 只由
  第三国合作定义，扭曲"i 的整体活跃度"这一参照基准。改 `$INCL_EU = 0` 可做
  稳健性检验
- 平衡面板，缺失补 0。EU 焦点面板 59,200 个 dyad-year（170 伙伴，5.7% 为 0）

## 数据来源

`eu_articles.txt` 由 `00_data_processing/raw data processing/6rebuild_eu_articles.py`
从 `raw_data_2026` 重建（`article_cntry_brexit.txt` + `article_brexit.txt`），
国名经 `cntry_convert.csv` 规范化。与旧版交叉验证：论文数均为 8,993,287，
OST_BK 100% 重合，EU-UK 逐年计数完全一致。

重建修正了旧版的国名标签问题：`IRAN, ISLAMIC REP.` / `KOREA, REP.` 含逗号，
在 CSV 里会被拆成两个伪国家；`GHANA ` / `MOLDOVA ` 有尾随空格。英国在原始
数据里分为 ENGLAND / SCOTLAND / WALES / NORTH-IRELAND，重建时先合并再去重，
避免把英格兰+苏格兰合著误判为两国合作。

## 结果

![](brexit_two_panel.png)

**EU to UK**：pooled `exp(beta)-1 = -10.7%`（95% CI −13.4% 到 −7.8%，p<0.001）。
27 国中 25 国系数为负，20 国在 5% 水平显著。MALTA −38.8%、IRELAND −25.8%、
LATVIA −24.5%、PORTUGAL −19.7% 跌幅最大；LUXEMBOURG (+4.1%)、CYPRUS (+0.5%)、
AUSTRIA、LITHUANIA 不显著。

**UK to EU**：EU27 aggregate −17.1%，但 robust SE 下 p=0.066，99% CI 跨 0。
逐国系数在 −28.7%（FRANCE）到 +98.2%（LATVIA）之间，而安慰剂分布很宽
（median |beta| = 0.24，p90 = 0.70），**没有任何一国通过 10% 的置换检验**
（最小 p_placebo = 0.10，LATVIA）。即在英国自己的伙伴组合内部，EU 国家的
变化与随机挑一个非 EU 伙伴没有统计差别。

两方向合起来的读法：EU 国家相对自身增长确实减少了对英合作，但英国相对自身
增长并没有特别地把 EU 换成其他地区——更像是英国整体科研增速放缓，而非
定向转移。

### 重要保留

`st_eu_to_uk_event.csv` 显示 **显著的预趋势**：2005–2015 的 `beta_k` 全部为正
且单调收敛于 0（2005 年 +22.3% → 2015 年 +4.2%），即 EU 与 UK 的合作在公投前
已经相对其他伙伴持续下滑。平行趋势假设在全窗口不成立。

加入 UK dyad 专属线性趋势后 pooled 效应消失并转正（全窗口 +3.6%；2013–2024
窗口 +0.6%，p=0.38），趋势项本身 −1.0 到 −1.7%/年（`results_robustness.csv`）。

趋势断点检验（`15slope_change.do`）进一步显示下滑在公投后**变慢**：公投前
斜率 −2.95%/年，公投后 −1.29%/年，斜率变化 +1.51%/年（p=0.009）。若 Brexit
有负面冲击，该系数应显著为负。

结论是**现有数据无法把 Brexit 的断点效应与长期既存下滑分离**，`-10.7%` 应
理解为 post 期的相对水平差，而非 Brexit 的因果效应。

另：2020–2021 的 `beta_k` 回到 0 以上（+2.6%、+2.4%），2022 年起才转负。该
时点与 Brexit 不符，更像 COVID 跨国研究激增的扰动；而制度上真正的断点
（正式脱欧、Horizon Europe 准入变化）在 2021 年。

## 输出

| 文件 | 内容 |
|---|---|
| `dyad_panel.csv` / `.dta` | EU 焦点面板 |
| `uk_dyad_panel.csv` / `.dta` | UK 焦点面板 |
| `st_eu_to_uk_pooled.csv` | EU→UK 规格 (1) |
| `st_eu_to_uk_event.csv` | EU→UK 规格 (2) 逐年 `beta_k` |
| `st_eu_to_uk_by_country.csv` | EU→UK 规格 (3) 各国 |
| `st_uk_to_eu_pooled.csv` | UK→EU aggregate |
| `st_uk_to_eu_by_country.csv` | UK→EU 各国（含 `p_placebo`） |
| `st_uk_to_eu_placebo.csv` | 50 个非 EU 伙伴的安慰剂分布 |
| `brexit_two_panel.pdf` | 双栏 coefficient plot |
| `event_study_uk_dyadic.pdf` | 事件研究路径图 |

| `st_pool_shares.csv` | EU-27 组合中 UK / 中美 / 其余伙伴的份额演变 |
| `st_pool_sensitivity.csv` | 不同对照池下的 pooled beta |

`2estimate_dyad_ppml.py` / `3plot_results.py` / `4robustness.py` 是 pyfixest
版本，保留作交叉验证：pooled beta 两边都是 −0.1126 (se 0.0161)。

## 补充检验

`16exclude_china_us.do` 检验了"中美挤压英国"这一假设，结论是**不成立**。
剔除中美后 pooled 效应反而更负（−20.5%），预趋势也更陡（2005 年
+28.8% → +50.4%）。原因见 `st_pool_shares.csv`：中美份额的下滑幅度
（31.3% → 21.9%，−9.4pp）比英国（17.2% → 12.4%，−4.8pp）更大，它们与英国
一同被稀释。真正扩张的是其余 140 余个中小伙伴（51% → 66%），即 EU 合作
网络的整体多元化。
