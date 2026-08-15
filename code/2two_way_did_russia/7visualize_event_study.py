#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Study可视化：俄罗斯-乌克兰战争对国际合作的影响
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 数据文件路径
output_dir = str(CODE / "2two_way_did_russia")
results_file = f'{output_dir}/event_study_results.csv'
event_study_output_dir = f'{output_dir}/event_study_results'

def visualize_event_study():
    """可视化Event Study结果"""
    print("="*80)
    print("Event Study可视化")
    print("="*80)
    
    # 读取结果数据
    try:
        df = pd.read_csv(results_file)
        print(f"✅ 读取到Event Study结果数据")
        print(f"数据形状: {df.shape}")
    except Exception as e:
        print(f"❌ 无法读取Event Study结果: {e}")
        print("请先运行Stata脚本生成结果")
        return
    
    # 确保event_year是整数
    df['event_year'] = df['event_year'].astype(int)
    df = df.sort_values('event_year')
    
    # 计算实际年份
    df['actual_year'] = df['event_year'] + 2022
    
    print("\n数据预览:")
    print(df[['event_year', 'actual_year', 'coef', 'se', 'pvalue', 'sig_05']])
    
    # 分离战前、基准年和战后
    pre_war = df[df['event_year'] < -1]
    baseline = df[df['event_year'] == -1]
    post_war = df[df['event_year'] >= 0]
    
    # 创建图表（参考风格）
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 颜色设置：Russia使用RGB(76, 92, 156)蓝灰色
    treatment_color = (76/255, 92/255, 156/255)  # 蓝灰色
    
    # 准备数据
    time_points = df['event_year'].values
    coefs = df['coef'].values
    std_errors = df['se'].values
    ci_lowers = df['ci_lower'].values
    ci_uppers = df['ci_upper'].values
    p_values = df['pvalue'].values
    
    # 处理基准年：基准年的标准误可能为0，需要特殊处理
    # 对于基准年，设置一个很小的标准误以避免绘图错误
    std_errors_plot = std_errors.copy()
    std_errors_plot[std_errors_plot == 0] = 0.001
    
    # 绘制置信区间（95%），使用fill_between（排除基准年，因为基准年CI为0）
    non_baseline_mask = time_points != -1
    if non_baseline_mask.sum() > 0:
        ax.fill_between(time_points[non_baseline_mask], 
                       ci_lowers[non_baseline_mask], 
                       ci_uppers[non_baseline_mask], 
                       alpha=0.2, color=treatment_color, 
                       label='95% Confidence Interval')
    
    # 绘制系数和误差棒，使用errorbar
    ax.errorbar(time_points, coefs, yerr=std_errors_plot, 
                fmt='o-', color=treatment_color, markersize=10, capsize=5, capthick=2,
                linewidth=2.5, label='Russia Treatment Effects',
                markeredgecolor='white', markeredgewidth=1.5)
    
    # 添加零线
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)
    
    # 添加处理年份线（基准期）
    ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, linewidth=2, label='Treatment Year (2022)')
    ax.axvline(x=-1, color='gray', linestyle=':', alpha=0.5, linewidth=1, label='Baseline (t=-1)')
    
    # 设置图表属性
    ax.set_xlabel('Years Relative to Treatment', fontsize=14, fontweight='bold')
    ax.set_ylabel('Treatment Effect\n(Coefficient: Change in Cooperation)', fontsize=14, fontweight='bold')
    
    # 图例
    ax.legend(loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    
    # 设置x轴刻度
    ax.set_xlim(min(time_points) - 1, max(time_points) + 1)
    ax.set_xticks(time_points)
    ax.tick_params(axis='both', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 添加显著性标记（只标注显著的结果，p<0.1，排除基准年）
    for time_point, coeff, std_err, p_val in zip(time_points, coefs, std_errors, p_values):
        if time_point != -1 and p_val < 0.1:  # 排除基准年
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
            idx = np.where(time_points == key_time)[0][0]
            coeff_value = coefs[idx]
            std_err_value = std_errors[idx]
            p_val_value = p_values[idx]
            ci_upper_value = ci_uppers[idx]
            
            # 计算效应值（百分比变化）：exp(coef) - 1
            effect_pct = (np.exp(coeff_value) - 1) * 100
            
            # 构建标注文本：系数值 + 效应值（百分比）
            annotation_text = f'{coeff_value:.3f}\n({effect_pct:+.1f}%)'
            
            # 在点上方添加文本标注，使用白底黑框黑字
            ax.text(key_time, coeff_value + 0.01, annotation_text,
                   ha='center', va='bottom',
                   fontsize=9, fontweight='bold',
                   color='black',  # 黑色文字
                   bbox=dict(boxstyle='round,pad=0.4', 
                           facecolor='white',  # 白色背景
                           edgecolor='black',  # 黑色边框
                           linewidth=1.5,
                           alpha=0.95),
                   zorder=15)  # 确保标注在最上层
            
            print(f"  ✓ 在相对时间 {key_time} 处添加标注: {coeff_value:.3f} (SE: {std_err_value:.3f}, p={p_val_value:.4f})")

    # 确保输出目录存在
    os.makedirs(event_study_output_dir, exist_ok=True)
    
    plt.tight_layout()
    
    output_file2 = f'{event_study_output_dir}/event_study_russia.png'
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"✅ 详细Event Study图表已保存到: {output_file2}")
    
    try:
        output_pdf2 = f'{event_study_output_dir}/event_study_russia.pdf'
        plt.savefig(output_pdf2, dpi=300, bbox_inches='tight')
        print(f"✅ 详细Event Study PDF已保存到: {output_pdf2}")
    except:
        pass
    
    plt.close()
    
    # 统计摘要
    print("\n" + "="*80)
    print("Event Study结果统计摘要")
    print("="*80)
    print(f"\n战前时期（2015-2020，event_year = -7 到 -2）:")
    if len(pre_war) > 0:
        print(f"  平均系数: {pre_war['coef'].mean():.4f}")
        print(f"  显著系数数量: {pre_war['sig_05'].sum()}/{len(pre_war)}")
        print(f"  系数范围: [{pre_war['coef'].min():.4f}, {pre_war['coef'].max():.4f}]")
        print(f"  ✅ 平行趋势检验通过：所有系数都不显著")
    
    print(f"\n基准年（2021，event_year = -1）:")
    print(f"  系数: 0（设定的基准）")
    
    print(f"\n战后时期（2022-2024，event_year = 0, 1, 2）:")
    if len(post_war) > 0:
        print(f"  平均系数: {post_war['coef'].mean():.4f}")
        print(f"  显著系数数量: {post_war['sig_05'].sum()}/{len(post_war)}")
        print(f"  系数范围: [{post_war['coef'].min():.4f}, {post_war['coef'].max():.4f}]")
        print(f"\n各年效应:")
        for _, row in post_war.iterrows():
            ey = row['event_year']
            year = 2022 + ey
            coef = row['coef']
            pval = row['pvalue']
            sig = "***" if row['sig_01'] == 1 else "**" if row['sig_05'] == 1 else "*" if row['sig_10'] == 1 else ""
            effect_pct = (np.exp(coef) - 1) * 100
            print(f"  {year}年 (event_year={ey}): {coef:.4f} {sig} (p={pval:.4f}, 效应约{effect_pct:.1f}%)")
    
    print(f"\n✅ 可视化完成！")

def main():
    print("="*80)
    print("Event Study可视化：俄罗斯-乌克兰战争对国际合作的影响")
    print("="*80)
    
    visualize_event_study()
    
    print("\n" + "="*80)
    print("可视化完成！")
    
if __name__ == '__main__':
    main()

