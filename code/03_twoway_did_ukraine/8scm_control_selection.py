#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合成控制法（Synthetic Control Method, SCM）控制组选择
为乌克兰构建合成控制组，使用多个控制国家的加权组合

方法：
1. 使用战前时期（2015-2021）的数据来拟合权重
2. 权重通过最小化预测误差（MSPE）来确定
3. 可以使用结果变量的滞后值作为预测变量
4. 权重必须非负且和为1
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent


import pandas as pd
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import os
from sklearn.linear_model import LinearRegression

# 数据文件路径
output_dir = str(HERE)
existing_file = f'{output_dir}/control_group_cooperation_data.xlsx'
scm_output_file = f'{output_dir}/scm_control_selection_results.xlsx'

# 候选控制组国家（排除乌克兰）
candidate_countries = {
    'SERBIA': ['REPUBLIC OF SERBIA'],
    'GEORGIA': ['GEORGIA'],
    'ARMENIA': ['ARMENIA'],
    'AZERBAIJAN': ['AZERBAIJAN'],
    'MOLDOVA': ['MOLDOVA'],
    'BOSNIA-HERZEGOVINA': ['BOSNIA & HERZEGOVINA'],
    'BRAZIL': ['BRAZIL'],
    'SOUTH AFRICA': ['SOUTH AFRICA'],
    'ARGENTINA': ['ARGENTINA']
}

def load_y_kt_data():
    """从已有文件加载Y_{k,t}数据"""
    print("\n" + "="*80)
    print("加载Y_{{k,t}}数据")
    print("="*80)
    
    print(f"\n读取数据文件: {existing_file}")
    
    # 读取控制组国家与集合P的合作数据
    control_group_df = pd.read_excel(existing_file, sheet_name='控制组与集合P合作汇总')
    print(f"  控制组数据形状: {control_group_df.shape}")
    
    # 读取乌克兰与集合P的合作数据
    ukraine_df = pd.read_excel(existing_file, sheet_name='乌克兰与集合P合作')
    print(f"  乌克兰数据形状: {ukraine_df.shape}")
    
    # 构建y_kt
    control_y_kt = control_group_df[['year', 'country', 'coop_articles_with_P']].copy()
    control_y_kt.columns = ['year', 'country', 'Y_kt']
    
    ukraine_y_kt = ukraine_df[['year', 'ukraine_coop_with_P']].copy()
    ukraine_y_kt['country'] = 'UKRAINE'
    ukraine_y_kt.columns = ['year', 'Y_kt', 'country']
    ukraine_y_kt = ukraine_y_kt[['year', 'country', 'Y_kt']]
    
    y_kt = pd.concat([control_y_kt, ukraine_y_kt], ignore_index=True)
    y_kt['year'] = y_kt['year'].astype(int)
    y_kt['log_Y_kt'] = np.log(y_kt['Y_kt'] + 1)
    y_kt = y_kt.sort_values(['country', 'year']).reset_index(drop=True)
    
    print(f"\n✅ Y_{{k,t}}数据加载完成")
    print(f"  数据形状: {y_kt.shape}")
    print(f"  包含国家: {sorted(y_kt['country'].unique())}")
    print(f"  年份范围: {y_kt['year'].min()} - {y_kt['year'].max()}")
    
    return y_kt

def prepare_scm_data(y_kt, pre_period_start=2015, pre_period_end=2021):
    """
    准备SCM分析所需的数据结构
    
    返回:
    - Y_treated: 乌克兰在战前时期的值 (T0 x 1)
    - Y_control: 控制国家在战前时期的值 (T0 x J)
    - X_treated: 乌克兰的预测变量 (K x 1)
    - X_control: 控制国家的预测变量 (K x J)
    """
    print("\n" + "="*80)
    print("准备SCM数据结构")
    print("="*80)
    
    # 获取战前时期的数据
    pre_years = list(range(pre_period_start, pre_period_end + 1))
    
    # 乌克兰数据
    ukraine_data = y_kt[y_kt['country'] == 'UKRAINE'].copy()
    ukraine_data = ukraine_data[ukraine_data['year'].isin(pre_years)]
    ukraine_data = ukraine_data.sort_values('year')
    
    # 控制国家数据
    control_countries_list = list(candidate_countries.keys())
    control_data_list = []
    
    for country in control_countries_list:
        country_data = y_kt[y_kt['country'] == country].copy()
        country_data = country_data[country_data['year'].isin(pre_years)]
        country_data = country_data.sort_values('year')
        
        # 检查数据完整性
        if len(country_data) == len(pre_years):
            control_data_list.append(country_data)
        else:
            print(f"  ⚠️ {country}的数据不完整，跳过")
    
    if len(control_data_list) == 0:
        raise ValueError("没有可用的控制国家数据")
    
    print(f"\n✅ 数据准备完成")
    print(f"  战前时期: {pre_period_start}-{pre_period_end} ({len(pre_years)}年)")
    print(f"  控制国家数量: {len(control_data_list)}")
    
    # 构建Y矩阵：结果变量（log_Y_kt）
    Y_treated = ukraine_data['log_Y_kt'].values.reshape(-1, 1)
    Y_control = np.column_stack([df['log_Y_kt'].values for df in control_data_list])
    
    print(f"  Y_treated形状: {Y_treated.shape}")
    print(f"  Y_control形状: {Y_control.shape}")
    
    # 构建X矩阵：预测变量
    # 方法1：使用结果变量的平均值和滞后值
    # 方法2：使用结果变量的所有年份值（Abadie & Gardeazabal 2003的方法）
    
    # 使用所有年份值作为预测变量（这是SCM的标准做法）
    X_treated = Y_treated.flatten()  # (T0,)
    X_control = Y_control.T  # 转置，使得每行是一个控制国家，每列是一个时间点 (J, T0)
    
    print(f"  X_treated形状: {X_treated.shape}")
    print(f"  X_control形状: {X_control.shape}")
    print(f"  注意: X_control的每一行是一个控制国家，每一列是一个时间点")
    
    return {
        'Y_treated': Y_treated,
        'Y_control': Y_control,
        'X_treated': X_treated,
        'X_control': X_control,
        'control_countries': [df['country'].iloc[0] for df in control_data_list],
        'pre_years': pre_years,
        'ukraine_data': ukraine_data,
        'control_data_list': control_data_list
    }

def scm_objective(weights, X_treated, X_control):
    """
    SCM目标函数：最小化预测误差
    使用均方预测误差（MSPE）
    
    参数:
    - weights: (J,) 权重向量
    - X_treated: (T0,) 处理组的预测变量
    - X_control: (J, T0) 控制组的预测变量，每行是一个控制国家
    """
    # 计算合成控制组的预测值
    # X_control: (J, T0), weights: (J,) -> X_synthetic: (T0,)
    X_synthetic = X_control.T @ weights  # 转置X_control使得 (T0, J) @ (J,) = (T0,)
    
    # 计算预测误差
    prediction_error = X_treated - X_synthetic
    
    # 返回均方误差
    mse = np.mean(prediction_error ** 2)
    return mse

def scm_constraint(weights):
    """约束：权重之和必须等于1"""
    return np.sum(weights) - 1.0

def fit_synthetic_control(X_treated, X_control, method='SLSQP'):
    """
    拟合合成控制组权重
    
    参数:
    - X_treated: 处理组（乌克兰）的预测变量 (T0,)
    - X_control: 控制组的预测变量 (J, T0)，每行是一个控制国家
    - method: 优化方法（SLSQP支持约束）
    
    返回:
    - weights: 最优权重 (J,)
    - mse: 最小均方误差
    """
    print("\n" + "="*80)
    print("拟合合成控制组权重")
    print("="*80)
    
    J = X_control.shape[0]  # 控制国家数量
    
    # 初始权重：均匀分布
    initial_weights = np.ones(J) / J
    
    # 约束：权重非负且和为1
    constraints = [
        {'type': 'eq', 'fun': scm_constraint}
    ]
    
    bounds = [(0, 1) for _ in range(J)]
    
    # 优化
    print(f"\n使用优化方法: {method}")
    print(f"控制国家数量: {J}")
    print(f"预测变量维度: {X_treated.shape[0]}")
    
    result = minimize(
        scm_objective,
        initial_weights,
        args=(X_treated, X_control),
        method=method,
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 10000, 'ftol': 1e-9}
    )
    
    if result.success:
        weights = result.x
        mse = result.fun
        rmse = np.sqrt(mse)
        
        print(f"\n✅ 优化成功")
        print(f"  最小MSE: {mse:.6f}")
        print(f"  RMSE: {rmse:.6f}")
        print(f"  迭代次数: {result.nit}")
        
        return weights, mse, rmse
    else:
        print(f"\n⚠️ 优化未完全收敛")
        print(f"  消息: {result.message}")
        weights = result.x
        mse = result.fun
        rmse = np.sqrt(mse)
        
        return weights, mse, rmse

def calculate_rmspe(y_actual, y_synthetic, pre_period_end=2021):
    """
    计算RMSPE（Root Mean Squared Prediction Error）
    
    参数:
    - y_actual: 实际值（所有年份）
    - y_synthetic: 合成控制组值（所有年份）
    - pre_period_end: 战前时期结束年份
    """
    # 对齐数据：按年份合并
    merged = pd.merge(
        y_actual[['year', 'log_Y_kt']],
        y_synthetic[['year', 'log_Y_kt']],
        on='year',
        suffixes=('_actual', '_synthetic')
    )
    
    # 分离战前和战后
    pre_data = merged[merged['year'] <= pre_period_end]
    post_data = merged[merged['year'] > pre_period_end]
    
    # 战前RMSPE
    if len(pre_data) > 0:
        pre_error = pre_data['log_Y_kt_actual'].values - pre_data['log_Y_kt_synthetic'].values
        pre_rmspe = np.sqrt(np.mean(pre_error ** 2))
    else:
        pre_rmspe = np.nan
    
    # 战后RMSPE
    if len(post_data) > 0:
        post_error = post_data['log_Y_kt_actual'].values - post_data['log_Y_kt_synthetic'].values
        post_rmspe = np.sqrt(np.mean(post_error ** 2))
    else:
        post_rmspe = np.nan
    
    # RMSPE比率
    if pre_rmspe > 0 and not np.isnan(post_rmspe):
        rmspe_ratio = post_rmspe / pre_rmspe
    else:
        rmspe_ratio = np.nan
    
    return {
        'pre_rmspe': pre_rmspe,
        'post_rmspe': post_rmspe,
        'rmspe_ratio': rmspe_ratio
    }

def create_synthetic_control(y_kt, weights, control_countries, all_years):
    """
    使用权重构建合成控制组的时间序列
    """
    # 获取所有控制国家的数据
    control_data_dict = {}
    for country in control_countries:
        country_data = y_kt[y_kt['country'] == country].copy()
        country_data = country_data[country_data['year'].isin(all_years)]
        country_data = country_data.sort_values('year')
        control_data_dict[country] = country_data
    
    # 构建合成控制组
    synthetic_data = []
    for year in sorted(all_years):
        year_values = []
        for country in control_countries:
            if country in control_data_dict:
                year_data = control_data_dict[country][control_data_dict[country]['year'] == year]
                if len(year_data) > 0:
                    year_values.append(year_data['log_Y_kt'].values[0])
        
        if len(year_values) == len(control_countries):
            # 加权平均
            synthetic_value = np.average(year_values, weights=weights)
            synthetic_data.append({
                'year': year,
                'log_Y_kt': synthetic_value
            })
    
    synthetic_df = pd.DataFrame(synthetic_data)
    return synthetic_df

def visualize_scm_results(y_kt, synthetic_df, weights, control_countries, rmspe_stats):
    """可视化SCM结果"""
    print("\n" + "="*80)
    print("创建SCM可视化图表")
    print("="*80)
    
    plot_dir = f'{output_dir}/scm_plots'
    os.makedirs(plot_dir, exist_ok=True)
    
    # 1. 主要结果图：乌克兰 vs 合成控制组
    print("\n创建图表1: 乌克兰 vs 合成控制组...")
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 颜色设置
    treatment_color = (227/255, 195/255, 65/255)  # 金黄色
    synthetic_color = 'gray'  # 灰色
    
    # 乌克兰数据
    ukraine_data = y_kt[y_kt['country'] == 'UKRAINE'].copy()
    ukraine_data = ukraine_data.sort_values('year')
    
    ax.plot(
        ukraine_data['year'], ukraine_data['log_Y_kt'],
        color=treatment_color, linewidth=4, marker='o', markersize=10,
        label='Ukraine (Actual)',
        markeredgecolor='white', markeredgewidth=1.5,
        zorder=10
    )
    
    # 合成控制组
    synthetic_sorted = synthetic_df.sort_values('year')
    ax.plot(
        synthetic_sorted['year'], synthetic_sorted['log_Y_kt'],
        color=synthetic_color, linewidth=3.5, linestyle='--', alpha=0.9,
        marker='s', markersize=8, markevery=2,
        label='Synthetic Control',
        zorder=5
    )
    
    # 添加关键事件线
    ax.axvline(x=2022, color='red', linestyle='--', alpha=0.7, linewidth=2,
               label='2022: Russia-Ukraine War', zorder=3)
    ax.axvline(x=2021, color='gray', linestyle=':', alpha=0.5, linewidth=1,
               label='Pre-treatment End (2021)', zorder=3)
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('log(Y_{{k,t}}) = log(Total International Cooperation Articles + 1)',
                  fontsize=14, fontweight='bold')
    
    # 构建标题，包含权重信息
    top_countries = []
    for i, (country, weight) in enumerate(sorted(zip(control_countries, weights), 
                                                  key=lambda x: x[1], reverse=True)[:5]):
        if weight > 0.01:  # 只显示权重>1%的国家
            top_countries.append(f"{country.replace('_', ' ').title()}: {weight:.2%}")
    
    title = 'Synthetic Control Method: Ukraine vs Synthetic Control\n'
    if top_countries:
        title += f"Top Contributors: {', '.join(top_countries[:3])}"
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # 图例
    ax.legend(loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    
    # 网格和刻度
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.set_xticks(range(2015, 2025, 2))
    ax.tick_params(axis='both', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 设置x轴范围
    ax.set_xlim(left=2014.5, right=2024.5)
    
    # 添加RMSPE信息到图表
    rmspe_text = f"Pre-treatment RMSPE: {rmspe_stats['pre_rmspe']:.4f}\n"
    if not np.isnan(rmspe_stats['post_rmspe']):
        rmspe_text += f"Post-treatment RMSPE: {rmspe_stats['post_rmspe']:.4f}\n"
        rmspe_text += f"RMSPE Ratio: {rmspe_stats['rmspe_ratio']:.2f}"
    
    ax.text(0.02, 0.98, rmspe_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存图表
    plot_filename_png = f'{plot_dir}/scm_ukraine_synthetic.png'
    plt.savefig(plot_filename_png, dpi=300, bbox_inches='tight')
    print(f"  ✅ PNG已保存: {plot_filename_png}")
    
    try:
        plot_filename_pdf = f'{plot_dir}/scm_ukraine_synthetic.pdf'
        plt.savefig(plot_filename_pdf, format='pdf', bbox_inches='tight')
        print(f"  ✅ PDF已保存: {plot_filename_pdf}")
    except Exception as e:
        print(f"  ⚠️ PDF保存失败: {e}")
    
    plt.close()
    
    # 2. 权重可视化
    print("\n创建图表2: 控制国家权重...")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 按权重排序
    sorted_data = sorted(zip(control_countries, weights), key=lambda x: x[1], reverse=True)
    sorted_countries = [c.replace('_', ' ').title() for c, _ in sorted_data]
    sorted_weights = [w for _, w in sorted_data]
    
    # 只显示权重>0.01的国家
    significant_mask = np.array(sorted_weights) > 0.01
    if significant_mask.sum() > 0:
        display_countries = [c for i, c in enumerate(sorted_countries) if significant_mask[i]]
        display_weights = [w for i, w in enumerate(sorted_weights) if significant_mask[i]]
    else:
        display_countries = sorted_countries
        display_weights = sorted_weights
    
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(display_countries)))
    bars = ax.barh(display_countries, display_weights, color=colors)
    
    # 添加权重标签
    for i, (bar, weight) in enumerate(zip(bars, display_weights)):
        ax.text(weight + 0.01, bar.get_y() + bar.get_height()/2,
                f'{weight:.2%}', va='center', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Weight', fontsize=12, fontweight='bold')
    ax.set_title('Synthetic Control Weights\n(Countries Contributing to Synthetic Ukraine)',
                 fontsize=14, fontweight='bold', pad=15)
    ax.set_xlim(0, max(display_weights) * 1.2)
    ax.grid(True, alpha=0.3, axis='x')
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    
    plot_filename = f'{plot_dir}/scm_weights.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"  ✅ 已保存: {plot_filename}")
    plt.close()
    
    # 3. 处理效应图（Gap图）
    print("\n创建图表3: 处理效应（Gap）...")
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # 计算gap
    ukraine_sorted = ukraine_data.sort_values('year')
    synthetic_sorted = synthetic_df.sort_values('year')
    
    # 对齐年份
    common_years = sorted(set(ukraine_sorted['year']) & set(synthetic_sorted['year']))
    ukraine_aligned = ukraine_sorted[ukraine_sorted['year'].isin(common_years)].sort_values('year')
    synthetic_aligned = synthetic_sorted[synthetic_sorted['year'].isin(common_years)].sort_values('year')
    
    gap = ukraine_aligned['log_Y_kt'].values - synthetic_aligned['log_Y_kt'].values
    
    ax.plot(common_years, gap, color=treatment_color, linewidth=3,
            marker='o', markersize=8, label='Treatment Effect (Gap)')
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3, linewidth=1)
    ax.axvline(x=2022, color='red', linestyle='--', alpha=0.7, linewidth=2,
               label='2022: Russia-Ukraine War')
    ax.fill_between(common_years, gap, 0, alpha=0.2, color=treatment_color)
    
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('Treatment Effect\n(log(Y_{{Ukraine}}) - log(Y_{{Synthetic}}))',
                  fontsize=14, fontweight='bold')
    ax.set_title('Treatment Effect: Ukraine vs Synthetic Control',
                 fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.set_xticks(range(2015, 2025, 2))
    ax.tick_params(axis='both', labelsize=12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(left=2014.5, right=2024.5)
    
    plt.tight_layout()
    
    plot_filename = f'{plot_dir}/scm_treatment_effect.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"  ✅ 已保存: {plot_filename}")
    plt.close()
    
    print(f"\n✅ 所有图表已保存到: {plot_dir}/")

def main():
    print("="*80)
    print("合成控制法（SCM）控制组选择")
    print("="*80)
    
    # 1. 加载数据
    y_kt = load_y_kt_data()
    
    # 2. 准备SCM数据
    scm_data = prepare_scm_data(y_kt, pre_period_start=2015, pre_period_end=2021)
    
    # 3. 拟合合成控制组
    weights, mse, rmse = fit_synthetic_control(
        scm_data['X_treated'],
        scm_data['X_control']
    )
    
    # 4. 显示权重结果
    print("\n" + "="*80)
    print("合成控制组权重结果")
    print("="*80)
    
    weight_df = pd.DataFrame({
        'country': scm_data['control_countries'],
        'weight': weights
    }).sort_values('weight', ascending=False)
    
    print("\n权重分配:")
    print(weight_df.to_string(index=False))
    
    # 显示主要贡献国家
    significant_weights = weight_df[weight_df['weight'] > 0.01]
    print(f"\n主要贡献国家（权重 > 1%）:")
    for _, row in significant_weights.iterrows():
        print(f"  {row['country']:25s}: {row['weight']:6.2%}")
    
    # 5. 构建合成控制组时间序列
    all_years = sorted(y_kt['year'].unique())
    synthetic_df = create_synthetic_control(
        y_kt, weights, scm_data['control_countries'], all_years
    )
    
    # 6. 计算RMSPE
    ukraine_all = y_kt[y_kt['country'] == 'UKRAINE'].copy()
    rmspe_stats = calculate_rmspe(ukraine_all, synthetic_df, pre_period_end=2021)
    
    print("\n" + "="*80)
    print("RMSPE统计")
    print("="*80)
    print(f"战前RMSPE: {rmspe_stats['pre_rmspe']:.6f}")
    if not np.isnan(rmspe_stats['post_rmspe']):
        print(f"战后RMSPE: {rmspe_stats['post_rmspe']:.6f}")
        print(f"RMSPE比率: {rmspe_stats['rmspe_ratio']:.2f}")
    
    # 7. 可视化
    visualize_scm_results(y_kt, synthetic_df, weights, 
                          scm_data['control_countries'], rmspe_stats)
    
    # 8. 保存结果
    print("\n" + "="*80)
    print("保存结果")
    print("="*80)
    
    with pd.ExcelWriter(scm_output_file, engine='openpyxl') as writer:
        # 权重结果
        weight_df.to_excel(writer, sheet_name='SCM_Weights', index=False)
        
        # 合成控制组时间序列
        synthetic_df.to_excel(writer, sheet_name='Synthetic_Control_Series', index=False)
        
        # 乌克兰实际值
        ukraine_all.to_excel(writer, sheet_name='Ukraine_Actual', index=False)
        
        # RMSPE统计
        rmspe_df = pd.DataFrame([rmspe_stats])
        rmspe_df.to_excel(writer, sheet_name='RMSPE_Statistics', index=False)
        
        # 处理效应（Gap）
        ukraine_sorted = ukraine_all.sort_values('year')
        synthetic_sorted = synthetic_df.sort_values('year')
        common_years = sorted(set(ukraine_sorted['year']) & set(synthetic_sorted['year']))
        ukraine_aligned = ukraine_sorted[ukraine_sorted['year'].isin(common_years)].sort_values('year')
        synthetic_aligned = synthetic_sorted[synthetic_sorted['year'].isin(common_years)].sort_values('year')
        
        gap_df = pd.DataFrame({
            'year': common_years,
            'ukraine_log_Y': ukraine_aligned['log_Y_kt'].values,
            'synthetic_log_Y': synthetic_aligned['log_Y_kt'].values,
            'gap': ukraine_aligned['log_Y_kt'].values - synthetic_aligned['log_Y_kt'].values,
            'gap_pct': ((np.exp(ukraine_aligned['log_Y_kt'].values) - np.exp(synthetic_aligned['log_Y_kt'].values)) / 
                       np.exp(ukraine_aligned['log_Y_kt'].values) * 100)
        })
        gap_df.to_excel(writer, sheet_name='Treatment_Effect', index=False)
    
    print(f"\n✅ 结果已保存到: {scm_output_file}")
    
    print("\n" + "="*80)
    print("SCM控制组选择完成！")
    print("="*80)
    print("\n建议使用的控制组国家（按权重排序）:")
    for i, (_, row) in enumerate(significant_weights.iterrows(), 1):
        print(f"  {i}. {row['country']} (权重: {row['weight']:.2%})")

if __name__ == '__main__':
    main()

