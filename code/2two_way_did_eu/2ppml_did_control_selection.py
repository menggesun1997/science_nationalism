#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPML-DiD 控制组选择流程（欧盟分析）
实现两阶段控制组选择方法：
- 第0步：准备聚合数据（创建J_Master清单和补零面板）
- 第1阶段：斜率匹配（基于增长率）
- 第2阶段：RMSE最小化（基于增长轨迹）
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import os
from collections import defaultdict

# 数据文件路径
raw_data_dir = str(CODE / "0raw_publiations_process/brexit_experimental_data/article_countries_aggregated.txt")

# 候选控制组国家（7个）
candidate_countries = {
    'UNITED STATES': ['UNITED STATES'],
    'CANADA': ['CANADA'],
    'AUSTRALIA': ['AUSTRALIA'],
    'SWITZERLAND': ['SWITZERLAND'],
    'NORWAY': ['NORWAY'],
    'JAPAN': ['JAPAN'],
    'KOREA': ['KOREA, REP.']
}

# 输出文件路径
output_dir = str(CODE / "2two_way_did_eu")
output_file = f'{output_dir}/ppml_did_control_selection_results.xlsx'

# EU-27标识（用于数据处理）
EU_27_NAME = 'EU_27'

def load_y_kt_from_existing_file(existing_file):
    """
    从1build_control_group_data.py的输出文件中直接构建y_kt
    这样可以跳过第0步，直接使用已有数据
    """
    print("\n" + "="*80)
    print("从已有文件构建Y_{{k,t}}数据（跳过第0步，EU分析）")
    print("="*80)
    
    print(f"\n读取已有数据文件: {existing_file}")
    
    # 1. 读取控制组国家与非EU-27的合作数据
    print("\n步骤1: 读取控制组国家与非EU-27的合作数据...")
    control_group_df = pd.read_excel(existing_file, sheet_name='控制组与非EU-27合作汇总')
    print(f"  控制组数据形状: {control_group_df.shape}")
    print(f"  列名: {control_group_df.columns.tolist()}")
    
    # 2. 读取EU-27与非EU-27的合作数据
    print("\n步骤2: 读取EU-27与非EU-27的合作数据...")
    eu_df = pd.read_excel(existing_file, sheet_name='EU-27与非EU-27合作')
    print(f"  EU-27数据形状: {eu_df.shape}")
    print(f"  列名: {eu_df.columns.tolist()}")
    
    # 3. 读取J_Master清单
    print("\n步骤3: 读取J_Master清单...")
    j_master_df = pd.read_excel(existing_file, sheet_name='非EU-27国家列表')
    j_master = j_master_df['partner_country'].str.upper().tolist()
    print(f"  J_Master大小: {len(j_master)}")
    
    # 4. 构建y_kt：合并控制组国家和EU-27的数据
    print("\n步骤4: 构建Y_{{k,t}}数据...")
    
    # 准备控制组国家的数据
    control_y_kt = control_group_df[['year', 'country', 'coop_articles_with_P']].copy()
    control_y_kt.columns = ['year', 'country', 'Y_kt']
    
    # 准备EU-27的数据
    eu_y_kt = eu_df[['year', 'eu_coop_with_non_eu']].copy()
    eu_y_kt['country'] = EU_27_NAME
    eu_y_kt.columns = ['year', 'Y_kt', 'country']
    eu_y_kt = eu_y_kt[['year', 'country', 'Y_kt']]
    
    # 合并数据
    y_kt = pd.concat([control_y_kt, eu_y_kt], ignore_index=True)
    
    # 确保年份是整数
    y_kt['year'] = y_kt['year'].astype(int)
    
    # 创建log_Y_kt
    y_kt['log_Y_kt'] = np.log(y_kt['Y_kt'] + 1)
    
    # 按国家和年份排序
    y_kt = y_kt.sort_values(['country', 'year']).reset_index(drop=True)
    
    print(f"\n✅ Y_{{k,t}}数据构建完成")
    print(f"  数据形状: {y_kt.shape}")
    print(f"  包含国家: {sorted(y_kt['country'].unique())}")
    print(f"  年份范围: {y_kt['year'].min()} - {y_kt['year'].max()}")
    print(f"\nY_{{k,t}}预览:")
    print(y_kt.head(10))
    
    # 统计信息
    print("\n各国家的Y_{{k,t}}统计:")
    print(y_kt.groupby('country')['Y_kt'].agg(['mean', 'std', 'min', 'max']))
    
    return y_kt, j_master, None  # panel_df设为None，因为不需要

def parse_countries(country_str):
    """解析国家字符串，提取所有国家"""
    if pd.isna(country_str) or country_str == '' or str(country_str).upper() == 'NAN':
        return []
    countries_str = str(country_str).strip().upper()
    
    # 去除引号
    if countries_str.startswith('"') and countries_str.endswith('"'):
        countries_str = countries_str[1:-1]
    elif countries_str.startswith("'") and countries_str.endswith("'"):
        countries_str = countries_str[1:-1]
    
    # 智能分割
    special_suffixes = ['REP.', 'ISLAMIC REP.']
    parts = countries_str.split(',')
    countries = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
        
        if i + 1 < len(parts):
            next_part = parts[i + 1].strip()
            if next_part in special_suffixes:
                countries.append((part + ', ' + next_part).strip())
                i += 2
                continue
        
        countries.append(part)
        i += 1
    
    countries = [c for c in countries if c and c != 'NAN' and c.strip() != '']
    return countries


def step0_prepare_aggregate_data(df, use_existing_data=False, existing_file=None):
    """
    第0步：准备聚合数据
    1. 定义J_Master清单（所有与EU-27合作过的国家，即非EU-27国家）
    2. 创建(k-j-t)补零面板
    3. 聚合Y_{k,t}
    4. 创建log_Y_{k,t}
    如果use_existing_data=True，尝试从已有文件中读取部分数据
    """
    print("\n" + "="*80)
    print("第0步：准备聚合数据（欧盟分析）")
    print("="*80)
    
    # 1. 构建J_Master清单（所有与EU-27合作过的国家，即非EU-27国家）
    print("\n步骤0.1: 构建J_Master清单（所有与EU-27合作过的国家，即非EU-27国家）...")
    
    # 如果使用已有数据，尝试从已有文件读取
    if use_existing_data and existing_file and os.path.exists(existing_file):
        print("\n尝试从已有文件读取J_Master清单...")
        try:
            # 读取非EU-27国家列表
            j_master_df = pd.read_excel(existing_file, sheet_name='非EU-27国家列表')
            j_master = j_master_df['partner_country'].str.upper().tolist()
            print(f"✅ 从已有文件读取到 {len(j_master)} 个合作伙伴国家（非EU-27国家）")
        except Exception as e:
            print(f"⚠️ 无法从已有文件读取J_Master清单: {e}")
            print("将重新从原始数据构建...")
            j_master = None
    else:
        j_master = None
    
    # 如果无法从已有文件读取，从原始数据构建
    if j_master is None:
        # EU-27国家变体（需要导入或定义）
        from collections import defaultdict
        eu_variants = {
            'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
            'CZECHIA', 'CZECH REPUBLIC', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
            'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
            'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
            'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVAKIA', 'SLOVENIA', 
            'SPAIN', 'SWEDEN'
        }
        j_master_set = set()
        
        # 找到所有包含EU-27国家的文章
        for _, row in df.iterrows():
            countries = row['country_list']
            country_set = {c.upper().strip() for c in countries}
            
            # 检查是否包含EU-27国家
            if country_set & eu_variants:
                # 添加所有非EU-27国家作为合作伙伴
                for country in countries:
                    country_upper = country.upper().strip()
                    if country_upper not in eu_variants:
                        j_master_set.add(country_upper)
        
        j_master = sorted(list(j_master_set))
        print(f"✅ 从原始数据构建了 {len(j_master)} 个合作伙伴国家（非EU-27国家）")
    
    print(f"J_Master清单大小: {len(j_master)}")
    print(f"前20个合作伙伴: {j_master[:20]}")
    
    # 创建j_master_set用于快速查找
    j_master_set = set(j_master)
    
    # 2. 创建(k-j-t)补零面板
    print("\n步骤0.2: 创建(k-j-t)补零面板...")
    
    # 获取所有年份
    all_years = sorted(df['year'].unique())
    all_years = [y for y in all_years if 2005 <= y <= 2024]
    
    # 创建完整的面板
    panel_data = []
    
    for country_name in candidate_countries.keys():
        for year in all_years:
            for partner in j_master:
                panel_data.append({
                    'country': country_name,
                    'partner': partner,
                    'year': year,
                    'paper_count': 0  # 初始化为0
                })
    
    panel_df = pd.DataFrame(panel_data)
    print(f"补零面板大小: {panel_df.shape}")
    
    # 3. 填充实际数据
    print("\n步骤0.3: 填充实际合作数据...")
    
    for _, row in df.iterrows():
        year = row['year']
        if year not in all_years:
            continue
        
        countries = row['country_list']
        country_set = {c.upper().strip() for c in countries}
        
        # 找出文章中的候选国和合作伙伴
        candidate_in_article = []
        partners_in_article = []
        
        for country in countries:
            country_upper = country.upper().strip()
            
            # 检查是否是候选国
            for country_name, variants in candidate_countries.items():
                if country_upper in [v.upper() for v in variants]:
                    candidate_in_article.append(country_name)
                    break
            
            # 检查是否是J_Master中的合作伙伴
            if country_upper in j_master_set:
                partners_in_article.append(country_upper)
        
        # 更新面板数据
        if candidate_in_article and partners_in_article:
            for candidate in candidate_in_article:
                for partner in partners_in_article:
                    mask = (panel_df['country'] == candidate) & \
                           (panel_df['partner'] == partner) & \
                           (panel_df['year'] == year)
                    panel_df.loc[mask, 'paper_count'] += 1
    
    print(f"填充后的面板数据形状: {panel_df.shape}")
    print(f"非零记录数: {(panel_df['paper_count'] > 0).sum()}")
    
    # 4. 聚合Y_{k,t}：每个国家每年的国际合作文章总数
    print("\n步骤0.4: 聚合Y_{k,t}（每个国家每年的国际合作文章总数）...")
    
    y_kt = panel_df.groupby(['country', 'year'])['paper_count'].sum().reset_index()
    y_kt.columns = ['country', 'year', 'Y_kt']
    
    print(f"Y_{{k,t}}数据形状: {y_kt.shape}")
    print("\nY_{{k,t}}预览:")
    print(y_kt.head(10))
    
    # 5. 创建log_Y_{k,t}
    print("\n步骤0.5: 创建log_Y_{{k,t}} = log(Y_{{k,t}} + 1)...")
    
    y_kt['log_Y_kt'] = np.log(y_kt['Y_kt'] + 1)
    
    print("\nlog_Y_{{k,t}}预览:")
    print(y_kt.head(10))
    
    # 统计信息
    print("\n各国家的Y_{{k,t}}统计:")
    print(y_kt.groupby('country')['Y_kt'].agg(['mean', 'std', 'min', 'max']))
    
    return y_kt, j_master, panel_df

def calculate_slope(data, country, start_year, end_year):
    """计算指定国家在指定时期的斜率"""
    country_data = data[(data['country'] == country) & 
                        (data['year'] >= start_year) & 
                        (data['year'] <= end_year)].copy()
    
    if len(country_data) < 2:
        return np.nan
    
    country_data = country_data.sort_values('year')
    
    # 使用线性回归计算斜率
    X = country_data['year'].values.reshape(-1, 1)
    y = country_data['log_Y_kt'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    return model.coef_[0]

def stage1_slope_matching(y_kt):
    """
    第1阶段：斜率匹配
    计算长期(2005-2015)的斜率
    选择与EU-27斜率最相似的5个国家
    """
    print("\n" + "="*80)
    print("第1阶段：斜率匹配（基于增长率）")
    print("="*80)
    
    # 计算EU-27的斜率
    print("\n步骤1.1: 计算EU-27的斜率...")
    eu_long_slope = calculate_slope(y_kt, EU_27_NAME, 2005, 2015)
    
    print(f"EU-27长期斜率(2005-2015): {eu_long_slope:.6f}")
    
    # 计算所有候选国的斜率
    print("\n步骤1.2: 计算所有候选国的斜率...")
    
    candidate_slopes = []
    
    for country in candidate_countries.keys():
        long_slope = calculate_slope(y_kt, country, 2005, 2015)
        
        if not np.isnan(long_slope):
            # 计算度量（与EU-27的斜率差异）
            metric = abs(long_slope - eu_long_slope)
            
            candidate_slopes.append({
                'country': country,
                'long_slope': long_slope,
                'metric': metric
            })
            
            print(f"{country:20s} | 长期斜率(2005-2015): {long_slope:8.6f} | 度量: {metric:.6f}")
    
    slopes_df = pd.DataFrame(candidate_slopes)
    
    # 选择metric最小的前5个
    print("\n步骤1.3: 选择metric最小的前5个国家...")
    top5 = slopes_df.nsmallest(5, 'metric')
    
    print("\n第1阶段筛选结果（前5名）:")
    print(top5[['country', 'long_slope', 'metric']].to_string(index=False))
    
    return top5['country'].tolist(), slopes_df

def stage2_rmse_minimization(y_kt, stage1_countries):
    """
    第2阶段：RMSE最小化
    计算与EU-27在整个处理前时期(2005-2015)的RMSE
    选择RMSE最小的前3个国家
    """
    print("\n" + "="*80)
    print("第2阶段：RMSE最小化（基于增长轨迹）")
    print("="*80)
    
    # 获取EU-27的处理前数据
    eu_preperiod = y_kt[(y_kt['country'] == EU_27_NAME) & 
                        (y_kt['year'] >= 2005) & 
                        (y_kt['year'] <= 2015)].copy()
    eu_preperiod = eu_preperiod.sort_values('year')
    eu_log_y = eu_preperiod['log_Y_kt'].values
    
    print(f"\nEU-27处理前数据点数: {len(eu_log_y)}")
    
    # 计算每个候选国的RMSE
    print("\n步骤2.1: 计算每个候选国与EU-27的RMSE...")
    
    rmse_results = []
    
    for country in stage1_countries:
        country_preperiod = y_kt[(y_kt['country'] == country) & 
                                 (y_kt['year'] >= 2005) & 
                                 (y_kt['year'] <= 2015)].copy()
        country_preperiod = country_preperiod.sort_values('year')
        
        # 确保年份对齐
        common_years = set(eu_preperiod['year']) & set(country_preperiod['year'])
        if len(common_years) < len(eu_preperiod):
            print(f"警告: {country}的数据年份不完整")
            continue
        
        # 对齐数据
        country_log_y = country_preperiod['log_Y_kt'].values
        
        # 计算RMSE
        rmse = np.sqrt(np.mean((country_log_y - eu_log_y) ** 2))
        
        rmse_results.append({
            'country': country,
            'rmse': rmse
        })
        
        print(f"{country:20s} | RMSE: {rmse:.6f}")
    
    rmse_df = pd.DataFrame(rmse_results)
    
    # 选择RMSE最小的前3个
    print("\n步骤2.2: 选择RMSE最小的前3个国家...")
    top3 = rmse_df.nsmallest(3, 'rmse')
    
    print("\n第2阶段筛选结果（前3名，最终控制组）:")
    print(top3[['country', 'rmse']].to_string(index=False))
    
    return top3['country'].tolist(), rmse_df

def create_visualizations(y_kt, stage1_results, stage2_results, final_control_group):
    """创建可视化图表"""
    print("\n" + "="*80)
    print("创建可视化图表")
    print("="*80)
    
    plot_dir = f'{output_dir}/control_selection_plots'
    os.makedirs(plot_dir, exist_ok=True)
    
    # 1. 绘制所有候选国的log_Y_{k,t}时间序列
    print("\n创建图表1: 所有候选国的log_Y_{{k,t}}时间序列...")
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(candidate_countries) + 1))
    color_map = {country: colors[i] for i, country in enumerate(candidate_countries.keys())}
    
    for country in candidate_countries.keys():
        country_data = y_kt[y_kt['country'] == country].copy()
        country_data = country_data.sort_values('year')
        
        ax.plot(country_data['year'], country_data['log_Y_kt'], 
               marker='o', linewidth=1.5, markersize=4, 
               label=country, color=color_map[country], alpha=0.7)
    
    # 绘制EU-27
    eu_data = y_kt[y_kt['country'] == EU_27_NAME].copy()
    eu_data = eu_data.sort_values('year')
    ax.plot(eu_data['year'], eu_data['log_Y_kt'], 
           marker='o', linewidth=3, markersize=8, 
           label='EU-27', color=(227/255, 195/255, 65/255), alpha=0.9)
    
    ax.axvline(x=2015, color='gray', linestyle='--', linewidth=2, alpha=0.7, label='Baseline Year (2015)')
    ax.axvline(x=2016, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Brexit (2016)')
    
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('log(Total International Cooperation Articles + 1)', fontsize=12, fontweight='bold')
    ax.set_title('All Candidate Countries (EU Analysis)', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='best', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(left=2014.5, right=2024.5)
    
    plt.tight_layout()
    plot_filename = f'{plot_dir}/all_candidates_logY_timeseries.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"  ✅ 已保存: {plot_filename}")
    plt.close()
    
    # 2. 绘制第1阶段结果（斜率比较）
    print("\n创建图表2: 第1阶段斜率匹配结果...")
    
    fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
    
    # 长期斜率比较
    ax1.scatter(stage1_results['long_slope'], [0]*len(stage1_results), 
               s=100, alpha=0.6, label='Candidates')
    ax1.axvline(x=calculate_slope(y_kt, EU_27_NAME, 2005, 2015), 
               color=(227/255, 195/255, 65/255), linestyle='--', linewidth=2, label='EU-27')
    for _, row in stage1_results.iterrows():
        ax1.annotate(row['country'], 
                    (row['long_slope'], 0),
                    xytext=(5, 5), textcoords='offset points', fontsize=8)
    ax1.set_xlabel('Long-term Slope (2005-2015)', fontsize=12, fontweight='bold')
    ax1.set_title('Long-term Growth Rate Comparison', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_filename = f'{plot_dir}/stage1_slope_comparison.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"  ✅ 已保存: {plot_filename}")
    plt.close()
    
    # 3. 绘制最终控制组与英国的比较（参考风格，显示所有候选国家和选择过程）
    print("\n创建图表3: 最终控制组与英国的比较（显示选择过程）...")
    
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # 颜色设置：UK使用RGB(227, 195, 65)金黄色
    treatment_color = (227/255, 195/255, 65/255)  # 金黄色
    control_avg_color = 'gray'  # 控制组使用灰色
    
    # 计算所有候选国家的斜率（用于图例显示）
    slopes_05_15 = {}
    for country in candidate_countries.keys():
        slope = calculate_slope(y_kt, country, 2005, 2015)
        slopes_05_15[country] = slope if not np.isnan(slope) else 0.0
    
    # 计算EU-27的斜率
    eu_slope_05_15 = calculate_slope(y_kt, EU_27_NAME, 2005, 2015)
    
    # 准备Top 5和Top 3信息（用于信息框）
    top5_countries = stage1_results.nsmallest(5, 'metric')['country'].tolist()
    top3_countries = final_control_group
    
    # 控制组颜色调色板
    control_palette = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#17becf', '#bcbd22']
    country_colors = {country: control_palette[i % len(control_palette)] 
                     for i, country in enumerate(candidate_countries.keys())}
    
    # Top 3标记
    top3_markers = ['s', '^', 'D']  # 方形、三角形、菱形
    
    # 绘制所有候选国家
    for country in candidate_countries.keys():
        country_data = y_kt[y_kt['country'] == country].copy()
        country_data = country_data.sort_values('year')
        
        slope_str = f"05-15:{slopes_05_15.get(country, 0.0):.4f}"
        country_display = country.replace('_', ' ').replace('-', ' ').title()
        
        # 判断是否为最终选定的控制组
        if country in top3_countries:
            marker_idx = top3_countries.index(country) % len(top3_markers)
            marker = top3_markers[marker_idx]
            ax.plot(
                country_data['year'], country_data['log_Y_kt'],
                color=country_colors.get(country, '#999999'), 
                linewidth=2.5, alpha=0.9,
                marker=marker, markersize=8, markevery=2,
                label=f"[TOP3] {country_display} ({slope_str})"
            )
        else:
            # 普通候选国家
            ax.plot(
                country_data['year'], country_data['log_Y_kt'],
                color=country_colors.get(country, '#999999'), 
                linewidth=1.8, alpha=0.8,
                label=f"{country_display} ({slope_str})"
            )
    
    # 计算控制组平均值（仅使用最终选定的控制国家）
    control_avg_data = {}
    all_years = set()
    
    for country in final_control_group:
        country_data = y_kt[y_kt['country'] == country].copy()
        all_years.update(country_data['year'].values)
    
    for year in sorted(all_years):
        year_values = []
        for country in final_control_group:
            country_data = y_kt[(y_kt['country'] == country) & (y_kt['year'] == year)]
            if len(country_data) > 0:
                year_values.append(country_data['log_Y_kt'].values[0])
        if len(year_values) > 0:
            control_avg_data[year] = np.mean(year_values)
    
    # 计算控制组平均值的斜率
    control_avg_slope = 0.0
    if len(control_avg_data) > 0:
        control_years = sorted(control_avg_data.keys())
        control_avg_values = [control_avg_data[y] for y in control_years]
        # 创建一个临时DataFrame来计算斜率
        temp_df = pd.DataFrame({'year': control_years, 'log_Y_kt': control_avg_values})
        # 使用线性回归计算斜率
        if len(temp_df) >= 2:
            X = temp_df['year'].values.reshape(-1, 1)
            y = temp_df['log_Y_kt'].values
            model = LinearRegression()
            model.fit(X, y)
            control_avg_slope = model.coef_[0]
            if np.isnan(control_avg_slope):
                control_avg_slope = 0.0
    
    # 绘制控制组平均值线
    if len(control_avg_data) > 0:
        control_years = sorted(control_avg_data.keys())
        control_avg_values = [control_avg_data[y] for y in control_years]
        
        selected_countries_str = ', '.join([c.replace('_', ' ').replace('-', ' ').title() 
                                           for c in final_control_group])
        
        ax.plot(
            control_years, control_avg_values,
            color=control_avg_color, linewidth=3.5, linestyle='--', alpha=0.9,
            marker='s', markersize=8, markevery=2,
            label=f'Control Group Average (05-15:{control_avg_slope:.4f})',
            zorder=5
        )
    
    # 绘制EU-27（处理组）
    eu_data = y_kt[y_kt['country'] == EU_27_NAME].copy()
    eu_data = eu_data.sort_values('year')
    ax.plot(
        eu_data['year'], eu_data['log_Y_kt'], 
        color=treatment_color, linewidth=4, marker='o', markersize=10,
        label=f'Treatment: EU-27 (05-15:{eu_slope_05_15:.4f})',
        markeredgecolor='white', markeredgewidth=1.5,
        zorder=10  # 确保处理组线在最上层
    )
    
    # 添加关键事件线
    ax.axvline(x=2016, color='red', linestyle='--', alpha=0.7, linewidth=2, 
               label='2016: Brexit', zorder=3)
    
    # 添加处理前期间阴影区域
    ax.axvspan(2005, 2015, alpha=0.1, color='gray', zorder=0)
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('log(Total International Cooperation Articles + 1)', 
                  fontsize=14, fontweight='bold')
    ax.set_title('Parallel Trends Test: EU-27 \n(Pre-treatment Period: 2005-2015)', 
                fontsize=16, fontweight='bold', pad=20)
    
    # 图例：放在右侧
    handles, labels = ax.get_legend_handles_labels()
    # 去重，保持顺序
    unique_labels = []
    unique_handles = []
    for h, l in zip(handles, labels):
        if l not in unique_labels:
            unique_labels.append(l)
            unique_handles.append(h)
    
    ax.legend(unique_handles, unique_labels, bbox_to_anchor=(1.05, 1), loc='upper left', 
             fontsize=9, framealpha=0.9)
    
    # 添加信息框：Top 5 by Slope Difference
    top5_slope_lines = ["Top 5 by Slope Difference:"]
    for i, country in enumerate(top5_countries, 1):
        metric_val = stage1_results[stage1_results['country'] == country]['metric'].values[0]
        country_display = country.replace('_', ' ').replace('-', ' ').title()
        top5_slope_lines.append(f"{i}. {country_display}: {metric_val:.6f}")
    slope_text = "\n".join(top5_slope_lines)
    plt.figtext(0.8, 0.6, slope_text, ha='left', va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.9))
    
    # 添加信息框：Top 3 by RMSE
    top3_rmse_lines = ["Top 3 by RMSE:"]
    for i, country in enumerate(top3_countries, 1):
        rmse_val = stage2_results[stage2_results['country'] == country]['rmse'].values[0]
        country_display = country.replace('_', ' ').replace('-', ' ').title()
        top3_rmse_lines.append(f"{i}. {country_display}: {rmse_val:.6f}")
    rmse_text = "\n".join(top3_rmse_lines)
    plt.figtext(0.8, 0.5, rmse_text, ha='left', va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.9))
    
    # 网格和刻度
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xticks(range(2005, 2025, 2))
    ax.tick_params(axis='both', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 设置x轴范围
    ax.set_xlim(left=2004.5, right=2024.5)
    
    # 调整布局以适应右侧图例
    plt.subplots_adjust(right=0.75)
    
    # 保存图表（同时保存PNG和PDF格式）
    plot_filename_png = f'{plot_dir}/final_control_group_comparison_eu.png'
    plt.savefig(plot_filename_png, dpi=300, bbox_inches='tight')
    print(f"  ✅ PNG已保存: {plot_filename_png}")
    
    try:
        plot_filename_pdf = f'{plot_dir}/ppml_did_control_group_comparison_eu.pdf'
        plt.savefig(plot_filename_pdf, format='pdf', bbox_inches='tight')
        print(f"  ✅ PDF已保存: {plot_filename_pdf}")
    except Exception as e:
        print(f"  ⚠️ PDF保存失败: {e}")
    
    plt.close()
    
    # 4. 绘制总趋势图（简洁版：只显示英国和控制组平均值）
    print("\n创建图表4: 总趋势图（英国 vs 控制组平均值）...")
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 颜色设置：UK使用RGB(227, 195, 65)金黄色
    treatment_color = (227/255, 195/255, 65/255)  # 金黄色
    control_avg_color = 'gray'  # 控制组使用灰色
    
    # 计算控制组平均值（仅使用最终选定的控制国家）
    control_avg_data = {}
    all_years = set()
    
    for country in final_control_group:
        country_data = y_kt[y_kt['country'] == country].copy()
        all_years.update(country_data['year'].values)
    
    for year in sorted(all_years):
        year_values = []
        for country in final_control_group:
            country_data = y_kt[(y_kt['country'] == country) & (y_kt['year'] == year)]
            if len(country_data) > 0:
                year_values.append(country_data['log_Y_kt'].values[0])
        if len(year_values) > 0:
            control_avg_data[year] = np.mean(year_values)
    
    # 绘制控制组平均值线
    if len(control_avg_data) > 0:
        control_years = sorted(control_avg_data.keys())
        control_avg_values = [control_avg_data[y] for y in control_years]
        
        selected_countries_str = ', '.join([c.replace('_', ' ').replace('-', ' ').title() 
                                           for c in final_control_group])
        
        ax.plot(
            control_years, control_avg_values,
            color=control_avg_color, linewidth=3.5, linestyle='--', alpha=0.9,
            marker='s', markersize=8, markevery=2,
            label='Control Group Average',
            zorder=5
        )
    
    # 绘制EU-27（处理组）
    eu_data = y_kt[y_kt['country'] == EU_27_NAME].copy()
    eu_data = eu_data.sort_values('year')
    ax.plot(
        eu_data['year'], eu_data['log_Y_kt'], 
        color=treatment_color, linewidth=4, marker='o', markersize=10,
        label='Treatment: EU-27',
        markeredgecolor='white', markeredgewidth=1.5,
        zorder=10  # 确保处理组线在最上层
    )
    
    # 添加关键事件线
    ax.axvline(x=2016, color='red', linestyle='--', alpha=0.7, linewidth=2, 
               label='2016: Brexit', zorder=3)
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel('log(Total International Cooperation Articles + 1)', 
                  fontsize=14, fontweight='bold')
    ax.set_title('Parallel Trends: EU-27 vs Control Group Average Comparison', 
                fontsize=16, fontweight='bold', pad=20)
    
    # 准备图例标签，包含控制国家信息
    selected_countries_str = ', '.join([c.replace('_', ' ').replace('-', ' ').title() 
                                       for c in final_control_group])
    
    # 获取现有的图例句柄和标签
    handles, labels = ax.get_legend_handles_labels()
    
    # 添加控制国家信息到控制组平均值的标签中
    for i, label in enumerate(labels):
        if 'Control Group Average' in label:
            labels[i] = f'Control Group Average\n({selected_countries_str})'
            break
    
    # 创建图例
    ax.legend(handles, labels, loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    
    # 网格和刻度
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.set_xticks(range(2005, 2025, 2))
    ax.tick_params(axis='both', labelsize=12)
    
    # 去掉上边和右边的边框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 设置x轴范围
    ax.set_xlim(left=2004.5, right=2024.5)
    
    plt.tight_layout()
    
    # 保存图表（同时保存PNG和PDF格式）
    plot_filename_png = f'{plot_dir}/ppml_did_parallel_trends_summary_eu.png'
    plt.savefig(plot_filename_png, dpi=300, bbox_inches='tight')
    print(f"  ✅ PNG已保存: {plot_filename_png}")
    
    try:
        plot_filename_pdf = f'{plot_dir}/ppml_did_parallel_trends_summary_eu.pdf'
        plt.savefig(plot_filename_pdf, format='pdf', bbox_inches='tight')
        print(f"  ✅ PDF已保存: {plot_filename_pdf}")
    except Exception as e:
        print(f"  ⚠️ PDF保存失败: {e}")
    
    plt.close()
    
    print(f"\n✅ 所有图表已保存到: {plot_dir}/")



def main():
    print("="*80)
    print("PPML-DiD 控制组选择流程（欧盟分析）")
    print("="*80)
    
    # 检查是否存在已有数据文件
    existing_file = f'{output_dir}/control_group_cooperation_data.xlsx'
    use_existing = os.path.exists(existing_file)
    
    if use_existing:
        print(f"\n✅ 检测到已有数据文件: {existing_file}")
        print("将直接从已有文件构建Y_{{k,t}}数据，跳过第0步")
        
        # 直接从已有文件构建y_kt
        y_kt, j_master, panel_df = load_y_kt_from_existing_file(existing_file)
    else:
        print(f"\n⚠️ 未找到已有数据文件: {existing_file}")
        print("将执行完整的第0步：准备聚合数据...")
        
        # 读取原始数据
        print("\n读取原始数据...")
        df = pd.read_csv(
            raw_data_dir,
            dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
        )
        df.columns = ['article_id', 'year', 'countries']
        df = df.dropna(subset=['countries', 'year'])
        df['year'] = df['year'].astype(int)
        df = df[(df['year'] >= 2005) & (df['year'] <= 2024)].copy()
        
        print(f"数据形状: {df.shape}")
        print(f"年份范围: {df['year'].min()} - {df['year'].max()}")
        
        # 解析国家信息
        print("\n解析国家信息...")
        df['country_list'] = df['countries'].apply(parse_countries)
        
        # 第0步：准备聚合数据
        y_kt, j_master, panel_df = step0_prepare_aggregate_data(df, use_existing_data=False, existing_file=None)
    
    # 第1阶段：斜率匹配
    stage1_countries, stage1_results = stage1_slope_matching(y_kt)
    
    # 第2阶段：RMSE最小化
    final_control_group, stage2_results = stage2_rmse_minimization(y_kt, stage1_countries)
    
    # 创建可视化
    create_visualizations(y_kt, stage1_results, stage2_results, final_control_group)
    
    # 保存结果
    print("\n" + "="*80)
    print("保存结果")
    print("="*80)
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Y_{{k,t}}数据
        y_kt.to_excel(writer, sheet_name='Y_kt_Data', index=False)
        
        # J_Master清单
        pd.DataFrame({'partner': j_master}).to_excel(
            writer, sheet_name='J_Master_List', index=False
        )
        
        # 第1阶段结果
        stage1_results.to_excel(writer, sheet_name='Stage1_Slope_Matching', index=False)
        
        # 第2阶段结果
        stage2_results.to_excel(writer, sheet_name='Stage2_RMSE_Minimization', index=False)
        
        # 最终控制组
        pd.DataFrame({
            'country': final_control_group,
            'rank': range(1, len(final_control_group) + 1)
        }).to_excel(writer, sheet_name='Final_Control_Group', index=False)
        
        # 面板数据（样本，如果存在）
        if panel_df is not None:
            panel_sample = panel_df.head(10000)
            print(f"\n保存面板数据样本...")
            print(f"  面板数据样本形状: {panel_sample.shape}")
            panel_sample.to_excel(writer, sheet_name='Panel_Data_Sample', index=False)
            print(f"  ✅ 面板数据样本已保存到sheet 'Panel_Data_Sample'")
        else:
            print(f"\n⚠️ 面板数据不可用（从已有文件读取时未生成）")
    
    print(f"\n✅ 结果已保存到: {output_file}")
    print(f"\n最终选择的控制组国家（前3名）:")
    for i, country in enumerate(final_control_group, 1):
        print(f"  {i}. {country}")
    
    print("\n" + "="*80)
    print("PPML-DiD 控制组选择流程完成！")
    print("="*80)

if __name__ == '__main__':
    main()