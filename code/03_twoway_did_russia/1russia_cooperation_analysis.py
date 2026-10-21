
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent

import pandas as pd
import numpy as np
from collections import defaultdict
import re

# 数据文件路径
analyze_data_dir = str(CODE / "00_data_processing/russia_articles/russia_articles.txt")

df = pd.read_csv(
        analyze_data_dir,
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
    )

# 重命名列以便处理
df.columns = ['article_id', 'year', 'countries']

print(f"数据形状: {df.shape}")
print(f"年份范围: {df['year'].min()} - {df['year'].max()}")
print(f"前5行数据:")
print(df.head())

# 数据预处理
df = df.dropna(subset=['countries', 'year'])  # 删除缺失值
df['year'] = df['year'].astype(int)  # 确保年份为整数

# 解析国家信息
def parse_countries(country_str):
    """
    解析国家字符串，提取所有国家
    处理可能的引号、逗号分隔等情况
    注意：需要处理国家名称中包含逗号的情况，如 "KOREA, REP." 和 "IRAN, ISLAMIC REP."
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
    
    return countries

print("\n正在解析国家信息...")
df['country_list'] = df['countries'].apply(parse_countries)

# 过滤出包含俄罗斯的文章
def contains_russia(country_list):
    """检查国家列表中是否包含俄罗斯"""
    russia_variants = {'RUSSIA', 'RUSSIAN FEDERATION', 'RU', 'RUS'}  # 使用集合提高效率
    # 统一转换为大写进行比较
    country_set = {country.upper().strip() for country in country_list}
    return bool(country_set & russia_variants)  # 使用集合交集

df['has_russia'] = df['country_list'].apply(contains_russia)

# 只保留包含俄罗斯的文章
russia_df = df[df['has_russia']].copy()
print(f"\n包含俄罗斯的文章数量: {len(russia_df)}")

# 分析每年的国际合作文章数
print("\n正在分析每年的国际合作文章数...")
yearly_international = russia_df.groupby('year').size().reset_index(name='international_articles')
print("每年国际合作文章数:")
print(yearly_international)

# 分析每个合作国家的合作文章数
print("\n正在分析每个合作国家的合作文章数...")

# 创建年份-国家合作矩阵
cooperation_data = []

for _, row in russia_df.iterrows():
    year = row['year']
    countries = row['country_list']
    
    # 为每个合作国家记录一次合作
    # 排除俄罗斯自己（统一转换为大写进行比较）
    russia_variants = {'RUSSIA', 'RUSSIAN FEDERATION', 'RU', 'RUS'}
    for country in countries:
        country_upper = country.upper().strip()
        if country_upper not in russia_variants:  # 排除俄罗斯自己
            cooperation_data.append({
                'year': year,
                'country': country,  # 保留原始大小写格式
                'article_id': row['article_id']
            })

cooperation_df = pd.DataFrame(cooperation_data)

# 按年份和国家统计合作文章数
country_yearly_cooperation = cooperation_df.groupby(['year', 'country']).size().reset_index(name='cooperation_articles')

print(f"合作数据形状: {country_yearly_cooperation.shape}")
print("前10行合作数据:")
print(country_yearly_cooperation.head(10))

# 创建完整的年份-国家矩阵，确保所有国家在所有年份都有数据
print("\n正在创建完整的年份-国家矩阵...")

# 获取所有年份和所有国家
all_years = sorted(russia_df['year'].unique())
all_countries = sorted(cooperation_df['country'].unique())

print(f"年份范围: {min(all_years)} - {max(all_years)}")
print(f"国家数量: {len(all_countries)}")

# 创建完整的年份-国家组合
year_country_combinations = []
for year in all_years:
    for country in all_countries:
        year_country_combinations.append({'year': year, 'country': country})

# 创建完整的DataFrame
complete_df = pd.DataFrame(year_country_combinations)

# 将实际数据与完整矩阵合并，缺失值填充为0
country_yearly_cooperation_complete = complete_df.merge(
    country_yearly_cooperation, 
    on=['year', 'country'], 
    how='left'
).fillna(0)

# 确保cooperation_articles列为整数
country_yearly_cooperation_complete['cooperation_articles'] = country_yearly_cooperation_complete['cooperation_articles'].astype(int)

print(f"完整合作数据形状: {country_yearly_cooperation_complete.shape}")
print("前10行完整合作数据:")
print(country_yearly_cooperation_complete.head(10))

# 计算合作比例
print("\n正在计算合作比例...")

# 合并完整数据计算比例
merged_data = country_yearly_cooperation_complete.merge(
    yearly_international, 
    on='year', 
    how='left'
)

# 计算合作比例，避免除零错误
merged_data['cooperation_ratio'] = merged_data['cooperation_articles'] / merged_data['international_articles'].replace(0, np.nan)
merged_data['cooperation_ratio'] = merged_data['cooperation_ratio'].fillna(0)  # 将NaN填充为0

# 创建透视表格式的结果
print("\n正在创建透视表...")

# 国际合作文章数（按年份）
international_pivot = yearly_international.set_index('year')['international_articles']

# 合作文章数（按年份和国家）
cooperation_pivot = country_yearly_cooperation_complete.pivot(
    index='year', 
    columns='country', 
    values='cooperation_articles'
)

# 合作比例（按年份和国家）
ratio_pivot = merged_data.pivot(
    index='year', 
    columns='country', 
    values='cooperation_ratio'
)

print(f"合作文章数透视表形状: {cooperation_pivot.shape}")
print(f"合作比例透视表形状: {ratio_pivot.shape}")

# 输出到Excel
output_file = str(HERE / "russia_cooperation_analysis_results.xlsx")

print(f"\n正在导出结果到Excel文件: {output_file}")

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # 1. 每年国际合作文章数
    yearly_international.to_excel(writer, sheet_name='每年国际合作文章数', index=False)
    
    # 2. 合作文章数（透视表）
    cooperation_pivot.to_excel(writer, sheet_name='合作文章数_透视表')
    
    # 3. 合作比例（透视表）
    ratio_pivot.to_excel(writer, sheet_name='合作比例_透视表')
    
    # 4. 详细数据
    merged_data.to_excel(writer, sheet_name='详细合作数据', index=False)
    
    # 5. 按国家汇总的合作统计（只包含有实际合作的国家）
    country_summary = merged_data[merged_data['cooperation_articles'] > 0].groupby('country').agg({
        'cooperation_articles': 'sum',
        'cooperation_ratio': 'mean'
    }).reset_index()
    country_summary = country_summary.sort_values('cooperation_articles', ascending=False)
    country_summary.to_excel(writer, sheet_name='国家合作汇总', index=False)
    
    # 6. 完整数据（包含0值）
    merged_data.to_excel(writer, sheet_name='完整合作数据_含0值', index=False)

print("分析完成！")
print(f"\n结果已保存到: {output_file}")
print(f"\n包含以下工作表:")
print("1. 每年国际合作文章数 - 俄罗斯每年的国际合作文章总数")
print("2. 合作文章数_透视表 - 每年与每个国家的合作文章数（缺失值显示为0）")
print("3. 合作比例_透视表 - 每年与每个国家的合作比例（缺失值显示为0）")
print("4. 详细合作数据 - 包含所有年份、国家和比例的详细数据（缺失值显示为0）")
print("5. 国家合作汇总 - 按国家汇总的合作统计（只包含有实际合作的国家）")
print("6. 完整合作数据_含0值 - 完整的年份-国家矩阵，缺失值填充为0")

# 显示一些统计信息
print(f"\n统计摘要:")
print(f"总年份数: {len(yearly_international)}")
print(f"合作国家数: {len(country_summary)}")
print(f"总合作文章数: {cooperation_df.shape[0]}")
print(f"平均每年国际合作文章数: {yearly_international['international_articles'].mean():.1f}")

print(f"\n合作最多的前10个国家:")
print(country_summary.head(10)[['country', 'cooperation_articles', 'cooperation_ratio']])
