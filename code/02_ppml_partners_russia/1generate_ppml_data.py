#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成PPML分析数据（俄罗斯内部控制组分析）
根据公式要求生成数据：
- paper_count: 双边合作计数（Count_jt）
- partner_id: 合作伙伴国家ID（j）
- year: 年份（t）
- post_war: 战后虚拟变量（Post_t，2022年及之后为1）
- ln_total_vol: offset变量（ln(Total_t^Intl)，俄罗斯总合作量的对数）
- ln_total_pub: 控制变量（ln(Total_jt^Pub)，合作伙伴国家总发文量的对数）
模型：E[Count_jt] = exp(α_j + λ_t + β_j · Post_t + ln(Total_t^Intl) + γ · ln(Total_jt^Pub))
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
countries_stats_file = str(CODE / "00_data_processing/raw data processing/countries_yearly_statistics.csv")
output_dir = str(HERE)

# 输出文件路径
output_csv = f'{output_dir}/ppml_data.csv'
output_dta = f'{output_dir}/ppml_data.dta'
output_xlsx = f'{output_dir}/ppml_data.xlsx'

# 战争开始年份（2022年2月）
WAR_START_YEAR = 2022

def main():
    print("="*80)
    print("生成PPML分析数据（俄罗斯内部控制组分析）")
    print("="*80)
    
    # 1. 读取俄罗斯与合作伙伴详细合作数据
    print("\n步骤1: 读取俄罗斯与合作伙伴详细合作数据...")
    df_russia = pd.read_excel(input_file, sheet_name='俄罗斯与合作伙伴详细合作')
    print(f"✅ 读取成功")
    print(f"  数据形状: {df_russia.shape}")
    print(f"  列名: {list(df_russia.columns)}")
    print(f"  年份范围: {df_russia['year'].min()} - {df_russia['year'].max()}")
    print(f"  唯一合作伙伴数: {df_russia['partner_country'].nunique()}")
    
    # 重命名列以匹配模型要求
    df_russia = df_russia.rename(columns={
        'coop_articles': 'paper_count'
    })
    
    
    # 2. 读取俄罗斯总合作量数据（用于offset）
    print("\n步骤2: 读取俄罗斯总合作量数据...")
    df_total = pd.read_excel(input_file, sheet_name='俄罗斯与集合P合作')
    print(f"✅ 读取成功")
    print(f"  数据形状: {df_total.shape}")
    print(f"  列名: {list(df_total.columns)}")
    
    # 重命名列
    df_total = df_total.rename(columns={
        'russia_coop_with_P': 'total_vol'
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
    df_russia['partner_country'] = df_russia['partner_country'].str.upper().str.strip()
    
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
    # 先合并俄罗斯总合作量
    ppml_data = df_russia.merge(df_total[['year', 'total_vol', 'ln_total_vol']], 
                                 on='year', how='left')
    
    # 再合并各国发文量（如果存在）
    ppml_data = ppml_data.merge(
        df_countries_stats[['partner_country', 'year', 'total_pub', 'ln_total_pub', 'total_international', 'ln_total_international']],
        on=['partner_country', 'year'],
        how='left'
    )
    print(f"✅ 合并完成")
    print(f"  合并后数据形状: {ppml_data.shape}")
    
    # 检查合并情况
    missing_pub = ppml_data['ln_total_pub'].isna().sum()
    print(f"\n合并情况检查:")
    if missing_pub > 0:
        print(f"⚠️  警告: 有 {missing_pub} 个观测值缺少合作伙伴发文量数据")
        
        # 找出未合并成功的国家
        missing_countries = ppml_data[ppml_data['ln_total_pub'].isna()]['partner_country'].unique()
        print(f"  未成功合并的国家数量: {len(missing_countries)}")
        print(f"  未成功合并的国家列表:")
        for country in sorted(missing_countries):
            missing_count = ppml_data[(ppml_data['partner_country'] == country) & (ppml_data['ln_total_pub'].isna())].shape[0]
            print(f"    - {country} ({missing_count} 个观测值)")
        
        # 检查这些国家在df_countries_stats中是否存在
        print(f"\n  检查这些国家在统计数据中是否存在:")
        countries_in_stats = set(df_countries_stats['partner_country'].unique())
        countries_in_russia = set(df_russia['partner_country'].unique())
        countries_not_in_stats = countries_in_russia - countries_in_stats
        if len(countries_not_in_stats) > 0:
            print(f"  在俄罗斯数据中但不在统计数据中的国家 ({len(countries_not_in_stats)} 个):")
            for country in sorted(countries_not_in_stats):
                print(f"    - {country}")
        else:
            print(f"  ✅ 所有国家都在统计数据中（可能是名称不匹配）")
        
        print(f"\n  这些观测值将使用0填充（ln_total_pub = ln(1) = 0）")
        # 使用0填充缺失值（ln(1) = 0）
        ppml_data['ln_total_pub'] = ppml_data['ln_total_pub'].fillna(0)
        ppml_data['total_pub'] = ppml_data['total_pub'].fillna(1)  # 对应的原始值设为1
        print(f"✅ 已使用0填充缺失值")
    else:
        print(f"✅ 所有观测值都成功合并了合作伙伴发文量数据")
    
    
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
    
    # 如果存在各国发文量数据，也需要合并到完整面板
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

