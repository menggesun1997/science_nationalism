#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成PPML-DiD分析数据
基于SCM选择的控制组国家（根据权重选择）
生成包含以下变量的数据：
- focal_country: 焦点国家（英国 + 控制组国家）
- partner_country: 合作伙伴国家（J_Master中的国家）
- year: 年份
- paper_count: 合作文章数
- post_brexit: 是否Brexit后（2016年及之后为1）
- treated_country: 是否为处理组（英国为1，控制组国家为0）
- did_dummy: DID交互项（post_brexit * treated_country）
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import pandas as pd
import numpy as np
import os

# 配置：选择控制组国家的方法
# 可选值: 'two_stage' (两阶段方法) 或 'scm' (合成控制法)
CONTROL_SELECTION_METHOD = 'two_stage'  # 默认使用两阶段方法

# 数据文件路径
raw_data_dir = str(CODE / "0raw_publiations_process/brexit_experimental_data/article_countries_aggregated.txt")
# PPML-DID控制选择结果文件（两阶段方法）
ppml_did_results_file = str(CODE / "2two_way_did_uk/ppml_did_control_selection_results.xlsx")
# SCM结果文件（合成控制法）
scm_results_file = str(CODE / "2two_way_did_uk/scm_control_selection_results.xlsx")
# 控制组合作数据文件（用于获取详细合作数据）
control_cooperation_file = str(CODE / "2two_way_did_uk/control_group_cooperation_data.xlsx")

# 输出文件路径
output_dir = str(CODE / "2two_way_did_uk")
output_file = f'{output_dir}/ppml_did_data.dta'  # Stata格式
output_csv_file = f'{output_dir}/ppml_did_data.csv'  # CSV格式（备用）

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

def contains_uk(country_list):
    """检查国家列表中是否包含英国"""
    uk_variants = {'UNITED KINGDOM', 'UK', 'GB', 'GBR', 'GREAT BRITAIN'}
    country_set = {country.upper().strip() for country in country_list}
    return bool(country_set & uk_variants)

def main():
    print("="*80)
    print("生成PPML-DiD分析数据")
    print("="*80)
    
    # 1. 根据配置选择控制组国家的方法
    print("\n步骤1: 读取控制组国家...")
    print(f"使用的方法: {CONTROL_SELECTION_METHOD}")
    
    final_control_countries = None
    control_weights_dict = {}
    
    if CONTROL_SELECTION_METHOD == 'two_stage':
        # 使用两阶段方法（PPML-DID控制选择）
        print("从两阶段方法（PPML-DID控制选择）读取控制组国家...")
        try:
            # 读取最终控制组（已经通过两阶段筛选选出的国家）
            final_control_df = pd.read_excel(ppml_did_results_file, sheet_name='Final_Control_Group')
            final_control_countries = final_control_df['country'].str.upper().tolist()
            print(f"✅ 从PPML-DID结果文件读取到最终控制组: {final_control_countries}")
            
            # 使用等权重
            n_countries = len(final_control_countries)
            equal_weight = 1.0 / n_countries
            control_weights_dict = {country: equal_weight for country in final_control_countries}
            print(f"   使用等权重: {equal_weight:.2%}")
            print(f"   权重分布:")
            for country in final_control_countries:
                print(f"     {country:25s}: {equal_weight:6.2%}")
                
        except Exception as e:
            print(f"⚠️ 无法从PPML-DID结果文件读取控制组: {e}")
            print("请先运行2ppml_did_control_selection.py生成两阶段控制选择结果")
            raise ValueError(f"无法读取两阶段控制组国家: {e}")
    
    elif CONTROL_SELECTION_METHOD == 'scm':
        # 使用SCM方法（合成控制法）
        print("从SCM方法（合成控制法）读取控制组国家...")
        try:
            scm_weights_df = pd.read_excel(scm_results_file, sheet_name='SCM_Weights')
            # 只选择权重>0.001的国家（这些是SCM实际使用的控制国家）
            scm_weights_df = scm_weights_df[scm_weights_df['weight'] > 0.001].copy()
            final_control_countries = scm_weights_df['country'].str.upper().tolist()
            control_weights_dict = dict(zip(scm_weights_df['country'].str.upper(), scm_weights_df['weight']))
            print(f"✅ 从SCM结果文件读取到控制组: {final_control_countries}")
            print(f"   权重分布:")
            for country, weight in sorted(control_weights_dict.items(), key=lambda x: x[1], reverse=True):
                print(f"     {country:25s}: {weight:6.2%}")
                
        except Exception as e:
            print(f"⚠️ 无法从SCM结果文件读取控制组: {e}")
            print("请先运行2scm_control_selection.py生成SCM控制选择结果")
            raise ValueError(f"无法读取SCM控制组国家: {e}")
    
    else:
        raise ValueError(f"未知的控制组选择方法: {CONTROL_SELECTION_METHOD}。请设置为 'two_stage' 或 'scm'")
    
    if final_control_countries is None or len(final_control_countries) == 0:
        raise ValueError(f"无法读取控制组国家，请先运行相应的控制选择脚本")
    
    # 焦点国家列表（英国 + 最终控制组）
    focal_countries = ['UNITED KINGDOM'] + final_control_countries
    print(f"\n焦点国家: {focal_countries}")
    
    # 2. 读取J_Master清单
    print("\n步骤2: 读取J_Master清单...")
    j_master = None
    
    # 优先从控制组合作数据文件读取（两种方法都使用这个文件）
    try:
        j_master_df = pd.read_excel(control_cooperation_file, sheet_name='集合P国家列表')
        j_master = j_master_df['partner_country'].str.upper().tolist()
        print(f"✅ 从控制组合作数据文件读取到J_Master清单")
    except Exception as e:
        print(f"⚠️ 无法从控制组合作数据文件读取J_Master清单: {e}")
        
        # 如果使用两阶段方法，尝试从PPML-DID结果文件读取
        if CONTROL_SELECTION_METHOD == 'two_stage':
            try:
                j_master_df = pd.read_excel(ppml_did_results_file, sheet_name='J_Master_List')
                j_master = j_master_df['partner'].str.upper().tolist()
                print(f"✅ 从PPML-DID结果文件读取到J_Master清单")
            except Exception as e2:
                print(f"⚠️ 无法从PPML-DID结果文件读取J_Master清单: {e2}")
                raise ValueError("无法读取J_Master清单")
        else:
            raise ValueError("无法读取J_Master清单")
    
    j_master_set = set(j_master)
    print(f"J_Master大小: {len(j_master)}")
    
    # 3. 尝试从选择结果文件读取面板数据（包含所有候选国与合作伙伴的详细数据）
    print("\n步骤3: 尝试从选择结果文件读取面板数据...")
    try:
        control_partner_df = pd.read_excel(control_cooperation_file, sheet_name='控制组与集合P详细合作')
        print(f"✅ 从控制组合作数据文件读取详细数据")
        print(f"  控制组详细数据形状: {control_partner_df.shape}")
        
        # 筛选最终控制组国家并限制年份范围（2005-2024）
        control_partner_df = control_partner_df[
            (control_partner_df['control_country'].isin(final_control_countries)) &
            (control_partner_df['year'] >= 2005) &
            (control_partner_df['year'] <= 2024)
        ].copy()
        print(f"  筛选后的控制组数据形状: {control_partner_df.shape}")
        print(f"  年份范围: {control_partner_df['year'].min()} - {control_partner_df['year'].max()}")
        
        # 准备控制组数据
        control_summary = control_partner_df[['year', 'control_country', 'partner_country', 'coop_articles']].copy()
        control_summary.columns = ['year', 'focal_country', 'partner_country', 'paper_count']
        
        # 从Excel文件读取英国与合作伙伴的详细数据
        print("\n步骤3.1: 从Excel文件读取英国与合作伙伴的详细数据...")
        try:
            uk_partner_df = pd.read_excel(control_cooperation_file, sheet_name='英国与合作伙伴详细合作')
            print(f"✅ 从Excel文件读取到英国详细数据")
            print(f"  英国详细数据形状: {uk_partner_df.shape}")
            print(f"  列名: {uk_partner_df.columns.tolist()}")
            
            # 限制年份范围（2005-2024）
            uk_partner_df = uk_partner_df[
                (uk_partner_df['year'] >= 2005) & 
                (uk_partner_df['year'] <= 2024)
            ].copy()
            print(f"  筛选后的数据形状: {uk_partner_df.shape}")
            print(f"  年份范围: {uk_partner_df['year'].min()} - {uk_partner_df['year'].max()}")
            
            # 准备英国数据（重命名列以匹配格式）
            uk_summary = uk_partner_df[['year', 'partner_country', 'coop_articles']].copy()
            uk_summary['focal_country'] = 'UNITED KINGDOM'
            uk_summary.columns = ['year', 'partner_country', 'paper_count', 'focal_country']
            uk_summary = uk_summary[['year', 'focal_country', 'partner_country', 'paper_count']]
            
            print(f"  英国汇总数据形状: {uk_summary.shape}")
            
        except Exception as e:
            print(f"⚠️ 无法从Excel文件读取英国详细数据: {e}")
            print("将尝试从原始数据生成...")
            
            # 备用方法：从原始数据生成
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
                    df = df.iloc[1:].reset_index(drop=True)
            
            df = df.dropna(subset=['countries', 'year'])
            df['year'] = df['year'].astype(int)
            df = df[(df['year'] >= 2005) & (df['year'] <= 2024)].copy()
            df['country_list'] = df['countries'].apply(parse_countries)
            
            uk_articles = df[df['country_list'].apply(contains_uk)].copy()
            uk_partner_data = []
            
            for _, row in uk_articles.iterrows():
                year = row['year']
                countries = row['country_list']
                article_id = row['article_id']
                
                for country in countries:
                    country_upper = country.upper().strip()
                    if country_upper in j_master_set:
                        uk_partner_data.append({
                            'year': year,
                            'focal_country': 'UNITED KINGDOM',
                            'partner_country': country_upper,
                            'article_id': article_id
                        })
            
            uk_partner_df = pd.DataFrame(uk_partner_data)
            uk_summary = uk_partner_df.groupby(['year', 'focal_country', 'partner_country']).agg({
                'article_id': 'nunique'
            }).reset_index()
            uk_summary.columns = ['year', 'focal_country', 'partner_country', 'paper_count']
        
        # 合并数据
        panel_data = pd.concat([uk_summary, control_summary], ignore_index=True)
        print(f"  合并后的数据形状: {panel_data.shape}")
        
    except Exception as e:
        print(f"⚠️ 无法读取详细合作数据: {e}")
        print("将需要从原始数据完全重新生成...")
        panel_data = None
    
    # 如果仍然没有数据，从原始数据完全重新生成
    if panel_data is None or len(panel_data) == 0:
        print("\n步骤4: 从原始数据完全重新生成面板数据...")
        # 这里可以添加完整的重新生成逻辑
        raise ValueError("无法获取面板数据，请先运行2ppml_did_control_selection.py生成数据")
    
    # 统一列名
    if 'paper_count' not in panel_data.columns:
        # 检查是否有其他名称的列
        if 'coop_articles' in panel_data.columns:
            panel_data['paper_count'] = panel_data['coop_articles']
        else:
            raise ValueError("面板数据中找不到paper_count或coop_articles列")
    
    print(f"\n✅ 最终面板数据形状: {panel_data.shape}")
    print(f"  列名: {panel_data.columns.tolist()}")
    print(f"  包含的焦点国家: {sorted(panel_data['focal_country'].unique())}")
    
    # 4. 创建完整的面板（补零）
    print("\n步骤4: 创建完整面板（补零）...")
    
    all_years = sorted(panel_data['year'].unique())
    all_focal = sorted(panel_data['focal_country'].unique())
    all_partners = sorted(panel_data['partner_country'].unique())
    
    print(f"年份: {len(all_years)}个 ({min(all_years)}-{max(all_years)})")
    print(f"焦点国家: {len(all_focal)}个")
    print(f"合作伙伴: {len(all_partners)}个")
    
    # 创建完整面板（补零）
    full_panel_list = []
    for focal in all_focal:
        for partner in all_partners:
            for year in all_years:
                full_panel_list.append({
                    'focal_country': focal,
                    'partner_country': partner,
                    'year': year
                })
    
    full_panel_df = pd.DataFrame(full_panel_list)
    print(f"完整面板大小: {full_panel_df.shape}")
    
    # 合并实际数据（从panel_data中获取paper_count）
    ppml_data = full_panel_df.merge(
        panel_data[['focal_country', 'partner_country', 'year', 'paper_count']],
        on=['focal_country', 'partner_country', 'year'],
        how='left'
    ).fillna(0)
    
    ppml_data['paper_count'] = ppml_data['paper_count'].astype(int)
    
    print(f"PPML数据形状: {ppml_data.shape}")
    
    # 6. 创建DID变量
    print("\n步骤6: 创建DID变量...")
    
    # post_brexit: 2016年及之后为1
    ppml_data['post_brexit'] = (ppml_data['year'] >= 2016).astype(int)
    
    # treated_country: 英国为1，控制组国家为0
    ppml_data['treated_country'] = (ppml_data['focal_country'] == 'UNITED KINGDOM').astype(int)
    
    # did_dummy: DID交互项
    ppml_data['did_dummy'] = ppml_data['post_brexit'] * ppml_data['treated_country']
    
    # 添加控制组权重（如果可用）
    if control_weights_dict:
        ppml_data['control_weight'] = ppml_data['focal_country'].map(control_weights_dict).fillna(0)
        print(f"\n控制组权重已添加到数据中")
        print(f"  权重列名: control_weight")
        print(f"  有权重的国家: {sorted([c for c in control_weights_dict.keys()])}")
    
    print("\n变量统计:")
    print(f"  post_brexit: {ppml_data['post_brexit'].value_counts().to_dict()}")
    print(f"  treated_country: {ppml_data['treated_country'].value_counts().to_dict()}")
    print(f"  did_dummy: {ppml_data['did_dummy'].value_counts().to_dict()}")
    
    # 7. 数据预览
    print("\n步骤7: 数据预览...")
    print("\n前20行数据:")
    print(ppml_data.head(20))
    
    print("\n按焦点国家统计:")
    print(ppml_data.groupby('focal_country')['paper_count'].agg(['sum', 'mean', 'std']))
    
    print("\n按年份统计:")
    print(ppml_data.groupby('year')['paper_count'].sum())
    
    # 8. 保存数据
    print("\n步骤8: 保存数据...")
    
    # 保存为CSV格式
    ppml_data.to_csv(output_csv_file, index=False, encoding='utf-8')
    print(f"✅ CSV格式已保存到: {output_csv_file}")
    
    # 保存为Stata格式
    try:
        ppml_data.to_stata(output_file, write_index=False, version=118)
        print(f"✅ Stata格式已保存到: {output_file}")
    except Exception as e:
        print(f"⚠️ 保存Stata格式时出错: {e}")
        print("   请使用CSV文件，可以在Stata中使用: import delimited using \"ppml_did_data.csv\"")
    
    # 保存为Excel格式（便于查看）
    excel_file = f'{output_dir}/ppml_did_data.xlsx'
    ppml_data.to_excel(excel_file, index=False, engine='openpyxl')
    print(f"✅ Excel格式已保存到: {excel_file}")
    
    
    print("\n" + "="*80)
    print("数据生成完成！")
    print("="*80)
    print(f"\n数据摘要:")
    print(f"  焦点国家数量: {len(all_focal)}")
    print(f"  合作伙伴数量: {len(all_partners)}")
    print(f"  年份范围: {min(all_years)} - {max(all_years)}")
    print(f"  总观测数: {len(ppml_data)}")
    print(f"  零值数量: {(ppml_data['paper_count'] == 0).sum()}")
    print(f"  零值比例: {(ppml_data['paper_count'] == 0).sum() / len(ppml_data) * 100:.2f}%")

if __name__ == '__main__':
    main()

