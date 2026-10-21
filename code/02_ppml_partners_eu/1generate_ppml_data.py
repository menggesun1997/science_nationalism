#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成PPML分析数据（EU-27内部控制组分析）
根据图片中的模型要求生成数据：
- paper_count: 双边合作计数
- partner_id: 合作伙伴国家ID
- year: 年份
- post_brexit: Brexit后虚拟变量（2017年及之后为1，2016年为基准年）
- ln_total_vol: offset变量（EU-27总合作量的对数）
- ln_total_pub: 控制变量（合作伙伴国家总发文量的对数）
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent


import pandas as pd
import numpy as np
import os

# 数据文件路径
input_file = str(HERE / "control_group_cooperation_data.xlsx")
countries_stats_file = str(CODE / "00_data_processing/brexit_experimental_data/countries_yearly_statistics.csv")
output_dir = str(HERE)

# 输出文件路径
output_csv = f'{output_dir}/ppml_data.csv'
output_dta = f'{output_dir}/ppml_data.dta'
output_xlsx = f'{output_dir}/ppml_data.xlsx'

# Brexit基准年份（2016年）
BREXIT_YEAR = 2016

def main():
    print("="*80)
    print("生成PPML分析数据（EU-27内部控制组分析 - Brexit影响）")
    print("="*80)
    
    # 1. 读取EU-27与合作伙伴详细合作数据
    print("\n步骤1: 读取EU-27与合作伙伴详细合作数据...")
    df_eu = pd.read_excel(input_file, sheet_name='EU-27与合作伙伴详细合作')
    print(f"✅ 读取成功")
    print(f"  数据形状: {df_eu.shape}")
    print(f"  列名: {list(df_eu.columns)}")
    print(f"  年份范围: {df_eu['year'].min()} - {df_eu['year'].max()}")
    print(f"  唯一合作伙伴数: {df_eu['partner_country'].nunique()}")
    
    # 标准化国家名称（确保大写且去除空格）
    if 'partner_country' in df_eu.columns:
        df_eu['partner_country'] = df_eu['partner_country'].str.upper().str.strip()
    
    # 重命名列以匹配模型要求
    df_eu = df_eu.rename(columns={
        'coop_articles': 'paper_count'
    })
    
    # 2. 读取EU-27总合作量数据（用于offset）
    print("\n步骤2: 读取EU-27总合作量数据...")
    df_total = pd.read_excel(input_file, sheet_name='EU-27与非EU-27合作')
    print(f"✅ 读取成功")
    print(f"  数据形状: {df_total.shape}")
    print(f"  列名: {list(df_total.columns)}")
    
    # 重命名列
    df_total = df_total.rename(columns={
        'eu_coop_with_non_eu': 'total_vol'
    })
    
    # 计算对数（避免log(0)）
    df_total['ln_total_vol'] = np.log(df_total['total_vol'].clip(lower=1))
    
    # 2.5 读取各国发文量统计数据（用于控制变量）
    print("\n步骤2.5: 读取各国发文量统计数据...")
    df_countries_stats = pd.read_csv(countries_stats_file)
    print(f"✅ 读取成功")
    print(f"  数据形状: {df_countries_stats.shape}")
    print(f"  列名: {list(df_countries_stats.columns)}")
    
    # 标准化国家名称（确保大写且去除空格）
    df_countries_stats['Country'] = df_countries_stats['Country'].str.upper().str.strip()
    
    # 重命名列以便合并
    df_countries_stats = df_countries_stats.rename(columns={
        'Country': 'partner_country',
        'Year': 'year',
        'Total_Publications': 'total_pub',
        'International_Collaborations': 'total_international'
    })
    
    # 计算对数（避免log(0)）
    df_countries_stats['ln_total_pub'] = np.log(df_countries_stats['total_pub'].clip(lower=1))
    df_countries_stats['ln_total_international'] = np.log(df_countries_stats['total_international'].clip(lower=1))
    
    print(f"  年份范围: {df_countries_stats['year'].min()} - {df_countries_stats['year'].max()}")
    print(f"  唯一国家数: {df_countries_stats['partner_country'].nunique()}")
    
    # 3. 合并数据
    print("\n步骤3: 合并数据...")
    # 先合并EU-27总合作量
    ppml_data = df_eu.merge(df_total[['year', 'total_vol', 'ln_total_vol']], 
                                 on='year', how='left')
    # 再合并各国发文量
    ppml_data = ppml_data.merge(
        df_countries_stats[['partner_country', 'year', 'total_pub', 'ln_total_pub', 'total_international', 'ln_total_international']],
        on=['partner_country', 'year'],
        how='left'
    )
    print(f"✅ 合并完成")
    print(f"  合并后数据形状: {ppml_data.shape}")
    
    # 检查合并情况
    missing_pub = ppml_data['ln_total_pub'].isna().sum()
    if missing_pub > 0:
        print(f"⚠️  警告: 有 {missing_pub} 个观测值缺少合作伙伴发文量数据")
        print(f"  这些观测值将使用0填充（ln_total_pub = ln(1) = 0）")
        
        # 打印缺失值的详细信息
        missing_data = ppml_data[ppml_data['ln_total_pub'].isna()][['partner_country', 'year', 'paper_count']].copy()
        print(f"\n缺失值详细信息（前20个）:")
        print(missing_data.head(20).to_string(index=False))
        if len(missing_data) > 20:
            print(f"... 共 {len(missing_data)} 个缺失值")
        
        # 按国家统计缺失值
        missing_by_country = missing_data.groupby('partner_country').size().sort_values(ascending=False)
        print(f"\n按国家统计缺失值数量（前20个国家）:")
        print(missing_by_country.head(20).to_string())
        if len(missing_by_country) > 20:
            print(f"... 共 {len(missing_by_country)} 个国家有缺失值")
        
        # 使用0填充缺失值（ln(1) = 0）
        ppml_data['ln_total_pub'] = ppml_data['ln_total_pub'].fillna(0)
        ppml_data['total_pub'] = ppml_data['total_pub'].fillna(1)  # 对应的原始值设为1
        print(f"✅ 已使用0填充缺失值")
    
    # 4. 创建完整面板（补零）
    print("\n步骤4: 创建完整面板（补零）...")
    all_years = sorted(ppml_data['year'].unique())
    all_partners = sorted(ppml_data['partner_country'].unique())
    
    print(f"  年份数: {len(all_years)} ({min(all_years)}-{max(all_years)})")
    print(f"  合作伙伴数: {len(all_partners)}")
    
    # 创建完整面板
    full_panel_list = []
    for partner in all_partners:
        for year in all_years:
            full_panel_list.append({
                'partner_country': partner,
                'year': year
            })
    
    full_panel_df = pd.DataFrame(full_panel_list)
    print(f"  完整面板大小: {full_panel_df.shape}")
    
    # 合并实际数据
    ppml_data_full = full_panel_df.merge(
        ppml_data[['partner_country', 'year', 'paper_count']],
        on=['partner_country', 'year'],
        how='left'
    ).fillna(0)
    
    # 合并总合作量数据
    ppml_data_full = ppml_data_full.merge(
        df_total[['year', 'total_vol', 'ln_total_vol']],
        on='year',
        how='left'
    )
    
    # 合并各国发文量数据
    # 确保partner_country已标准化
    ppml_data_full['partner_country'] = ppml_data_full['partner_country'].str.upper().str.strip()

    ppml_data_full = ppml_data_full.merge(
        df_countries_stats[['partner_country', 'year', 'total_pub', 'ln_total_pub', 'total_international', 'ln_total_international']],
        on=['partner_country', 'year'],
        how='left'
    )
    # 填充缺失值
    ppml_data_full['ln_total_pub'] = ppml_data_full['ln_total_pub'].fillna(0)
    ppml_data_full['total_pub'] = ppml_data_full['total_pub'].fillna(1)
    ppml_data_full['ln_total_international'] = ppml_data_full['ln_total_international'].fillna(0)
    ppml_data_full['total_international'] = ppml_data_full['total_international'].fillna(1)
    ppml_data_full['paper_count'] = ppml_data_full['paper_count'].astype(int)
    
    print(f"✅ 完整面板创建完成")
    print(f"  最终数据形状: {ppml_data_full.shape}")
    
    # 8. 保存数据
    print("\n步骤8: 保存数据...")
    
    # 保存为CSV格式
    ppml_data_full.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"✅ CSV格式已保存到: {output_csv}")
    
    # 保存为Excel格式（便于查看）
    ppml_data_full.to_excel(output_xlsx, index=False, engine='openpyxl')
    print(f"✅ Excel格式已保存到: {output_xlsx}")
    
    # 保存为Stata格式
    try:
        ppml_data_full.to_stata(output_dta, write_index=False, version=118)
        print(f"✅ Stata格式已保存到: {output_dta}")
    except Exception as e:
        print(f"⚠️ 保存Stata格式时出错: {e}")
        print("   请使用CSV文件，可以在Stata中使用: import delimited using \"ppml_data.csv\"")
    
    print("\n" + "="*80)
    print("数据生成完成！")
    print("="*80)
    print(f"\n数据摘要:")
    print(f"  合作伙伴数量: {len(all_partners)}")
    print(f"  年份范围: {min(all_years)} - {max(all_years)}")
    print(f"  总观测数: {len(ppml_data_full)}")
    print(f"  零值数量: {(ppml_data_full['paper_count'] == 0).sum()}")
    print(f"  零值比例: {(ppml_data_full['paper_count'] == 0).sum() / len(ppml_data_full) * 100:.2f}%")

if __name__ == '__main__':
    main()

