#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建控制组国家数据（欧盟分析）
步骤：
1. 定义欧盟（EU-27）作为整体，使用Whole Counting方法
2. 计算控制组国家（United States, Japan, Canada, Australia, Korea Rep., Switzerland, Norway）
   与非EU-27国家（包括英国）的合作数量，从2005-2024年
3. 计算EU-27与非EU-27国家（包括英国）的合作数量（因变量 Y_{EU,t}）
4. 生成用于PPML分析的数据
"""

import pandas as pd
import numpy as np
from collections import defaultdict
import re
import matplotlib.pyplot as plt
import matplotlib
import os

# 数据文件路径
raw_data_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/brexit_experimental_data/article_countries_aggregated.txt'

# 输出文件路径
output_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/2two_way_did_eu'
output_file = f'{output_dir}/control_group_cooperation_data.xlsx'

# EU-27国家列表（不包括英国）
eu_27_countries = [
    'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
    'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
    'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
    'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
    'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
    'SPAIN', 'SWEDEN'
]

# 控制组国家列表
control_countries = [
    'UNITED STATES', 'JAPAN', 'CANADA', 'AUSTRALIA', 
    'KOREA, REP.', 'SWITZERLAND', 'NORWAY'
]

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

def get_eu_countries_set():
    """获取EU-27国家的完整集合（包括变体名称）"""
    eu_variants = {
        'AUSTRIA': ['AUSTRIA', 'AUT'],
        'BELGIUM': ['BELGIUM', 'BEL'],
        'BULGARIA': ['BULGARIA', 'BGR'],
        'CROATIA': ['CROATIA', 'HRV', 'CRO'],
        'CYPRUS': ['CYPRUS', 'CYP'],
        'CZECHIA': ['CZECHIA', 'CZECH REPUBLIC', 'CZE'],
        'DENMARK': ['DENMARK', 'DNK', 'DK'],
        'ESTONIA': ['ESTONIA', 'EST'],
        'FINLAND': ['FINLAND', 'FIN'],
        'FRANCE': ['FRANCE', 'FRA', 'FR'],
        'GERMANY': ['GERMANY', 'DEU', 'DE'],
        'GREECE': ['GREECE', 'GRC', 'GR'],
        'HUNGARY': ['HUNGARY', 'HUN', 'HU'],
        'IRELAND': ['IRELAND', 'IRL', 'IE'],
        'ITALY': ['ITALY', 'ITA', 'IT'],
        'LATVIA': ['LATVIA', 'LVA', 'LV'],
        'LITHUANIA': ['LITHUANIA', 'LTU', 'LT'],
        'LUXEMBOURG': ['LUXEMBOURG', 'LUX', 'LU'],
        'MALTA': ['MALTA', 'MLT', 'MT'],
        'NETHERLANDS': ['NETHERLANDS', 'NLD', 'NL'],
        'POLAND': ['POLAND', 'POL', 'PL'],
        'PORTUGAL': ['PORTUGAL', 'PRT', 'PT'],
        'ROMANIA': ['ROMANIA', 'ROU', 'RO'],
        'SLOVAK REPUBLIC': ['SLOVAK REPUBLIC', 'SLOVAKIA', 'SVK', 'SK'],
        'SLOVENIA': ['SLOVENIA', 'SVN', 'SI'],
        'SPAIN': ['SPAIN', 'ESP', 'ES'],
        'SWEDEN': ['SWEDEN', 'SWE', 'SE']
    }
    
    eu_set = set()
    for country in eu_27_countries:
        if country in eu_variants:
            eu_set.update(eu_variants[country])
        else:
            eu_set.add(country.upper().strip())
    
    return eu_set

def contains_eu_country(country_list):
    """
    检查国家列表中是否包含任何EU-27国家
    使用Whole Counting方法：只要有一篇文章中有任何一个EU-27国家，就算是EU发文
    """
    eu_countries_set = get_eu_countries_set()
    country_set = {country.upper().strip() for country in country_list}
    return bool(country_set & eu_countries_set)

def is_eu_country(country):
    """检查单个国家是否是EU-27成员国"""
    country_upper = country.upper().strip()
    eu_countries_set = get_eu_countries_set()
    return country_upper in eu_countries_set

def is_non_eu_country(country):
    """
    检查国家是否是非EU-27国家（包括英国）
    非EU-27国家包括：英国、控制组国家、以及其他所有非EU-27国家
    """
    country_upper = country.upper().strip()
    eu_countries_set = get_eu_countries_set()
    
    # 排除EU-27国家
    if country_upper in eu_countries_set:
        return False
    
    # 其他所有国家都是非EU国家（包括英国）
    return True

def normalize_by_baseline(data, baseline_year=2015):
    """
    以基准年（2015，Brexit前一年）为基准进行标准化
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
        'UNITED STATES': ['UNITED STATES', 'USA', 'US', 'UNITED STATES OF AMERICA', 'U.S.A.', 'U.S.'],
        'JAPAN': ['JAPAN'],
        'CANADA': ['CANADA'],
        'AUSTRALIA': ['AUSTRALIA', 'COMMONWEALTH OF AUSTRALIA'],
        'KOREA, REP.': ['KOREA, REP.', 'SOUTH KOREA'],
        'SWITZERLAND': ['SWITZERLAND', 'SWISS CONFEDERATION', 'CH'],
        'NORWAY': ['NORWAY', 'KINGDOM OF NORWAY']
    }
    
    # 首先检查精确匹配标准名称
    if country_upper in control_variants:
        return True, country_upper
    
    # 检查是否匹配变体名称
    for control_name, variants in control_variants.items():
        if country_upper in variants:
            return True, control_name
    return False, None

def main():
    print("=" * 80)
    print("构建控制组国家数据（欧盟分析）")
    print("=" * 80)
    
    print(f"\nEU-27国家数量: {len(eu_27_countries)}")
    print(f"EU-27国家列表: {', '.join(eu_27_countries)}")
    print(f"\n控制组国家数量: {len(control_countries)}")
    print(f"控制组国家列表: {', '.join(control_countries)}")
    
    # 1. 读取原始数据
    print("\n步骤1: 读取原始数据...")
    df = pd.read_csv(
        raw_data_dir,
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
    )
    df.columns = ['article_id', 'year', 'countries']
    
    # 删除第一行（如果第一行是列名）
    if len(df) > 0:
        first_row = df.iloc[0]
        if (str(first_row['article_id']).upper().strip() == 'OST_BK' or
            str(first_row['year']).upper().strip() == 'ANNEE_BIBLIOGRAPHIQUE' or
            str(first_row['countries']).upper().strip() in ['PAYS', 'COUNTRIES']):
            print("检测到第一行为列名重复，删除第一行...")
            df = df.iloc[1:].reset_index(drop=True)
    
    df = df.dropna(subset=['countries', 'year'])
    df['year'] = df['year'].astype(int)
    
    # 只保留2005-2024年的数据
    df = df[(df['year'] >= 2005) & (df['year'] <= 2024)].copy()
    
    print(f"数据形状: {df.shape}")
    print(f"年份范围: {df['year'].min()} - {df['year'].max()}")
    
    # 解析国家信息
    print("\n步骤2: 解析国家信息...")
    df['country_list'] = df['countries'].apply(parse_countries)
    
    # 2. 识别EU-27文章（Whole Counting方法）
    print("\n步骤3: 识别EU-27文章（Whole Counting方法）...")
    print("方法：只要一篇文章中有任何一个EU-27国家，就算作EU-27发文")
    df['has_eu_country'] = df['country_list'].apply(contains_eu_country)
    eu_articles = df[df['has_eu_country']].copy()
    print(f"包含EU-27国家的文章数量: {len(eu_articles)}")
    print(f"EU-27文章占比: {len(eu_articles) / len(df) * 100:.2f}%")
    
    # 3. 提取所有非EU-27国家（包括英国）作为合作伙伴集合P
    print("\n步骤4: 提取所有非EU-27国家（包括英国）作为合作伙伴集合P...")
    non_eu_countries_set = set()
    
    for _, row in df.iterrows():
        countries = row['country_list']
        for country in countries:
            country_upper = country.upper().strip()
            if is_non_eu_country(country_upper):
                non_eu_countries_set.add(country_upper)
    
    partner_countries = sorted(list(non_eu_countries_set))
    print(f"非EU-27国家数量（集合P，包括英国）: {len(partner_countries)}")
    print(f"前20个非EU-27国家: {partner_countries[:20]}")
    
    # 4. 计算控制组国家与非EU-27国家的合作数量
    print("\n步骤5: 计算控制组国家与非EU-27国家的合作数量...")
    
    partner_countries_set = set(partner_countries)
    
    # 创建控制组国家与非EU-27国家的合作数据
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
        
        # 如果文章包含控制组国家，检查是否也包含非EU-27国家（集合P）
        if control_in_article:
            partners_in_article = []
            for country in countries:
                country_upper = country.upper().strip()
                if country_upper in partner_countries_set:
                    partners_in_article.append(country_upper)
            
            # 如果同时包含控制组国家和非EU-27国家，记录合作
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
    
    # 5. 计算EU-27与非EU-27国家（包括英国）每年的总合作数量（因变量 Y_{EU,t}）
    print("\n步骤6: 计算EU-27与非EU-27国家（包括英国）每年的总合作数量（因变量 Y_{{EU,t}}）...")
    print("定义：EU-27 与 非 EU-27 国家（包括英国）的合作文章总数")
    print("去重规则：每篇文章只计算一次，即使包含多个EU国家（如德、法、意）也只算1篇EU文章")
    
    # 使用set确保每篇文章只记录一次（deduplication）
    eu_non_eu_cooperation_set = set()
    
    for _, row in eu_articles.iterrows():
        year = row['year']
        countries = row['country_list']
        article_id = row['article_id']
        
        # 检查文章中的国家是否属于集合P（非EU-27国家，已在步骤4中确定）
        non_eu_partners_in_article = []
        for country in countries:
            country_upper = country.upper().strip()
            if country_upper in partner_countries_set:
                non_eu_partners_in_article.append(country_upper)
        
        # 如果包含非EU-27国家，记录合作
        # Whole Counting + Deduplication：
        # - 只要文章中有EU国家和非EU国家，就算一次合作
        # - 每篇文章只记录一次，即使包含多个EU国家（如德、法、意）也只算1篇
        if non_eu_partners_in_article:
            # 使用(year, article_id)作为唯一标识，确保每篇文章只记录一次
            eu_non_eu_cooperation_set.add((year, article_id))
    
    # 转换为DataFrame
    eu_non_eu_cooperation = [{'year': year, 'article_id': article_id} 
                             for year, article_id in eu_non_eu_cooperation_set]
    eu_non_eu_df = pd.DataFrame(eu_non_eu_cooperation)
    
    print(f"去重后的EU-27与非EU-27合作文章数: {len(eu_non_eu_df)}")
    print(f"原始EU-27文章数: {len(eu_articles)}")
    
    # 按年份汇总EU-27与非EU-27的总合作数（因变量 Y_{EU,t}）
    # 使用nunique确保每篇文章只计算一次
    eu_non_eu_yearly = eu_non_eu_df.groupby('year').agg({
        'article_id': 'nunique'
    }).reset_index()
    eu_non_eu_yearly.columns = ['year', 'eu_coop_with_non_eu']
    
    # 创建完整的年份序列（包含所有年份）
    all_years_df = pd.DataFrame({'year': sorted(df['year'].unique())})
    eu_non_eu_yearly = all_years_df.merge(eu_non_eu_yearly, on='year', how='left').fillna(0)
    eu_non_eu_yearly['eu_coop_with_non_eu'] = eu_non_eu_yearly['eu_coop_with_non_eu'].astype(int)
    
    print("\nEU-27与非EU-27国家（包括英国）每年的合作数量（Y_{{EU,t}}）:")
    print(eu_non_eu_yearly)
    
    # 按年份和每个非EU-27国家汇总EU-27的详细合作数据
    print("\n步骤6.1: 计算EU-27与每个非EU-27国家的详细合作数据...")
    print("注意：每篇文章只计算一次，即使包含多个EU国家（如德、法、意）也只算1篇")
    
    # 使用set确保每篇文章只记录一次（deduplication）
    eu_non_eu_by_partner_set = set()
    
    for _, row in eu_articles.iterrows():
        year = row['year']
        countries = row['country_list']
        article_id = row['article_id']
        
        # 检查文章中的国家是否属于集合P（非EU-27国家，已在步骤4中确定）
        non_eu_partners_in_article = []
        for country in countries:
            country_upper = country.upper().strip()
            if country_upper in partner_countries_set:
                non_eu_partners_in_article.append(country_upper)
        
        # 如果包含非EU-27国家，记录合作
        # 对于每篇文章，与每个非EU国家的合作只记录一次
        # 即使文章包含多个EU国家（如德、法、意），每篇文章也只算1次
        if non_eu_partners_in_article:
            for partner_country in non_eu_partners_in_article:
                # 使用(year, partner_country, article_id)作为唯一标识
                eu_non_eu_by_partner_set.add((year, partner_country, article_id))
    
    # 转换为DataFrame
    eu_non_eu_by_partner = [{'year': year, 'partner_country': partner_country, 'article_id': article_id}
                            for year, partner_country, article_id in eu_non_eu_by_partner_set]
    eu_non_eu_partner_df = pd.DataFrame(eu_non_eu_by_partner)
    
    # 按年份和每个非EU-27国家汇总，使用nunique确保每篇文章只计算一次
    eu_non_eu_by_partner_summary = eu_non_eu_partner_df.groupby(['year', 'partner_country']).agg({
        'article_id': 'nunique'
    }).reset_index()
    eu_non_eu_by_partner_summary.columns = ['year', 'partner_country', 'coop_articles']
    
    print(f"EU-27与合作伙伴详细数据形状: {eu_non_eu_by_partner_summary.shape}")
    print("\n前10行EU-27与合作伙伴详细数据:")
    print(eu_non_eu_by_partner_summary.head(10))
    
    # 7. 保存数据
    print("\n步骤7: 保存数据...")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # 保存汇总数据（用于PPML分析）
        summary_complete.to_excel(writer, sheet_name='控制组与非EU-27合作汇总', index=False)
        
        # 保存详细数据（按控制组国家和非EU-27中的每个国家）
        summary_by_control_partner.to_excel(writer, sheet_name='控制组与非EU-27详细合作', index=False)
        
        # 保存非EU-27国家列表（集合P）
        pd.DataFrame({'partner_country': partner_countries}).to_excel(
            writer, sheet_name='非EU-27国家列表', index=False
        )
        
        # 保存EU-27与非EU-27的合作数据（汇总，因变量 Y_{EU,t}）
        eu_non_eu_yearly.to_excel(writer, sheet_name='EU-27与非EU-27合作', index=False)
        
        # 保存EU-27与每个非EU-27国家的详细合作数据
        eu_non_eu_by_partner_summary.to_excel(writer, sheet_name='EU-27与合作伙伴详细合作', index=False)
    
    print(f"✅ 数据已保存到: {output_file}")
    print("\n输出文件包含以下sheet:")
    print("  - 控制组与非EU-27合作汇总: 用于PPML分析的主要数据")
    print("  - 控制组与非EU-27详细合作: 按控制组国家和非EU-27中每个国家的详细合作数据")
    print("  - 非EU-27国家列表: 所有非EU-27国家列表（包括英国）")
    print("  - EU-27与非EU-27合作: EU-27与非EU-27每年的总合作数量（因变量 Y_{{EU,t}}）")
    print("  - EU-27与合作伙伴详细合作: EU-27与每个非EU-27国家每年的详细合作数量")
    
    # 输出统计信息
    print("\n" + "=" * 80)
    print("数据统计摘要")
    print("=" * 80)
    print(f"非EU-27国家数量（集合P，包括英国）: {len(partner_countries)}")
    print(f"控制组国家数量: {len(all_control_countries)}")
    print(f"年份范围: {summary_complete['year'].min()} - {summary_complete['year'].max()}")
    print(f"总观测数: {len(summary_complete)}")
    print(f"零值数量: {(summary_complete['coop_articles_with_P'] == 0).sum()}")
    print(f"零值比例: {(summary_complete['coop_articles_with_P'] == 0).sum() / len(summary_complete) * 100:.2f}%")
    print(f"\nEU-27与非EU-27合作统计:")
    print(f"  总合作文章数: {eu_non_eu_yearly['eu_coop_with_non_eu'].sum()}")
    print(f"  平均每年合作文章数: {eu_non_eu_yearly['eu_coop_with_non_eu'].mean():.1f}")
    
    # 8. 绘制时间序列图（标准化形式）
    print("\n步骤8: 绘制时间序列图（标准化形式，用于平行趋势检验）...")
    plot_dir = f'{output_dir}/parallel_trends_plots'
    os.makedirs(plot_dir, exist_ok=True)
    
    # 对EU-27数据进行标准化
    eu_data = eu_non_eu_yearly.copy().sort_values('year')
    eu_baseline_value = eu_data[eu_data['year'] == 2015]['eu_coop_with_non_eu'].values
    if len(eu_baseline_value) > 0 and eu_baseline_value[0] > 0:
        eu_baseline = eu_baseline_value[0]
    else:
        prev_year_data = eu_data[eu_data['year'] < 2015]
        if len(prev_year_data) > 0:
            prev_values = prev_year_data['eu_coop_with_non_eu'].values
            prev_nonzero = prev_values[prev_values > 0]
            if len(prev_nonzero) > 0:
                eu_baseline = prev_nonzero[-1]
            else:
                eu_baseline = 1
        else:
            eu_baseline = 1
    eu_data['normalized'] = eu_data['eu_coop_with_non_eu'] / eu_baseline
    
    # 为每个控制组国家创建单独的图表（标准化形式）
    for control_country in all_control_countries:
        # 提取该控制组国家的数据
        control_data = summary_complete[summary_complete['country'] == control_country].copy()
        control_data = control_data.sort_values('year')
        
        # 标准化
        control_data_norm, baseline = normalize_by_baseline(control_data, baseline_year=2015)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 绘制标准化后的控制组国家数据
        ax.plot(control_data_norm['year'], control_data_norm['normalized'], 
                marker='o', linewidth=2, markersize=8, 
                label=f'{control_country} (Normalized, baseline={baseline:.0f})', 
                color='#2E86AB')
        
        # 绘制标准化后的EU-27数据
        ax.plot(eu_data['year'], eu_data['normalized'], 
                marker='s', linewidth=2, markersize=8, 
                label=f'EU-27 (Normalized, baseline={eu_baseline:.0f})', 
                color='#A23B72', linestyle='--')
        
        # 添加基准线（y=1）
        ax.axhline(y=1, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline (2015)')
        
        # 添加2016年垂直线（Brexit年份）
        ax.axvline(x=2016, color='red', linestyle=':', linewidth=2, alpha=0.7, label='Brexit (2016)')
        
        # 添加2015年垂直线（基准年）
        ax.axvline(x=2015, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline Year (2015)')
        
        # 设置图表属性
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Normalized Cooperation Articles\n(Relative to 2015 baseline)', fontsize=12, fontweight='bold')
        ax.set_title(f'{control_country} vs EU-27 Cooperation with Non-EU-27 Countries\n(Normalized by 2015 Baseline)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(left=2004.5, right=2024.5)
        
        # 设置x轴刻度
        ax.set_xticks(sorted(df['year'].unique()))
        ax.tick_params(axis='x', rotation=45)
        
        # 添加文本说明
        pre_brexit_years = control_data_norm[control_data_norm['year'] <= 2015]
        post_brexit_years = control_data_norm[control_data_norm['year'] >= 2016]
        
        if len(pre_brexit_years) > 0 and len(post_brexit_years) > 0:
            pre_avg = pre_brexit_years['normalized'].mean()
            post_avg = post_brexit_years['normalized'].mean()
            textstr = f'Pre-Brexit Avg (normalized): {pre_avg:.2f}\nPost-Brexit Avg (normalized): {post_avg:.2f}'
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
        control_data_norm, _ = normalize_by_baseline(control_data, baseline_year=2015)
        
        ax.plot(control_data_norm['year'], control_data_norm['normalized'], 
                marker='o', linewidth=2, markersize=6, 
                label=f'{control_country}', color=colors[i])
    
    # 绘制标准化后的EU-27数据
    ax.plot(eu_data['year'], eu_data['normalized'], 
            marker='s', linewidth=3, markersize=10, 
            label='EU-27', color='black', linestyle='--', alpha=0.8)
    
    # 添加基准线和垂直线
    ax.axhline(y=1, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline (2015)')
    ax.axvline(x=2016, color='red', linestyle=':', linewidth=2, alpha=0.7, label='Brexit (2016)')
    ax.axvline(x=2015, color='gray', linestyle=':', linewidth=1, alpha=0.5, label='Baseline Year (2015)')
    
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel('Normalized Cooperation Articles\n(Relative to 2015 baseline)', fontsize=12, fontweight='bold')
    ax.set_title('All Control Group Countries vs EU-27 Cooperation with Non-EU-27 Countries\n(Normalized by 2015 Baseline)', 
                fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='best', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(left=2004.5, right=2024.5)
    ax.set_xticks(sorted(df['year'].unique()))
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plot_filename = f'{plot_dir}/all_control_countries_parallel_trends.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"  ✅ 已保存: {plot_filename}")
    plt.close()
    
    print(f"\n✅ 所有图表已保存到: {plot_dir}/")
    print(f"✅ 可视化完成！所有图表已使用标准化形式（以2015年为基准）")

if __name__ == '__main__':
    main()

