#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建控制组国家数据
步骤：
1. 找到与乌克兰合作过的所有国家P
2. 计算控制组国家（Serbia, Georgia, Armenia, Azerbaijan, Moldova, Bosnia-Herzegovina, Brazil, South Africa, Argentina）
   与集合P中所有国家的合作数量，从2005-2024年
3. 生成用于PPML分析的数据
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import pandas as pd
import numpy as np
from collections import defaultdict
import re
import matplotlib.pyplot as plt
import matplotlib
import os

# 数据文件路径
raw_data_dir = str(CODE / "0raw_publiations_process/brexit_experimental_data/article_countries_aggregated.txt")

# 控制组国家列表
control_countries = [
    'SERBIA', 'GEORGIA', 'ARMENIA', 'AZERBAIJAN', 
    'MOLDOVA', 'BOSNIA-HERZEGOVINA', 'BOSNIA AND HERZEGOVINA',
    'BRAZIL', 'SOUTH AFRICA', 'ARGENTINA'
]

# 输出文件路径
output_dir = str(CODE / "2two_way_did_ukraine")
output_file = f'{output_dir}/control_group_cooperation_data.xlsx'

def parse_countries(country_str):
    """
    解析国家字符串，提取所有国家
    处理可能的引号、逗号分隔等情况
    """
    if pd.isna(country_str) or country_str == '' or str(country_str).upper() == 'NAN':
        return []
    
    # 转换为字符串并去除首尾空白
    countries_str = str(country_str).strip().upper()
    
    # 如果字符串以引号开始和结束，去除引号
    if countries_str.startswith('"') and countries_str.endswith('"'):
        countries_str = countries_str[1:-1]
    elif countries_str.startswith("'") and countries_str.endswith("'"):
        countries_str = countries_str[1:-1]
    
    # 智能分割：处理国家名称中包含逗号的情况
    special_suffixes = ['REP.', 'ISLAMIC REP.']
    
    # 先按逗号分割
    parts = countries_str.split(',')
    countries = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
        
        # 检查下一个部分是否是当前部分的后缀
        if i + 1 < len(parts):
            next_part = parts[i + 1].strip()
            if next_part in special_suffixes:
                countries.append((part + ', ' + next_part).strip())
                i += 2
                continue
        
        countries.append(part)
        i += 1
    
    # 过滤空字符串和NAN
    countries = [c for c in countries if c and c != 'NAN' and c.strip() != '']
    
    return countries

def contains_ukraine(country_list):
    """检查国家列表中是否包含乌克兰"""
    ukraine_variants = {'UKRAINE', 'UKRAINIAN', 'UA', 'UKR'}
    country_set = {country.upper().strip() for country in country_list}
    return bool(country_set & ukraine_variants)

def normalize_by_baseline(data, baseline_year=2021):
    """
    以基准年（2021）为基准进行标准化
    标准化后的值 = 当前值 / 基准年值
    """
    data = data.copy()
    data = data.sort_values('year')
    
    # 找到基准年的值
    baseline_value = data[data['year'] == baseline_year]['coop_articles_with_P'].values
    if len(baseline_value) > 0 and baseline_value[0] > 0:
        baseline = baseline_value[0]
    else:
        # 如果基准年为0，尝试使用前一年的值
        prev_year_data = data[data['year'] < baseline_year]
        if len(prev_year_data) > 0:
            prev_values = prev_year_data['coop_articles_with_P'].values
            prev_nonzero = prev_values[prev_values > 0]
            if len(prev_nonzero) > 0:
                baseline = prev_nonzero[-1]  # 使用最后一个非零值
            else:
                baseline = 1  # 如果所有值都是0，设为1避免除零
        else:
            baseline = 1
    
    # 计算标准化值
    data['normalized'] = data['coop_articles_with_P'] / baseline
    
    return data, baseline

def is_control_country(country):
    """检查是否属于控制组国家"""
    country_upper = country.upper().strip()
    # 处理变体名称
    control_variants = {
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
    
    for control_name, variants in control_variants.items():
        if country_upper in variants:
            return True, control_name
    return False, None

def main():
    print("=" * 80)
    print("构建控制组国家数据")
    print("=" * 80)
    
    # 1. 读取原始数据
    print("\n步骤1: 读取原始数据...")
    df = pd.read_csv(
        raw_data_dir,
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
    )
    df.columns = ['article_id', 'year', 'countries']
    df = df.dropna(subset=['countries', 'year'])
    df['year'] = df['year'].astype(int)
    
    # 只保留2005-2024年的数据
    df = df[(df['year'] >= 2005) & (df['year'] <= 2024)].copy()
    
    print(f"数据形状: {df.shape}")
    print(f"年份范围: {df['year'].min()} - {df['year'].max()}")
    
    # 解析国家信息
    print("\n步骤2: 解析国家信息...")
    df['country_list'] = df['countries'].apply(parse_countries)
    
    # 2. 找到与乌克兰合作过的所有国家P
    print("\n步骤3: 找到与乌克兰合作过的所有国家P...")
    ukraine_articles = df[df['country_list'].apply(contains_ukraine)].copy()
    print(f"包含乌克兰的文章数量: {len(ukraine_articles)}")
    
    # 提取所有与乌克兰合作过的国家（排除乌克兰自己）
    ukraine_variants = {'UKRAINE', 'UKRAINIAN', 'UA', 'UKR'}
    partner_countries_set = set()
    
    for _, row in ukraine_articles.iterrows():
        countries = row['country_list']
        for country in countries:
            country_upper = country.upper().strip()
            if country_upper not in ukraine_variants:
                partner_countries_set.add(country_upper)
    
    partner_countries = sorted(list(partner_countries_set))
    print(f"与乌克兰合作过的国家数量（集合P）: {len(partner_countries)}")
    print(f"前20个合作伙伴: {partner_countries[:20]}")
    
    # 3. 计算控制组国家与集合P的合作数量
    print("\n步骤4: 计算控制组国家与集合P的合作数量...")
    
    # 创建控制组国家与集合P的合作数据
    control_cooperation_data = []
    
    # 遍历所有文章
    for _, row in df.iterrows():
        year = row['year']
        countries = row['country_list']
        article_id = row['article_id']
        
        # 检查是否包含控制组国家
        control_in_article = []
        for country in countries:
            is_control, control_name = is_control_country(country)
            if is_control:
                control_in_article.append(control_name)
        
        # 如果文章包含控制组国家，检查是否也包含集合P中的国家
        if control_in_article:
            partners_in_article = []
            for country in countries:
                country_upper = country.upper().strip()
                if country_upper in partner_countries_set:
                    partners_in_article.append(country_upper)
            
            # 如果同时包含控制组国家和集合P中的国家，记录合作
            if partners_in_article:
                for control_country in control_in_article:
                    for partner_country in partners_in_article:
                        control_cooperation_data.append({
                            'year': year,
                            'control_country': control_country,
                            'partner_country': partner_country,
                            'article_id': article_id
                        })
    
    # 转换为DataFrame
    cooperation_df = pd.DataFrame(control_cooperation_data)
    
    if len(cooperation_df) == 0:
        print("警告：未找到控制组国家与集合P的合作数据！")
        return
    
    print(f"控制组国家与集合P的合作记录数: {len(cooperation_df)}")
    
    # 4. 汇总数据：按年份、控制组国家、集合P汇总合作文章数
    print("\n步骤5: 汇总数据...")
    
    # 方法1：按控制组国家和年份汇总与集合P的总合作数
    summary_by_control = cooperation_df.groupby(['year', 'control_country']).agg({
        'article_id': 'nunique'  # 计算不重复的文章数
    }).reset_index()
    summary_by_control.columns = ['year', 'country', 'coop_articles_with_P']
    
    # 方法2：按控制组国家、年份、集合P中的每个国家汇总
    summary_by_control_partner = cooperation_df.groupby(['year', 'control_country', 'partner_country']).agg({
        'article_id': 'nunique'
    }).reset_index()
    summary_by_control_partner.columns = ['year', 'control_country', 'partner_country', 'coop_articles']
    
    # 创建完整的年份-控制组国家矩阵（方法1）
    all_years = sorted(df['year'].unique())
    all_control_countries = sorted(summary_by_control['country'].unique())
    
    year_control_combinations = []
    for year in all_years:
        for country in all_control_countries:
            year_control_combinations.append({'year': year, 'country': country})
    
    complete_df = pd.DataFrame(year_control_combinations)
    summary_complete = complete_df.merge(
        summary_by_control,
        on=['year', 'country'],
        how='left'
    ).fillna(0)
    
    summary_complete['coop_articles_with_P'] = summary_complete['coop_articles_with_P'].astype(int)
    
    # 计算每年所有控制组国家与集合P的总合作数（用于offset）
    summary_complete['total_control_P_coop'] = summary_complete.groupby('year')['coop_articles_with_P'].transform('sum')
    summary_complete['log_total_control_P'] = np.log(summary_complete['total_control_P_coop'] + 1)
    
    print(f"\n汇总数据形状: {summary_complete.shape}")
    print("\n前10行汇总数据:")
    print(summary_complete.head(10))
    
    print("\n按控制组国家统计:")
    print(summary_complete.groupby('country')['coop_articles_with_P'].sum().sort_values(ascending=False))
    
    print("\n按年份统计:")
    print(summary_complete.groupby('year')['coop_articles_with_P'].sum())
    
    # 5. 计算乌克兰与集合P每年的总合作数量（用于对比）
    print("\n步骤5: 计算乌克兰与集合P每年的总合作数量...")
    ukraine_P_cooperation = []
    
    for _, row in ukraine_articles.iterrows():
        year = row['year']
        countries = row['country_list']
        article_id = row['article_id']
        
        # 提取集合P中的国家
        partners_in_article = []
        for country in countries:
            country_upper = country.upper().strip()
            if country_upper in partner_countries_set:
                partners_in_article.append(country_upper)
        
        # 如果包含集合P中的国家，记录合作
        if partners_in_article:
            for partner_country in partners_in_article:
                ukraine_P_cooperation.append({
                    'year': year,
                    'partner_country': partner_country,
                    'article_id': article_id
                })
    
    ukraine_P_df = pd.DataFrame(ukraine_P_cooperation)
    
    # 按年份汇总乌克兰与集合P的总合作数
    ukraine_P_yearly = ukraine_P_df.groupby('year').agg({
        'article_id': 'nunique'
    }).reset_index()
    ukraine_P_yearly.columns = ['year', 'ukraine_coop_with_P']
    
    # 创建完整的年份序列（包含所有年份）
    all_years_df = pd.DataFrame({'year': sorted(df['year'].unique())})
    ukraine_P_yearly = all_years_df.merge(ukraine_P_yearly, on='year', how='left').fillna(0)
    ukraine_P_yearly['ukraine_coop_with_P'] = ukraine_P_yearly['ukraine_coop_with_P'].astype(int)
    
    print("\n乌克兰与集合P每年的合作数量:")
    print(ukraine_P_yearly)
    
    # 按年份和每个合作伙伴国家汇总乌克兰的详细合作数据
    print("\n步骤5.1: 计算乌克兰与每个合作伙伴国家的详细合作数据...")
    ukraine_P_by_partner = ukraine_P_df.groupby(['year', 'partner_country']).agg({
        'article_id': 'nunique'
    }).reset_index()
    ukraine_P_by_partner.columns = ['year', 'partner_country', 'coop_articles']
    
    print(f"乌克兰与合作伙伴详细数据形状: {ukraine_P_by_partner.shape}")
    print("\n前10行乌克兰与合作伙伴详细数据:")
    print(ukraine_P_by_partner.head(10))
    
    # 6. 保存数据
    print("\n步骤6: 保存数据...")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 保存汇总数据（用于PPML分析）
        summary_complete.to_excel(writer, sheet_name='控制组与集合P合作汇总', index=False)
        
        # 保存详细数据（按控制组国家和集合P中的每个国家）
        summary_by_control_partner.to_excel(writer, sheet_name='控制组与集合P详细合作', index=False)
        
        # 保存集合P国家列表
        pd.DataFrame({'partner_country': partner_countries}).to_excel(
            writer, sheet_name='集合P国家列表', index=False
        )
        
        # 保存乌克兰与集合P的合作数据（汇总）
        ukraine_P_yearly.to_excel(writer, sheet_name='乌克兰与集合P合作', index=False)
        
        # 保存乌克兰与每个合作伙伴国家的详细合作数据
        ukraine_P_by_partner.to_excel(writer, sheet_name='乌克兰与合作伙伴详细合作', index=False)
    
    print(f"✅ 数据已保存到: {output_file}")
    print("\n输出文件包含以下sheet:")
    print("  - 控制组与集合P合作汇总: 用于PPML分析的主要数据")
    print("  - 控制组与集合P详细合作: 按控制组国家和集合P中每个国家的详细合作数据")
    print("  - 集合P国家列表: 与乌克兰合作过的所有国家列表")
    print("  - 乌克兰与集合P合作: 乌克兰与集合P每年的总合作数量（用于对比）")
    print("  - 乌克兰与合作伙伴详细合作: 乌克兰与每个合作伙伴国家每年的详细合作数量")
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print("数据统计摘要")
    print("=" * 80)
    print(f"集合P国家数量: {len(partner_countries)}")
    print(f"控制组国家数量: {len(all_control_countries)}")
    print(f"年份范围: {summary_complete['year'].min()} - {summary_complete['year'].max()}")
    print(f"总观测数: {len(summary_complete)}")
    print(f"零值数量: {(summary_complete['coop_articles_with_P'] == 0).sum()}")
    print(f"零值比例: {(summary_complete['coop_articles_with_P'] == 0).sum() / len(summary_complete) * 100:.2f}%")
    
    # 7. 绘制时间序列图（标准化形式）
    print("\n步骤7: 绘制时间序列图（标准化形式，用于平行趋势检验）...")
    plot_dir = f'{output_dir}/parallel_trends_plots'
    os.makedirs(plot_dir, exist_ok=True)
    
    # 对乌克兰数据进行标准化
    ukraine_data = ukraine_P_yearly.copy().sort_values('year')
    ukraine_baseline_value = ukraine_data[ukraine_data['year'] == 2021]['ukraine_coop_with_P'].values
    if len(ukraine_baseline_value) > 0 and ukraine_baseline_value[0] > 0:
        ukraine_baseline = ukraine_baseline_value[0]
    else:
        prev_year_data = ukraine_data[ukraine_data['year'] < 2021]
        if len(prev_year_data) > 0:
            prev_values = prev_year_data['ukraine_coop_with_P'].values
            prev_nonzero = prev_values[prev_values > 0]
            if len(prev_nonzero) > 0:
                ukraine_baseline = prev_nonzero[-1]
            else:
                ukraine_baseline = 1
        else:
            ukraine_baseline = 1
    ukraine_data['normalized'] = ukraine_data['ukraine_coop_with_P'] / ukraine_baseline
    
    # 为每个控制组国家创建单独的图表（标准化形式）
    for control_country in all_control_countries:
        # 提取该控制组国家的数据
        control_data = summary_complete[summary_complete['country'] == control_country].copy()
        control_data = control_data.sort_values('year')
        
        # 标准化
        control_data_norm, baseline = normalize_by_baseline(control_data, baseline_year=2021)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制标准化后的控制组国家数据
        ax.plot(control_data_norm['year'], control_data_norm['normalized'], 
                marker='o', linewidth=2, markersize=8, 
                label=f'{control_country} (Normalized, baseline={baseline:.0f})', 
                color='#2E86AB')
        
        # 绘制标准化后的乌克兰数据
        ax.plot(ukraine_data['year'], ukraine_data['normalized'], 
                marker='s', linewidth=2, markersize=8, 
                label=f'Ukraine (Normalized, baseline={ukraine_baseline:.0f})', 
                color='#A23B72', linestyle='--')
        
        # 添加基准线（y=1）
        ax.axhline(y=1, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline (2021)')
        
        # 添加2022年垂直线（战争开始年份）
        ax.axvline(x=2022, color='red', linestyle=':', linewidth=2, alpha=0.7, label='War Start (2022)')
        
        # 添加2021年垂直线（基准年）
        ax.axvline(x=2021, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline Year (2021)')
        
        # 设置图表属性
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Normalized Cooperation Articles\n(Relative to 2021 baseline)', fontsize=12, fontweight='bold')
        ax.set_title(f'{control_country} vs Ukraine Cooperation with Set P\n(Normalized by 2021 Baseline)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(left=2004.5, right=2024.5)
        
        # 设置x轴刻度
        ax.set_xticks(sorted(df['year'].unique()))
        ax.tick_params(axis='x', rotation=45)
        
        # 添加文本说明
        pre_war_years = control_data_norm[control_data_norm['year'] <= 2021]
        post_war_years = control_data_norm[control_data_norm['year'] >= 2022]
        
        if len(pre_war_years) > 0 and len(post_war_years) > 0:
            pre_avg = pre_war_years['normalized'].mean()
            post_avg = post_war_years['normalized'].mean()
            textstr = f'Pre-war Avg (normalized): {pre_avg:.2f}\nPost-war Avg (normalized): {post_avg:.2f}'
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                   verticalalignment='top', bbox=props)
        
        plt.tight_layout()
        
        # 保存图表
        plot_filename = f'{plot_dir}/{control_country}_parallel_trends.png'
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
        print(f"  ✅ 已保存: {plot_filename}")
        plt.close()
    
    # 创建综合图表：所有控制组国家在一张图上（标准化形式）
    print("\n创建综合图表（所有控制组国家，标准化形式）...")
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 为每个控制组国家绘制线条（标准化）
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_control_countries)))
    for i, control_country in enumerate(all_control_countries):
        control_data = summary_complete[summary_complete['country'] == control_country].copy()
        control_data = control_data.sort_values('year')
        control_data_norm, _ = normalize_by_baseline(control_data, baseline_year=2021)
        
        ax.plot(control_data_norm['year'], control_data_norm['normalized'], 
                marker='o', linewidth=2, markersize=6, 
                label=f'{control_country}', color=colors[i])
    
    # 绘制标准化后的乌克兰数据
    ax.plot(ukraine_data['year'], ukraine_data['normalized'], 
            marker='s', linewidth=3, markersize=10, 
            label='Ukraine', color='black', linestyle='--', alpha=0.8)
    
    # 添加基准线和垂直线
    ax.axhline(y=1, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline (2021)')
    ax.axvline(x=2022, color='red', linestyle=':', linewidth=2, alpha=0.7, label='War Start (2022)')
    ax.axvline(x=2021, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline Year (2021)')
    
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Normalized Cooperation Articles\n(Relative to 2021 baseline)', fontsize=12, fontweight='bold')
    ax.set_title('All Control Group Countries vs Ukraine Cooperation with Set P\n(Normalized by 2021 Baseline)', 
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='best', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(left=2014.5, right=2024.5)
    ax.set_xticks(sorted(df['year'].unique()))
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plot_filename = f'{plot_dir}/all_control_countries_parallel_trends.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"  ✅ 已保存: {plot_filename}")
    plt.close()
    
    print(f"\n✅ 所有图表已保存到: {plot_dir}/")
    print(f"✅ 可视化完成！所有图表已使用标准化形式（以2021年为基准）")

if __name__ == '__main__':
    main()

