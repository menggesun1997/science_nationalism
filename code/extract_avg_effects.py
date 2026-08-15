#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取三个事件文件夹中所有学科的 avg_effect 数据
生成 Excel 表格汇总
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import pandas as pd
import os
from pathlib import Path
import glob

# 基础路径
base_dir = Path(str(CODE))

# 三个事件文件夹
event_folders = {
    'disciplines_brexit': 'Brexit',
    'disciplines_crimes': 'Crimes',
    'disciplines_crimes_2014': 'Crimes_2014'
}

# 变量类型文件夹（注意拼写不同）
variable_folders = ['intil_ratio', 'initil_ratio', 'total_publications']

# 存储所有结果
results = []

def extract_avg_effect_from_dta(file_path):
    """从 dta 文件中提取 avg_effect 值"""
    try:
        df = pd.read_stata(file_path)
        # 查找包含 avg_effect 的列
        avg_effect_cols = [col for col in df.columns if 'avg_effect' in col.lower()]
        
        if not avg_effect_cols:
            return None
        
        # 提取第一个非空值
        for col in avg_effect_cols:
            values = df[col].dropna()
            if len(values) > 0:
                return values.iloc[0]
        
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def get_country_from_filename(filename):
    """从文件名中提取国家名称"""
    filename_lower = filename.lower()
    if 'eu' in filename_lower:
        return 'EU'
    elif 'uk' in filename_lower and 'ukraine' not in filename_lower:
        return 'UK'
    elif 'russia' in filename_lower:
        return 'Russia'
    elif 'ukraine' in filename_lower:
        return 'Ukraine'
    return 'Unknown'

def process_event_folder(event_folder_name, event_display_name):
    """处理一个事件文件夹"""
    event_path = base_dir / event_folder_name
    
    if not event_path.exists():
        print(f"Warning: {event_path} does not exist")
        return
    
    # disciplines_brexit 的结构不同
    if event_folder_name == 'disciplines_brexit':
        disciplines_path = event_path
    else:
        disciplines_path = event_path / 'disciplines'
    
    if not disciplines_path.exists():
        print(f"Warning: {disciplines_path} does not exist")
        return
    
    # 获取所有学科文件夹
    discipline_dirs = [d for d in disciplines_path.iterdir() 
                      if d.is_dir() and not d.name.startswith('.')]
    
    for discipline_dir in discipline_dirs:
        discipline_name = discipline_dir.name
        
        # 遍历变量类型文件夹
        for var_folder in variable_folders:
            var_path = discipline_dir / var_folder
            
            if not var_path.exists():
                continue
            
            # 查找所有包含 results 的 dta 文件
            result_files = list(var_path.glob('*results.dta'))
            
            for result_file in result_files:
                avg_effect = extract_avg_effect_from_dta(result_file)
                
                if avg_effect is not None:
                    country = get_country_from_filename(result_file.name)
                    
                    results.append({
                        '事件': event_display_name,
                        '学科': discipline_name,
                        '变量类型': var_folder,
                        '国家': country,
                        'Effect值': avg_effect,
                        '文件': str(result_file.relative_to(base_dir))
                    })
                    print(f"Extracted: {event_display_name} - {discipline_name} - {var_folder} - {country} - {avg_effect}")

def main():
    """主函数"""
    print("开始提取 avg_effect 数据...")
    
    # 处理每个事件文件夹
    for event_folder, event_name in event_folders.items():
        print(f"\n处理事件文件夹: {event_folder} ({event_name})")
        process_event_folder(event_folder, event_name)
    
    # 创建 DataFrame
    if results:
        df = pd.DataFrame(results)
        
        # 按事件、学科、变量类型、国家排序
        df = df.sort_values(['事件', '学科', '变量类型', '国家'])
        
        # 统一变量类型名称（将 initil_ratio 和 intil_ratio 统一）
        df['变量类型'] = df['变量类型'].replace('initil_ratio', 'intil_ratio')
        
        # 创建透视表：按事件、学科、变量类型分组，国家作为列
        pivot_df = df.pivot_table(
            index=['事件', '学科', '变量类型'],
            columns='国家',
            values='Effect值',
            aggfunc='first'
        ).reset_index()
        
        # 保存为 Excel，包含多个工作表
        output_file = base_dir / '学科avg_effect汇总.xlsx'
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # 详细数据表
            df.to_excel(writer, sheet_name='详细数据', index=False)
            
            # 透视表（按 intil_ratio 和 total_publications 分别）
            for var_type in ['intil_ratio', 'total_publications']:
                var_df = pivot_df[pivot_df['变量类型'] == var_type].copy()
                if not var_df.empty:
                    var_df = var_df.drop('变量类型', axis=1)
                    var_df.to_excel(writer, sheet_name=f'{var_type}_透视表', index=False)
            
            # 所有数据的透视表
            pivot_df.to_excel(writer, sheet_name='全部透视表', index=False)
        
        print(f"\n完成！共提取 {len(results)} 条记录")
        print(f"结果已保存到: {output_file}")
        print("\nExcel文件包含以下工作表:")
        print("  - 详细数据: 所有原始数据")
        print("  - intil_ratio_透视表: intil_ratio 变量的透视表")
        print("  - total_publications_透视表: total_publications 变量的透视表")
        print("  - 全部透视表: 所有数据的透视表")
        
        # 显示统计信息
        print("\n统计信息:")
        print(df.groupby(['事件', '变量类型']).size())
        
        # 显示前几行
        print("\n前10行数据:")
        print(df.head(10).to_string())
    else:
        print("未找到任何数据！")

if __name__ == '__main__':
    main()

