#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Study / Dynamic DID Plot 分析
专门用于分析俄罗斯和乌克兰的西方-东方合作比例差异
"""

import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')
from matplotlib.lines import Line2D


# 数据路径
data_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile'
russia_data_path = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile/russia_west_east_tile.csv'
ukraine_data_path = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile/ukraine_west_east_tile.csv'

# 分析设置
TREAT_YEAR = 2022  # 处理年份
TREATED_COUNTRIES = ['russia', 'ukraine']  # 处理国家
DEPENDENT_VARIABLES = ['west_cooperation_ratio-east_cooperation_ratio']

# 事件研究时间窗口（仅使用该时间范围内的数据）
YEAR_START = 2005
YEAR_END = 2024

def get_country_data_path(country):
    """根据国家名称获取数据路径"""
    if country == 'russia':
        return russia_data_path
    elif country == 'ukraine':
        return ukraine_data_path
    else:
        raise ValueError(f"不支持的国家: {country}")

def get_variable_display_name(dep_var):
    """获取因变量的显示名称"""
    if dep_var == 'west_cooperation_ratio-east_cooperation_ratio':
        return 'West-East Cooperation Difference'
    elif dep_var == 'west_cooperation_ratio/east_cooperation_ratio':
        return 'West/East Cooperation Ratio'
    else:
        return dep_var

def get_safe_filename(dep_var, country):
    """生成安全的文件名"""
    safe_var = dep_var.replace('/', '_div_').replace('-', '_minus_').replace(' ', '_')
    return f'event_study_{country}_{TREAT_YEAR}_{safe_var}.png'

def calculate_dependent_variable(data, dep_var):
    """根据DEPENDENT_VARIABLE设置计算因变量值"""
    if dep_var == 'west_cooperation_ratio-east_cooperation_ratio':
        return data['west_cooperation_ratio'] - data['east_cooperation_ratio']
    elif dep_var == 'west_cooperation_ratio/east_cooperation_ratio':
        # 避免除零错误
        return data['west_cooperation_ratio'] / (data['east_cooperation_ratio'] + 1e-8)
    else:
        return data[dep_var]

def get_control_countries(treat_country):
    """根据处理国家获取对应的控制组国家（与平行趋势检验中选择的控制组一致）"""
    if treat_country == 'russia':
        return ['south_africa', 'rep-of-georgia','azerbaijan']
    elif treat_country == 'ukraine':
        return ['serbia', 'rep-of-georgia', 'argentina']
    else:
        raise ValueError(f"不支持的国家: {treat_country}")

def load_and_prepare_data(treated_country, dep_var, treat_year):
    """加载并准备Event Study分析所需的数据"""
    
    # 获取控制组国家列表
    control_countries = get_control_countries(treated_country)
    
    # 加载处理国家数据
    treated_data_path = get_country_data_path(treated_country)
    if not os.path.exists(treated_data_path):
        raise FileNotFoundError(f"处理国家数据文件不存在: {treated_data_path}")
    
    treated_data = pd.read_csv(treated_data_path)
    treated_data['country'] = treated_country
    treated_data['treated'] = 1
    # 只保留指定年份范围
    treated_data = treated_data[(treated_data['year'] >= YEAR_START) & (treated_data['year'] <= YEAR_END)]
    
    # 计算因变量
    treated_data['dependent_var'] = calculate_dependent_variable(treated_data, dep_var)
    print(f"  加载处理组数据: {treated_country} ({len(treated_data)} 条记录)")
    
    # 加载控制国家数据
    control_data_list = []
    for control_country in control_countries:
        data_path = os.path.join(data_base_dir, f'{control_country}_west_east_tile.csv')
        if os.path.exists(data_path):
            data = pd.read_csv(data_path)
            data['country'] = control_country
            data['treated'] = 0
            # 计算因变量
            data['dependent_var'] = calculate_dependent_variable(data, dep_var)
            # 只保留指定年份范围
            data = data[(data['year'] >= YEAR_START) & (data['year'] <= YEAR_END)]
            control_data_list.append(data)
            print(f"  加载控制组数据: {control_country} ({len(data)} 条记录)")
        else:
            print(f"  ⚠ 警告: 控制国家数据文件不存在，跳过: {data_path}")
    
    if len(control_data_list) == 0:
        raise ValueError(f"未找到任何控制国家数据！请检查数据文件路径: {data_base_dir}")
    
    # 合并所有数据
    all_data = pd.concat([treated_data] + control_data_list, ignore_index=True)
    
    # 创建相对时间变量（相对于处理年份）
    all_data['relative_time'] = all_data['year'] - treat_year
    
    # 创建时间虚拟变量（排除基准期）
    # 为了避免statsmodels公式语法问题，将负时间转换为正数标识符
    all_data['time_id'] = all_data['relative_time'].astype(str)
    # 将负号替换为下划线前缀
    all_data['time_id'] = all_data['time_id'].str.replace('-', 'neg_')
    
    time_dummies = pd.get_dummies(all_data['time_id'], prefix='time')
    # 排除基准期（-1年，即neg_1，这是处理前一年）
    if 'time_neg_1' in time_dummies.columns:
        time_dummies = time_dummies.drop('time_neg_1', axis=1)
    
    # 合并数据
    all_data = pd.concat([all_data, time_dummies], axis=1)
    
    return all_data

def conduct_event_study_analysis(data, treated_country):
    """执行Event Study分析
    
    模型: Y_it = α_i + γ_t + β_t * treated_i * time_t + ε_it
    其中：
    - α_i: 国家固定效应
    - γ_t: 年份固定效应（控制所有年份的共同趋势）
    - β_t: 处理效应（随时间变化的动态效应，通过交互项 estimated）
    - treated_i: 处理组指示变量
    - time_t: 时间虚拟变量（相对于处理年份）
    
    注意：时间虚拟变量（time_cols）控制相对于处理年份的时间效应，
    年份固定效应（year_factor）控制绝对年份的固定效应。
    这两者不完全共线，因为时间虚拟变量是基于相对时间的。
    但为了更标准的Event Study设定，我们只使用年份固定效应和时间虚拟变量的交互项。
    
    标准Event Study模型设定：
    Y_it = α_i + γ_t + Σ_t β_t * (treated_i × 1[relative_time = t]) + ε_it
    
    基准期：处理前一年（relative_time = -1），该期的系数被省略作为基准
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    
    # 获取时间虚拟变量列
    time_cols = [col for col in data.columns if col.startswith('time_')]
    
    if len(time_cols) == 0:
        raise ValueError("未找到时间虚拟变量！请检查数据准备过程。")
    
    # 创建国家固定效应
    data['country_factor'] = data['country'].astype('category')
    
    # 创建年份固定效应
    data['year_factor'] = data['year'].astype('category')
    
    # 构建回归公式
    # Event Study标准设定：
    # 1. 国家固定效应：控制国家层面的不随时间变化的特征
    # 2. 年份固定效应：控制所有年份的共同趋势和冲击
    # 3. 处理组虚拟变量：控制处理组和控制组的水平差异
    # 4. 时间虚拟变量：控制相对于处理年份的时间趋势（对所有国家）
    # 5. 交互项（treated × time）：这是我们要估计的动态处理效应
    
    # 注意：时间虚拟变量和年份固定效应不完全共线，但为了模型的可识别性，
    # 我们通常使用年份固定效应来吸收所有绝对年份的冲击，而时间虚拟变量
    # 则捕捉相对于处理年份的时间模式。在实际估计中，statsmodels会自动处理
    # 完全共线的情况。
    
    time_terms = ' + '.join(time_cols)
    interaction_terms = ' + '.join([f'treated:{col}' for col in time_cols])
    formula = f"dependent_var ~ C(country_factor) + C(year_factor) + treated + {time_terms} + {interaction_terms}"
    
    print(f"\nEvent Study回归模型:")
    print(f"  模型设定: Y_it = α_i + γ_t + treated_i + Σ_t time_t + Σ_t β_t * (treated_i × time_t) + ε_it")
    print(f"  国家固定效应: C(country_factor)")
    print(f"  年份固定效应: C(year_factor)")
    print(f"  处理组虚拟变量: treated")
    print(f"  时间虚拟变量数量: {len(time_cols)}")
    print(f"  交互项数量: {len(time_cols)}")
    print(f"  基准期: relative_time = -1 (处理前一年，被省略)")
    print(f"  基准期解释: 所有处理效应都是相对于处理前一年的变化")
    print("-" * 60)
    
    # 执行回归
    try:
        model = ols(formula, data=data).fit()
    except Exception as e:
        print(f"回归模型估计出错: {e}")
        print("提示: 如果出现完全多重共线性错误，可能是因为时间虚拟变量和年份固定效应完全共线。")
        print("      可以尝试只使用年份固定效应，或者只使用时间虚拟变量。")
        import traceback
        traceback.print_exc()
        raise
    
    # 提取处理效应系数（交互项系数）
    interaction_coeffs = {}
    for col in time_cols:
        interaction_term = f'treated:{col}'
        if interaction_term in model.params.index:
            interaction_coeffs[col] = {
                'coef': model.params[interaction_term],
                'std_err': model.bse[interaction_term],
                'p_value': model.pvalues[interaction_term],
                't_stat': model.tvalues[interaction_term],
                'ci_lower': model.conf_int().loc[interaction_term, 0],
                'ci_upper': model.conf_int().loc[interaction_term, 1]
            }
        else:
            print(f"  ⚠ 警告: 交互项 {interaction_term} 不在回归结果中")
    
    # 打印模型摘要（只显示关键系数，避免输出过长）
    print("\n回归模型关键统计量:")
    print(f"  R-squared: {model.rsquared:.4f}")
    print(f"  Adj. R-squared: {model.rsquared_adj:.4f}")
    print(f"  观测数: {model.nobs}")
    print(f"  交互项系数数量: {len(interaction_coeffs)}")
    
    # 显示部分交互项系数（处理前后各3年）
    print("\n关键时间点的处理效应系数:")
    print(f"  {'相对时间':<10} {'系数':<12} {'标准误':<12} {'p值':<12} {'显著性':<10}")
    print("  " + "-" * 60)
    
    # 按相对时间排序显示
    time_coeff_list = []
    for col, coeff_info in interaction_coeffs.items():
        time_str = col.replace('time_', '')
        if time_str.startswith('neg_'):
            time_point = -int(time_str.replace('neg_', ''))
        else:
            time_point = int(time_str)
        time_coeff_list.append((time_point, coeff_info))
    
    time_coeff_list.sort(key=lambda x: x[0])
    
    # 显示所有时间点的系数
    for time_point, coeff_info in time_coeff_list:
        sig = ''
        if coeff_info['p_value'] < 0.01:
            sig = '***'
        elif coeff_info['p_value'] < 0.05:
            sig = '**'
        elif coeff_info['p_value'] < 0.10:
            sig = '*'
        
        print(f"  {time_point:<10} {coeff_info['coef']:<12.4f} {coeff_info['std_err']:<12.4f} "
              f"{coeff_info['p_value']:<12.4f} {sig:<10}")
    
    return interaction_coeffs, model

def create_event_study_plot(coefficients, treated_country, dep_var, treat_year, output_dir):
    """创建Event Study图表"""
    
    if not coefficients:
        print("  ⚠ 警告: 没有找到任何交互项系数，无法绘制Event Study图")
        return [], [], []
    
    # 提取时间点和系数
    time_points = []
    coefs = []
    std_errors = []
    ci_lowers = []
    ci_uppers = []
    p_values = []
    
    for time_col, coeff_info in coefficients.items():
        # 处理新的时间标识符格式
        time_str = time_col.replace('time_', '')
        if time_str.startswith('neg_'):
            time_point = -int(time_str.replace('neg_', ''))
        else:
            time_point = int(time_str)
        time_points.append(time_point)
        coefs.append(coeff_info['coef'])
        std_errors.append(coeff_info['std_err'])
        ci_lowers.append(coeff_info.get('ci_lower', coeff_info['coef'] - 1.96 * coeff_info['std_err']))
        ci_uppers.append(coeff_info.get('ci_upper', coeff_info['coef'] + 1.96 * coeff_info['std_err']))
        p_values.append(coeff_info['p_value'])
    
    # 排序
    sorted_indices = np.argsort(time_points)
    time_points = [time_points[i] for i in sorted_indices]
    coefs = [coefs[i] for i in sorted_indices]
    std_errors = [std_errors[i] for i in sorted_indices]
    ci_lowers = [ci_lowers[i] for i in sorted_indices]
    ci_uppers = [ci_uppers[i] for i in sorted_indices]
    p_values = [p_values[i] for i in sorted_indices]
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 颜色设置：Russia使用RGB(76, 92, 156)，Ukraine使用RGB(227, 195, 65)
    if treated_country == 'russia':
        treatment_color = (76/255, 92/255, 156/255)  # 蓝灰色
    else:
        treatment_color = (227/255, 195/255, 65/255)  # 金黄色
    
    # 绘制置信区间（95%）
    ax.fill_between(time_points, ci_lowers, ci_uppers, alpha=0.2, color=treatment_color, 
                    label='95% Confidence Interval')
    
    # 绘制系数和误差棒
    ax.errorbar(time_points, coefs, yerr=std_errors, 
                fmt='o-', color=treatment_color, markersize=10, capsize=5, capthick=2,
                linewidth=2.5, label=f'{treated_country.title()} Treatment Effects',
                markeredgecolor='white', markeredgewidth=1.5)
    
    # 添加零线
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)
    
    # 添加处理年份线（基准期）
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, linewidth=2, label=f'Treatment Year ({treat_year})')
    ax.axvline(x=-1, color='gray', linestyle=':', alpha=0.5, linewidth=1, label='Baseline (t=-1)')
    
    # 设置图表属性
    ax.set_xlabel('Years Relative to Treatment', fontsize=14, fontweight='bold')
    ax.set_ylabel(f'Treatment Effect\n({get_variable_display_name(dep_var)})', fontsize=14, fontweight='bold')
    # ax.set_title(f'Event Study: {treated_country.title()} - {get_variable_display_name(dep_var)}', 
    #             fontsize=16, fontweight='bold', pad=20)
    
    # 图例
    ax.legend(loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    
    # 网格
    # ax.grid(True, alpha=0.2, linestyle='--')
    
    # 设置x轴刻度
    if len(time_points) > 0:
        ax.set_xlim(min(time_points) - 1, max(time_points) + 1)
        # 设置x轴刻度，如果点太多则只显示部分
        if len(time_points) <= 20:
            ax.set_xticks(time_points)
        else:
            # 每隔2年显示一个刻度
            ax.set_xticks(range(min(time_points), max(time_points) + 1, 2))
    
    ax.tick_params(axis='both', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 添加显著性标记（可选，避免图表过于拥挤）
    # 只标注显著的结果
    for time_point, coeff, std_err, p_val in zip(time_points, coefs, std_errors, p_values):
        if p_val < 0.1:
            # 显著性标记
            if p_val < 0.01:
                significance = '***'
            elif p_val < 0.05:
                significance = '**'
            else:
                significance = '*'
            
            # 在点上方添加显著性标记
            ax.text(time_point, coeff + std_err + 0.01, significance, 
                   ha='center', va='bottom', fontsize=10, fontweight='bold', 
                   color=treatment_color)
    
    # 在相对时间为0、1、2的地方标注具体的treatment effect值
    key_time_points = [0, 1, 2]  # 处理年份和之后两年
    
    for key_time in key_time_points:
        if key_time in time_points:
            # 找到对应的时间点索引
            idx = time_points.index(key_time)
            coeff_value = coefs[idx]
            std_err_value = std_errors[idx]
            p_val_value = p_values[idx]
            ci_upper_value = ci_uppers[idx]
            
            # 构建标注文本：只显示系数值（不包含显著性标记）
            annotation_text = f'{coeff_value:.3f}'
            
            # 在点上方添加文本标注，使用白底黑框黑字
            ax.text(key_time, coeff_value + 0.01, annotation_text,
                   ha='center', va='bottom',
                   fontsize=10, fontweight='bold',
                   color='black',  # 黑色文字
                   bbox=dict(boxstyle='round,pad=0.4', 
                           facecolor='white',  # 白色背景
                           edgecolor='black',  # 黑色边框
                           linewidth=1.5,
                           alpha=0.95),
                   zorder=15)  # 确保标注在最上层
            
            print(f"  ✓ 在相对时间 {key_time} 处添加标注: {coeff_value:.3f} (SE: {std_err_value:.3f}, p={p_val_value:.4f})")
    
    plt.tight_layout()
    
    # 保存图表（同时保存PNG和PDF格式）
    filename = get_safe_filename(dep_var, treated_country).replace('.png', '')
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存PNG格式
        png_path = os.path.join(output_dir, f'{filename}.png')
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        print(f"✓ Event Study图表已保存 (PNG): {png_path}")
        
        # 同时保存PDF格式
        pdf_path = os.path.join(output_dir, f'{filename}.pdf')
        plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
        print(f"✓ Event Study图表已保存 (PDF): {pdf_path}")
    except Exception as e:
        print(f"⚠ Warning: Failed to save chart: {e}")
        import traceback
        traceback.print_exc()
    
    plt.close()  # 关闭图形以释放内存，不自动显示
    
    return time_points, coefs, std_errors

def create_parallel_trends_plot(data, treated_country, dep_var, treat_year, output_dir):
    """创建平行趋势检验图（用于Event Study分析的平行趋势可视化）"""
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 分组数据
    treated_data = data[data['treated'] == 1]
    control_data = data[data['treated'] == 0]
    
    # 计算各组的年度均值
    treated_means = treated_data.groupby('year')['dependent_var'].mean()
    control_means = control_data.groupby('year')['dependent_var'].mean()
    
    # 颜色设置：Russia使用RGB(76, 92, 156)，Ukraine使用RGB(227, 195, 65)
    if treated_country == 'russia':
        treatment_color = (76/255, 92/255, 156/255)  # 蓝灰色
    else:
        treatment_color = (227/255, 195/255, 65/255)  # 金黄色
    control_color = 'gray'  # 控制组使用灰色
    
    # 绘制时间序列
    ax.plot(treated_means.index, treated_means.values, 
            marker='o', linewidth=3.5, markersize=10, 
            label=f'Treatment: {treated_country.title()}', 
            color=treatment_color, markeredgecolor='white', markeredgewidth=1.5)
    ax.plot(control_means.index, control_means.values, 
            marker='s', linewidth=3, markersize=8, 
            label='Control Group Average', 
            color=control_color, linestyle='--', alpha=0.9)
    
    # 添加处理年份线
    ax.axvline(x=treat_year, color='red', linestyle='--', alpha=0.7, linewidth=2, 
               label=f'Treatment Year ({treat_year})')
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel(f'{get_variable_display_name(dep_var)}', fontsize=14, fontweight='bold')
    ax.set_title(f'Parallel Trends: {treated_country.title()} vs Control Group\n{get_variable_display_name(dep_var)}', 
                fontsize=16, fontweight='bold', pad=20)
    
    # 组装包含控制组国家名单的图例
    handles, labels = ax.get_legend_handles_labels()
    control_names = ', '.join([c.replace('_', ' ').title().replace('Rep Of Georgia', 'Georgia') 
                               for c in get_control_countries(treated_country)])
    
    # 添加控制国家信息到控制组标签
    for i, label in enumerate(labels):
        if 'Control Group Average' in label:
            labels[i] = f'Control Group Average\n({control_names})'
            break
    
    ax.legend(handles, labels, fontsize=11, loc='best', framealpha=0.95, fancybox=True, shadow=True)
    
    # 网格
    ax.grid(True, alpha=0.2, linestyle='--')
    
    # 设置x轴范围
    ax.set_xlim(YEAR_START - 1, YEAR_END + 1)
    ax.set_xticks(range(YEAR_START, YEAR_END + 1, 2))
    ax.tick_params(axis='both', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # 保存图表（同时保存PNG和PDF格式）
    safe_var = dep_var.replace('/', '_div_').replace('-', '_minus_').replace(' ', '_')
    filename_base = f'parallel_trends_event_study_{treated_country}_{treat_year}_{safe_var}'
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存PNG格式
        png_path = os.path.join(output_dir, f'{filename_base}.png')
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        print(f"✓ 平行趋势图已保存 (PNG): {png_path}")
        
        # 同时保存PDF格式
        pdf_path = os.path.join(output_dir, f'{filename_base}.pdf')
        plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
        print(f"✓ 平行趋势图已保存 (PDF): {pdf_path}")
    except Exception as e:
        print(f"⚠ Warning: Failed to save chart: {e}")
        import traceback
        traceback.print_exc()
    
    plt.close()  # 关闭图形以释放内存，不自动显示

def main():
    """主函数"""
    # 输出目录
    output_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/event_study_results'
    os.makedirs(output_base_dir, exist_ok=True)
    
    print("=" * 80)
    print("Event Study / Dynamic DID Plot 分析")
    print("=" * 80)
    print(f"处理年份: {TREAT_YEAR}")
    print(f"处理国家: {', '.join(TREATED_COUNTRIES)}")
    print(f"因变量: {', '.join(DEPENDENT_VARIABLES)}")
    print(f"输出目录: {output_base_dir}")
    print("=" * 80)
    
    results_summary = []
    
    for treated_country in TREATED_COUNTRIES:
        print(f"\n{'=' * 80}")
        print(f"正在分析 {treated_country.title()}...")
        print(f"{'=' * 80}")
        
        for dep_var in DEPENDENT_VARIABLES:
            print(f"\n因变量: {get_variable_display_name(dep_var)}")
            print("-" * 60)
            
            try:
                # 加载数据
                print("正在加载数据...")
                data = load_and_prepare_data(treated_country, dep_var, TREAT_YEAR)
                print(f"\n数据加载完成！")
                print(f"  总观测数: {len(data)}")
                print(f"  时间范围: {data['year'].min()} - {data['year'].max()}")
                print(f"  国家数量: {data['country'].nunique()}")
                print(f"  处理组国家: {treated_country}")
                print(f"  控制组国家: {', '.join(get_control_countries(treated_country))}")
                
                # 执行Event Study分析
                print("\n正在执行Event Study分析...")
                coefficients, model = conduct_event_study_analysis(data, treated_country)
                
                if not coefficients:
                    print("  ⚠ 警告: 未找到任何交互项系数，跳过图表生成")
                    continue
                
                print(f"  找到 {len(coefficients)} 个时间点的处理效应")
                
                # 创建Event Study图表
                print("\n正在生成Event Study图表...")
                time_points, coefs, std_errors = create_event_study_plot(
                    coefficients, treated_country, dep_var, TREAT_YEAR, output_base_dir
                )
                
                # 创建平行趋势图
                print("\n正在生成平行趋势图...")
                create_parallel_trends_plot(data, treated_country, dep_var, TREAT_YEAR, output_base_dir)
                
                # 保存结果摘要
                for time_point, coef, std_err in zip(time_points, coefs, std_errors):
                    # 从coefficients字典中获取完整的统计信息
                    time_col = None
                    for col in coefficients.keys():
                        time_str = col.replace('time_', '')
                        if time_str.startswith('neg_'):
                            t_point = -int(time_str.replace('neg_', ''))
                        else:
                            t_point = int(time_str)
                        if t_point == time_point:
                            time_col = col
                            break
                    
                    if time_col and time_col in coefficients:
                        coeff_info = coefficients[time_col]
                        results_summary.append({
                            'country': treated_country,
                            'dependent_variable': dep_var,
                            'relative_time': time_point,
                            'coefficient': coeff_info['coef'],
                            'std_error': coeff_info['std_err'],
                            't_statistic': coeff_info.get('t_stat', coeff_info['coef'] / coeff_info['std_err']),
                            'p_value': coeff_info['p_value'],
                            'ci_lower': coeff_info.get('ci_lower', coeff_info['coef'] - 1.96 * coeff_info['std_err']),
                            'ci_upper': coeff_info.get('ci_upper', coeff_info['coef'] + 1.96 * coeff_info['std_err']),
                            'significant_90': coeff_info['p_value'] < 0.10,
                            'significant_95': coeff_info['p_value'] < 0.05,
                            'significant_99': coeff_info['p_value'] < 0.01
                        })
                
                print(f"\n✓ {treated_country.title()} - {get_variable_display_name(dep_var)} 分析完成")
                
            except Exception as e:
                print(f"\n✗ 分析 {treated_country.title()} - {get_variable_display_name(dep_var)} 时出错: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
    
    # 保存结果摘要
    if results_summary:
        results_df = pd.DataFrame(results_summary)
        output_file = os.path.join(output_base_dir, f'event_study_results_{TREAT_YEAR}.csv')
        results_df.to_csv(output_file, index=False)
        print(f"\n结果摘要已保存到: {output_file}")
        
        # 显示结果摘要
        print("\n" + "=" * 80)
        print("结果摘要")
        print("=" * 80)
        print(results_df.to_string(index=False))
        
        # 显示显著效应的摘要
        print("\n" + "=" * 80)
        print("显著处理效应摘要 (p < 0.05)")
        print("=" * 80)
        significant_results = results_df[results_df['significant_95'] == True]
        if len(significant_results) > 0:
            print(significant_results[['country', 'relative_time', 'coefficient', 'std_error', 'p_value']].to_string(index=False))
        else:
            print("  未发现显著的处理效应 (p < 0.05)")
    else:
        print("\n⚠ 警告: 没有结果可以保存")
    
    print("\n" + "=" * 80)
    print("所有分析完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
