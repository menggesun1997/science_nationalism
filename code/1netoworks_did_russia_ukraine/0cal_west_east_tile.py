
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import pandas as pd
import numpy as np
import os
from collections import defaultdict


def parse_countries(countries_str):
    """
    解析countries字符串，返回国家集合
    处理可能的引号、逗号分隔等情况
    注意：需要处理国家名称中包含逗号的情况，如 "KOREA, REP." 和 "IRAN, ISLAMIC REP."
    """
    if pd.isna(countries_str) or countries_str == '' or str(countries_str).upper() == 'NAN':
        return set()
    
    # 转换为字符串并去除首尾空白
    countries_str = str(countries_str).strip().upper()
    
    # 如果字符串以引号开始和结束，去除引号
    if countries_str.startswith('"') and countries_str.endswith('"'):
        countries_str = countries_str[1:-1]
    elif countries_str.startswith("'") and countries_str.endswith("'"):
        countries_str = countries_str[1:-1]
    
    # 智能分割：处理国家名称中包含逗号的情况
    # 已知包含逗号的国家名称后缀
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
        
        # 检查下一个部分是否是当前部分的后缀（如 ", REP." 或 ", ISLAMIC REP."）
        if i + 1 < len(parts):
            next_part = parts[i + 1].strip()
            # 如果下一个部分是特殊后缀，合并它们（保留空格）
            if next_part in special_suffixes:
                countries.append((part + ', ' + next_part).strip())
                i += 2
                continue
        
        countries.append(part)
        i += 1
    
    # 过滤空字符串和NAN
    countries = [c for c in countries if c and c != 'NAN' and c.strip() != '']
    
    return set(countries)

def get_target_country_name(analyze_country):
    """
    根据分析国家名称返回数据中的标准国家名称
    """
    country_mapping = {
        'russia': 'RUSSIAN FEDERATION',
        'ukraine': 'UKRAINE',
        'uk': 'UNITED KINGDOM',
        # 控制国家映射
        'brazil': 'BRAZIL',
        'south_africa': 'SOUTH AFRICA',
        'indonesia': 'INDONESIA',
        'argentina': 'ARGENTINA',
        'serbia': 'REPUBLIC OF SERBIA',
        'rep-of-georgia': 'GEORGIA',
        'armenia': 'ARMENIA',
        'azerbaijan': 'AZERBAIJAN',
        'moldova': 'MOLDOVA',
        'bosnia-&-herceg': 'BOSNIA & HERZEGOVINA'
    }
    return country_mapping.get(analyze_country.lower(), analyze_country.upper())

def analyze_russia_cooperation(networks_data_dir, output_file, analyze_country, west_countries, east_countries):
    """
    分析指定国家与西方国家、东方国家的年度合作数量和比率
    
    参数:
    - networks_data_dir: 数据文件路径
    - output_file: 输出文件路径
    - analyze_country: 要分析的国家名称（如 'russia', 'ukraine'）
    - west_countries: 西方国家列表
    - east_countries: 东方国家列表
    """
    # 读取CSV文件，指定数据类型
    print("正在读取数据...")
    df = pd.read_csv(
        networks_data_dir,
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
    )
    
    # 如果列名不对，重命名列
    if 'Annee_Bibliographique' not in df.columns:
        if len(df.columns) == 3:
            df.columns = ['OST_BK', 'Annee_Bibliographique', 'countries']
        else:
            print(f"警告：数据文件列数不正确，期望3列，实际{len(df.columns)}列")
            print(f"实际列名: {df.columns.tolist()}")
    
    print(f"成功读取 {len(df)} 条记录")
    print(f"数据列: {df.columns.tolist()}")
    
    # 获取目标国家的标准名称
    target_country = get_target_country_name(analyze_country)
    print(f"分析目标国家: {target_country}")
    
    # 将国家列表转换为大写集合以便快速查找
    west_countries_set = set(c.upper() for c in west_countries)
    east_countries_set = set(c.upper() for c in east_countries)
    
    # 初始化统计字典
    yearly_stats = defaultdict(lambda: {
        'west_cooperation': 0,
        'east_cooperation': 0,
        'total_articles': 0
    })
    
    print("正在分析合作数据...")
    
    # 遍历每一行数据
    processed = 0
    for idx, row in df.iterrows():
        # 获取年份（修复：使用正确的列名）
        year_str = str(row['Annee_Bibliographique']).strip()
        if pd.isna(year_str) or year_str == 'nan' or year_str == '':
            continue
        
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            continue
        
        # 解析国家信息
        countries_str = str(row['countries'])
        countries_set = parse_countries(countries_str)
        
        # 跳过没有国家信息的行
        if not countries_set:
            continue
        
        # 检查文章是否包含目标国家
        if target_country not in countries_set:
            continue
        
        # 统计该文章中的合作情况（排除目标国家本身）
        other_countries = countries_set - {target_country}
        
        # 检查是否有西方国家合作
        has_west = len(other_countries.intersection(west_countries_set)) > 0
        
        # 检查是否有东方国家合作
        has_east = len(other_countries.intersection(east_countries_set)) > 0
        
        # 更新年度统计
        yearly_stats[year]['total_articles'] += 1
        if has_west:
            yearly_stats[year]['west_cooperation'] += 1
        if has_east:
            yearly_stats[year]['east_cooperation'] += 1
        
        processed += 1
        if processed % 50000 == 0:
            print(f"  已处理 {processed:,} 条记录...")
    
    # 打印处理统计
    print(f"\n处理完成！共处理 {processed:,} 条包含目标国家的记录")
    print(f"找到 {len(yearly_stats)} 个年份的数据")
    
    # 转换为DataFrame并计算比率
    results = []
    for year in sorted(yearly_stats.keys()):
        stats = yearly_stats[year]
        # 这里的 total 是每年该国家的发文总量（即当年的发文量）
        total = stats['total_articles']
        
        if total > 0:
            west_ratio = stats['west_cooperation'] / total
            east_ratio = stats['east_cooperation'] / total
        else:
            west_ratio = 0
            east_ratio = 0
            
        results.append({
            'year': year,
            'total_articles': total,
            'west_cooperation_count': stats['west_cooperation'],
            'east_cooperation_count': stats['east_cooperation'],
            'west_cooperation_ratio': west_ratio,
            'east_cooperation_ratio': east_ratio
        })
    
    # 创建结果DataFrame
    results_df = pd.DataFrame(results)
    
    # 检查是否有数据
    if len(results_df) == 0:
        print(f"\n⚠ 警告：未找到任何包含目标国家 {target_country} 的文章数据！")
        print(f"请检查：")
        print(f"  1. 数据文件路径是否正确: {networks_data_dir}")
        print(f"  2. 目标国家名称是否正确: {target_country}")
        print(f"  3. 数据文件中是否包含该国家的文章")
        
        # 创建一个空的结果文件，包含列名
        empty_df = pd.DataFrame(columns=['year', 'total_articles', 'west_cooperation_count', 
                                         'east_cooperation_count', 'west_cooperation_ratio', 
                                         'east_cooperation_ratio'])
        empty_df.to_csv(output_file, index=False)
        print(f"已创建空的结果文件: {output_file}")
        return empty_df
    
    # 保存结果
    results_df.to_csv(output_file, index=False)
    print(f"分析结果已保存到: {output_file}")
    
    # 显示结果摘要
    print("\n=== 合作分析结果摘要 ===")
    print(results_df.to_string(index=False))
    
    # 计算总体统计
    total_west = results_df['west_cooperation_count'].sum()
    total_east = results_df['east_cooperation_count'].sum()
    total_articles = results_df['total_articles'].sum()
    
    if total_articles > 0:
        print(f"\n=== 总体统计 ===")
        print(f"总文章数: {total_articles}")
        print(f"与西方国家合作文章数: {total_west}")
        print(f"与东方国家合作文章数: {total_east}")
        print(f"与西方国家合作比率: {total_west/total_articles:.3f}")
        print(f"与东方国家合作比率: {total_east/total_articles:.3f}")
    else:
        print(f"\n⚠ 警告：总文章数为0，无法计算合作比率")
    
    return results_df

if __name__ == "__main__":
    # 西方国家列表（使用数据中的实际国家名称）
    west_countries = [
        'CANADA', 'UNITED STATES', 'ALBANIA', 'BELGIUM', 'BULGARIA', 
        'CROATIA', 'CZECHIA', 'DENMARK', 'ESTONIA', 'FRANCE', 
        'GERMANY', 'GREECE', 'HUNGARY', 'ICELAND', 'ITALY', 
        'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MONTENEGRO', 'NETHERLANDS', 
        'MACEDONIA', 'NORTH MACEDONIA', 'NORWAY', 'POLAND', 'PORTUGAL', 'ROMANIA', 
        'SLOVAK REPUBLIC',  # 数据中使用的是 SLOVAK REPUBLIC，不是 SLOVAKIA
        'SLOVENIA', 'SPAIN', 
        'TURKIYE',  # 数据中使用的是 TURKIYE，不是 TURKEY
        'UNITED KINGDOM'
    ]

    # 额外的西方国家（日本、韩国等）
    west_countries_plus = [
        'JAPAN', 
        'KOREA, REP.',  # 数据中使用的是 KOREA, REP.，不是 SOUTH KOREA
        'AUSTRALIA', 
        'NEW ZEALAND'
    ]

    # 选择分析模式：'single' 分析单个国家，'control' 分析所有控制国家，'all' 分析所有国家
    analysis_mode = 'all'  # 可以改为 'single', 'control', 'all'
    
    # 单个国家分析（当 analysis_mode = 'single' 时使用）
    # analyze_country_file = 'ukraine'
    # analyze_country = 'ukraine'
    # analyze_country_file = 'russia'
    # analyze_country = 'russia'
    
    # 控制国家列表
    control_countries = [
        'brazil',
        'south_africa',
        'indonesia',
        'argentina',
        'serbia',
        'rep-of-georgia',
        'armenia',
        'azerbaijan',
        'moldova',
        'bosnia-&-herceg'
    ]
    
    # 所有国家列表（包括俄罗斯和乌克兰）
    all_countries = {
        'russia': 'russia',
        'ukraine': 'ukraine'
    }
    
    analyze_data_dir = str(CODE / "0raw_publiations_process")
    output_base_dir = str(CODE / "1netoworks_did_russia_ukraine/west_east_tile")
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 根据分析模式选择要处理的国家列表
    if analysis_mode == 'control':
        countries_to_process = [(country, 'countrol_countries') for country in control_countries]
        print("=" * 80)
        print("开始批量处理所有控制国家...")
        print(f"共 {len(control_countries)} 个国家")
        print("=" * 80)
    elif analysis_mode == 'all':
        countries_to_process = [(country, country) for country in all_countries.keys()]
        countries_to_process.extend([(country, 'countrol_countries') for country in control_countries])
        print("=" * 80)
        print("开始批量处理所有国家（包括俄罗斯、乌克兰和控制国家）...")
        print(f"共 {len(countries_to_process)} 个国家")
        print("=" * 80)
    else:  # single mode
        analyze_country_file = 'countrol_countries'
        analyze_country = 'rep-of-georgia'
        countries_to_process = [(analyze_country, analyze_country_file)]
    
    # 处理结果统计
    success_count = 0
    error_count = 0
    error_countries = []
    
    # 循环处理每个国家
    for idx, (analyze_country, analyze_country_file) in enumerate(countries_to_process, 1):
        print("\n" + "=" * 80)
        print(f"[{idx}/{len(countries_to_process)}] 正在处理: {analyze_country}")
        print("=" * 80)
        
        try:
            # 确定东方国家列表
            if analyze_country == 'russia':
                # 如果分析俄罗斯，east_countries中不包含俄罗斯
                east_countries = ['CHINA','KAZAKHSTAN','KYRGYZSTAN','TAJIKISTAN','UZBEKISTAN','INDIA','PAKISTAN']
            else:
                # 如果分析其他国家，east_countries中包含俄罗斯
                east_countries = ['CHINA','RUSSIAN FEDERATION','KAZAKHSTAN','KYRGYZSTAN','TAJIKISTAN','UZBEKISTAN','INDIA','PAKISTAN']
            
            # 根据国家类型确定数据文件路径
            if analyze_country_file == 'countrol_countries':
                # 控制国家的文件在countrol_countries_articles目录
                networks_data_dir = f'{analyze_data_dir}/countrol_countries_articles/{analyze_country}_articles.txt'
            else:
                # 其他国家的文件在对应的国家目录
                networks_data_dir = f'{analyze_data_dir}/{analyze_country_file}_articles/{analyze_country}_articles.txt'
            
            # 输出文件路径
            output_file = f'{output_base_dir}/{analyze_country}_west_east_tile.csv'
            
            # 检查数据文件是否存在
            if not os.path.exists(networks_data_dir):
                print(f"⚠ 警告：数据文件不存在，跳过: {networks_data_dir}")
                error_count += 1
                error_countries.append(analyze_country)
                continue
            
            # 运行分析
            results = analyze_russia_cooperation(
                networks_data_dir, 
                output_file, 
                analyze_country, 
                west_countries, 
                east_countries
            )
            
            # 检查结果是否有效
            if len(results) > 0:
                print(f"✓ {analyze_country} 分析完成！共 {len(results)} 年的数据")
                success_count += 1
            else:
                print(f"⚠ {analyze_country} 分析完成，但未找到数据")
                error_count += 1
                error_countries.append(analyze_country)
                
        except Exception as e:
            print(f"✗ {analyze_country} 分析过程中出现错误: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
            error_countries.append(analyze_country)
    
    # 打印最终统计
    print("\n" + "=" * 80)
    print("批量处理完成！")
    print("=" * 80)
    print(f"成功处理: {success_count} 个国家")
    print(f"处理失败: {error_count} 个国家")
    if error_countries:
        print(f"失败的国家: {', '.join(error_countries)}")
    print("=" * 80)