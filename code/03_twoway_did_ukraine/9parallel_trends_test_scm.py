#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
平行趋势检验：使用SCM选择的控制组
验证乌克兰与控制组在战前时期的平行趋势
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy import stats
from sklearn.linear_model import LinearRegression

# 数据文件路径
output_dir = str(HERE)
scm_results_file = f'{output_dir}/scm_control_selection_results.xlsx'
control_cooperation_file = f'{output_dir}/control_group_cooperation_data.xlsx'
plot_dir = f'{output_dir}/scm_parallel_trends_plots'

os.makedirs(plot_dir, exist_ok=True)

def load_data():
    """加载数据"""
    print("="*80)
    print("加载数据")
    print("="*80)
    
    # 读取SCM权重
    scm_weights_df = pd.read_excel(scm_results_file, sheet_name='SCM_Weights')
    scm_weights_df = scm_weights_df[scm_weights_df['weight'] > 0.001].copy()
    control_countries = scm_weights_df['country'].str.upper().tolist()
    weights = scm_weights_df['weight'].tolist()
    
    print(f"\nSCM控制组国家: {control_countries}")
    print(f"权重: {weights}")
    
    # 读取Y_kt数据
    control_group_df = pd.read_excel(control_cooperation_file, sheet_name='控制组与集合P合作汇总')
    control_y_kt = control_group_df[['year', 'country', 'coop_articles_with_P']].copy()
    control_y_kt.columns = ['year', 'country', 'Y_kt']
    
    ukraine_df = pd.read_excel(control_cooperation_file, sheet_name='乌克兰与集合P合作')
    ukraine_y_kt = ukraine_df[['year', 'ukraine_coop_with_P']].copy()
    ukraine_y_kt['country'] = 'UKRAINE'
    ukraine_y_kt.columns = ['year', 'Y_kt', 'country']
    ukraine_y_kt = ukraine_y_kt[['year', 'country', 'Y_kt']]
    
    y_kt = pd.concat([control_y_kt, ukraine_y_kt], ignore_index=True)
    y_kt['year'] = y_kt['year'].astype(int)
    y_kt['log_Y_kt'] = np.log(y_kt['Y_kt'] + 1)
    y_kt = y_kt.sort_values(['country', 'year']).reset_index(drop=True)
    
    return y_kt, control_countries, weights

def calculate_synthetic_control(y_kt, control_countries, weights, years):
    """计算合成控制组的值"""
    synthetic_values = []
    
    for year in years:
        year_values = []
        for country in control_countries:
            country_data = y_kt[(y_kt['country'] == country) & (y_kt['year'] == year)]
            if len(country_data) > 0:
                year_values.append(country_data['log_Y_kt'].values[0])
        
        if len(year_values) == len(control_countries):
            # 加权平均
            synthetic_value = np.average(year_values, weights=weights)
            synthetic_values.append(synthetic_value)
        else:
            synthetic_values.append(np.nan)
    
    return np.array(synthetic_values)

def test_parallel_trends(y_kt, control_countries, weights, pre_start=2015, pre_end=2021):
    """
    检验平行趋势
    使用战前时期的数据进行F检验
    """
    print("\n" + "="*80)
    print("平行趋势检验（战前时期：2015-2021）")
    print("="*80)
    
    # 获取战前数据
    pre_years = list(range(pre_start, pre_end + 1))
    
    # 乌克兰数据
    ukraine_data = y_kt[(y_kt['country'] == 'UKRAINE') & 
                       (y_kt['year'].isin(pre_years))].copy()
    ukraine_data = ukraine_data.sort_values('year')
    ukraine_log_y = ukraine_data['log_Y_kt'].values
    
    # 合成控制组数据
    synthetic_log_y = calculate_synthetic_control(y_kt, control_countries, weights, pre_years)
    
    # 方法1：斜率检验
    # 检验乌克兰和合成控制组的斜率是否相同
    X = np.array(pre_years).reshape(-1, 1)
    
    model_ukraine = LinearRegression()
    model_ukraine.fit(X, ukraine_log_y)
    slope_ukraine = model_ukraine.coef_[0]
    intercept_ukraine = model_ukraine.intercept_
    
    model_synthetic = LinearRegression()
    model_synthetic.fit(X, synthetic_log_y)
    slope_synthetic = model_synthetic.coef_[0]
    intercept_synthetic = model_synthetic.intercept_
    
    print(f"\n斜率比较:")
    print(f"  乌克兰斜率: {slope_ukraine:.6f}")
    print(f"  合成控制组斜率: {slope_synthetic:.6f}")
    print(f"  斜率差异: {slope_ukraine - slope_synthetic:.6f}")
    
    # 方法2：F检验（检验斜率是否显著不同）
    # 使用合并回归模型
    n = len(pre_years)
    
    # 构建合并数据
    y_combined = np.concatenate([ukraine_log_y, synthetic_log_y])
    X_combined = np.vstack([np.column_stack([np.ones(n), pre_years]),
                            np.column_stack([np.ones(n), pre_years])])
    group_dummy = np.concatenate([np.zeros(n), np.ones(n)])
    interaction = X_combined[:, 1] * group_dummy
    
    # 无约束模型（允许斜率不同）
    X_unrestricted = np.column_stack([X_combined, group_dummy, interaction])
    
    # 约束模型（斜率相同）
    X_restricted = np.column_stack([X_combined, group_dummy])
    
    # OLS回归
    from numpy.linalg import inv
    
    # 无约束模型
    beta_unrestricted = inv(X_unrestricted.T @ X_unrestricted) @ X_unrestricted.T @ y_combined
    residuals_unrestricted = y_combined - X_unrestricted @ beta_unrestricted
    ssr_unrestricted = np.sum(residuals_unrestricted ** 2)
    df_unrestricted = len(y_combined) - X_unrestricted.shape[1]
    
    # 约束模型
    beta_restricted = inv(X_restricted.T @ X_restricted) @ X_restricted.T @ y_combined
    residuals_restricted = y_combined - X_restricted @ beta_restricted
    ssr_restricted = np.sum(residuals_restricted ** 2)
    df_restricted = len(y_combined) - X_restricted.shape[1]
    
    # F统计量
    f_stat = ((ssr_restricted - ssr_unrestricted) / (df_restricted - df_unrestricted)) / \
             (ssr_unrestricted / df_unrestricted)
    p_value = 1 - stats.f.cdf(f_stat, df_restricted - df_unrestricted, df_unrestricted)
    
    print(f"\nF检验结果:")
    print(f"  F统计量: {f_stat:.4f}")
    print(f"  p值: {p_value:.4f}")
    
    if p_value > 0.05:
        print(f"  ✅ 不能拒绝平行趋势假设（p={p_value:.4f} > 0.05）")
    else:
        print(f"  ⚠️ 拒绝平行趋势假设（p={p_value:.4f} <= 0.05）")
    
    # 方法3：RMSPE检验
    gap = ukraine_log_y - synthetic_log_y
    rmspe = np.sqrt(np.mean(gap ** 2))
    
    print(f"\nRMSPE统计:")
    print(f"  战前RMSPE: {rmspe:.6f}")
    
    return {
        'slope_ukraine': slope_ukraine,
        'slope_synthetic': slope_synthetic,
        'slope_diff': slope_ukraine - slope_synthetic,
        'f_stat': f_stat,
        'p_value': p_value,
        'rmspe': rmspe,
        'parallel_trends_passed': p_value > 0.05
    }

def visualize_parallel_trends(y_kt, control_countries, weights, test_results):
    """可视化平行趋势"""
    print("\n" + "="*80)
    print("创建平行趋势可视化")
    print("="*80)
    
    all_years = sorted(y_kt['year'].unique())
    all_years = [y for y in all_years if 2015 <= y <= 2024]
    
    # 乌克兰数据
    ukraine_data = y_kt[y_kt['country'] == 'UKRAINE'].copy()
    ukraine_data = ukraine_data[ukraine_data['year'].isin(all_years)]
    ukraine_data = ukraine_data.sort_values('year')
    
    # 合成控制组数据
    synthetic_values = calculate_synthetic_control(y_kt, control_countries, weights, all_years)
    synthetic_df = pd.DataFrame({
        'year': all_years,
        'log_Y_kt': synthetic_values
    })
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 颜色设置
    treatment_color = (227/255, 195/255, 65/255)  # 金黄色
    synthetic_color = 'gray'  # 灰色
    
    # 绘制乌克兰
    ax.plot(
        ukraine_data['year'], ukraine_data['log_Y_kt'],
        color=treatment_color, linewidth=4, marker='o', markersize=10,
        label='Ukraine (Actual)',
        markeredgecolor='white', markeredgewidth=1.5,
        zorder=10
    )
    
    # 绘制合成控制组
    ax.plot(
        synthetic_df['year'], synthetic_df['log_Y_kt'],
        color=synthetic_color, linewidth=3.5, linestyle='--', alpha=0.9,
        marker='s', markersize=8, markevery=2,
        label='Synthetic Control (SCM)',
        zorder=5
    )
    
    # 添加关键事件线
    ax.axvline(x=2022, color='red', linestyle='--', alpha=0.7, linewidth=2,
               label='2022: Russia-Ukraine War', zorder=3)
    ax.axvline(x=2021, color='gray', linestyle=':', alpha=0.5, linewidth=1,
               label='Pre-treatment End (2021)', zorder=3)
    
    # 添加平行趋势检验结果
    p_value = test_results['p_value']
    if p_value > 0.05:
        test_text = f"Parallel Trends Test: PASSED\n(p-value = {p_value:.4f})"
        text_color = 'green'
    else:
        test_text = f"Parallel Trends Test: FAILED\n(p-value = {p_value:.4f})"
        text_color = 'red'
    
    ax.text(0.02, 0.98, test_text, transform=ax.transAxes,
            fontsize=11, verticalalignment='top', color=text_color, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('log(Y_{{k,t}}) = log(Total International Cooperation Articles + 1)',
                  fontsize=14, fontweight='bold')
    ax.set_title('Parallel Trends Test: Ukraine vs Synthetic Control (SCM)\nPre-treatment Period: 2015-2021',
                 fontsize=16, fontweight='bold', pad=20)
    
    # 图例
    ax.legend(loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    
    # 网格和刻度
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.set_xticks(range(2015, 2025, 2))
    ax.tick_params(axis='both', labelsize=12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(left=2014.5, right=2024.5)
    
    plt.tight_layout()
    
    # 保存图表
    plot_filename_png = f'{plot_dir}/parallel_trends_test_scm.png'
    plt.savefig(plot_filename_png, dpi=300, bbox_inches='tight')
    print(f"  ✅ PNG已保存: {plot_filename_png}")
    
    try:
        plot_filename_pdf = f'{plot_dir}/parallel_trends_test_scm.pdf'
        plt.savefig(plot_filename_pdf, format='pdf', bbox_inches='tight')
        print(f"  ✅ PDF已保存: {plot_filename_pdf}")
    except Exception as e:
        print(f"  ⚠️ PDF保存失败: {e}")
    
    plt.close()

def main():
    print("="*80)
    print("平行趋势检验：使用SCM选择的控制组")
    print("="*80)
    
    # 加载数据
    y_kt, control_countries, weights = load_data()
    
    # 平行趋势检验
    test_results = test_parallel_trends(y_kt, control_countries, weights)
    
    # 可视化
    visualize_parallel_trends(y_kt, control_countries, weights, test_results)
    
    # 保存结果
    results_df = pd.DataFrame([test_results])
    results_file = f'{output_dir}/parallel_trends_test_scm_results.xlsx'
    results_df.to_excel(results_file, index=False)
    print(f"\n✅ 检验结果已保存到: {results_file}")
    
    print("\n" + "="*80)
    print("平行趋势检验完成！")
    print("="*80)
    
    if test_results['parallel_trends_passed']:
        print("\n✅ 平行趋势假设通过！可以使用SCM选择的控制组进行DiD分析。")
    else:
        print("\n⚠️ 平行趋势假设未通过，建议：")
        print("  1. 检查数据质量")
        print("  2. 考虑调整战前时期范围")
        print("  3. 考虑使用其他控制组选择方法")

if __name__ == '__main__':
    main()






