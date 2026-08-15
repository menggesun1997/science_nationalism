
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict, Counter

def analyze_eu_top10_cooperation():
    """
    分析欧盟与top10国家的国际合作比例变化
    将欧盟作为一个整体，只要与欧盟中的任意一个国家合作就算是国际合作
    """
    # 欧盟国家列表（EU-27，不包括英国）
    eu_countries = [
        'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
        'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
        'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
        'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
        'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
        'SPAIN', 'SWEDEN'
    ]
    eu_countries_set = set(eu_countries)
    
    # 设置文件路径
    data_file = str(CODE / "0raw_publiations_process/eu_articles/eu_articles.txt")
    output_file = str(CODE / "0raw_publiations_process/eu_articles/eu_top10_cooperation_analysis.csv")
    
    print("开始分析欧盟与top10国家的国际合作...")
    
    try:
        # 读取数据
        df = pd.read_csv(data_file)
        print(f"成功读取数据，共 {len(df)} 行")
        print(f"列名: {list(df.columns)}")
        
        # 检查并重命名列（根据实际文件格式）
        if 'Annee_Bibliographique' in df.columns:
            df = df.rename(columns={'Annee_Bibliographique': 'year'})
        elif 'year' not in df.columns:
            print("警告: 未找到year列，请检查数据格式")
        
        # 过滤掉没有国家信息的行
        df = df.dropna(subset=['countries'])
        print(f"过滤后数据行数: {len(df)}")
        
        # 解析国家列表（处理引号和逗号分隔）
        def parse_countries(country_str):
            """解析国家字符串，处理引号和逗号"""
            if pd.isna(country_str):
                return []
            # 移除引号
            country_str = str(country_str).strip().strip('"').strip("'")
            # 按逗号分割并清理
            countries = [c.strip() for c in country_str.split(',') if c.strip()]
            return list(set(countries))  # 去重
        
        df['country_list'] = df['countries'].apply(parse_countries)
        
        # 检查是否包含欧盟国家，且是国际合作文章（包含多个国家）
        df['has_eu'] = df['country_list'].apply(lambda x: any(c in eu_countries_set for c in x))
        df['is_international'] = df['country_list'].apply(lambda x: len(x) > 1)
        
        # 数据统计信息
        total_articles = len(df)
        international_articles = df['is_international'].sum()
        single_country_articles = total_articles - international_articles
        articles_with_eu = df['has_eu'].sum()
        eu_international_articles = df[(df['has_eu']) & (df['is_international'])].shape[0]
        
        print(f"\n数据统计:")
        print(f"  总文章数: {total_articles:,}")
        print(f"  - 国际合作文章（多国）: {international_articles:,} ({international_articles/total_articles*100:.1f}%)")
        print(f"  - 单国文章: {single_country_articles:,} ({single_country_articles/total_articles*100:.1f}%)")
        print(f"  包含EU国家的文章: {articles_with_eu:,} ({articles_with_eu/total_articles*100:.1f}%)")
        print(f"  包含EU国家的国际合作文章: {eu_international_articles:,} ({eu_international_articles/total_articles*100:.1f}%)")
        
        # 只分析包含欧盟国家的国际合作文章
        eu_international_df = df[(df['has_eu']) & (df['is_international'])].copy()
        print(f"\n用于分析的文章数: {len(eu_international_df):,}")
        
        # 统计每年与各国的合作情况
        yearly_cooperation = defaultdict(lambda: defaultdict(int))
        yearly_total = defaultdict(int)
        
        for idx, row in eu_international_df.iterrows():
            year = row['year']
            countries = row['country_list']
            
            # 统计与各国的合作（排除欧盟国家自己）
            yearly_total[year] += 1
            for country in countries:
                if country not in eu_countries_set:
                    yearly_cooperation[year][country] += 1
        
        # 计算top10国家（基于总合作次数，包括所有国家）
        all_countries = Counter()
        for year_data in yearly_cooperation.values():
            for country, count in year_data.items():
                all_countries[country] += count
        
        top10_countries = [country for country, count in all_countries.most_common(10)]
        print(f"\nTop10合作国家（按总合作次数排序）:")
        for i, (country, count) in enumerate(all_countries.most_common(10), 1):
            print(f"  {i}. {country}: {count} 次")
        
        # 计算每年的合作比例
        results = []
        years = sorted(yearly_total.keys())
        
        for year in years:
            total_articles = yearly_total[year]
            year_data = {'year': year, 'total_articles': total_articles}
            
            for country in top10_countries:
                cooperation_count = yearly_cooperation[year].get(country, 0)
                cooperation_ratio = cooperation_count / total_articles if total_articles > 0 else 0
                year_data[f'{country}_count'] = cooperation_count
                year_data[f'{country}_ratio'] = cooperation_ratio
            
            results.append(year_data)
        
        # 创建结果DataFrame
        results_df = pd.DataFrame(results)
        
        # 保存结果
        results_df.to_csv(output_file, index=False)
        print(f"结果已保存到: {output_file}")
        
        # 设置横坐标刻度（整数年，每两年间隔一次）
        min_year = int(min(years))
        max_year = int(max(years))
        # 生成每两年间隔的年份列表（从最小年份开始，每隔一年）
        year_ticks = list(range(min_year, max_year + 1, 2))
        # 如果最大年份不在列表中，添加它
        if max_year not in year_ticks:
            year_ticks.append(max_year)
        year_ticks = sorted(year_ticks)
        
        # 绘制图表 - 分成三个独立的图
        # 图1：合作比例变化
        plt.figure(figsize=(14, 8))
        colors = plt.cm.tab10(np.linspace(0, 1, len(top10_countries)))
        
        for i, country in enumerate(top10_countries):
            plt.plot(results_df['year'], results_df[f'{country}_ratio'], 
                    marker='o', label=country, linewidth=2, color=colors[i])
        
        plt.title('EU International Cooperation Ratio with Top10 Countries', fontsize=16, fontweight='bold')
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Cooperation Ratio', fontsize=12)
        plt.xticks(year_ticks, [int(y) for y in year_ticks])  # 设置横坐标刻度为整数年，每两年间隔
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存合作比例图表
        ratio_chart_file = output_file.replace('.csv', '_ratio_chart.png')
        plt.savefig(ratio_chart_file, dpi=300, bbox_inches='tight')
        print(f"合作比例图表已保存到: {ratio_chart_file}")
        plt.close()
        
        # 图2：合作数量变化
        plt.figure(figsize=(14, 8))
        
        for i, country in enumerate(top10_countries):
            plt.plot(results_df['year'], results_df[f'{country}_count'], 
                    marker='s', label=country, linewidth=2, color=colors[i])
        
        plt.title('EU International Cooperation Count with Top10 Countries', fontsize=16, fontweight='bold')
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Number of Cooperation Articles', fontsize=12)
        plt.xticks(year_ticks, [int(y) for y in year_ticks])  # 设置横坐标刻度为整数年，每两年间隔
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存合作数量图表
        count_chart_file = output_file.replace('.csv', '_count_chart.png')
        plt.savefig(count_chart_file, dpi=300, bbox_inches='tight')
        print(f"合作数量图表已保存到: {count_chart_file}")
        plt.close()
        
        # 图3：堆叠面积图显示比例变化
        plt.figure(figsize=(14, 8))
        
        # 准备堆叠数据
        ratio_data = []
        for country in top10_countries:
            ratio_data.append(results_df[f'{country}_ratio'].values)
        
        plt.stackplot(results_df['year'], *ratio_data, labels=top10_countries, alpha=0.7)
        plt.title('EU International Cooperation Ratio Distribution', fontsize=16, fontweight='bold')
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Cumulative Cooperation Ratio', fontsize=12)
        plt.xticks(year_ticks, [int(y) for y in year_ticks])  # 设置横坐标刻度为整数年，每两年间隔
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # 保存堆叠面积图
        stacked_chart_file = output_file.replace('.csv', '_stacked_chart.png')
        plt.savefig(stacked_chart_file, dpi=300, bbox_inches='tight')
        print(f"堆叠面积图已保存到: {stacked_chart_file}")
        plt.close()
        
        # 显示统计信息
        print(f"\n统计摘要:")
        print(f"分析年份范围: {min(years)} - {max(years)}")
        print(f"总国际合作文章数: {sum(yearly_total.values())}")
        
        print(f"\nTop10国家总合作次数:")
        for country in top10_countries:
            total_count = sum(results_df[f'{country}_count'])
            avg_ratio = results_df[f'{country}_ratio'].mean()
            print(f"{country}: {total_count} 次合作, 平均比例: {avg_ratio:.4f}")
        
        # 计算Brexit前后的变化
        brexit_year = 2016
        pre_brexit = results_df[results_df['year'] <= brexit_year]
        post_brexit = results_df[results_df['year'] > brexit_year]
        
        print(f"\nBrexit前后变化分析 (2016年为分界点):")
        for country in top10_countries:
            pre_avg = pre_brexit[f'{country}_ratio'].mean()
            post_avg = post_brexit[f'{country}_ratio'].mean()
            change = post_avg - pre_avg
            change_pct = (change / pre_avg) * 100 if pre_avg > 0 else 0
            print(f"{country}: {pre_avg:.4f} → {post_avg:.4f} (变化: {change:+.4f}, {change_pct:+.1f}%)")
        
        return results_df
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = analyze_eu_top10_cooperation()
