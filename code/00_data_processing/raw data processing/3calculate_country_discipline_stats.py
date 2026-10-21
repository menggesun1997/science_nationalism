
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent

import pandas as pd
import numpy as np
import os

base_dir = '/root/autodl-tmp'
output_base_dir = '/root/autodl-tmp'

# base_dir = str(HERE / "../publications_raw_data")
# output_base_dir = str(HERE / "../brexit_experimental_data")


def standard_country_name(df):
    """
    标准化国家名称
    """
    # 统一国家名称的大小写
    df['Pays'] = df['Pays'].str.upper()
    standard_country_maps = {
        'CZECH REPUBLIC': 'CZECHIA',
        'IRAN': 'IRAN, ISLAMIC REP.',
        'SOUTH KOREA': 'KOREA, REP.',
        'RUSSIA': 'RUSSIAN FEDERATION',
        'SLOVAKIA': 'SLOVAK REPUBLIC',
        'TURKEY': 'TURKIYE',
        'VIETNAM': 'VIET NAM'
    }
    df['Pays'] = df['Pays'].astype(str).str.upper()
    df['Pays'] = df['Pays'].replace(standard_country_maps)
    return df


def load_discipline_mapping():
    """
    加载学科代码映射文件，将 Code_Discipline 映射为 EDiscipline
    """
    discipline_map = {}
    discipline_code_file = os.path.join(base_dir, 'discipline_code.txt')
    
    if os.path.exists(discipline_code_file):
        try:
            with open(discipline_code_file, 'r', encoding='utf-8') as f:
                # 跳过表头
                next(f)
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 3:  # 确保至少有Code_Discipline和EDiscipline
                            code = parts[0].strip()
                            discipline = parts[2].strip()  # EDiscipline是第三列
                            if code and discipline:
                                discipline_map[code] = discipline
            
            print(f"成功读取学科代码映射，共 {len(discipline_map)} 条记录")
        except Exception as e:
            print(f"读取学科代码映射文件时出错：{str(e)}")
    else:
        print(f"警告：未找到学科代码映射文件 {discipline_code_file}")
    
    return discipline_map


def calculate_country_discipline_publications():
    """
    计算每个国家在每个学科中的发文统计：
    1. 按国家、学科、年份统计总发文数量
    2. 按国家、学科、年份统计国际发文量（至少有一个非本国国家）
    """
    print("\n开始计算每个国家在每个学科中的发文统计...")
    
    # 1. 读取原始数据
    original_article_file = os.path.join(output_base_dir, 'article_process_1.txt')
    print("\n正在读取数据...")
    df = pd.read_csv(
        original_article_file,
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'Code_Discipline': str, 'Pays': str, 'initial_fou': float},
        sep=','
    )
    print(f"成功读取数据，共 {len(df)} 条记录")
    
    # 2. 标准化国家名称
    print("\n正在标准化国家名称...")
    df = standard_country_name(df)
    print("标准化国家名称完成")
    
    # 3. 加载学科代码映射
    print("\n正在加载学科代码映射...")
    discipline_map = load_discipline_mapping()
    
    # 4. 应用学科映射
    if discipline_map:
        df['EDiscipline'] = df['Code_Discipline'].map(discipline_map)
        # 对于无法映射的，使用原始 Code_Discipline
        df['EDiscipline'] = df['EDiscipline'].fillna(df['Code_Discipline'])
        print(f"学科映射完成，共有 {df['EDiscipline'].notna().sum()} 条记录成功映射")
        print(f"映射后的学科数量：{df['EDiscipline'].nunique()}")
    else:
        # 如果没有映射文件，直接使用 Code_Discipline 作为 EDiscipline
        df['EDiscipline'] = df['Code_Discipline']
        print("未找到映射文件，使用原始 Code_Discipline 作为 EDiscipline")
    
    # 5. 去除重复记录
    print("\n步骤1/3: 去除重复记录...")
    df_unique = df[['OST_BK', 'Annee_Bibliographique', 'Code_Discipline', 'EDiscipline', 'Pays']].drop_duplicates()
    print(f"去重后共 {len(df_unique)} 条记录")
    
    # 6. 对于每篇文章，聚合所有相关国家
    print("\n步骤2/3: 正在按文章聚合国家信息（这可能需要几分钟，请耐心等待）...")
    
    # 使用字典聚合：按 (OST_BK, Annee_Bibliographique, EDiscipline) 聚合国家
    article_dict = {}
    total_rows = len(df_unique)
    processed = 0
    
    for row in df_unique.itertuples(index=False):
        key = (row.OST_BK, row.Annee_Bibliographique, row.EDiscipline)
        pays = row.Pays
        if pd.notna(pays) and pd.notna(row.EDiscipline):
            if key not in article_dict:
                article_dict[key] = set()
            article_dict[key].add(pays)
        
        processed += 1
        if processed % 100000 == 0:
            print(f"  已处理 {processed}/{total_rows} 条记录 ({processed*100//total_rows}%)...")
    
    print("步骤3/3: 转换结果格式...")
    # 转换为DataFrame
    article_countries_discipline = pd.DataFrame([
        {
            'OST_BK': k[0], 
            'Annee_Bibliographique': k[1], 
            'EDiscipline': k[2],
            'countries': v
        }
        for k, v in article_dict.items()
    ])
    
    print(f"聚合完成！共处理 {len(article_countries_discipline)} 篇文章")
    
    # 7. 判断每篇文章是否为国际发文（至少有两个不同的国家）
    print("\n正在判断国际发文...")
    article_countries_discipline['is_international'] = article_countries_discipline['countries'].apply(
        lambda x: len(x) > 1 if x else False
    )
    
    # 8. 对于每篇文章，确定哪些国家参与了该文章
    # 将文章展开，每个国家对应一行
    print("\n正在展开文章-国家关系...")
    expanded_rows = []
    for _, row in article_countries_discipline.iterrows():
        for country in row['countries']:
            expanded_rows.append({
                'OST_BK': row['OST_BK'],
                'Annee_Bibliographique': row['Annee_Bibliographique'],
                'EDiscipline': row['EDiscipline'],
                'Country': country,
                'is_international': row['is_international']
            })
    
    expanded_df = pd.DataFrame(expanded_rows)
    print(f"展开后共 {len(expanded_df)} 条记录")
    
    # 9. 按国家、学科、年份统计
    print("\n正在按国家、学科、年份统计...")
    
    # 将年份转换为整数
    expanded_df['Annee_Bibliographique'] = pd.to_numeric(
        expanded_df['Annee_Bibliographique'], errors='coerce'
    )
    expanded_df = expanded_df.dropna(subset=['Annee_Bibliographique', 'EDiscipline', 'Country'])
    expanded_df['Annee_Bibliographique'] = expanded_df['Annee_Bibliographique'].astype(int)
    
    # 按国家、学科、年份统计总发文数（每篇文章只计算一次）
    total_publications = expanded_df.groupby(['Country', 'EDiscipline', 'Annee_Bibliographique']).agg({
        'OST_BK': 'nunique'  # 使用nunique确保每篇文章只计算一次
    }).reset_index()
    total_publications.columns = ['Country', 'EDiscipline', 'Year', 'pub_total']
    
    # 按国家、学科、年份统计国际发文数（只统计is_international为True的文章）
    international_publications = expanded_df[expanded_df['is_international'] == True].groupby(
        ['Country', 'EDiscipline', 'Annee_Bibliographique']
    ).agg({
        'OST_BK': 'nunique'
    }).reset_index()
    international_publications.columns = ['Country', 'EDiscipline', 'Year', 'pub_intl']
    
    # 10. 合并总发文数和国际发文数
    print("\n正在合并统计结果...")
    country_discipline_stats = pd.merge(
        total_publications,
        international_publications,
        on=['Country', 'EDiscipline', 'Year'],
        how='left'
    )
    
    # 填充缺失的国际发文数为0
    country_discipline_stats['pub_intl'] = country_discipline_stats['pub_intl'].fillna(0).astype(int)
    
    # 重命名列
    country_discipline_stats.columns = ['Country', '学科名称', 'Year', 'pub_total', 'pub_intl']
    
    # 按国家、学科、年份排序
    country_discipline_stats = country_discipline_stats.sort_values(['Country', '学科名称', 'Year'])
    
    print("\n统计结果预览：")
    print(country_discipline_stats.head(20))
    
    # 11. 保存结果
    output_file = os.path.join(output_base_dir, 'country_discipline_publications.txt')
    country_discipline_stats.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n结果已保存到：{output_file}")
    
    # 12. 打印汇总信息
    print("\n汇总统计：")
    print(f"国家数量：{country_discipline_stats['Country'].nunique()}")
    print(f"学科数量：{country_discipline_stats['学科名称'].nunique()}")
    print(f"年份范围：{country_discipline_stats['Year'].min()} - {country_discipline_stats['Year'].max()}")
    print(f"总记录数：{len(country_discipline_stats)}")
    print(f"总发文数（累计）：{country_discipline_stats['pub_total'].sum()}")
    print(f"国际发文数（累计）：{country_discipline_stats['pub_intl'].sum()}")
    
    # 13. 按国家汇总统计
    print("\n各国家累计统计（前20名）：")
    country_summary = country_discipline_stats.groupby('Country').agg({
        'pub_total': 'sum',
        'pub_intl': 'sum'
    }).reset_index()
    country_summary = country_summary.sort_values('pub_total', ascending=False)
    country_summary['intl_ratio'] = country_summary['pub_intl'] / country_summary['pub_total']
    print(country_summary.head(20))
    
    # 保存按国家汇总的结果
    country_summary_file = os.path.join(output_base_dir, 'country_publications_summary.txt')
    country_summary.to_csv(country_summary_file, index=False, encoding='utf-8')
    print(f"\n国家汇总结果已保存到：{country_summary_file}")
    
    # 14. 按学科汇总统计
    print("\n各学科累计统计（前20名）：")
    discipline_summary = country_discipline_stats.groupby('学科名称').agg({
        'pub_total': 'sum',
        'pub_intl': 'sum'
    }).reset_index()
    discipline_summary = discipline_summary.sort_values('pub_total', ascending=False)
    discipline_summary['intl_ratio'] = discipline_summary['pub_intl'] / discipline_summary['pub_total']
    print(discipline_summary.head(20))
    
    # 保存按学科汇总的结果
    discipline_summary_file = os.path.join(output_base_dir, 'discipline_publications_summary.txt')
    discipline_summary.to_csv(discipline_summary_file, index=False, encoding='utf-8')
    print(f"\n学科汇总结果已保存到：{discipline_summary_file}")
    
    return country_discipline_stats


# 执行计算
if __name__ == "__main__":
    calculate_country_discipline_publications()

