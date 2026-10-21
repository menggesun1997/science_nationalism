#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Event Study结果
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 读取数据
data_file = "event_study_results/event_study_all_countries_data.csv"
df = pd.read_csv(data_file)

print("="*80)
print("Event Study结果分析")
print("="*80)
print(f"\n数据概览:")
print(f"总记录数: {len(df)}")
print(f"国家数: {df['country'].nunique()}")
print(f"年份范围: {df['year'].min()} - {df['year'].max()}")
print(f"\n国家列表: {sorted(df['country'].unique())}")

# 检查数据问题
print("\n" + "="*80)
print("数据质量检查")
print("="*80)

# 检查标准误
zero_se_count = (df['se'] == 0).sum()
print(f"\n⚠️  标准误为0的记录数: {zero_se_count} / {len(df)} ({zero_se_count/len(df)*100:.1f}%)")

# 检查重复年份
duplicates = df.groupby(['country', 'year']).size()
duplicate_years = duplicates[duplicates > 1]
if len(duplicate_years) > 0:
    print(f"\n⚠️  发现重复年份的国家:")
    for (country, year), count in duplicate_years.items():
        print(f"  {country}, {year}: {count}条记录")

# 检查基准年
base_year = 2016
baseline_data = df[df['year'] == base_year]
print(f"\n基准年({base_year})数据:")
print(f"  记录数: {len(baseline_data)}")
print(f"  系数范围: [{baseline_data['coef'].min():.4f}, {baseline_data['coef'].max():.4f}]")
print(f"  预期: 所有系数应该接近0（基准年）")

# 分析每个国家
print("\n" + "="*80)
print("各国分析结果")
print("="*80)

target_countries = sorted(df['country'].unique())

for country in target_countries:
    country_data = df[df['country'] == country].copy()
    country_data = country_data.sort_values('year')
    
    # 分离Brexit前后
    pre_brexit = country_data[country_data['year'] < base_year]
    baseline = country_data[country_data['year'] == base_year]
    post_brexit = country_data[country_data['year'] > base_year]
    
    print(f"\n{country}:")
    print(f"  数据点: {len(country_data)}个年份 ({country_data['year'].min()}-{country_data['year'].max()})")
    
    # Brexit前趋势
    if len(pre_brexit) > 0:
        pre_mean = pre_brexit['coef'].mean()
        pre_std = pre_brexit['coef'].std()
        pre_trend = np.polyfit(pre_brexit['year'], pre_brexit['coef'], 1)[0]
        print(f"  Brexit前(2010-2015):")
        print(f"    平均系数: {pre_mean:.4f} (标准差: {pre_std:.4f})")
        print(f"    趋势斜率: {pre_trend:.4f} {'(上升)' if pre_trend > 0 else '(下降)' if pre_trend < 0 else '(平稳)'}")
        print(f"    系数范围: [{pre_brexit['coef'].min():.4f}, {pre_brexit['coef'].max():.4f}]")
    
    # 基准年
    if len(baseline) > 0:
        baseline_coefs = baseline['coef'].values
        print(f"  基准年(2016):")
        print(f"    系数: {baseline_coefs}")
        if len(baseline_coefs) > 1:
            print(f"    ⚠️  警告: 基准年有多个系数值!")
    
    # Brexit后效应
    if len(post_brexit) > 0:
        post_mean = post_brexit['coef'].mean()
        post_std = post_brexit['coef'].std()
        post_trend = np.polyfit(post_brexit['year'], post_brexit['coef'], 1)[0]
        
        # 计算百分比变化
        pct_change_mean = (np.exp(post_mean) - 1) * 100
        
        print(f"  Brexit后(2017-2024):")
        print(f"    平均系数: {post_mean:.4f} (标准差: {post_std:.4f})")
        print(f"    平均百分比变化: {pct_change_mean:.2f}%")
        print(f"    趋势斜率: {post_trend:.4f} {'(上升)' if post_trend > 0 else '(下降)' if post_trend < 0 else '(平稳)'}")
        print(f"    系数范围: [{post_brexit['coef'].min():.4f}, {post_brexit['coef'].max():.4f}]")
        
        # 短期vs长期
        short_term = post_brexit[post_brexit['year'] <= 2018]
        long_term = post_brexit[post_brexit['year'] >= 2020]
        
        if len(short_term) > 0:
            st_mean = short_term['coef'].mean()
            st_pct = (np.exp(st_mean) - 1) * 100
            print(f"    短期效应(2017-2018): 平均系数={st_mean:.4f} ({st_pct:.2f}%)")
        
        if len(long_term) > 0:
            lt_mean = long_term['coef'].mean()
            lt_pct = (np.exp(lt_mean) - 1) * 100
            print(f"    长期效应(2020-2024): 平均系数={lt_mean:.4f} ({lt_pct:.2f}%)")

# 总结
print("\n" + "="*80)
print("主要发现总结")
print("="*80)

print("\n1. 平行趋势检验（Brexit前，2010-2015）:")
pre_brexit_all = df[df['year'] < base_year]
if len(pre_brexit_all) > 0:
    pre_mean_all = pre_brexit_all['coef'].mean()
    pre_std_all = pre_brexit_all['coef'].std()
    print(f"   所有国家Brexit前平均系数: {pre_mean_all:.4f} (标准差: {pre_std_all:.4f})")
    print(f"   如果接近0且标准差小，说明平行趋势假设可能成立")

print("\n2. Brexit效应（2017-2024）:")
post_brexit_all = df[df['year'] > base_year]
if len(post_brexit_all) > 0:
    post_mean_all = post_brexit_all['coef'].mean()
    post_std_all = post_brexit_all['coef'].std()
    pct_change_all = (np.exp(post_mean_all) - 1) * 100
    print(f"   所有国家Brexit后平均系数: {post_mean_all:.4f} (标准差: {post_std_all:.4f})")
    print(f"   平均百分比变化: {pct_change_all:.2f}%")
    
    # 按国家分组
    country_effects = post_brexit_all.groupby('country')['coef'].mean()
    positive_effects = country_effects[country_effects > 0]
    negative_effects = country_effects[country_effects < 0]
    
    print(f"\n   正效应国家({len(positive_effects)}个):")
    for country, coef in positive_effects.sort_values(ascending=False).items():
        pct = (np.exp(coef) - 1) * 100
        print(f"     {country}: {coef:.4f} ({pct:.2f}%)")
    
    print(f"\n   负效应国家({len(negative_effects)}个):")
    for country, coef in negative_effects.sort_values().items():
        pct = (np.exp(coef) - 1) * 100
        print(f"     {country}: {coef:.4f} ({pct:.2f}%)")

print("\n3. 数据质量问题:")
print(f"   ⚠️  所有标准误为0，无法进行统计显著性检验")
print(f"   ⚠️  置信区间等于系数值，说明标准误提取有问题")
print(f"   建议: 检查Stata代码中的parmest命令是否正确提取了标准误")

print("\n" + "="*80)
print("分析完成")
print("="*80)



















