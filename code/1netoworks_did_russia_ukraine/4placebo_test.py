#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安慰剂检验 (Placebo Test)
通过将处理年份提前到实际处理之前，验证DID估计的稳健性
"""

import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 数据路径
data_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile'
russia_data_path = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile/russia_west_east_tile.csv'
ukraine_data_path = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile/ukraine_west_east_tile.csv'

# 分析设置
REAL_TREAT_YEAR = 2022  # 真实的处理年份
PLACEBO_YEARS = [2018, 2019, 2020, 2021]  # 安慰剂检验的处理年份
TREATED_COUNTRIES = ['russia', 'ukraine']  # 处理国家
DEPENDENT_VARIABLES = ['west_cooperation_ratio-east_cooperation_ratio']

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

def get_safe_filename(dep_var, country, placebo_year):
    """生成安全的文件名"""
    safe_var = dep_var.replace('/', '_div_').replace('-', '_minus_').replace(' ', '_')
    return f'placebo_test_{country}_{placebo_year}_{safe_var}.png'

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
        return ['azerbaijan', 'south_africa', 'rep-of-georgia']
    elif treat_country == 'ukraine':
        return ['serbia', 'rep-of-georgia', 'argentina']
    else:
        raise ValueError(f"不支持的国家: {treat_country}")

def load_and_prepare_data(treated_country, dep_var, placebo_year):
    """加载并准备安慰剂检验所需的数据"""
    
    # 获取控制组国家列表
    control_countries = get_control_countries(treated_country)
    
    # 加载处理国家数据
    treated_data_path = get_country_data_path(treated_country)
    if not os.path.exists(treated_data_path):
        raise FileNotFoundError(f"处理国家数据文件不存在: {treated_data_path}")
    
    treated_data = pd.read_csv(treated_data_path)
    treated_data['country'] = treated_country
    treated_data['treated'] = 1
    
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
            control_data_list.append(data)
            print(f"  加载控制组数据: {control_country} ({len(data)} 条记录)")
        else:
            print(f"  ⚠ 警告: 控制国家数据文件不存在，跳过: {data_path}")
    
    if len(control_data_list) == 0:
        raise ValueError(f"未找到任何控制国家数据！请检查数据文件路径: {data_base_dir}")
    
    # 合并所有数据
    all_data = pd.concat([treated_data] + control_data_list, ignore_index=True)
    
    # 创建相对时间变量（相对于安慰剂处理年份）
    all_data['relative_time'] = all_data['year'] - placebo_year
    
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

def conduct_placebo_analysis(data, treated_country, placebo_year):
    """执行安慰剂检验分析
    
    使用与Event Study相同的模型设定，包含国家固定效应和年份固定效应
    模型: Y_it = α_i + γ_t + treated_i + Σ_t time_t + Σ_t β_t * (treated_i × time_t) + ε_it
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
    
    # 构建回归公式（与Event Study保持一致）
    time_terms = ' + '.join(time_cols)
    interaction_terms = ' + '.join([f'treated:{col}' for col in time_cols])
    formula = f"dependent_var ~ C(country_factor) + C(year_factor) + treated + {time_terms} + {interaction_terms}"
    
    print(f"\n安慰剂检验回归模型 (Placebo Year: {placebo_year}):")
    print(f"  模型设定: Y_it = α_i + γ_t + treated_i + Σ_t time_t + Σ_t β_t * (treated_i × time_t) + ε_it")
    print(f"  时间虚拟变量数量: {len(time_cols)}")
    print(f"  基准期: relative_time = -1 (处理前一年)")
    print("-" * 60)
    
    # 执行回归
    try:
        model = ols(formula, data=data).fit()
    except Exception as e:
        print(f"回归模型估计出错: {e}")
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
    
    print(f"  找到 {len(interaction_coeffs)} 个时间点的处理效应")
    
    return interaction_coeffs, model

def create_placebo_plot(coefficients, treated_country, dep_var, placebo_year, output_dir):
    """创建安慰剂检验图表"""
    
    if not coefficients:
        print("  ⚠ 警告: 没有找到任何交互项系数，无法绘制安慰剂检验图")
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
    
    # 颜色设置：使用灰色表示安慰剂检验
    placebo_color = 'gray'
    
    # 绘制置信区间（95%）
    ax.fill_between(time_points, ci_lowers, ci_uppers, alpha=0.2, color=placebo_color, 
                    label='95% Confidence Interval')
    
    # 绘制系数和误差棒
    ax.errorbar(time_points, coefs, yerr=std_errors, 
                fmt='o-', color=placebo_color, markersize=10, capsize=5, capthick=2,
                linewidth=2.5, label=f'{treated_country.title()} Placebo Treatment Effects',
                markeredgecolor='white', markeredgewidth=1.5)
    
    # 添加零线
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)
    
    # 添加安慰剂处理年份线
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, linewidth=2, 
               label=f'Placebo Treatment Year ({placebo_year})')
    ax.axvline(x=-1, color='gray', linestyle=':', alpha=0.5, linewidth=1, label='Baseline (t=-1)')
    
    # 添加真实处理年份线（如果数据包含）
    real_treat_line = REAL_TREAT_YEAR - placebo_year
    if max(time_points) >= real_treat_line:
        ax.axvline(x=real_treat_line, color='blue', linestyle='--', alpha=0.7, linewidth=2, 
                   label=f'Real Treatment Year ({REAL_TREAT_YEAR})')
    
    # 设置图表属性
    ax.set_xlabel('Years Relative to Placebo Treatment', fontsize=14, fontweight='bold')
    ax.set_ylabel(f'Placebo Treatment Effect\n({get_variable_display_name(dep_var)})', fontsize=14, fontweight='bold')
    # 不显示标题（与event study保持一致）
    # ax.set_title(f'Placebo Test: {treated_country.title()} - {get_variable_display_name(dep_var)}\nPlacebo Year: {placebo_year} (Real: {REAL_TREAT_YEAR})', 
    #             fontsize=16, fontweight='bold', pad=20)
    
    # 图例
    ax.legend(loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    
    # 网格
    # ax.grid(True, alpha=0.2, linestyle='--')
    
    # 设置x轴刻度
    if len(time_points) > 0:
        ax.set_xlim(min(time_points) - 1, max(time_points) + 1)
        if len(time_points) <= 20:
            ax.set_xticks(time_points)
        else:
            ax.set_xticks(range(min(time_points), max(time_points) + 1, 2))
    
    ax.tick_params(axis='both', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # 保存图表（同时保存PNG和PDF格式）
    filename_base = get_safe_filename(dep_var, treated_country, placebo_year).replace('.png', '')
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存PNG格式
        png_path = os.path.join(output_dir, f'{filename_base}.png')
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        print(f"✓ 安慰剂检验图表已保存 (PNG): {png_path}")
        
        # 同时保存PDF格式
        pdf_path = os.path.join(output_dir, f'{filename_base}.pdf')
        plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
        print(f"✓ 安慰剂检验图表已保存 (PDF): {pdf_path}")
    except Exception as e:
        print(f"⚠ Warning: Failed to save chart: {e}")
        import traceback
        traceback.print_exc()
    
    plt.close()  # 关闭图形以释放内存，不自动显示
    
    return time_points, coefs, std_errors

def create_placebo_summary_plot(all_results, treated_country, dep_var, output_dir):
    """创建安慰剂检验结果汇总图"""
    
    # 提取所有安慰剂年份的DID估计值
    placebo_years = []
    did_estimates = []
    p_values = []
    
    for result in all_results:
        if result['country'] == treated_country and result['dependent_variable'] == dep_var:
            placebo_years.append(result['placebo_year'])
            did_estimates.append(result['did_estimate'])
            p_values.append(result['p_value'])
    
    if len(placebo_years) == 0:
        print(f"  ⚠ 警告: 没有找到 {treated_country} 的安慰剂检验结果")
        return
    
    # 创建汇总图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 颜色设置：显著结果用红色，不显著用灰色
    colors = ['red' if p is not None and p < 0.05 else 'gray' for p in p_values]
    
    # 左图：DID估计值对比
    ax1.scatter(placebo_years, did_estimates, c=colors, s=100, alpha=0.7, edgecolors='black', linewidths=1.5)
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=1)
    ax1.axvline(x=REAL_TREAT_YEAR, color='blue', linestyle='--', alpha=0.7, linewidth=2, 
                label=f'Real Treatment Year ({REAL_TREAT_YEAR})')
    ax1.set_xlabel('Placebo Treatment Year', fontsize=14, fontweight='bold')
    ax1.set_ylabel(f'DID Estimate\n({get_variable_display_name(dep_var)})', fontsize=14, fontweight='bold')
    # ax1.set_title(f'Placebo Test Results: {treated_country.title()}\n{get_variable_display_name(dep_var)}', 
    #              fontsize=16, fontweight='bold', pad=20)
    ax1.legend(fontsize=11, framealpha=0.95)
    # ax1.grid(True, alpha=0.2, linestyle='--')
    
    # 设置x轴刻度为整数年份
    ax1.set_xticks(placebo_years)
    ax1.set_xticklabels([int(year) for year in placebo_years])
    ax1.tick_params(axis='x', labelsize=12)
    
    # 设置y轴范围
    ax1.set_ylim(-0.05, 0.01) 
    
    # 去掉上边和右边的边框线
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # 添加显著性标记
    for i, (year, estimate, p_val) in enumerate(zip(placebo_years, did_estimates, p_values)):
        if p_val is not None and p_val < 0.05:
            ax1.text(year, estimate, f'p={p_val:.3f}', 
                    ha='center', va='bottom', fontsize=9, 
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='black', alpha=0.8))
    
    # 右图：P值分布
    ax2.scatter(placebo_years, p_values, c=colors, s=100, alpha=0.7, edgecolors='black', linewidths=1.5)
    ax2.axhline(y=0.05, color='red', linestyle='--', alpha=0.7, linewidth=2, label='p=0.05 significance level')
    ax2.axvline(x=REAL_TREAT_YEAR, color='blue', linestyle='--', alpha=0.7, linewidth=2, 
                label=f'Real Treatment Year ({REAL_TREAT_YEAR})')
    ax2.set_xlabel('Placebo Treatment Year', fontsize=14, fontweight='bold')
    ax2.set_ylabel('P-value', fontsize=14, fontweight='bold')
    # ax2.set_title(f'P-value Distribution: {treated_country.title()}\n{get_variable_display_name(dep_var)}', 
    #              fontsize=16, fontweight='bold', pad=20)
    ax2.legend(fontsize=11, framealpha=0.95)
    # ax2.grid(True, alpha=0.2, linestyle='--')
    ax2.set_ylim(-0.05, max(p_values) * 1.1 if p_values else 1.0)
    
    # 设置x轴刻度为整数年份
    ax2.set_xticks(placebo_years)
    ax2.set_xticklabels([int(year) for year in placebo_years])
    ax2.tick_params(axis='x', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    # 保存图表（同时保存PNG和PDF格式）
    safe_var = dep_var.replace('/', '_div_').replace('-', '_minus_').replace(' ', '_')
    filename_base = f'placebo_summary_{treated_country}_{safe_var}'
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存PNG格式
        png_path = os.path.join(output_dir, f'{filename_base}.png')
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        print(f"✓ 安慰剂检验汇总图已保存 (PNG): {png_path}")
        
        # 同时保存PDF格式
        pdf_path = os.path.join(output_dir, f'{filename_base}.pdf')
        plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
        print(f"✓ 安慰剂检验汇总图已保存 (PDF): {pdf_path}")
    except Exception as e:
        print(f"⚠ Warning: Failed to save chart: {e}")
        import traceback
        traceback.print_exc()
    
    plt.close()  # 关闭图形以释放内存，不自动显示

def main():
    """主函数"""
    # 输出目录
    output_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/placebo_test_results'
    os.makedirs(output_base_dir, exist_ok=True)
    
    print("=" * 80)
    print("安慰剂检验 (Placebo Test) 分析")
    print("=" * 80)
    print(f"真实处理年份: {REAL_TREAT_YEAR}")
    print(f"安慰剂检验年份: {', '.join(map(str, PLACEBO_YEARS))}")
    print(f"处理国家: {', '.join(TREATED_COUNTRIES)}")
    print(f"因变量: {', '.join(DEPENDENT_VARIABLES)}")
    print(f"输出目录: {output_base_dir}")
    print("=" * 80)
    
    all_results = []
    
    for treated_country in TREATED_COUNTRIES:
        print(f"\n{'=' * 80}")
        print(f"正在分析 {treated_country.title()}...")
        print(f"{'=' * 80}")
        
        for dep_var in DEPENDENT_VARIABLES:
            print(f"\n因变量: {get_variable_display_name(dep_var)}")
            print("-" * 60)
            
            country_results = []
            
            for placebo_year in PLACEBO_YEARS:
                print(f"\n安慰剂检验年份: {placebo_year}")
                
                try:
                    # 加载数据
                    print("正在加载数据...")
                    data = load_and_prepare_data(treated_country, dep_var, placebo_year)
                    print(f"数据加载完成！总观测数: {len(data)}")
                    print(f"时间范围: {data['year'].min()} - {data['year'].max()}")
                    print(f"国家数量: {data['country'].nunique()}")
                    
                    # 执行安慰剂检验分析
                    print("正在执行安慰剂检验分析...")
                    coefficients, model = conduct_placebo_analysis(data, treated_country, placebo_year)
                    
                    if not coefficients:
                        print("  ⚠ 警告: 未找到任何交互项系数，跳过图表生成")
                        continue
                    
                    # 创建安慰剂检验图表
                    print("正在生成安慰剂检验图表...")
                    time_points, coefs, std_errors = create_placebo_plot(
                        coefficients, treated_country, dep_var, placebo_year, output_base_dir
                    )
                    
                    # 计算DID估计值（使用真实处理年份后的效应）
                    # 在安慰剂检验中，我们关注的是真实处理年份（2022）之后的效应
                    # 相对于安慰剂处理年份的相对时间
                    real_treat_relative_time = REAL_TREAT_YEAR - placebo_year
                    did_estimate = None
                    did_p_value = None
                    did_std_err = None
                    
                    # 从coefficients中构建时间点到p值的映射
                    time_to_pvalue = {}
                    for col, info in coefficients.items():
                        time_str = col.replace('time_', '')
                        if time_str.startswith('neg_'):
                            t_point = -int(time_str.replace('neg_', ''))
                        else:
                            t_point = int(time_str)
                        time_to_pvalue[t_point] = info.get('p_value')
                    
                    # 寻找真实处理年份后的时间点
                    if real_treat_relative_time in time_points:
                        idx = time_points.index(real_treat_relative_time)
                        did_estimate = coefs[idx]
                        did_std_err = std_errors[idx]
                        did_p_value = time_to_pvalue.get(real_treat_relative_time)
                    else:
                        # 如果没有精确匹配，使用最接近真实处理年份后的时间点
                        post_treat_points = [t for t in time_points if t >= real_treat_relative_time]
                        if post_treat_points:
                            closest_time = min(post_treat_points)
                            idx = time_points.index(closest_time)
                            did_estimate = coefs[idx]
                            did_std_err = std_errors[idx]
                            did_p_value = time_to_pvalue.get(closest_time)
                        else:
                            # 如果真实处理年份在所有时间点之后，使用最后一个时间点
                            if len(time_points) > 0:
                                idx = len(time_points) - 1
                                did_estimate = coefs[idx]
                                did_std_err = std_errors[idx]
                                did_p_value = time_to_pvalue.get(time_points[idx])
                    
                    # 如果还是没有找到，使用处理后1年的效应（作为备选）
                    if did_estimate is None:
                        if 1 in time_points:
                            idx = time_points.index(1)
                            did_estimate = coefs[idx]
                            did_std_err = std_errors[idx]
                            did_p_value = time_to_pvalue.get(1)
                    
                    # 保存结果
                    result = {
                        'country': treated_country,
                        'dependent_variable': dep_var,
                        'placebo_year': placebo_year,
                        'did_estimate': did_estimate,
                        'std_error': did_std_err,
                        'p_value': did_p_value,
                        'coefficients': coefficients
                    }
                    
                    country_results.append(result)
                    all_results.append(result)
                    
                    if did_estimate is not None:
                        print(f"✓ {placebo_year}年安慰剂检验完成，DID估计值: {did_estimate:.4f}, p值: {did_p_value:.4f if did_p_value else 'N/A'}")
                    else:
                        print(f"⚠ {placebo_year}年安慰剂检验完成，但未找到合适的DID估计值")
                    
                except Exception as e:
                    print(f"✗ {placebo_year}年安慰剂检验出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # 创建该国家的安慰剂检验汇总图
            if country_results:
                print("\n正在生成安慰剂检验汇总图...")
                create_placebo_summary_plot(country_results, treated_country, dep_var, output_base_dir)
    
    # 保存所有结果
    if all_results:
        # 创建结果摘要
        summary_data = []
        for result in all_results:
            summary_data.append({
                'country': result['country'],
                'dependent_variable': result['dependent_variable'],
                'placebo_year': result['placebo_year'],
                'did_estimate': result['did_estimate'],
                'std_error': result.get('std_error'),
                'p_value': result['p_value'],
                'significant_90': result['p_value'] < 0.10 if result['p_value'] is not None else False,
                'significant_95': result['p_value'] < 0.05 if result['p_value'] is not None else False,
                'significant_99': result['p_value'] < 0.01 if result['p_value'] is not None else False
            })
        
        results_df = pd.DataFrame(summary_data)
        output_file = os.path.join(output_base_dir, f'placebo_test_results_{REAL_TREAT_YEAR}.csv')
        results_df.to_csv(output_file, index=False)
        print(f"\n安慰剂检验结果已保存到: {output_file}")
        
        # 显示结果摘要
        print("\n" + "=" * 80)
        print("安慰剂检验结果摘要")
        print("=" * 80)
        print(results_df.to_string(index=False))
        
        # 统计显著结果数量
        significant_count_95 = results_df['significant_95'].sum()
        total_count = len(results_df)
        if total_count > 0:
            print(f"\n显著结果统计 (p < 0.05): {significant_count_95}/{total_count} ({significant_count_95/total_count*100:.1f}%)")
            
            if significant_count_95 / total_count < 0.1:  # 显著结果少于10%
                print("✓ 安慰剂检验通过！显著结果比例较低，表明DID估计是稳健的。")
            else:
                print("⚠️ 安慰剂检验警告！显著结果比例较高，需要进一步检查DID估计的稳健性。")
    
    print("\n" + "=" * 80)
    print("所有安慰剂检验分析完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()


