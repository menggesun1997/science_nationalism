import pandas as pd
import os

# 定义基础目录
base_dir = '/Users/sunmengge/Dropbox/brexit_rawdata'

# 定义欧盟国家列表（2016年后的成员国，不包括英国）
eu_countries = [
    'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
    'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
    'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
    'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
    'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
    'SPAIN', 'SWEDEN'
]

def calculate_eu_indicators():
    # 读取原始数据
    original_data = pd.read_excel(os.path.join(base_dir, 'original_data.xlsx'))
    merged_data = pd.read_excel(os.path.join(base_dir, 'merged_data.xlsx'))
    
    # 筛选欧盟国家的数据
    eu_data = original_data[original_data['Country'].isin(eu_countries)].copy()
    
    # 计算欧盟国家的指标均值
    eu_indicators = eu_data.groupby('Year')[['gdp_per_capita', 'RD', 'Researchers in RD']].mean().reset_index()
    
    # 添加Country列，标记为EU
    eu_indicators.insert(0, 'Country', 'EU')
    
    # 将EU数据添加到merged_data中
    # 首先删除merged_data中可能存在的EU数据
    merged_data = merged_data[merged_data['Country'] != 'EU']
    
    # 合并数据
    updated_merged_data = pd.concat([merged_data, eu_indicators], ignore_index=True)
    
    # 按Country和Year排序
    updated_merged_data = updated_merged_data.sort_values(['Country', 'Year'])
    
    # 保存更新后的数据
    output_file = os.path.join(base_dir, 'merged_data_with_eu.xlsx')
    updated_merged_data.to_excel(output_file, index=False)
    
    print("EU指标计算完成，数据已保存到：", output_file)
    print("\nEU数据预览：")
    print(eu_indicators.head())
    
    return eu_indicators, updated_merged_data

if __name__ == "__main__":
    eu_indicators, updated_merged_data = calculate_eu_indicators() 