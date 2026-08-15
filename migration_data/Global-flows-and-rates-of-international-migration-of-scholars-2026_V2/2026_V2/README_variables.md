# Scholarly Migration Database 2026 V2 — 变量说明

本目录为 [Scholarly Migration Database](https://www.scholarlymigration.org/data.html) **2026 V2** 国家层面处理后的数据。OpenAlex 与 Scopus 两套文件字段相同。

数据来源与方法说明见：
- 官网：[https://www.scholarlymigration.org/data.html](https://www.scholarlymigration.org/data.html)
- Scientific Data 论文：[Akbaritabar et al. (2024)](https://doi.org/10.1038/s41597-024-03655-9)
- 本仓库处理脚本：`../../01_prepare_enrich_data_2026_V2.py`

---

## 1. 国家—年层面：`*_scholarlymigration_country.csv`

每一行 = 某个国家 × 年份 × 性别 × 学科 的汇总。

| 变量名 | 含义 |
|--------|------|
| `year` | 年份 |
| `area` | 区域代码（国家层面通常等于 `iso3code`） |
| `iso2code` | ISO 两位国家代码 |
| `iso3code` | ISO 三位国家代码 |
| `countryname` | 国家名称 |
| `gender` | 性别切片：`f`（女）、`m`（男）、`u`（未知）、`all`（全部） |
| `field` | 学科切片，见下方「学科代码」 |
| `padded_population_of_researchers` | **学者人口（分母）**：经 2 年向前回填（backward fill / padding）后的活跃学者数。若某年无发文，但之后最多 2 年内有发文，仍按下一可用年份的居住国计入当年人口，用于处理出版延迟与间断发文 |
| `number_of_inmigrations` | 该国该年**总迁入**学者数（来自所有其他国家合计） |
| `number_of_outmigrations` | 该国该年**总迁出**学者数（前往所有其他国家合计） |
| `netmigration` | 净迁移 = 迁入 − 迁出 |
| `inmigrationrate` | 迁入率 = `number_of_inmigrations` / `padded_population_of_researchers` |
| `outmigrationrate` | 迁出率 = `number_of_outmigrations` / `padded_population_of_researchers` |
| `netmigrationrate` | 净迁移率 = `netmigration` / `padded_population_of_researchers` |
| `avg_paddedpop` | 该国在同一 `gender` × `field` 下，各年 `padded_population_of_researchers` 的平均值 |

---

## 2. 双边流：`*_scholarlymigration_countryflows.csv`

每一行 = 某年从国家 A 迁往国家 B、某一性别 × 学科切片下的双边流量。

| 变量名 | 含义 |
|--------|------|
| `n_migrations` | **双边迁移人数**：该年从 `iso3codefrom` → `iso3codeto` 的学者数（真正的双边流量） |
| `year` | 迁移年份（居住国首次变为目的国的年份） |
| `gender` | 性别切片（同上） |
| `field` | 学科切片（同上） |
| `iso3codefrom` | 来源国 ISO3 |
| `iso3codeto` | 目的国 ISO3 |
| `countrynamefrom` | 来源国名称 |
| `countrynameto` | 目的国名称 |
| `paddedpopfrom` | **来源国**该年、该 gender/field 下的学者人口（= 国家表中的 `padded_population_of_researchers`） |
| `paddedpopto` | **目的国**该年、该 gender/field 下的学者人口 |
| `number_of_outmigrationsfrom` | **来源国**该年、该 gender/field 下的**全国总迁出**（到所有国家合计，**不是**这对国家之间的流量） |
| `number_of_inmigrationsto` | **目的国**该年、该 gender/field 下的**全国总迁入**（从所有国家合计，**不是**这对国家之间的流量） |
| `normalized_migration1` | 标准化流量 1：\(10^{8} \times n\_migrations / (\text{number\_of\_inmigrationsto} \times \text{number\_of\_outmigrationsfrom})\) |
| `normalized_migration2` | 标准化流量 2：\(10^{11} \times n\_migrations / (\text{paddedpopfrom} \times \text{paddedpopto})\) |

### 易混淆点

- 看 **A→B 双边流量**：用 `n_migrations`
- `number_of_outmigrationsfrom` / `number_of_inmigrationsto` 是 origin / destination 两国的**全国总量**，用于构造 `normalized_migration1`，不是走廊流量
- `paddedpopfrom` / `paddedpopto` 是两国学者**存量规模**（分母），不是迁移人数

---

## 3. 学科代码（`field`）

| 代码 | 含义 |
|------|------|
| `all` | 全部学科 |
| `MhS` | Medical and Health Sciences（医学与健康科学） |
| `HumSS` | Humanities and Social Sciences（人文与社会科学） |
| `AgEnNat` | Agricultural Sciences, Engineering and Technology, and Natural Sciences（农学、工程技术与自然科学） |

---

## 4. 文件一览

| 文件 | 内容 |
|------|------|
| `openalex_2026_V2_scholarlymigration_country.csv` | OpenAlex 国家—年指标 |
| `openalex_2026_V2_scholarlymigration_countryflows.csv` | OpenAlex 双边流 |
| `scopus_2026_V2_scholarlymigration_country.csv` | Scopus 国家—年指标 |
| `scopus_2026_V2_scholarlymigration_countryflows.csv` | Scopus 双边流 |

同名 `.parquet` 与 `.csv` 内容一致。

---

## 5. 引用

使用本数据时请引用 Scholarly Migration Database 及对应论文/工作论文，并参考官网最新要求：
[https://www.scholarlymigration.org/data.html](https://www.scholarlymigration.org/data.html)
