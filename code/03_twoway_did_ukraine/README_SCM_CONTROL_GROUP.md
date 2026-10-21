# SCM控制组选择和使用指南

## 概述

本目录现在使用**合成控制法（Synthetic Control Method, SCM）**为乌克兰选择控制组，替代了之前的斜率匹配和RMSE最小化方法。

## SCM方法说明

SCM通过以下方式构建合成控制组：
1. 使用战前时期（2015-2021）的数据来拟合权重
2. 最小化预测误差（MSPE）
3. 权重非负且和为1
4. 使用结果变量的所有年份值作为预测变量

## SCM选择的控制组

根据SCM分析，合成控制组的主要贡献国家为：

| 国家 | 权重 | 说明 |
|------|------|------|
| ARGENTINA | 40.56% | 主要贡献者 |
| ARMENIA | 24.72% | 主要贡献者 |
| SERBIA | 19.14% | 主要贡献者 |
| MOLDOVA | 9.22% | 次要贡献者 |
| BOSNIA-HERZEGOVINA | 6.36% | 次要贡献者 |

**总权重**: 100%（5个国家）

## 平行趋势检验结果

✅ **平行趋势假设通过**

- **F检验p值**: 0.7041 (> 0.05)
- **战前RMSPE**: 0.011168
- **斜率差异**: -0.001636（乌克兰斜率: 0.045469，合成控制组斜率: 0.047105）

结论：不能拒绝平行趋势假设，可以使用SCM选择的控制组进行DiD分析。

## 文件说明

### 核心脚本

1. **`8scm_control_selection.py`** - SCM控制组选择脚本
   - 运行此脚本生成SCM权重和控制组选择结果
   - 输出文件：`scm_control_selection_results.xlsx`

2. **`9parallel_trends_test_scm.py`** - 平行趋势检验脚本
   - 验证SCM选择的控制组是否满足平行趋势假设
   - 输出文件：`parallel_trends_test_scm_results.xlsx` 和可视化图表

3. **`3generate_ppml_did_data.py`** - PPML-DiD数据生成脚本（已更新）
   - 现在自动从SCM结果文件读取控制组国家
   - 输出文件：`ppml_did_data.xlsx`, `ppml_did_data.dta`, `ppml_did_data.csv`

4. **`6event_study_analysis.do`** - Event Study分析脚本（Stata）
   - 使用SCM选择的控制组进行event study分析
   - 输出文件：`event_study_results.xlsx`, `event_study_results.csv`

5. **`10event_study_scm.py`** - Event Study分析脚本（Python版本）
   - Python版本的event study分析（备用）

### 输出文件

- `scm_control_selection_results.xlsx` - SCM分析完整结果
  - Sheet `SCM_Weights`: 控制国家权重
  - Sheet `Synthetic_Control_Series`: 合成控制组时间序列
  - Sheet `Ukraine_Actual`: 乌克兰实际值
  - Sheet `RMSPE_Statistics`: RMSPE统计
  - Sheet `Treatment_Effect`: 处理效应（Gap）

- `parallel_trends_test_scm_results.xlsx` - 平行趋势检验结果

- `ppml_did_data.xlsx` - PPML-DiD分析数据（使用SCM控制组）

- `event_study_results.xlsx` - Event Study结果

### 可视化文件

- `scm_plots/scm_ukraine_synthetic.png/pdf` - 乌克兰 vs 合成控制组
- `scm_plots/scm_weights.png` - 控制国家权重可视化
- `scm_plots/scm_treatment_effect.png` - 处理效应图
- `scm_parallel_trends_plots/parallel_trends_test_scm.png/pdf` - 平行趋势检验图

## 使用流程

### 1. 运行SCM控制组选择

```bash
cd .
python 8scm_control_selection.py
```

这将生成：
- SCM权重结果
- 合成控制组时间序列
- 可视化图表

### 2. 验证平行趋势

```bash
python 9parallel_trends_test_scm.py
```

这将：
- 进行正式的平行趋势检验（F检验）
- 生成平行趋势可视化图表
- 输出检验结果

### 3. 生成PPML-DiD数据

```bash
python 3generate_ppml_did_data.py
```

这将：
- 从SCM结果文件读取控制组国家
- 生成包含SCM控制组的PPML-DiD分析数据

### 4. 运行Event Study分析

**Stata版本（推荐）**：
```stata
cd "."
do 6event_study_analysis.do
```

**Python版本（备用）**：
```bash
python 10event_study_scm.py
```

## 主要改进

1. **更稳健的控制组选择**：SCM方法通过加权组合多个国家，比简单选择几个国家更稳健

2. **平行趋势得到保证**：通过正式的统计检验，确认了平行趋势假设

3. **更好的拟合质量**：
   - 战前RMSPE: 0.011168（非常小）
   - RMSPE比率: 0.29（<1，说明战后拟合更好）

4. **自动化流程**：数据生成脚本自动从SCM结果文件读取控制组，无需手动指定

## 注意事项

1. **权重解释**：SCM权重表示每个控制国家在构建"合成乌克兰"时的贡献。权重越大，该国家与乌克兰在战前时期的相似性越高。

2. **控制组使用**：在PPML-DiD分析中，我们使用所有5个权重>0的国家作为控制组。虽然SCM给出了权重，但PPML-DiD分析中每个国家都是独立的观测值。

3. **平行趋势**：虽然整体平行趋势检验通过，但在event study中仍需检查战前各期的系数是否显著。如果战前期系数不显著，说明平行趋势假设成立。

## 参考文献

- Abadie, A., & Gardeazabal, J. (2003). The economic costs of conflict: A case study of the Basque Country. *American Economic Review*, 93(1), 113-132.
- Abadie, A., Diamond, A., & Hainmueller, J. (2010). Synthetic control methods for comparative case studies: Estimating the effect of California's tobacco control program. *Journal of the American Statistical Association*, 105(490), 493-505.






