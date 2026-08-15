import pandas as pd

def merge_all_data():
    """
    合并所有数据：original_data + uk和控制国家的tile数据
    """
    # 读取原始数据
    original_data_dir = '/Users/sunmengge/Dropbox/brexit_data/clean data/Data completion copy/final_completed.xlsx'
    original_data = pd.read_excel(original_data_dir)
    
    print("原始数据形状:", original_data.shape)
    print("原始数据列:", original_data.columns.tolist())
    
    # 定义要分析的国家列表
    # 注意：原始数据中只有部分国家有数据
    countries_to_analyze = ['uk', 'iceland', 'japan', 'switzerland', 'singapore', 'norway', 'israel', 'south-korea']
    
    # 存储所有tile数据
    all_tile_data = []
    
    # 处理英国数据
    uk_tile_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_uk/uk_eu_non_eu_west_tile.csv'
    uk_tile_data = pd.read_csv(uk_tile_file)
    uk_tile_data['country'] = 'uk'
    all_tile_data.append(uk_tile_data)
    
    # 处理控制国家数据
    control_countries_dir = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_countrol_countries_brexit'
    
    for country in countries_to_analyze[1:]:  # 跳过uk，因为已经处理了
        tile_file = f'{control_countries_dir}/{country}_eu_non_eu_west_tile.csv'
        try:
            country_tile_data = pd.read_csv(tile_file)
            country_tile_data['country'] = country
            all_tile_data.append(country_tile_data)
            print(f"成功读取 {country} 的tile数据")
        except FileNotFoundError:
            print(f"警告: 找不到 {country} 的tile数据文件")
    
    # 合并所有tile数据
    combined_tile_data = pd.concat(all_tile_data, ignore_index=True)
    print(f"合并后的tile数据形状: {combined_tile_data.shape}")
    
    # 重命名列以便合并
    combined_tile_data = combined_tile_data.rename(columns={'year': 'Year'})
    
    # 将国家名称标准化以匹配original_data
    country_mapping = {
        'uk': 'UNITED KINGDOM',
        'iceland': 'ICELAND', 
        'japan': 'JAPAN',
        'switzerland': 'SWITZERLAND',
        'singapore': 'SINGAPORE',
        'norway': 'NORWAY',
        'israel': 'ISRAEL',
        'south-korea': 'KOREA, REP.'
    }
    
    combined_tile_data['Country'] = combined_tile_data['country'].map(country_mapping)
    
    # 检查哪些国家在原始数据中存在
    available_countries = original_data['Country'].unique()
    print(f"原始数据中可用的国家: {len(available_countries)} 个")
    
    # 过滤掉在原始数据中不存在的国家
    before_filter = len(combined_tile_data)
    combined_tile_data = combined_tile_data[combined_tile_data['Country'].isin(available_countries)]
    after_filter = len(combined_tile_data)
    
    print(f"过滤前tile数据: {before_filter} 行")
    print(f"过滤后tile数据: {after_filter} 行")
    print(f"成功匹配的国家: {sorted(combined_tile_data['Country'].unique())}")
    
    # 只保留需要的列
    tile_data_for_merge = combined_tile_data[['Country', 'Year', 'ratio_difference']].copy()
    
    # 合并数据
    merged_data = pd.merge(original_data, tile_data_for_merge, on=['Country', 'Year'], how='inner')
    
    print(f"合并后数据形状: {merged_data.shape}")
    print("合并后数据列:", merged_data.columns.tolist())
    
    # 保存合并后的数据
    output_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/networks_sdid_brexit/merged_all_data.csv'
    merged_data.to_csv(output_file, index=False)
    print(f"合并数据已保存到: {output_file}")
    
    # 显示数据摘要
    print("\n=== 数据摘要 ===")
    print("包含的国家:")
    print(merged_data['Country'].unique())
    print("\n年份范围:")
    print(f"{merged_data['Year'].min()} - {merged_data['Year'].max()}")
    print("\n每个国家的数据量:")
    print(merged_data['Country'].value_counts().sort_index())
    
    return merged_data

if __name__ == "__main__":
    merged_data = merge_all_data()
