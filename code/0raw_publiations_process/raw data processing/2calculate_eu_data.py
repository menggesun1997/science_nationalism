import pandas as pd
import numpy as np
import os

base_dir = '/root/autodl-tmp'
output_base_dir = '/root/autodl-tmp'

# base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/publications_raw_data'
# output_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/brexit_experimental_data'


# 定义欧盟国家列表（截至2016年的成员国，不包括英国）
eu_countries = [
    'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
    'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
    'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
    'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
    'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
    'SPAIN', 'SWEDEN'
]

# 将欧盟国家列表转换为集合以便快速查找
eu_countries_set = set(eu_countries)

def standard_country_name():
    # 读取数据
    original_article_file = os.path.join(output_base_dir, 'article_process_1.txt')
    print("正在读取数据...")
    df = pd.read_csv(
        original_article_file,
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'Code_Discipline': str, 'Pays': str, 'initial_fou': float},
        sep=','
    )
    print(f"成功读取数据，共 {len(df)} 条记录")
    print("\n数据预览：")
    print(df.head())
    
    # 统一国家名称的大小写
    df['Pays'] = df['Pays'].str.upper()
    standard_country_maps = {'CZECH REPUBLIC':['CZECHIA'],'IRAN':['IRAN, ISLAMIC REP.'],'SOUTH KOREA':['KOREA, REP.'],'RUSSIA':['RUSSIAN FEDERATION'],'SLOVAKIA':['SLOVAK REPUBLIC'],'TURKEY':['TURKIYE'],'VIETNAM':['VIET NAM']}
    df['Pays'] = df['Pays'].astype(str).str.upper()
    df['Pays'] = df['Pays'].replace(standard_country_maps)
    print("标准化国家名称完成")

    return df

def calculate_eu_publications():
    """
    计算每年的欧盟发文统计：
    1. 欧盟总发文数量（文章中至少有一个欧盟国家就算）
    2. 国际发文量（至少有一个欧盟国家和一个非欧盟国家）
    3. 欧盟内部发文（所有作者都来自欧盟国家）
    """
    # 检查是否已存在聚合后的数据文件
    article_output_file = os.path.join(output_base_dir, 'article_countries_aggregated.txt')
    
    if os.path.exists(article_output_file):
        print("\n检测到已存在的聚合数据文件，正在读取...")
        article_countries = pd.read_csv(
            article_output_file,
            dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
        )
        # 将countries字符串转换回集合格式
        article_countries['countries'] = article_countries['countries'].apply(
            lambda x: set([c for c in x.split(',') if c.strip()]) if x and x.strip() != '' else set()
        )
        print(f"成功读取聚合数据，共 {len(article_countries)} 篇文章")
        print("\n文章国家信息预览：")
        print(article_countries.head())
    else:
        print("\n未找到聚合数据文件，开始处理原始数据...")
        # 读取数据
        df = standard_country_name()
        
        # 对于每篇文章（OST_BK），获取其所有相关国家和年份
        print("\n正在按文章聚合国家信息...")
        print(f"原始数据共 {len(df)} 条记录")
        print("正在进行数据聚合，这可能需要一些时间，请耐心等待...")
        
        # 方法：先去除重复，然后分组聚合（更高效）
        # 先去重，减少数据量
        print("步骤1/3: 去除重复记录...")
        df_unique = df[['OST_BK', 'Annee_Bibliographique', 'Pays']].drop_duplicates()
        print(f"去重后共 {len(df_unique)} 条记录")
        
        # 使用更高效的分组方法：直接使用字典聚合
        print("步骤2/3: 正在聚合国家信息（这可能需要几分钟，请耐心等待）...")
        
        # 方法：使用字典手动聚合，使用itertuples更快
        article_dict = {}
        total_rows = len(df_unique)
        processed = 0
        
        # itertuples比iterrows快得多
        for row in df_unique.itertuples(index=False):
            key = (row.OST_BK, row.Annee_Bibliographique)
            pays = row.Pays
            if pd.notna(pays):
                if key not in article_dict:
                    article_dict[key] = set()
                article_dict[key].add(pays)
            
            processed += 1
            if processed % 100000 == 0:
                print(f"  已处理 {processed}/{total_rows} 条记录 ({processed*100//total_rows}%)...")
        
        print("步骤3/3: 转换结果格式...")
        # 转换为DataFrame
        article_countries = pd.DataFrame([
            {'OST_BK': k[0], 'Annee_Bibliographique': k[1], 'countries': v}
            for k, v in article_dict.items()
        ])
        
        print("聚合完成！")
        
        print(f"共处理 {len(article_countries)} 篇文章")
        print("\n文章国家信息预览：")
        print(article_countries.head())
        
        # 将countries集合转换为字符串格式（用逗号分隔）以便保存
        article_countries['countries_str'] = article_countries['countries'].apply(
            lambda x: ','.join(sorted(x)) if x else ''
        )
        
        # 保存聚合后的文章数据
        article_countries_save = article_countries[['OST_BK', 'Annee_Bibliographique', 'countries_str']].copy()
        article_countries_save.columns = ['OST_BK', 'Annee_Bibliographique', 'countries']
        article_countries_save.to_csv(article_output_file, index=False, encoding='utf-8')
        print(f"\n聚合后的文章数据已保存到：{article_output_file}")
    
    # 判断每篇文章的类型
    print("\n正在判断文章类型...")
    
    def classify_article(countries_set):
        """
        分类文章类型：
        返回 (is_eu_total, is_international, is_eu_internal)
        """
        if not countries_set:  # 如果没有国家信息
            return False, False, False
        
        # 提取欧盟国家和非欧盟国家
        eu_in_article = countries_set.intersection(eu_countries_set)
        non_eu_in_article = countries_set - eu_countries_set
        
        # 欧盟总发文：至少有一个欧盟国家
        is_eu_total = len(eu_in_article) > 0
        
        # 国际发文：至少有一个欧盟国家和一个非欧盟国家
        is_international = len(eu_in_article) > 0 and len(non_eu_in_article) > 0
        
        # 欧盟内部发文：所有国家都是欧盟国家
        is_eu_internal = len(eu_in_article) > 0 and len(non_eu_in_article) == 0
        
        return is_eu_total, is_international, is_eu_internal
    
    # 应用分类函数
    classification = article_countries['countries'].apply(classify_article)
    article_countries['is_eu_total'] = [x[0] for x in classification]
    article_countries['is_international'] = [x[1] for x in classification]
    article_countries['is_eu_internal'] = [x[2] for x in classification]
    
    print("\n分类结果预览：")
    print(article_countries.head(10))
    
    # 保存包含分类结果的完整文章数据
    article_complete_output_file = os.path.join(output_base_dir, 'article_countries_with_classification.txt')
    # 确保有countries_str列（如果是新处理的数据会有，从文件读取的需要生成）
    if 'countries_str' not in article_countries.columns:
        article_countries['countries_str'] = article_countries['countries'].apply(
            lambda x: ','.join(sorted(x)) if x else ''
        )
    article_countries_complete = article_countries[['OST_BK', 'Annee_Bibliographique', 'countries_str', 'is_eu_total', 'is_international', 'is_eu_internal']].copy()
    article_countries_complete.columns = ['OST_BK', 'Annee_Bibliographique', 'countries', 'is_eu_total', 'is_international', 'is_eu_internal']
    article_countries_complete.to_csv(article_complete_output_file, index=False, encoding='utf-8')
    print(f"\n包含分类结果的完整文章数据已保存到：{article_complete_output_file}")
    
    # 按年份统计
    print("\n正在按年份统计...")
    # 将年份转换为整数以便排序
    article_countries['Annee_Bibliographique'] = pd.to_numeric(
        article_countries['Annee_Bibliographique'], errors='coerce'
    )
    # 去除年份为空的行
    article_countries = article_countries.dropna(subset=['Annee_Bibliographique'])
    article_countries['Annee_Bibliographique'] = article_countries['Annee_Bibliographique'].astype(int)
    
    # 按年份统计
    yearly_stats = article_countries.groupby('Annee_Bibliographique').agg({
        'is_eu_total': 'sum',
        'is_international': 'sum',
        'is_eu_internal': 'sum'
    }).reset_index()
    
    yearly_stats.columns = ['年份', '欧盟总发文数', '国际发文数', '欧盟内部发文数']
    
    # 除以欧盟国家数量，得到平均值
    eu_countries_count = len(eu_countries)
    yearly_stats['欧盟总发文数'] = yearly_stats['欧盟总发文数'] / eu_countries_count
    yearly_stats['国际发文数'] = yearly_stats['国际发文数'] / eu_countries_count
    yearly_stats['欧盟内部发文数'] = yearly_stats['欧盟内部发文数'] / eu_countries_count
    
    # 按年份排序
    yearly_stats = yearly_stats.sort_values('年份')
    
    print("\n年度统计结果（平均值）：")
    print(yearly_stats)
    print(f"\n注意：已除以欧盟国家数量（{eu_countries_count}个国家）得到平均值")
    
    # 保存结果
    output_file = os.path.join(output_base_dir, 'eu_publications_yearly_stats.txt')
    yearly_stats.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n结果已保存到 {output_file}")
    
    # 打印汇总信息
    print("\n汇总统计：")
    print(f"总文章数（去重后）：{len(article_countries)}")
    print(f"欧盟总发文数（累计）：{yearly_stats['欧盟总发文数'].sum()}")
    print(f"国际发文数（累计）：{yearly_stats['国际发文数'].sum()}")
    print(f"欧盟内部发文数（累计）：{yearly_stats['欧盟内部发文数'].sum()}")
    print(f"年份范围：{yearly_stats['年份'].min()} - {yearly_stats['年份'].max()}")
    
    return yearly_stats


def merge_eu_with_final_data():
    """
    整合欧盟数据与final_combined_data.xlsx：
    1. 读取final_combined_data.xlsx
    2. 计算欧盟作为整体的指标（均值计算gdp_per_capita、RD、Researchers in RD）
    3. 使用之前计算的发文统计数据填充pub_total和pub_intl
    4. 提取非欧盟国家数据
    5. 合并并输出为Excel文件
    """
    try:
        # 1. 读取final_combined_data.xlsx
        excel_file = os.path.join(output_base_dir, 'final_completed.xlsx')
        print("正在读取Excel文件...")
        df_excel = pd.read_excel(excel_file)
        print(f"成功读取Excel文件，共 {len(df_excel)} 条记录")
        print("\nExcel数据列：", df_excel.columns.tolist())
        print("\nExcel数据预览：")
        print(df_excel.head())
        
        # 统一国家名称的大小写以便匹配
        df_excel['Country'] = df_excel['Country'].str.upper()
        
        # 2. 筛选欧盟国家的数据
        print("\n正在筛选欧盟国家数据...")
        eu_data = df_excel[df_excel['Country'].isin(eu_countries)].copy()
        print(f"找到 {len(eu_data)} 条欧盟国家数据")
        print(f"欧盟国家列表：{eu_data['Country'].unique()}")
        
        # 3. 计算欧盟国家各指标的均值（按年份）
        print("\n正在计算欧盟国家指标均值...")
        eu_indicators = eu_data.groupby('Year').agg({
            'gdp_per_capita': 'mean',
            'RD': 'mean',
            'Researchers in RD': 'mean'
        }).reset_index()
        
        # 4. 读取或计算欧盟发文统计数据
        pub_stats_file = os.path.join(output_base_dir, 'eu_publications_yearly_stats.txt')
        if os.path.exists(pub_stats_file):
            print(f"\n正在读取欧盟发文统计数据：{pub_stats_file}")
            eu_pub_stats = pd.read_csv(pub_stats_file)
            print("欧盟发文统计数据预览：")
            print(eu_pub_stats.head())
        else:
            print(f"\n未找到发文统计文件，正在计算...")
            eu_pub_stats_df = calculate_eu_publications()
            eu_pub_stats = eu_pub_stats_df.copy()
        
        # 确保年份列名一致
        if '年份' in eu_pub_stats.columns:
            eu_pub_stats = eu_pub_stats.rename(columns={'年份': 'Year'})
        
        # 5. 合并发文统计数据到欧盟指标数据
        print("\n正在合并发文统计数据...")
        eu_combined = pd.merge(
            eu_indicators,
            eu_pub_stats[['Year', '欧盟总发文数', '国际发文数']],
            on='Year',
            how='left'
        )
        
        # 重命名列为标准列名
        eu_combined = eu_combined.rename(columns={
            '欧盟总发文数': 'pub_total',
            '国际发文数': 'pub_intl'
        })
        
        # 添加Country列，标记为EU
        eu_combined.insert(0, 'Country', 'EU')
        
        # 填充缺失值为0（如果有的话）
        eu_combined['pub_total'] = eu_combined['pub_total'].fillna(0).astype(int)
        eu_combined['pub_intl'] = eu_combined['pub_intl'].fillna(0).astype(int)
        
        print("\n欧盟综合数据预览：")
        print(eu_combined.head(10))
        
        # 6. 提取非欧盟国家数据
        print("\n正在提取非欧盟国家数据...")
        non_eu_data = df_excel[~df_excel['Country'].isin(eu_countries)].copy()
        print(f"找到 {len(non_eu_data)} 条非欧盟国家数据")
        
        # 确保列顺序一致
        columns_order = ['Country', 'Year', 'pub_total', 'pub_intl', 'gdp_per_capita', 'RD', 'Researchers in RD']
        eu_combined = eu_combined[columns_order]
        non_eu_data = non_eu_data[columns_order]
        
        # 7. 合并欧盟数据和非欧盟国家数据
        print("\n正在合并数据...")
        final_data = pd.concat([non_eu_data, eu_combined], ignore_index=True)
        
        # 按国家和年份排序
        final_data = final_data.sort_values(['Country', 'Year'])
        
        print("\n最终合并数据预览：")
        print(final_data.head(15))
        print(f"\n最终数据共 {len(final_data)} 条记录")
        print(f"国家数量：{final_data['Country'].nunique()}")
        print(f"年份范围：{final_data['Year'].min()} - {final_data['Year'].max()}")
        
        # 8. 保存为Excel文件
        output_file = os.path.join(output_base_dir, 'final_combined_data_with_eu.xlsx')
        final_data.to_excel(output_file, index=False)
        print(f"\n结果已保存到：{output_file}")
        
        # 打印一些统计信息
        print("\n数据统计：")
        print(f"非欧盟国家数量：{non_eu_data['Country'].nunique()}")
        print(f"欧盟数据年份数：{len(eu_combined)}")
        print(f"EU数据示例（前5年）：")
        print(eu_combined[eu_combined['Country'] == 'EU'].head())
        
        return final_data
        
    except Exception as e:
        print(f"处理数据时出错：{str(e)}")
        import traceback
        print("\n详细错误信息：")
        print(traceback.format_exc())
        return None

def calculate_eu_publications_by_discipline():
    """
    计算欧盟在每个学科上的发文统计：
    1. 按学科和年份统计欧盟总发文数量（文章中至少有一个欧盟国家就算）
    2. 按学科和年份统计国际发文量（至少有一个欧盟国家和一个非欧盟国家）
    3. 按学科和年份统计欧盟内部发文（所有作者都来自欧盟国家）
    """
    # 检查是否已存在按学科聚合后的数据文件
    article_discipline_output_file = os.path.join(output_base_dir, 'article_countries_discipline_aggregated.txt')
    
    print("\n开始计算欧盟按学科的发文统计...")
    
    if os.path.exists(article_discipline_output_file):
        print("\n检测到已存在的按学科聚合数据文件，正在读取...")
        article_discipline_countries = pd.read_csv(
            article_discipline_output_file,
            dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'EDiscipline': str, 'countries': str}
        )
        # 将countries字符串转换回集合格式
        article_discipline_countries['countries'] = article_discipline_countries['countries'].apply(
            lambda x: set([c for c in x.split(',') if c.strip()]) if x and x.strip() != '' else set()
        )
        print(f"成功读取按学科聚合数据，共 {len(article_discipline_countries)} 篇文章")
        print("\n文章国家学科信息预览：")
        print(article_discipline_countries.head())
    else:
        print("\n未找到按学科聚合数据文件，开始处理原始数据...")
        # 读取数据
        df = standard_country_name()
        
        # 对于每篇文章（OST_BK），获取其所有相关国家、年份和学科
        print("\n正在按文章聚合国家信息和学科信息...")
        print(f"原始数据共 {len(df)} 条记录")
        print("正在进行数据聚合，这可能需要一些时间，请耐心等待...")
        
        # 方法：先去除重复，然后分组聚合（更高效）
        # 先去重，减少数据量（包含学科信息）
        print("步骤1/4: 去除重复记录...")
        df_unique = df[['OST_BK', 'Annee_Bibliographique', 'Code_Discipline', 'Pays']].drop_duplicates()
        print(f"去重后共 {len(df_unique)} 条记录")
        
        # 步骤2/4: 将 Code_Discipline 映射为 EDiscipline
        print("步骤2/4: 读取学科代码映射文件...")
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
                print("前5条映射示例：")
                for code, discipline in list(discipline_map.items())[:5]:
                    print(f"  {code} -> {discipline}")
            except Exception as e:
                print(f"读取学科代码映射文件时出错：{str(e)}")
                print("将使用原始 Code_Discipline")
        else:
            print(f"警告：未找到学科代码映射文件 {discipline_code_file}")
            print("将使用原始 Code_Discipline")
        
        # 应用映射：将 Code_Discipline 映射为 EDiscipline
        if discipline_map:
            df_unique['EDiscipline'] = df_unique['Code_Discipline'].map(discipline_map)
            # 对于无法映射的，使用原始 Code_Discipline
            df_unique['EDiscipline'] = df_unique['EDiscipline'].fillna(df_unique['Code_Discipline'])
            print(f"映射完成，共有 {df_unique['EDiscipline'].notna().sum()} 条记录成功映射")
            print(f"映射后的学科数量：{df_unique['EDiscipline'].nunique()}")
        else:
            # 如果没有映射文件，直接使用 Code_Discipline 作为 EDiscipline
            df_unique['EDiscipline'] = df_unique['Code_Discipline']
            print("未找到映射文件，使用原始 Code_Discipline 作为 EDiscipline")
        
        # 使用字典聚合：按 (OST_BK, Annee_Bibliographique, EDiscipline) 聚合国家
        print("步骤3/4: 正在聚合国家信息和学科信息（这可能需要几分钟，请耐心等待）...")
        
        # 方法：使用字典手动聚合，使用itertuples更快
        article_dict = {}
        total_rows = len(df_unique)
        processed = 0
        
        # itertuples比iterrows快得多
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
        
        print("步骤4/4: 转换结果格式...")
        # 转换为DataFrame
        article_discipline_countries = pd.DataFrame([
            {
                'OST_BK': k[0], 
                'Annee_Bibliographique': k[1], 
                'EDiscipline': k[2],
                'countries': v
            }
            for k, v in article_dict.items()
        ])
        
        print("聚合完成！")
        
        print(f"共处理 {len(article_discipline_countries)} 篇文章")
        print("\n文章国家学科信息预览：")
        print(article_discipline_countries.head())
        
        # 将countries集合转换为字符串格式（用逗号分隔）以便保存
        article_discipline_countries['countries_str'] = article_discipline_countries['countries'].apply(
            lambda x: ','.join(sorted(x)) if x else ''
        )
        
        # 保存聚合后的文章数据
        article_discipline_countries_save = article_discipline_countries[
            ['OST_BK', 'Annee_Bibliographique', 'EDiscipline', 'countries_str']
        ].copy()
        article_discipline_countries_save.columns = [
            'OST_BK', 'Annee_Bibliographique', 'EDiscipline', 'countries'
        ]
        article_discipline_countries_save.to_csv(
            article_discipline_output_file, index=False, encoding='utf-8'
        )
        print(f"\n聚合后的文章学科数据已保存到：{article_discipline_output_file}")
    
    # 判断每篇文章的类型
    print("\n正在判断文章类型...")
    
    def classify_article(countries_set):
        """
        分类文章类型：
        返回 (is_eu_total, is_international, is_eu_internal)
        """
        if not countries_set:  # 如果没有国家信息
            return False, False, False
        
        # 提取欧盟国家和非欧盟国家
        eu_in_article = countries_set.intersection(eu_countries_set)
        non_eu_in_article = countries_set - eu_countries_set
        
        # 欧盟总发文：至少有一个欧盟国家
        is_eu_total = len(eu_in_article) > 0
        
        # 国际发文：至少有一个欧盟国家和一个非欧盟国家
        is_international = len(eu_in_article) > 0 and len(non_eu_in_article) > 0
        
        # 欧盟内部发文：所有国家都是欧盟国家
        is_eu_internal = len(eu_in_article) > 0 and len(non_eu_in_article) == 0
        
        return is_eu_total, is_international, is_eu_internal
    
    # 应用分类函数
    classification = article_discipline_countries['countries'].apply(classify_article)
    article_discipline_countries['is_eu_total'] = [x[0] for x in classification]
    article_discipline_countries['is_international'] = [x[1] for x in classification]
    article_discipline_countries['is_eu_internal'] = [x[2] for x in classification]
    
    print("\n分类结果预览：")
    print(article_discipline_countries.head(10))
    
    # 保存包含分类结果的完整文章数据
    article_discipline_complete_output_file = os.path.join(
        output_base_dir, 'article_countries_discipline_with_classification.txt'
    )
    # 确保有countries_str列（如果是新处理的数据会有，从文件读取的需要生成）
    if 'countries_str' not in article_discipline_countries.columns:
        article_discipline_countries['countries_str'] = article_discipline_countries['countries'].apply(
            lambda x: ','.join(sorted(x)) if x else ''
        )
    article_discipline_complete = article_discipline_countries[
        ['OST_BK', 'Annee_Bibliographique', 'EDiscipline', 'countries_str', 
         'is_eu_total', 'is_international', 'is_eu_internal']
    ].copy()
    article_discipline_complete.columns = [
        'OST_BK', 'Annee_Bibliographique', 'EDiscipline', 'countries', 
        'is_eu_total', 'is_international', 'is_eu_internal'
    ]
    article_discipline_complete.to_csv(
        article_discipline_complete_output_file, index=False, encoding='utf-8'
    )
    print(f"\n包含分类结果的完整文章学科数据已保存到：{article_discipline_complete_output_file}")
    
    # 按年份和学科统计
    print("\n正在按年份和学科统计...")
    # 将年份转换为整数以便排序
    article_discipline_countries['Annee_Bibliographique'] = pd.to_numeric(
        article_discipline_countries['Annee_Bibliographique'], errors='coerce'
    )
    # 去除年份为空的行
    article_discipline_countries = article_discipline_countries.dropna(
        subset=['Annee_Bibliographique', 'EDiscipline']
    )
    article_discipline_countries['Annee_Bibliographique'] = article_discipline_countries[
        'Annee_Bibliographique'
    ].astype(int)
    
    # 按年份和学科统计
    yearly_discipline_stats = article_discipline_countries.groupby(
        ['Annee_Bibliographique', 'EDiscipline']
    ).agg({
        'is_eu_total': 'sum',
        'is_international': 'sum',
        'is_eu_internal': 'sum'
    }).reset_index()
    
    yearly_discipline_stats.columns = [
        '年份', '学科名称', '欧盟总发文数', '国际发文数', '欧盟内部发文数'
    ]
    
    # 除以欧盟国家数量，得到平均值
    eu_countries_count = len(eu_countries)
    yearly_discipline_stats['欧盟总发文数'] = yearly_discipline_stats['欧盟总发文数'] / eu_countries_count
    yearly_discipline_stats['国际发文数'] = yearly_discipline_stats['国际发文数'] / eu_countries_count
    yearly_discipline_stats['欧盟内部发文数'] = yearly_discipline_stats['欧盟内部发文数'] / eu_countries_count
    
    # 按年份和学科名称排序
    yearly_discipline_stats = yearly_discipline_stats.sort_values(['年份', '学科名称'])
    
    print("\n按学科年度统计结果预览（平均值）：")
    print(yearly_discipline_stats.head(20))
    print(f"\n注意：已除以欧盟国家数量（{eu_countries_count}个国家）得到平均值")
    
    # 保存结果
    output_file = os.path.join(output_base_dir, 'eu_publications_yearly_by_discipline.txt')
    yearly_discipline_stats.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n结果已保存到 {output_file}")
    
    # 打印汇总信息
    print("\n汇总统计：")
    print(f"总文章数（去重后）：{len(article_discipline_countries)}")
    print(f"学科数量：{yearly_discipline_stats['学科名称'].nunique()}")
    print(f"欧盟总发文数（累计）：{yearly_discipline_stats['欧盟总发文数'].sum()}")
    print(f"国际发文数（累计）：{yearly_discipline_stats['国际发文数'].sum()}")
    print(f"欧盟内部发文数（累计）：{yearly_discipline_stats['欧盟内部发文数'].sum()}")
    print(f"年份范围：{yearly_discipline_stats['年份'].min()} - {yearly_discipline_stats['年份'].max()}")
    
    # 按学科汇总统计（注意：已经是平均值，所以sum是累计平均值）
    print("\n各学科累计统计（平均值）：")
    discipline_summary = yearly_discipline_stats.groupby('学科名称').agg({
        '欧盟总发文数': 'sum',
        '国际发文数': 'sum',
        '欧盟内部发文数': 'sum'
    }).reset_index()
    discipline_summary = discipline_summary.sort_values('欧盟总发文数', ascending=False)
    print(discipline_summary.head(20))
    
    # 保存按学科汇总的结果
    discipline_summary_file = os.path.join(
        output_base_dir, 'eu_publications_by_discipline_summary.txt'
    )
    discipline_summary.to_csv(discipline_summary_file, index=False, encoding='utf-8')
    print(f"\n学科汇总结果已保存到：{discipline_summary_file}")
    
    return yearly_discipline_stats



# 执行计算
if __name__ == "__main__":
    # calculate_eu_publications()
    calculate_eu_publications_by_discipline()  # 计算按学科的发文统计
    # merge_eu_with_final_data()