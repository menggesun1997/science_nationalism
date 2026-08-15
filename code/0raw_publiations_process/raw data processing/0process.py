import pandas as pd
import numpy as np
import os

# base_dir = '/root/autodl-tmp'
# output_base_dir = '/root/autodl-tmp'

base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/publications_raw_data'
output_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/brexit_experimental_data'

def count_ost_country():
    # 读取原始数据
    country_df = pd.read_csv(os.path.join(base_dir, 'article_cntry_brexit.txt'),
                            sep=',',
                            names=['OST_BK', 'Pays'],
                            dtype={'OST_BK': str, 'Pays': str})
    
    # 统一国家名称的大小写
    country_df['Pays'] = country_df['Pays'].str.upper()
    
    # 按照 cntry_convert.xlsx 将 Clarivate country 名称转换为标准 Country 名称
    try:
        mapping_path = os.path.join(base_dir, 'cntry_convert.xlsx')
        if os.path.exists(mapping_path):
            mapping_df = pd.read_excel(mapping_path)
            # 只保留有效的两列，并清洗键列（Clarivate country）为大写以便匹配
            if {'Clarivate country', 'Country'}.issubset(set(mapping_df.columns)):
                mapping_df = mapping_df[['Clarivate country', 'Country']].dropna(subset=['Clarivate country'])
                mapping_df['Clarivate country'] = mapping_df['Clarivate country'].astype(str).str.strip().str.upper()
                mapping_dict = dict(zip(mapping_df['Clarivate country'], mapping_df['Country']))
                # 将 Pays 由 Clarivate 命名映射为标准 Country 名称；缺失映射则保留原值
                country_df['Pays'] = country_df['Pays'].map(mapping_dict).fillna(country_df['Pays'])
            else:
                print("警告：'cntry_convert.xlsx' 未包含需要的列 'Clarivate country' 与 'Country'，跳过名称转换。")
        else:
            print("提示：未找到映射文件 cntry_convert.xlsx（期望位置在 base_dir），跳过名称转换。")
    except Exception as e:
        print(f"国家名称映射时发生错误：{e}，将跳过名称转换。")
    
    # 去除空值所在的行
    country_df = country_df.dropna(subset=['OST_BK', 'Pays'])
    
    # 去重：如果'OST_BK'和'Pays'都相同，则只保留一行，这样是以防在计算total_publication时，重复计算
    country_df = country_df.drop_duplicates(subset=['OST_BK', 'Pays'])
    
    # 计算每个OST_BK的唯一Pays数量
    country_counts = country_df.groupby('OST_BK')['Pays'].nunique().reset_index()
    country_counts.columns = ['OST_BK', 'unique_countries']
    
    # 将计数结果合并回原始数据
    country_df = pd.merge(country_df, country_counts, on='OST_BK', how='left')
    
    # 根据唯一国家数量设置initial_fou
    country_df['initial_fou'] = (country_df['unique_countries'] > 1).astype(int)
    
    # 删除临时列
    country_df = country_df.drop('unique_countries', axis=1)
    
    # 保存为TXT（CSV）格式
    output_file = os.path.join(output_base_dir, 'article_cntry_brexit_initial.txt')
    country_df.to_csv(output_file,
                      index=False,
                      encoding='utf-8')
    
    print(f"\n处理完成，结果已保存到 {output_file}")
    print("\n数据预览：")
    print(country_df.head())
    
    return country_df

# count_ost_country()

def replace_country_name():
    try:
        # 读取国家代码映射文件（TXT）
        country_df = pd.read_csv(
            os.path.join(output_base_dir, 'article_cntry_brexit_initial.txt'),
            dtype={'OST_BK': str, 'Pays': str}
        )
        
        print(country_df.head())
        
        # 读取文章数据
        article_df = pd.read_csv(os.path.join(base_dir, 'article_brexit.txt'), 
                            sep=',',
                            names=['OST_BK', 'UID', 'Annee_Bibliographique', 'Code_Discipline'],
                            dtype={'OST_BK': str, 'UID': str, 'Annee_Bibliographique': str, 'Code_Discipline': str})
        
        print(f"成功读取数据，文章数据共 {len(article_df)} 行，国家映射共 {len(country_df)} 条")
        
        # 使用merge合并国家列表，保留所有Pays记录
        merged_df = pd.merge(
            article_df,
            country_df,
            on='OST_BK',
            how='left'
        )
        
        print("\n合并后的数据预览：")
        print(merged_df.head())
        print(f"\n合并后的数据行数：{len(merged_df)}")
        
        # 保存为TXT（CSV）格式
        output_file = os.path.join(output_base_dir, 'article_process_1.txt')
        merged_df[['OST_BK', 'Annee_Bibliographique', 'Code_Discipline', 'Pays', 'initial_fou']].to_csv(
            output_file,
            index=False,
            encoding='utf-8'
        )
        print(f"\n统计完成，共 {len(merged_df)} 条记录")
        print(f"结果已保存到 {output_file}")
    except Exception as e:
        print(f"处理数据时出错：{str(e)}")
        import traceback
        print("\n详细错误信息：")
        print(traceback.format_exc())
    return

# replace_country_name()

##先计算total_publications变量
def total_publication_count():
    # 读取数据
    merged_df = pd.read_csv(
        os.path.join(output_base_dir, 'article_process_1.txt'),
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'Code_Discipline': str, 'Pays': str, 'initial_fou': float}
    )
    print("\n原始数据预览：")
    print(merged_df.head())
    
    # 按国家、年份和学科代码分组统计
    publication_counts = merged_df.groupby(['Pays', 'Annee_Bibliographique', 'Code_Discipline']).size().reset_index(name='文章数量')
    
    print("\n统计结果预览：")
    print(publication_counts.head())
    
    # 保存结果为TXT（CSV）
    output_file = os.path.join(output_base_dir, 'publication_counts.txt')
    publication_counts.to_csv(output_file,
                              index=False,
                              encoding='utf-8')
    
    print(f"\n处理完成，结果已保存到 {output_file}")
    print("\n数据统计：")
    print(f"总记录数：{len(publication_counts)}")
    print(f"国家数量：{len(publication_counts['Pays'].unique())}")
    print(f"年份范围：{publication_counts['Annee_Bibliographique'].min()} - {publication_counts['Annee_Bibliographique'].max()}")
    print(f"学科代码数量：{len(publication_counts['Code_Discipline'].unique())}")
    
    return publication_counts

# total_publication_count()



##然后计算initial_publication变量
def initial_publication_count():
    # 读取数据
    merged_df = pd.read_csv(
        os.path.join(output_base_dir, 'article_process_1.txt'),
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'Code_Discipline': str, 'Pays': str, 'initial_fou': float}
    )
    print("\n原始数据预览：")
    print(merged_df.head())
    
    # 筛选出国际出版物（initial_fou=1.0）
    international_articles = merged_df[merged_df['initial_fou'] == 1.0]
    print(f"\n国际出版物数量：{len(international_articles)}")
    
    # 按国家、年份和学科代码分组统计
    publication_counts = international_articles.groupby(['Pays', 'Annee_Bibliographique', 'Code_Discipline']).size().reset_index(name='文章数量')
    
    print("\n统计结果预览：")
    print(publication_counts.head())
    
    # 保存结果为TXT（CSV）
    output_file = os.path.join(output_base_dir, 'international_publication_counts.txt')
    publication_counts.to_csv(output_file,
                              index=False,
                              encoding='utf-8')
    
    print(f"\n处理完成，结果已保存到 {output_file}")
    print("\n数据统计：")
    print(f"总记录数：{len(publication_counts)}")
    print(f"国家数量：{len(publication_counts['Pays'].unique())}")
    print(f"年份范围：{publication_counts['Annee_Bibliographique'].min()} - {publication_counts['Annee_Bibliographique'].max()}")
    print(f"学科代码数量：{len(publication_counts['Code_Discipline'].unique())}")
    
    return publication_counts

# initial_publication_count()

def merge_total_and_international_counts():
    try:
        total_path = os.path.join(output_base_dir, 'publication_counts.txt')
        intl_path = os.path.join(output_base_dir, 'international_publication_counts.txt')

        # 读取两个统计文件
        total_df = pd.read_csv(
            total_path,
            dtype={'Pays': str, 'Annee_Bibliographique': str, 'Code_Discipline': str}
        )
        intl_df = pd.read_csv(
            intl_path,
            dtype={'Pays': str, 'Annee_Bibliographique': str, 'Code_Discipline': str}
        )

        # 重命名计数字段
        if '文章数量' in total_df.columns:
            total_df = total_df.rename(columns={'文章数量': 'pub_total'})
        if '文章数量' in intl_df.columns:
            intl_df = intl_df.rename(columns={'文章数量': 'pub_intl'})

        # 合并（外连接，保留任一侧存在的键），并将缺失计数填0
        merged = pd.merge(
            total_df,
            intl_df,
            on=['Pays', 'Annee_Bibliographique', 'Code_Discipline'],
            how='outer'
        )
        merged['pub_total'] = merged['pub_total'].fillna(0).astype(int)
        merged['pub_intl'] = merged['pub_intl'].fillna(0).astype(int)

        # 输出保存
        output_file = os.path.join(output_base_dir, 'publication_counts_merged.csv')
        merged[['Pays', 'Annee_Bibliographique', 'Code_Discipline', 'pub_total', 'pub_intl']].to_csv(
            output_file,
            index=False,
            encoding='utf-8'
        )

        print(f"合并完成，结果已保存到 {output_file}")
        print(merged.head())
        return merged
    except Exception as e:
        print(f"合并统计文件时出错：{str(e)}")
        import traceback
        print("\n详细错误信息：")
        print(traceback.format_exc())
        return None

merge_total_and_international_counts()

##替换学科名称
def replace_discipline_name():
    try:
        # 读取学科代码和学科的映射关系
        discipline_map = {}
        with open(os.path.join(base_dir, 'discipline_code.txt'), 'r') as f:
            # 跳过表头
            next(f)
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(',')
                    if len(parts) >= 3:  # 确保至少有Code_Discipline和EDiscipline
                        code = parts[0]
                        discipline = parts[2]  # EDiscipline是第三列
                        discipline_map[code] = discipline
            
            print(f"成功读取学科代码映射，共 {len(discipline_map)} 条记录")
            print("前5条映射：")
            for code, discipline in list(discipline_map.items())[:5]:
                print(f"{code} -> {discipline}")
    except Exception as e:
        print(f"处理数据时出错：{str(e)}")
    
    # 读取文章数据
    article_df = pd.read_csv(
        os.path.join(output_base_dir, 'publication_counts.txt'),
        dtype={'Pays': str, 'Annee_Bibliographique': str, 'Code_Discipline': str, '文章数量': int}
    )
    #international_publication_counts
    print(f"\n成功读取数据，文章数据共 {len(article_df)} 行")
    
    # 使用映射字典替换学科代码
    article_df['学科名称'] = article_df['Code_Discipline'].map(discipline_map)
    print("\n映射后的数据：")
    print(article_df.head())
    
    # 选择需要的列并保存
    final_df = article_df[['Pays', 'Annee_Bibliographique', '学科名称', '文章数量']]
    print("\n最终数据：")
    print(final_df.head())
    
    # 保存为TXT（CSV）格式
    output_file = os.path.join(output_base_dir, 'publication_counts_change_discipline.txt')
    final_df.to_csv(output_file,
                    index=False,
                    encoding='utf-8')
    
    print(f"\n处理完成，结果已保存到 {output_file}")
    return

# replace_discipline_name()

def pilot_data():
    try:
        # 读取最终统计数据
        print("开始读取数据...")
        df = pd.read_csv(
            os.path.join(output_base_dir, 'publication_counts_change_discipline.txt'),
            dtype={'Pays': str, 'Annee_Bibliographique': str, '学科名称': str, '文章数量': int}
        )
        print(f"成功读取数据，共 {len(df)} 行")
        
        # 创建年份范围（2005-2024）
        years = list(range(2005, 2024))
        
        # 获取所有唯一的国家和学科
        countries = df['Pays'].unique()
        disciplines = df['学科名称'].unique()
        print(f"\n处理 {len(countries)} 个国家，{len(disciplines)} 个学科")
        
        # 创建一个空的数据框，包含所有国家和年份的组合
        result = pd.DataFrame(index=pd.MultiIndex.from_product([countries, years], names=['Pays', 'Annee_Bibliographique']))
        
        # 重塑数据
        for discipline in disciplines:
            print(f"\n处理学科：{discipline}")
            # 筛选当前学科的数据
            discipline_data = df[df['学科名称'] == discipline]
            print(f"该学科数据行数：{len(discipline_data)}")
            
            if len(discipline_data) > 0:  # 只在有数据时进行处理
                # 创建透视表
                pivot_data = discipline_data.pivot_table(
                    index=['Pays', 'Annee_Bibliographique'],
                    values='文章数量',
                    aggfunc='sum'
                )
                
                # 检查透视表
                print("透视表预览：")
                print(pivot_data.head())
                
                # 重命名列
                pivot_data.columns = [discipline]
                
                # 将年份转换为整数
                pivot_data.index = pivot_data.index.set_levels([
                    pivot_data.index.levels[0],
                    pivot_data.index.levels[1].astype(int)
                ])
                
                # 合并到结果数据框
                result = result.join(pivot_data, how='left')
        
        # 重置索引
        result = result.reset_index()
        
        # 重命名列
        result = result.rename(columns={
            'Pays': '国家',
            'Annee_Bibliographique': '年份'
        })
        
        # 将年份列转换为整数
        result['年份'] = result['年份'].astype(int)
        
        # 填充所有NaN值为0
        result = result.fillna(0)
        
        # 将数值列转换为整数
        for col in result.columns[2:]:  # 跳过国家和年份列
            result[col] = result[col].astype(int)
        
        # 保存为TXT（CSV）文件
        txt_file = os.path.join(output_base_dir, 'total_publication_pilot.txt')
        result.to_csv(txt_file, index=False, encoding='utf-8')
        
        print("\n处理完成，结果已保存到 total_publication_pilot.txt")
        print("\n结果数据预览：")
        print(result.head())

    except Exception as e:
        print(f"处理数据时出错：{str(e)}")
        import traceback
        print("\n详细错误信息：")
        print(traceback.format_exc())
    return result
    
# pilot_data()




