#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成PPML-DiD分析数据
基于最终选择的控制组国家（SOUTH AFRICA、BRAZIL、GEORGIA）
生成包含以下变量的数据：
- focal_country: 焦点国家（乌克兰 + 控制组国家）
- partner_country: 合作伙伴国家（J_Master中的国家）
- year: 年份
- paper_count: 合作文章数
- post_war: 是否战后（2022年及之后为1）
- treated_country: 是否为处理组（乌克兰为1，控制组国家为0）
- did_dummy: DID交互项（post_war * treated_country）
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
raw_data_dir = str(CODE / "00_data_processing/brexit_experimental_data/article_countries_aggregated.txt")
# 优先使用改进的SCM控制组选择结果文件
scm_improved_file = str(HERE / "scm_improved_results.xlsx")
# 备用：原始SCM结果文件
scm_results_file = str(HERE / "scm_control_selection_results.xlsx")
# 备用：旧的控制组选择结果文件
selection_results_file = str(HERE / "ppml_did_control_selection_results.xlsx")
# 备用：控制组合作数据文件（用于获取详细合作数据）
control_cooperation_file = str(HERE / "control_group_cooperation_data.xlsx")

# 输出文件路径
output_dir = str(HERE)
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

def contains_ukraine(country_list):
    """检查国家列表中是否包含乌克兰"""
    ukraine_variants = {'UKRAINE', 'UKRAINIAN', 'UA', 'UKR'}
    country_set = {country.upper().strip() for country in country_list}
    return bool(country_set & ukraine_variants)

def main():
    print("="*80)
    print("生成PPML-DiD分析数据")
    print("="*80)
    
    # 1. 优先从改进的SCM结果文件中读取控制组国家（权重>0的国家）
    print("\n步骤1: 读取改进的SCM选择的控制组国家...")
    final_control_countries = None
    
    try:
        scm_weights_df = pd.read_excel(scm_improved_file, sheet_name='SCM_Weights_Improved')
        # 只选择权重>0的国家（这些是SCM实际使用的控制国家）
        scm_weights_df = scm_weights_df[scm_weights_df['weight'] > 0.001].copy()
        final_control_countries = scm_weights_df['country'].str.upper().tolist()
        print(f"✅ 从改进的SCM结果文件读取到控制组（权重>0.1%）: {final_control_countries}")
        print(f"   权重分布:")
        for _, row in scm_weights_df.iterrows():
            print(f"     {row['country']:25s}: {row['weight']:6.2%}")
        
        # 读取摘要信息
        try:
            summary_df = pd.read_excel(scm_improved_file, sheet_name='Summary')
            if len(summary_df) > 0:
                p_value = summary_df['p_value'].iloc[0]
                print(f"   战前趋势检验p值: {p_value:.4f}")
                if p_value > 0.05:
                    print(f"   ✅ 平行趋势假设通过")
                else:
                    print(f"   ⚠️ 平行趋势假设未通过")
        except:
            pass
            
    except Exception as e:
        print(f"⚠️ 无法从改进的SCM结果文件读取控制组: {e}")
        print("尝试从原始SCM结果文件读取...")
        try:
            scm_weights_df = pd.read_excel(scm_results_file, sheet_name='SCM_Weights')
            scm_weights_df = scm_weights_df[scm_weights_df['weight'] > 0.001].copy()
            final_control_countries = scm_weights_df['country'].str.upper().tolist()
            print(f"✅ 从原始SCM结果文件读取到控制组: {final_control_countries}")
        except Exception as e2:
            print(f"⚠️ 无法从原始SCM结果文件读取控制组: {e2}")
            print("尝试从旧的选择结果文件读取...")
            try:
                final_control_df = pd.read_excel(selection_results_file, sheet_name='Final_Control_Group')
                final_control_countries = final_control_df['country'].str.upper().tolist()
                print(f"✅ 从旧选择结果文件读取到最终控制组: {final_control_countries}")
            except Exception as e3:
                print(f"⚠️ 无法从旧选择结果文件读取最终控制组: {e3}")
                print("使用改进的SCM默认控制组: ARMENIA, SOUTH AFRICA")
                final_control_countries = ['ARMENIA', 'SOUTH AFRICA']
    
    # 焦点国家列表（乌克兰 + 最终控制组）
    focal_countries = ['UKRAINE'] + final_control_countries
    print(f"\n焦点国家: {focal_countries}")
    
    # 2. 读取J_Master清单
    print("\n步骤2: 读取J_Master清单...")
    try:
        # 优先从控制组合作数据文件读取（这个文件更完整）
        j_master_df = pd.read_excel(control_cooperation_file, sheet_name='集合P国家列表')
        j_master = j_master_df['partner_country'].str.upper().tolist()
        print(f"✅ 从控制组合作数据文件读取到J_Master清单")
    except Exception as e:
        print(f"⚠️ 无法从控制组合作数据文件读取J_Master清单: {e}")
        print("尝试从SCM结果文件读取...")
        try:
            j_master_df = pd.read_excel(scm_results_file, sheet_name='J_Master_List')
            j_master = j_master_df['partner'].str.upper().tolist()
            print(f"✅ 从SCM结果文件读取到J_Master清单")
        except Exception as e2:
            print(f"⚠️ 无法从SCM结果文件读取J_Master清单: {e2}")
            print("尝试从旧选择结果文件读取...")
            j_master_df = pd.read_excel(selection_results_file, sheet_name='J_Master_List')
            j_master = j_master_df['partner'].str.upper().tolist()
    
    j_master_set = set(j_master)
    print(f"J_Master大小: {len(j_master)}")
    
    # 3. 尝试从选择结果文件读取面板数据（包含所有候选国与合作伙伴的详细数据）
    print("\n步骤3: 尝试从选择结果文件读取面板数据...")
    try:
        control_partner_df = pd.read_excel(control_cooperation_file, sheet_name='控制组与集合P详细合作')
        print(f"✅ 从控制组合作数据文件读取详细数据")
        print(f"  控制组详细数据形状: {control_partner_df.shape}")
        
        # 筛选最终控制组国家并限制年份范围（2015-2024）
        control_partner_df = control_partner_df[
            (control_partner_df['control_country'].isin(final_control_countries)) &
            (control_partner_df['year'] >= 2015) &
            (control_partner_df['year'] <= 2024)
        ].copy()
        print(f"  筛选后的控制组数据形状: {control_partner_df.shape}")
        print(f"  年份范围: {control_partner_df['year'].min()} - {control_partner_df['year'].max()}")
        
        # 准备控制组数据
        control_summary = control_partner_df[['year', 'control_country', 'partner_country', 'coop_articles']].copy()
        control_summary.columns = ['year', 'focal_country', 'partner_country', 'paper_count']
        
        # 从Excel文件读取乌克兰与合作伙伴的详细数据
        print("\n步骤3.1: 从Excel文件读取乌克兰与合作伙伴的详细数据...")
        try:
            ukraine_partner_df = pd.read_excel(control_cooperation_file, sheet_name='乌克兰与合作伙伴详细合作')
            print(f"✅ 从Excel文件读取到乌克兰详细数据")
            print(f"  乌克兰详细数据形状: {ukraine_partner_df.shape}")
            print(f"  列名: {ukraine_partner_df.columns.tolist()}")
            
            # 限制年份范围（2015-2024）
            ukraine_partner_df = ukraine_partner_df[
                (ukraine_partner_df['year'] >= 2015) & 
                (ukraine_partner_df['year'] <= 2024)
            ].copy()
            print(f"  筛选后的数据形状: {ukraine_partner_df.shape}")
            print(f"  年份范围: {ukraine_partner_df['year'].min()} - {ukraine_partner_df['year'].max()}")
            
            # 准备乌克兰数据（重命名列以匹配格式）
            ukraine_summary = ukraine_partner_df[['year', 'partner_country', 'coop_articles']].copy()
            ukraine_summary['focal_country'] = 'UKRAINE'
            ukraine_summary.columns = ['year', 'partner_country', 'paper_count', 'focal_country']
            ukraine_summary = ukraine_summary[['year', 'focal_country', 'partner_country', 'paper_count']]
            
            print(f"  乌克兰汇总数据形状: {ukraine_summary.shape}")
            
        except Exception as e:
            print(f"⚠️ 无法从Excel文件读取乌克兰详细数据: {e}")
            print("将尝试从原始数据生成...")
            
            # 备用方法：从原始数据生成
            df = pd.read_csv(
                raw_data_dir,
                dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
            )
            df.columns = ['article_id', 'year', 'countries']
            df = df.dropna(subset=['countries', 'year'])
            df['year'] = df['year'].astype(int)
            df = df[(df['year'] >= 2015) & (df['year'] <= 2024)].copy()
            df['country_list'] = df['countries'].apply(parse_countries)
            
            ukraine_articles = df[df['country_list'].apply(contains_ukraine)].copy()
            ukraine_partner_data = []
            
            for _, row in ukraine_articles.iterrows():
                year = row['year']
                countries = row['country_list']
                article_id = row['article_id']
                
                for country in countries:
                    country_upper = country.upper().strip()
                    if country_upper in j_master_set:
                        ukraine_partner_data.append({
                            'year': year,
                            'focal_country': 'UKRAINE',
                            'partner_country': country_upper,
                            'article_id': article_id
                        })
            
            ukraine_partner_df = pd.DataFrame(ukraine_partner_data)
            ukraine_summary = ukraine_partner_df.groupby(['year', 'focal_country', 'partner_country']).agg({
                'article_id': 'nunique'
            }).reset_index()
            ukraine_summary.columns = ['year', 'focal_country', 'partner_country', 'paper_count']
        
        # 合并数据
        panel_data = pd.concat([ukraine_summary, control_summary], ignore_index=True)
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
    
    # post_war: 2022年及之后为1
    ppml_data['post_war'] = (ppml_data['year'] >= 2022).astype(int)
    
    # treated_country: 乌克兰为1，控制组国家为0
    ppml_data['treated_country'] = (ppml_data['focal_country'] == 'UKRAINE').astype(int)
    
    # did_dummy: DID交互项
    ppml_data['did_dummy'] = ppml_data['post_war'] * ppml_data['treated_country']
    
    print("\n变量统计:")
    print(f"  post_war: {ppml_data['post_war'].value_counts().to_dict()}")
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

