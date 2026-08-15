import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from collections import defaultdict

def analyze_brexit_tile_index(networks_data_dir, output_file, eu_countries, non_eu_west_countries):
    """
    分析英国脱欧对英国与欧盟国家、非欧盟西方国家合作的影响
    """
    # 读取CSV文件
    print("正在读取数据...")
    df = pd.read_csv(networks_data_dir)
    
    # 重命名列以便处理
    df.columns = ['article_id', 'year', 'discipline', 'countries']
    
    # 初始化统计字典
    yearly_stats = defaultdict(lambda: {
        'eu_cooperation': 0,
        'non_eu_west_cooperation': 0,
        'international_articles': 0
    })
    
    print("正在分析合作数据...")
    
    # 遍历每一行数据
    for idx, row in df.iterrows():
        year = row['year']
        countries_str = str(row['countries'])
        
        # 跳过没有国家信息的行
        if pd.isna(countries_str) or countries_str == 'nan':
            continue
            
        # 将国家字符串分割成列表
        countries = [country.strip() for country in countries_str.split(',')]
        
        # 检查是否为国际合作文章（包含多个国家）
        if len(countries) <= 1:
            continue  # 跳过非国际合作文章
        
        # 统计该文章中的合作情况
        eu_count = 0
        non_eu_west_count = 0
        
        for country in countries:
            country_clean = country.strip().upper()
            
            # 检查是否为欧盟国家
            if any(eu_country.upper() in country_clean or country_clean in eu_country.upper() 
                   for eu_country in eu_countries):
                eu_count += 1
                
            # 检查是否为非欧盟西方国家
            if any(non_eu_west_country.upper() in country_clean or country_clean in non_eu_west_country.upper() 
                   for non_eu_west_country in non_eu_west_countries):
                non_eu_west_count += 1
        
        # 更新年度统计（只统计国际合作文章）
        yearly_stats[year]['international_articles'] += 1
        if eu_count > 0:
            yearly_stats[year]['eu_cooperation'] += 1
        if non_eu_west_count > 0:
            yearly_stats[year]['non_eu_west_cooperation'] += 1
    
    # 转换为DataFrame并计算比率
    results = []
    for year in sorted(yearly_stats.keys()):
        stats = yearly_stats[year]
        # 这里的 total 是每年该国家的国际合作文章数量
        total = stats['international_articles']
        
        if total > 0:
            eu_ratio = stats['eu_cooperation'] / total
            non_eu_west_ratio = stats['non_eu_west_cooperation'] / total
            ratio_difference = eu_ratio - non_eu_west_ratio
        else:
            eu_ratio = 0
            non_eu_west_ratio = 0
            ratio_difference = 0
            
        results.append({
            'year': year,
            'international_articles': total,
            'eu_cooperation_count': stats['eu_cooperation'],
            'non_eu_west_cooperation_count': stats['non_eu_west_cooperation'],
            'eu_cooperation_ratio': eu_ratio,
            'non_eu_west_cooperation_ratio': non_eu_west_ratio,
            'ratio_difference': ratio_difference
        })
    
    # 创建结果DataFrame
    results_df = pd.DataFrame(results)
    
    # 保存结果
    results_df.to_csv(output_file, index=False)
    print(f"分析结果已保存到: {output_file}")
    
    # 显示结果摘要
    print("\n=== 合作分析结果摘要 ===")
    print(results_df.to_string(index=False))
    
    # 计算总体统计
    total_eu = results_df['eu_cooperation_count'].sum()
    total_non_eu_west = results_df['non_eu_west_cooperation_count'].sum()
    total_international_articles = results_df['international_articles'].sum()
    
    print(f"\n=== 总体统计 ===")
    print(f"总国际合作文章数: {total_international_articles}")
    print(f"与欧盟国家合作文章数: {total_eu}")
    print(f"与非欧盟西方国家合作文章数: {total_non_eu_west}")
    print(f"与欧盟国家合作比率: {total_eu/total_international_articles:.3f}")
    print(f"与非欧盟西方国家合作比率: {total_non_eu_west/total_international_articles:.3f}")
    print(f"合作比率差值 (欧盟 - 非欧盟西方): {(total_eu/total_international_articles) - (total_non_eu_west/total_international_articles):.3f}")
    
    return results_df

def plot_country_cooperation_ratios(analyze_country_file, analyze_country, analyze_data_dir):
    """
    绘制特定国家的合作比例图表
    参数:
    - analyze_country_file: 数据文件夹名称
    - analyze_country: 国家名称
    - analyze_data_dir: 数据根目录
    """
    try:
        # 构建CSV文件路径
        csv_file_path = f'{analyze_data_dir}/networks_{analyze_country_file}/{analyze_country}_eu_non_eu_west_tile.csv'
        
        # 检查文件是否存在
        if not os.path.exists(csv_file_path):
            print(f"错误：找不到文件 {csv_file_path}")
            return None
        
        # 读取数据
        df = pd.read_csv(csv_file_path)
        
        # 设置英文字体
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 绘制三条线
        ax.plot(df['year'], df['eu_cooperation_ratio'], 
                marker='o', linewidth=2, markersize=6, 
                label='EU Cooperation Ratio', color='#2E8B57')
        
        ax.plot(df['year'], df['non_eu_west_cooperation_ratio'], 
                marker='s', linewidth=2, markersize=6, 
                label='Non-EU West Cooperation Ratio', color='#4169E1')
        
        ax.plot(df['year'], df['ratio_difference'], 
                marker='^', linewidth=2, markersize=6, 
                label='Ratio Difference (EU - Non-EU West)', color='#DC143C')
        
        # 添加Brexit参考线
        ax.axvline(x=2016, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(2016.2, ax.get_ylim()[1]*0.98, 'Brexit Vote (2016)', 
                fontsize=10, color='red', alpha=0.8)
        
        # 设置图表属性
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cooperation Ratio', fontsize=12, fontweight='bold')
        ax.set_title(f'{analyze_country.upper()} International Cooperation Ratios Over Time', 
                    fontsize=14, fontweight='bold')
        
        # 设置网格
        ax.grid(True, alpha=0.3)
        
        # 设置图例
        ax.legend(loc='best', fontsize=10)
        
        # 设置x轴刻度
        ax.set_xticks(df['year'])
        ax.tick_params(axis='x', rotation=45)
        
        # 调整布局
        plt.tight_layout()
        
        # 生成输出文件名
        plot_filename = f'{analyze_country}_eu_non_eu_west_tile_cooperation_ratios.png'
        plot_path = os.path.join(analyze_data_dir, 'networks_' + analyze_country_file, plot_filename)
        
        # 保存图表
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"{analyze_country.upper()}合作比例图表已保存到: {plot_path}")
        
        # 显示图表
        plt.show()
        
        return plot_path
        
    except Exception as e:
        print(f"绘制{analyze_country}合作比例图表时出错: {str(e)}")
        return None

if __name__ == "__main__":
    # 定义国家列表
    eu_countries = ['AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
    'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 'SPAIN', 'SWEDEN']

    non_eu_west_countries = ['UNITED STATES', 'CANADA', 'AUSTRALIA', 'NEW ZEALAND']

    # 设置分析参数
    analyze_data_dir = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related'
    analyze_country_file = 'uk'
    analyze_country = 'uk'
    
    # analyze_country_file = 'countrol_countries_brexit'
    # analyze_country = 'iceland'
    # analyze_country = 'japan'
    # analyze_country = 'singapore'
    # analyze_country = 'norway'
    # analyze_country = 'south-korea'
    
    
    # 运行分析
    # networks_data_dir = f'{analyze_data_dir}/networks_{analyze_country_file}/{analyze_country}_articles.csv'
    # output_file = f'{analyze_data_dir}/networks_{analyze_country_file}/{analyze_country}_eu_non_eu_west_tile.csv'
    # print(f"开始分析{analyze_country}与欧盟国家和非欧盟西方国家的合作情况...")
    # results_df = analyze_brexit_tile_index(networks_data_dir, output_file, eu_countries, non_eu_west_countries)


    
    # 绘制合作比例图表
    print(f"\n开始绘制{analyze_country}的合作比例图表...")
    plot_path = plot_country_cooperation_ratios(analyze_country_file, analyze_country, analyze_data_dir)
    if plot_path:
        print(f"图表绘制完成！")