import pandas as pd
import numpy as np
import os

# 定义路径
base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/brexit_experimental_data'
disciplines_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/disciplines_crimes_2014/disciplines'
disciplines_base_dir_1 = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/disciplines_crimes/disciplines'

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


def generate_discipline_excel_files():
    """
    根据 original_completed.xlsx 和 country_discipline_publications.txt
    生成14个学科的Excel文件
    """
    print("开始生成各学科的Excel文件...")
    
    # 1. 读取 original_completed.xlsx
    original_file = os.path.join(base_dir, 'original_completed.xlsx')
    print(f"\n正在读取原始数据文件：{original_file}")
    df_original = pd.read_excel(original_file)
    print(f"成功读取原始数据，共 {len(df_original)} 条记录")
    print(f"原始数据列：{df_original.columns.tolist()}")
    print("\n原始数据预览：")
    print(df_original.head())
    
    # 确保国家名称和年份格式一致
    df_original['Country'] = df_original['Country'].astype(str).str.upper()
    df_original['Year'] = df_original['Year'].astype(int)
    
    # 获取所有唯一的国家和年份
    all_countries = sorted(df_original['Country'].unique())
    all_years = sorted(df_original['Year'].unique())
    print(f"\n国家数量：{len(all_countries)}")
    print(f"年份范围：{all_years[0]} - {all_years[-1]}")
    
    # 2. 读取 country_discipline_publications.txt
    pub_file = os.path.join(base_dir, 'country_discipline_publications.txt')
    print(f"\n正在读取发文统计数据文件：{pub_file}")
    df_pub = pd.read_csv(pub_file)
    print(f"成功读取发文统计数据，共 {len(df_pub)} 条记录")
    print(f"发文数据列：{df_pub.columns.tolist()}")
    print("\n发文数据预览：")
    print(df_pub.head())
    
    # 确保列名和格式一致
    df_pub['Country'] = df_pub['Country'].astype(str).str.upper()
    df_pub['Year'] = df_pub['Year'].astype(int)
    
    # 获取所有学科
    all_disciplines = sorted(df_pub['学科名称'].unique())
    print(f"\n学科数量：{len(all_disciplines)}")
    print(f"学科列表：{all_disciplines}")
    
    # 3. 为每个学科生成Excel文件
    for discipline_name in discipline_folder_map.keys():
        folder_name = discipline_folder_map[discipline_name]
        excel_column_prefix = discipline_excel_column_map[discipline_name]
        
        print(f"\n{'='*60}")
        print(f"正在处理学科：{discipline_name} (文件夹: {folder_name})")
        
        # 检查学科是否在数据中存在
        if discipline_name not in all_disciplines:
            print(f"警告：学科 '{discipline_name}' 在发文数据中不存在，跳过")
            continue
        
        # 3.1 从原始数据中提取基础数据（gdp_per_capita, RD, Researchers in RD）
        df_base = df_original[['Country', 'Year', 'gdp_per_capita', 'RD', 'Researchers in RD']].copy()
        
        # 3.2 从发文数据中提取该学科的数据
        df_discipline_pub = df_pub[df_pub['学科名称'] == discipline_name][
            ['Country', 'Year', 'pub_total', 'pub_intl']
        ].copy()
        
        print(f"该学科发文数据记录数：{len(df_discipline_pub)}")
        
        # 3.3 创建完整的国家-年份组合
        # 使用所有原始数据中的国家-年份组合
        df_complete = df_base.copy()
        
        # 3.4 合并发文数据
        df_result = pd.merge(
            df_complete,
            df_discipline_pub,
            on=['Country', 'Year'],
            how='left'
        )
        
        # 3.5 填充缺失的发文数据为0
        df_result['pub_total'] = df_result['pub_total'].fillna(0).astype(int)
        df_result['pub_intl'] = df_result['pub_intl'].fillna(0).astype(int)
        
        # 3.6 重命名列以匹配Excel格式要求
        # 根据Stata代码，列名应该是：学科名_total 和 学科名_international
        # 但有些学科名有空格，需要处理
        total_col_name = f'{excel_column_prefix}_total'
        intl_col_name = f'{excel_column_prefix}_international'
        ratio_col_name = f'{excel_column_prefix}_international_ratio'
        
        df_result = df_result.rename(columns={
            'pub_total': total_col_name,
            'pub_intl': intl_col_name
        })
        
        # 3.7 计算国际发文比例列
        # 当总发文数为0时，比例设为0或NaN，这里设为0
        df_result[ratio_col_name] = df_result.apply(
            lambda row: row[intl_col_name] / row[total_col_name] if row[total_col_name] > 0 else 0.0,
            axis=1
        )
        
        # 3.8 按国家和年份排序
        df_result = df_result.sort_values(['Country', 'Year'])
        
        # 3.9 检查数据完整性
        print(f"\n数据统计：")
        print(f"  总记录数：{len(df_result)}")
        print(f"  国家数量：{df_result['Country'].nunique()}")
        print(f"  年份范围：{df_result['Year'].min()} - {df_result['Year'].max()}")
        print(f"  有发文数据的记录数：{(df_result[total_col_name] > 0).sum()}")
        print(f"  有国际发文数据的记录数：{(df_result[intl_col_name] > 0).sum()}")
        
        # 3.10 创建学科文件夹（如果不存在）并保存到两个路径
        excel_filename = f'discipline_{folder_name}.xlsx'
        
        # 保存到第一个路径
        discipline_folder_1 = os.path.join(disciplines_base_dir, folder_name)
        os.makedirs(discipline_folder_1, exist_ok=True)
        excel_path_1 = os.path.join(discipline_folder_1, excel_filename)
        df_result.to_excel(excel_path_1, index=False)
        print(f"\n已保存到路径1：{excel_path_1}")
        
        # 保存到第二个路径
        discipline_folder_2 = os.path.join(disciplines_base_dir_1, folder_name)
        os.makedirs(discipline_folder_2, exist_ok=True)
        excel_path_2 = os.path.join(discipline_folder_2, excel_filename)
        df_result.to_excel(excel_path_2, index=False)
        print(f"已保存到路径2：{excel_path_2}")
        
        # 3.11 显示前几行数据
        print("\n数据预览（前10行）：")
        print(df_result.head(10))
        
        # 3.12 显示一些统计信息
        print(f"\n累计统计：")
        print(f"  总发文数：{df_result[total_col_name].sum()}")
        print(f"  总国际发文数：{df_result[intl_col_name].sum()}")
        if df_result[total_col_name].sum() > 0:
            intl_ratio = df_result[intl_col_name].sum() / df_result[total_col_name].sum()
            print(f"  国际发文比例：{intl_ratio:.4f}")
    
    print(f"\n{'='*60}")
    print("所有学科的Excel文件生成完成！")
    
    # 4. 总结
    print("\n生成的文件列表：")
    for discipline_name, folder_name in discipline_folder_map.items():
        excel_filename = f'discipline_{folder_name}.xlsx'
        
        # 检查第一个路径
        excel_path_1 = os.path.join(disciplines_base_dir, folder_name, excel_filename)
        excel_path_2 = os.path.join(disciplines_base_dir_1, folder_name, excel_filename)
        
        if os.path.exists(excel_path_1) and os.path.exists(excel_path_2):
            print(f"  ✓ {discipline_name}")
            print(f"    路径1: {excel_path_1}")
            print(f"    路径2: {excel_path_2}")
        elif os.path.exists(excel_path_1):
            print(f"  ⚠ {discipline_name} -> 仅在路径1存在")
            print(f"    路径1: {excel_path_1}")
        elif os.path.exists(excel_path_2):
            print(f"  ⚠ {discipline_name} -> 仅在路径2存在")
            print(f"    路径2: {excel_path_2}")
        else:
            print(f"  ✗ {discipline_name} -> 未生成（可能数据中不存在该学科）")


# 执行生成
if __name__ == "__main__":
    generate_discipline_excel_files()
