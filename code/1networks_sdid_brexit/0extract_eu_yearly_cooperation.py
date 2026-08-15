
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import pandas as pd
import os

def extract_eu_yearly_cooperation():
    """
    从原始数据中提取EU国家每年的国际合作论文数据
    每年输出一个CSV文件
    国际合作定义：论文中包含至少一个EU成员国和一个非EU国家
    """
    
    # 定义EU国家列表（截至2016年的成员国，不包括英国）
    eu_countries = [
        'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
        'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
        'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
        'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
        'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 'SPAIN', 'SWEDEN'
    ]
    
    # 设置文件路径
    raw_data_file = str(LEGACY_BREXIT / "article_pays_list.txt")
    output_dir = str(LEGACY_BREXIT / "networks_eu")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print("开始读取原始数据文件...")
    
    try:
        # 定义函数判断是否为国际合作论文
        def is_international_cooperation(pays_str):
            if pd.isna(pays_str) or pays_str == '':
                return False
            
            pays_str = str(pays_str).upper()
            countries = [c.strip() for c in pays_str.split(',') if c.strip()]
            
            # 检查是否同时包含EU国家和非EU国家
            has_eu = any(country in [c.upper() for c in eu_countries] for country in countries)
            has_non_eu = any(country not in [c.upper() for c in eu_countries] for country in countries)
            
            return has_eu and has_non_eu
        
        # 初始化年份数据字典
        yearly_data = {}
        
        # 分块读取数据文件
        chunk_size = 100000
        total_rows = 0
        
        print("开始分块读取数据文件...")
        
        for chunk_num, chunk in enumerate(pd.read_csv(raw_data_file, sep='\t', chunksize=chunk_size, encoding='utf-8')):
            total_rows += len(chunk)
            print(f"处理第 {chunk_num + 1} 块数据，共 {len(chunk)} 行...")
            
            # 检查必要的列是否存在
            required_columns = ['OST_BK', 'Annee_Bibliographique', 'Code_Discipline', 'Pays']
            for col in required_columns:
                if col not in chunk.columns:
                    print(f"错误：未找到 {col} 列")
                    print(f"可用的列: {list(chunk.columns)}")
                    return False
            
            # 处理Pays列中的空值
            chunk['Pays'] = chunk['Pays'].fillna('')
            
            # 确保年份列是字符串类型，避免类型比较错误
            chunk['Annee_Bibliographique'] = chunk['Annee_Bibliographique'].astype(str)
            
            # 筛选国际合作论文
            mask = chunk['Pays'].apply(is_international_cooperation)
            international_chunk = chunk[mask]
            
            if len(international_chunk) > 0:
                # 按年份分组
                for year, year_group in international_chunk.groupby('Annee_Bibliographique'):
                    if year not in yearly_data:
                        yearly_data[year] = []
                    yearly_data[year].append(year_group)
            
            # 每处理10个chunk显示一次进度
            if (chunk_num + 1) % 10 == 0:
                print(f"已处理 {chunk_num + 1} 块，累计 {total_rows} 行数据")
        
        print(f"数据读取完成，总共处理了 {total_rows} 行数据")
        
        # 合并每年的数据并保存
        years = sorted(yearly_data.keys())
        print(f"数据年份范围: {min(years)} - {max(years)}")
        
        for year in years:
            print(f"正在处理 {year} 年的数据...")
            
            # 合并该年份的所有数据块
            year_data = pd.concat(yearly_data[year], ignore_index=True)
            
            # 保存该年份的数据
            output_file = os.path.join(output_dir, f'eu_international_cooperation_{year}.csv')
            year_data.to_csv(output_file, index=False, encoding='utf-8')
            
            print(f"  - {year} 年国际合作论文数: {len(year_data)}")
            print(f"  - 已保存到: {output_file}")
        
        print(f"\n所有年份的数据处理完成！")
        print(f"输出目录: {output_dir}")
        
        return True
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        print("请检查文件路径和格式是否正确")
        return False

if __name__ == "__main__":
    result = extract_eu_yearly_cooperation()
    if result is not None:
        print("\n处理完成！")
        print(result)
