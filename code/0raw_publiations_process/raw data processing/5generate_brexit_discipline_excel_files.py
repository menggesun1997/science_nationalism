import pandas as pd
import numpy as np
import os

# 定义路径
base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/brexit_experimental_data'
disciplines_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/disciplines_brexit'

# 学科名称映射：从学科名称到文件夹名称
discipline_folder_map = {
    'Social Sciences': 'social_science',
    'Biomedical Research': 'biomedical',
    'Clinical Medicine': 'clinical',
    'Biology': 'biology',
    'Psychology': 'psychology',
    'Health': 'health',
    'Earth and Space': 'earth',
    'Engineering and Technology': 'engineering',
    'Professional Fields': 'professional',
    'Physics': 'physics',
    'Chemistry': 'chemistry',
    'Mathematics': 'mathematics',
    'Humanities': 'humanities',
    'Arts': 'arts'
}

# Excel文件中的列名映射（学科名称 -> Excel列名前缀）
# 注意：列名格式为 学科名_total 和 学科名_international
discipline_excel_column_map = {
    'Social Sciences': 'SocialSciences',
    'Biomedical Research': 'BiomedicalResearch',
    'Clinical Medicine': 'ClinicalMedicine',
    'Biology': 'Biology',
    'Psychology': 'Psychology',
    'Health': 'Health',
    'Earth and Space': 'EarthAndSpace',
    'Engineering and Technology': 'EngineeringAndTechnology',
    'Professional Fields': 'ProfessionalFields',
    'Physics': 'Physics',
    'Chemistry': 'Chemistry',
    'Mathematics': 'Mathematics',
    'Humanities': 'Humanities',
    'Arts': 'Arts'
}


def generate_brexit_discipline_excel_files():
    """
    根据 brexit_non_eu.xlsx、eu_publications_yearly_by_discipline.txt 和 
    country_discipline_publications.txt 生成各学科的Excel文件
    """
    print("开始生成Brexit各学科的Excel文件...")
    
    # 1. 读取 brexit_non_eu.xlsx
    brexit_file = os.path.join(base_dir, 'brexit_non_eu.xlsx')
    print(f"\n正在读取Brexit数据文件：{brexit_file}")
    df_brexit = pd.read_excel(brexit_file)
    print(f"成功读取Brexit数据，共 {len(df_brexit)} 条记录")
    print(f"Brexit数据列：{df_brexit.columns.tolist()}")
    print("\nBrexit数据预览：")
    print(df_brexit.head())
    
    # 确保国家名称和年份格式一致
    df_brexit['Country'] = df_brexit['Country'].astype(str).str.upper()
    df_brexit['Year'] = df_brexit['Year'].astype(int)
    
    # 获取所有唯一的国家和年份
    all_countries = sorted(df_brexit['Country'].unique())
    all_years = sorted(df_brexit['Year'].unique())
    print(f"\n国家数量：{len(all_countries)}")
    print(f"年份范围：{all_years[0]} - {all_years[-1]}")
    
    # 检查是否包含EU
    has_eu = 'EU' in all_countries
    print(f"是否包含EU：{has_eu}")
    
    # 2. 读取 EU 按学科的统计数据
    eu_pub_file = os.path.join(base_dir, 'eu_publications_yearly_by_discipline.txt')
    print(f"\n正在读取EU发文统计数据文件：{eu_pub_file}")
    df_eu_pub = None
    if os.path.exists(eu_pub_file):
        df_eu_pub = pd.read_csv(eu_pub_file)
        print(f"成功读取EU发文统计数据，共 {len(df_eu_pub)} 条记录")
        print(f"EU发文数据列：{df_eu_pub.columns.tolist()}")
        print("\nEU发文数据预览：")
        print(df_eu_pub.head())
        
        # 确保列名和格式一致
        df_eu_pub['年份'] = df_eu_pub['年份'].astype(int)
        # 重命名列以便后续合并
        df_eu_pub = df_eu_pub.rename(columns={'年份': 'Year', '学科名称': 'EDiscipline'})
    else:
        print(f"警告：未找到EU发文统计文件 {eu_pub_file}")
    
    # 3. 读取各国按学科的统计数据
    country_pub_file = os.path.join(base_dir, 'country_discipline_publications.txt')
    print(f"\n正在读取各国发文统计数据文件：{country_pub_file}")
    df_country_pub = pd.read_csv(country_pub_file)
    print(f"成功读取各国发文统计数据，共 {len(df_country_pub)} 条记录")
    print(f"各国发文数据列：{df_country_pub.columns.tolist()}")
    print("\n各国发文数据预览：")
    print(df_country_pub.head())
    
    # 确保列名和格式一致
    df_country_pub['Country'] = df_country_pub['Country'].astype(str).str.upper()
    df_country_pub['Year'] = df_country_pub['Year'].astype(int)
    
    # 获取所有学科
    if df_eu_pub is not None:
        all_disciplines = sorted(set(df_country_pub['学科名称'].unique()) | set(df_eu_pub['EDiscipline'].unique()))
    else:
        all_disciplines = sorted(df_country_pub['学科名称'].unique())
    print(f"\n学科数量：{len(all_disciplines)}")
    print(f"学科列表：{all_disciplines}")
    
    # 4. 为每个学科生成Excel文件
    for discipline_name in discipline_folder_map.keys():
        folder_name = discipline_folder_map[discipline_name]
        excel_column_prefix = discipline_excel_column_map[discipline_name]
        
        print(f"\n{'='*60}")
        print(f"正在处理学科：{discipline_name} (文件夹: {folder_name})")
        
        # 检查学科是否在数据中存在
        discipline_exists = False
        if df_eu_pub is not None:
            discipline_exists = discipline_exists or (discipline_name in df_eu_pub['EDiscipline'].unique())
        discipline_exists = discipline_exists or (discipline_name in df_country_pub['学科名称'].unique())
        
        if not discipline_exists:
            print(f"警告：学科 '{discipline_name}' 在数据中不存在，跳过")
            continue
        
        # 4.1 从Brexit数据中提取基础数据（gdp_per_capita, RD, Researchers in RD）
        # 注意：需要检查列名，可能是 'Researchers in RD' 或 'ResearchersinRD'
        researcher_col = None
        for col in df_brexit.columns:
            if 'researcher' in col.lower() or 'researchers' in col.lower():
                researcher_col = col
                break
        
        if researcher_col is None:
            print("警告：未找到Researchers列，使用默认列名")
            researcher_col = 'Researchers in RD'
        
        df_base = df_brexit[['Country', 'Year', 'gdp_per_capita', 'RD', researcher_col]].copy()
        # 统一列名
        df_base.columns = ['Country', 'Year', 'gdp_per_capita', 'RD', 'Researchers in RD']
        
        # 4.2 提取该学科的数据
        # 对于EU国家
        df_eu_discipline = None
        if df_eu_pub is not None and 'EU' in all_countries:
            df_eu_discipline = df_eu_pub[df_eu_pub['EDiscipline'] == discipline_name][
                ['Year', '欧盟总发文数', '国际发文数']
            ].copy()
            df_eu_discipline['Country'] = 'EU'
            df_eu_discipline = df_eu_discipline.rename(columns={
                '欧盟总发文数': 'pub_total',
                '国际发文数': 'pub_intl'
            })
            print(f"EU该学科数据记录数：{len(df_eu_discipline)}")
        
        # 对于其他国家
        df_country_discipline = df_country_pub[df_country_pub['学科名称'] == discipline_name][
            ['Country', 'Year', 'pub_total', 'pub_intl']
        ].copy()
        print(f"其他国家该学科数据记录数：{len(df_country_discipline)}")
        
        # 4.3 合并EU和其他国家的发文数据
        if df_eu_discipline is not None:
            df_all_pub = pd.concat([df_eu_discipline, df_country_discipline], ignore_index=True)
        else:
            df_all_pub = df_country_discipline.copy()
        
        # 4.4 创建完整的国家-年份组合（基于Brexit数据）
        df_complete = df_base.copy()
        
        # 4.5 合并发文数据
        df_result = pd.merge(
            df_complete,
            df_all_pub,
            on=['Country', 'Year'],
            how='left'
        )
        
        # 4.6 填充缺失的发文数据为0
        df_result['pub_total'] = df_result['pub_total'].fillna(0).astype(int)
        df_result['pub_intl'] = df_result['pub_intl'].fillna(0).astype(int)
        
        # 4.7 重命名列为pub_total和pub_international
        df_result = df_result.rename(columns={
            'pub_intl': 'pub_international'
        })
        
        # 4.8 计算intl_ratio（国际发文比例）
        # 当pub_total为0时，intl_ratio设为0或NaN，这里设为0
        df_result['intl_ratio'] = df_result.apply(
            lambda row: row['pub_international'] / row['pub_total'] if row['pub_total'] > 0 else 0.0,
            axis=1
        )
        
        # 4.9 按国家和年份排序
        df_result = df_result.sort_values(['Country', 'Year'])
        
        # 4.10 检查数据完整性
        print(f"\n数据统计：")
        print(f"  总记录数：{len(df_result)}")
        print(f"  国家数量：{df_result['Country'].nunique()}")
        print(f"  年份范围：{df_result['Year'].min()} - {df_result['Year'].max()}")
        print(f"  有发文数据的记录数：{(df_result['pub_total'] > 0).sum()}")
        print(f"  有国际发文数据的记录数：{(df_result['pub_international'] > 0).sum()}")
        
        # 4.11 创建学科文件夹（如果不存在）并保存
        excel_filename = f'discipline_{folder_name}.xlsx'
        
        # 保存到路径
        discipline_folder = os.path.join(disciplines_base_dir, folder_name)
        os.makedirs(discipline_folder, exist_ok=True)
        excel_path = os.path.join(discipline_folder, excel_filename)
        df_result.to_excel(excel_path, index=False)
        print(f"\n已保存到：{excel_path}")
        
        # 4.12 显示前几行数据
        print("\n数据预览（前10行）：")
        print(df_result.head(10))
        
        # 4.13 显示一些统计信息
        print(f"\n累计统计：")
        print(f"  总发文数：{df_result['pub_total'].sum()}")
        print(f"  总国际发文数：{df_result['pub_international'].sum()}")
        if df_result['pub_total'].sum() > 0:
            overall_intl_ratio = df_result['pub_international'].sum() / df_result['pub_total'].sum()
            print(f"  总体国际发文比例：{overall_intl_ratio:.4f}")
    
    print(f"\n{'='*60}")
    print("所有学科的Excel文件生成完成！")
    
    # 5. 总结
    print("\n生成的文件列表：")
    for discipline_name, folder_name in discipline_folder_map.items():
        excel_filename = f'discipline_{folder_name}.xlsx'
        
        # 检查两个路径
        excel_path_1 = os.path.join(disciplines_base_dir, folder_name, excel_filename)
        
        if os.path.exists(excel_path_1):
            print(f"  ✓ {discipline_name}")
            print(f"    路径1: {excel_path_1}")
        else:
            print(f"  ✗ {discipline_name} -> 未生成（可能数据中不存在该学科）")


# 执行生成
if __name__ == "__main__":
    generate_brexit_discipline_excel_files()

