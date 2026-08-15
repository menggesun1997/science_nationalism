import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from collections import defaultdict

def analyze_uk_regional_cooperation():
    """
    分析英国与不同地区的国际合作比例
    计算：EU、五眼联盟、中国、世界其他地区的合作比例
    """
    
    # 定义地区国家列表
    eu_countries = [
        'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
        'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
        'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
        'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
        'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
        'SPAIN', 'SWEDEN'
    ]
    
    five_eyes_countries = ['UNITED STATES', 'CANADA', 'AUSTRALIA', 'NEW ZEALAND']
    china_country = ['CHINA']
    
    # 设置文件路径
    data_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_uk/uk_articles.csv'
    output_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_uk/uk_regional_cooperation.csv'
    
    print("开始分析英国与不同地区的国际合作...")
    
    try:
        # 读取数据
        df = pd.read_csv(data_file)
        print(f"成功读取数据，共 {len(df)} 行")
        
        # 重命名列
        df.columns = ['article_id', 'year', 'discipline', 'countries']
        
        # 初始化年度统计
        yearly_stats = defaultdict(lambda: {
            'total_international': 0,
            'complex_multi_bloc': 0,
            'eu_cooperation': 0,
            'five_eyes_cooperation': 0,
            'china_cooperation': 0,
            'rest_of_world_only': 0
        })
        
        print("正在分析合作数据...")
        
        # 遍历每一行数据
        for idx, row in df.iterrows():
            year = row['year']
            countries_str = str(row['countries'])
            
            # 跳过没有国家信息的行
            if pd.isna(countries_str) or countries_str == 'nan':
                continue
                
            # 将国家字符串分割成列表并去重
            countries = list(set([country.strip() for country in countries_str.split(',')]))
            
            # 检查是否为国际合作文章（包含多个国家）
            if len(countries) <= 1:
                continue  # 跳过非国际合作文章
            
            # 统计该文章中的合作情况（按新的分类逻辑）
            # 检查每个国家属于哪个阵营
            has_eu = False
            has_five_eyes = False
            has_china = False
            has_rest_of_world = False
            
            for country in countries:
                country_clean = country.strip().upper()
                
                # 跳过英国本身
                if country_clean == 'UNITED KINGDOM':
                    continue
                
                # 检查是否为欧盟国家
                if any(eu_country.upper() in country_clean or country_clean in eu_country.upper() 
                       for eu_country in eu_countries):
                    has_eu = True
                    
                # 检查是否为五眼联盟国家
                elif any(five_eyes_country.upper() in country_clean or country_clean in five_eyes_country.upper() 
                         for five_eyes_country in five_eyes_countries):
                    has_five_eyes = True
                    
                # 检查是否为中国
                elif any(china_country_name.upper() in country_clean or country_clean in china_country_name.upper() 
                         for china_country_name in china_country):
                    has_china = True
                    
                # 其他地区
                else:
                    has_rest_of_world = True
            
            # 检查是否真的有国际合作
            has_any_international = has_eu or has_five_eyes or has_china or has_rest_of_world
            
            if has_any_international:
                # 按照新的分类逻辑进行分类
                yearly_stats[year]['total_international'] += 1
                
                # 1. 复杂多边合作：英国与主要阵营中至少两个合作
                if sum([has_eu, has_five_eyes, has_china]) >= 2:
                    yearly_stats[year]['complex_multi_bloc'] += 1
                # 2. 如果不复杂，再检查是否包含“欧盟”
                elif has_eu:
                    yearly_stats[year]['eu_cooperation'] += 1
                # 3. 如果不复杂且不含欧盟，再检查是否包含“五眼联盟”
                elif has_five_eyes:
                    yearly_stats[year]['five_eyes_cooperation'] += 1
                # 4. 如果不满足以上所有条件，再检查是否包含“中国”
                elif has_china:
                    yearly_stats[year]['china_cooperation'] += 1
                # 5. 仅与世界其他地区合作（没有任何作者来自主要阵营）
                else:
                    yearly_stats[year]['rest_of_world_only'] += 1
        
        # 转换为DataFrame并计算比例
        results = []
        for year in sorted(yearly_stats.keys()):
            stats = yearly_stats[year]
            total = stats['total_international']
            
            if total > 0:
                complex_multi_bloc_ratio = stats['complex_multi_bloc'] / total
                eu_cooperation_ratio = stats['eu_cooperation'] / total
                five_eyes_cooperation_ratio = stats['five_eyes_cooperation'] / total
                china_cooperation_ratio = stats['china_cooperation'] / total
                rest_of_world_only_ratio = stats['rest_of_world_only'] / total
            else:
                complex_multi_bloc_ratio = eu_cooperation_ratio = five_eyes_cooperation_ratio = china_cooperation_ratio = rest_of_world_only_ratio = 0
                
            results.append({
                'year': year,
                'total_international': total,
                'complex_multi_bloc_count': stats['complex_multi_bloc'],
                'eu_cooperation_count': stats['eu_cooperation'],
                'five_eyes_cooperation_count': stats['five_eyes_cooperation'],
                'china_cooperation_count': stats['china_cooperation'],
                'rest_of_world_only_count': stats['rest_of_world_only'],
                'complex_multi_bloc_ratio': complex_multi_bloc_ratio,
                'eu_cooperation_ratio': eu_cooperation_ratio,
                'five_eyes_cooperation_ratio': five_eyes_cooperation_ratio,
                'china_cooperation_ratio': china_cooperation_ratio,
                'rest_of_world_only_ratio': rest_of_world_only_ratio
            })
        
        # 创建结果DataFrame
        results_df = pd.DataFrame(results)
        
        # 保存结果
        results_df.to_csv(output_file, index=False)
        print(f"分析结果已保存到: {output_file}")
        
        # 显示结果摘要
        print("\n=== 英国地区合作分析结果摘要 ===")
        print(results_df.to_string(index=False))
        
        return results_df
        
    except Exception as e:
        print(f"分析过程中出现错误: {str(e)}")
        return None

def plot_uk_regional_cooperation_stacked_area(csv_file_path):
    """
    绘制英国与不同地区合作的堆叠面积图
    """
    try:
        # 读取数据
        df = pd.read_csv(csv_file_path)
        
        # 设置英文字体
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 准备数据
        years = df['year']
        complex_multi_bloc_ratio = df['complex_multi_bloc_ratio']
        eu_cooperation_ratio = df['eu_cooperation_ratio']
        five_eyes_cooperation_ratio = df['five_eyes_cooperation_ratio']
        china_cooperation_ratio = df['china_cooperation_ratio']
        rest_of_world_only_ratio = df['rest_of_world_only_ratio']
        
        # 绘制堆叠面积图
        ax.fill_between(years, 0, complex_multi_bloc_ratio, 
                       label='Complex Multi-bloc Cooperation', color='#FF6B6B', alpha=0.8)
        
        ax.fill_between(years, complex_multi_bloc_ratio, 
                       complex_multi_bloc_ratio + eu_cooperation_ratio, 
                       label='EU Cooperation', color='#2E8B57', alpha=0.8)
        
        ax.fill_between(years, complex_multi_bloc_ratio + eu_cooperation_ratio, 
                       complex_multi_bloc_ratio + eu_cooperation_ratio + five_eyes_cooperation_ratio, 
                       label='Five Eyes Cooperation', color='#4169E1', alpha=0.8)
        
        ax.fill_between(years, complex_multi_bloc_ratio + eu_cooperation_ratio + five_eyes_cooperation_ratio, 
                       complex_multi_bloc_ratio + eu_cooperation_ratio + five_eyes_cooperation_ratio + china_cooperation_ratio, 
                       label='China Cooperation', color='#FF6347', alpha=0.8)
        
        ax.fill_between(years, complex_multi_bloc_ratio + eu_cooperation_ratio + five_eyes_cooperation_ratio + china_cooperation_ratio, 
                       complex_multi_bloc_ratio + eu_cooperation_ratio + five_eyes_cooperation_ratio + china_cooperation_ratio + rest_of_world_only_ratio, 
                       label='Rest of World-only Cooperation', color='#9370DB', alpha=0.8)
        
        # 添加Brexit参考线
        ax.axvline(x=2016, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(2016.2, ax.get_ylim()[1]*0.98, 'Brexit Vote (2016)', 
                fontsize=10, color='red', alpha=0.8)
        
        # 设置图表属性
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cooperation Ratio', fontsize=12, fontweight='bold')
        ax.set_title('UK International Cooperation Patterns (Stacked Area Chart)', 
                    fontsize=14, fontweight='bold')
        
        # 设置网格
        ax.grid(True, alpha=0.3)
        
        # 设置图例
        ax.legend(loc='upper left', fontsize=10)
        
        # 设置x轴刻度
        ax.set_xticks(years)
        ax.tick_params(axis='x', rotation=45)
        
        # 设置y轴范围
        ax.set_ylim(0, 1)
        
        # 调整布局
        plt.tight_layout()
        
        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(csv_file_path))[0]
        plot_filename = f'{base_name}_stacked_area_chart.png'
        plot_dir = os.path.dirname(csv_file_path)
        plot_path = os.path.join(plot_dir, plot_filename)
        
        # 保存图表
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"英国地区合作堆叠面积图已保存到: {plot_path}")
        
        # 显示图表
        plt.show()
        
        return plot_path
        
    except Exception as e:
        print(f"绘制堆叠面积图时出错: {str(e)}")
        return None

def plot_uk_regional_cooperation_line_chart(csv_file_path):
    """
    绘制英国与不同地区合作的折线图（多条线叠加）
    """
    try:
        # 读取数据
        df = pd.read_csv(csv_file_path)
        
        # 设置英文字体
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 准备数据
        years = df['year']
        
        # 计算各地区的合作比率（包括复杂多边合作中的部分）
        # 这里我们需要重新计算，因为原始数据是按互斥分类的
        # 我们需要计算每篇文章中实际包含的各地区合作比例
        
        # 读取原始数据重新计算
        data_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_uk/uk_articles.csv'
        df_raw = pd.read_csv(data_file)
        df_raw.columns = ['article_id', 'year', 'discipline', 'countries']
        
        # 定义地区国家列表
        eu_countries = [
            'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
            'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
            'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
            'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
            'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
            'SPAIN', 'SWEDEN'
        ]
        
        five_eyes_countries = ['UNITED STATES', 'CANADA', 'AUSTRALIA', 'NEW ZEALAND']
        china_country = ['CHINA']
        
        # 按年份统计各地区合作比例
        yearly_ratios = defaultdict(lambda: {
            'total_international': 0,
            'eu_papers': 0,
            'five_eyes_papers': 0,
            'china_papers': 0,
            'rest_of_world_papers': 0
        })
        
        for idx, row in df_raw.iterrows():
            year = row['year']
            countries_str = str(row['countries'])
            
            if pd.isna(countries_str) or countries_str == 'nan':
                continue
                
            countries = [country.strip() for country in countries_str.split(',')]
            
            if len(countries) <= 1:
                continue
            
            # 检查是否包含各地区
            has_eu = any(any(eu_country.upper() in country.upper() or country.upper() in eu_country.upper() 
                             for eu_country in eu_countries) for country in countries if country.upper() != 'UNITED KINGDOM')
            has_five_eyes = any(any(five_eyes_country.upper() in country.upper() or country.upper() in five_eyes_country.upper() 
                                   for five_eyes_country in five_eyes_countries) for country in countries if country.upper() != 'UNITED KINGDOM')
            has_china = any(any(china_country_name.upper() in country.upper() or country.upper() in china_country_name.upper() 
                               for china_country_name in china_country) for country in countries if country.upper() != 'UNITED KINGDOM')
            has_rest_of_world = any(country.upper() not in [c.upper() for c in eu_countries + five_eyes_countries + china_country] 
                                   and country.upper() != 'UNITED KINGDOM' for country in countries)
            
            # 检查是否真的有国际合作
            has_any_international = has_eu or has_five_eyes or has_china or has_rest_of_world
            
            if has_any_international:
                yearly_ratios[year]['total_international'] += 1
                
                if has_eu:
                    yearly_ratios[year]['eu_papers'] += 1
                if has_five_eyes:
                    yearly_ratios[year]['five_eyes_papers'] += 1
                if has_china:
                    yearly_ratios[year]['china_papers'] += 1
                if has_rest_of_world:
                    yearly_ratios[year]['rest_of_world_papers'] += 1
        
        # 计算比例
        line_data = []
        for year in sorted(yearly_ratios.keys()):
            stats = yearly_ratios[year]
            total = stats['total_international']
            
            if total > 0:
                eu_ratio = stats['eu_papers'] / total
                five_eyes_ratio = stats['five_eyes_papers'] / total
                china_ratio = stats['china_papers'] / total
                rest_of_world_ratio = stats['rest_of_world_papers'] / total
            else:
                eu_ratio = five_eyes_ratio = china_ratio = rest_of_world_ratio = 0
            
            line_data.append({
                'year': year,
                'eu_ratio': eu_ratio,
                'five_eyes_ratio': five_eyes_ratio,
                'china_ratio': china_ratio,
                'rest_of_world_ratio': rest_of_world_ratio
            })
        
        line_df = pd.DataFrame(line_data)
        
        # 绘制折线图
        ax.plot(line_df['year'], line_df['eu_ratio'], 
                marker='o', linewidth=2.5, markersize=6, 
                label='EU Cooperation Ratio', color='#2E8B57')
        
        ax.plot(line_df['year'], line_df['five_eyes_ratio'], 
                marker='s', linewidth=2.5, markersize=6, 
                label='Five Eyes Cooperation Ratio', color='#4169E1')
        
        ax.plot(line_df['year'], line_df['china_ratio'], 
                marker='^', linewidth=2.5, markersize=6, 
                label='China Cooperation Ratio', color='#FF6347')
        
        ax.plot(line_df['year'], line_df['rest_of_world_ratio'], 
                marker='d', linewidth=2.5, markersize=6, 
                label='Rest of World Cooperation Ratio', color='#9370DB')
        
        # 添加Brexit参考线
        ax.axvline(x=2016, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(2016.2, ax.get_ylim()[1]*0.98, 'Brexit Vote (2016)', 
                fontsize=10, color='red', alpha=0.8)
        
        # 设置图表属性
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cooperation Ratio', fontsize=12, fontweight='bold')
        ax.set_title('UK International Cooperation Ratios by Region (Line Chart)', 
                    fontsize=14, fontweight='bold')
        
        # 设置网格
        ax.grid(True, alpha=0.3)
        
        # 设置图例
        ax.legend(loc='best', fontsize=10)
        
        # 设置x轴刻度
        ax.set_xticks(line_df['year'])
        ax.tick_params(axis='x', rotation=45)
        
        # 设置y轴范围
        ax.set_ylim(0, None)
        
        # 调整布局
        plt.tight_layout()
        
        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(csv_file_path))[0]
        plot_filename = f'{base_name}_line_chart.png'
        plot_dir = os.path.dirname(csv_file_path)
        plot_path = os.path.join(plot_dir, plot_filename)
        
        # 保存图表
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"英国地区合作折线图已保存到: {plot_path}")
        
        # 显示图表
        plt.show()
        
        return plot_path
        
    except Exception as e:
        print(f"绘制折线图时出错: {str(e)}")
        return None

def plot_uk_specific_groups_line_chart():
    """
    绘制英国与特定群体合作的折线图
    群体包括：Major Commonwealth Partners, Key Asian R&D Powers, Major European Non-EU Partners
    """
    try:
        # 定义特定群体国家列表
        major_commonwealth_partners = ['INDIA', 'SOUTH AFRICA', 'SINGAPORE', 'MALAYSIA', 'NIGERIA']
        key_asian_rd_powers = ['JAPAN', 'SOUTH-KOREA', 'TAIWAN', 'SINGAPORE']
        china_country = ['CHINA']
        major_european_non_eu_partners = ['SWITZERLAND', 'NORWAY', 'ISRAEL', 'TURKIYE']
        BRICS_Nations = ['INDIA', 'SOUTH AFRICA', 'BRAZIL', 'RUSSIA']
        
        # 设置文件路径
        data_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_uk/uk_articles.csv'
        output_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_uk/uk_specific_groups_cooperation.csv'
        
        print("开始分析英国与特定群体的国际合作...")
        
        # 读取数据
        df = pd.read_csv(data_file)
        print(f"成功读取数据，共 {len(df)} 行")
        
        # 重命名列
        df.columns = ['article_id', 'year', 'discipline', 'countries']
        
        # 初始化年度统计
        yearly_stats = defaultdict(lambda: {
            'total_international': 0,
            'commonwealth_papers': 0,
            'asian_rd_papers': 0,
            'china_papers': 0,
            'european_non_eu_papers': 0,
            'brics_papers': 0
        })
        
        print("正在分析合作数据...")
        
        # 遍历每一行数据
        for idx, row in df.iterrows():
            year = row['year']
            countries_str = str(row['countries'])
            
            # 跳过没有国家信息的行
            if pd.isna(countries_str) or countries_str == 'nan':
                continue
                
            # 将国家字符串分割成列表并去重
            countries = list(set([country.strip() for country in countries_str.split(',')]))
            
            # 检查是否为国际合作文章（包含多个国家）
            if len(countries) <= 1:
                continue  # 跳过非国际合作文章
            
            # 检查是否包含各群体
            has_commonwealth = False
            has_asian_rd = False
            has_china = False
            has_european_non_eu = False
            has_brics = False
            
            for country in countries:
                country_clean = country.strip().upper()
                
                # 跳过英国本身
                if country_clean == 'UNITED KINGDOM':
                    continue
                
                # 检查是否为Major Commonwealth Partners
                if any(commonwealth_country.upper() in country_clean or country_clean in commonwealth_country.upper() 
                       for commonwealth_country in major_commonwealth_partners):
                    has_commonwealth = True
                    
                # 检查是否为Key Asian R&D Powers
                if any(asian_country.upper() in country_clean or country_clean in asian_country.upper() 
                       for asian_country in key_asian_rd_powers):
                    has_asian_rd = True
                    
                # 检查是否为中国
                if any(china_country_name.upper() in country_clean or country_clean in china_country_name.upper() 
                       for china_country_name in china_country):
                    has_china = True
                    
                # 检查是否为Major European Non-EU Partners
                if any(european_country.upper() in country_clean or country_clean in european_country.upper() 
                       for european_country in major_european_non_eu_partners):
                    has_european_non_eu = True
                    
                # 检查是否为BRICS Nations
                if any(brics_country.upper() in country_clean or country_clean in brics_country.upper() 
                       for brics_country in BRICS_Nations):
                    has_brics = True
            
            # 检查是否真的有国际合作
            has_any_international = has_commonwealth or has_asian_rd or has_china or has_european_non_eu or has_brics
            
            if has_any_international:
                yearly_stats[year]['total_international'] += 1
                
                if has_commonwealth:
                    yearly_stats[year]['commonwealth_papers'] += 1
                if has_asian_rd:
                    yearly_stats[year]['asian_rd_papers'] += 1
                if has_china:
                    yearly_stats[year]['china_papers'] += 1
                if has_european_non_eu:
                    yearly_stats[year]['european_non_eu_papers'] += 1
                if has_brics:
                    yearly_stats[year]['brics_papers'] += 1
        
        # 转换为DataFrame并计算比例
        results = []
        for year in sorted(yearly_stats.keys()):
            stats = yearly_stats[year]
            total = stats['total_international']
            
            if total > 0:
                commonwealth_ratio = stats['commonwealth_papers'] / total
                asian_rd_ratio = stats['asian_rd_papers'] / total
                china_ratio = stats['china_papers'] / total
                european_non_eu_ratio = stats['european_non_eu_papers'] / total
                brics_ratio = stats['brics_papers'] / total
            else:
                commonwealth_ratio = asian_rd_ratio = china_ratio = european_non_eu_ratio = brics_ratio = 0
                
            results.append({
                'year': year,
                'total_international': total,
                'commonwealth_cooperation_count': stats['commonwealth_papers'],
                'asian_rd_cooperation_count': stats['asian_rd_papers'],
                'china_cooperation_count': stats['china_papers'],
                'european_non_eu_cooperation_count': stats['european_non_eu_papers'],
                'brics_cooperation_count': stats['brics_papers'],
                'commonwealth_cooperation_ratio': commonwealth_ratio,
                'asian_rd_cooperation_ratio': asian_rd_ratio,
                'china_cooperation_ratio': china_ratio,
                'european_non_eu_cooperation_ratio': european_non_eu_ratio,
                'brics_cooperation_ratio': brics_ratio
            })
        
        # 创建结果DataFrame
        results_df = pd.DataFrame(results)
        
        # 保存结果
        results_df.to_csv(output_file, index=False)
        print(f"分析结果已保存到: {output_file}")
        
        # 显示结果摘要
        print("\n=== 英国特定群体合作分析结果摘要 ===")
        print(results_df.to_string(index=False))
        
        # 设置英文字体
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 绘制折线图
        ax.plot(results_df['year'], results_df['commonwealth_cooperation_ratio'], 
                marker='o', linewidth=2.5, markersize=6, 
                label='Major Commonwealth Partners', color='#FF8C00')
        
        ax.plot(results_df['year'], results_df['asian_rd_cooperation_ratio'], 
                marker='s', linewidth=2.5, markersize=6, 
                label='Key Asian R&D Powers', color='#4ECDC4')
        
        ax.plot(results_df['year'], results_df['china_cooperation_ratio'], 
                marker='^', linewidth=2.5, markersize=6, 
                label='China', color='#FF6347')
        
        ax.plot(results_df['year'], results_df['european_non_eu_cooperation_ratio'], 
                marker='d', linewidth=2.5, markersize=6, 
                label='Major European Non-EU Partners', color='#45B7D1')
        
        ax.plot(results_df['year'], results_df['brics_cooperation_ratio'], 
                marker='v', linewidth=2.5, markersize=6, 
                label='BRICS Nations', color='#9370DB')
        
        # 添加Brexit参考线
        ax.axvline(x=2016, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(2016.2, ax.get_ylim()[1]*0.98, 'Brexit Vote (2016)', 
                fontsize=10, color='red', alpha=0.8)
        
        # 设置图表属性
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cooperation Ratio', fontsize=12, fontweight='bold')
        ax.set_title('UK International Cooperation with Specific Groups (Line Chart)', 
                    fontsize=14, fontweight='bold')
        
        # 设置网格
        ax.grid(True, alpha=0.3)
        
        # 设置图例
        ax.legend(loc='best', fontsize=10)
        
        # 设置x轴刻度
        ax.set_xticks(results_df['year'])
        ax.tick_params(axis='x', rotation=45)
        
        # 设置y轴范围
        ax.set_ylim(0, None)
        
        # 调整布局
        plt.tight_layout()
        
        # 生成输出文件名
        plot_filename = 'uk_specific_groups_cooperation_line_chart.png'
        plot_dir = os.path.dirname(output_file)
        plot_path = os.path.join(plot_dir, plot_filename)
        
        # 保存图表
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"英国特定群体合作折线图已保存到: {plot_path}")
        
        # 显示图表
        plt.show()
        
        return results_df, plot_path
        
    except Exception as e:
        print(f"分析过程中出现错误: {str(e)}")
        return None, None

if __name__ == "__main__":
    # 分析英国与不同地区的合作， 绘制堆叠面积图
    # print("开始分析英国与不同地区的国际合作...")
    # results_df = analyze_uk_regional_cooperation()
    # output_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_uk/uk_regional_cooperation.csv'
    # print(f"\n开始绘制英国地区合作堆叠面积图...")
    # plot_path = plot_uk_regional_cooperation_stacked_area(output_file)
    # if plot_path:
    #     print(f"堆叠面积图绘制完成！")
        
    # # 绘制折线图
    # print(f"\n开始绘制英国地区合作折线图...")
    # line_plot_path = plot_uk_regional_cooperation_line_chart(output_file)
    # if line_plot_path:
    #     print(f"折线图绘制完成！")
    
    # 分析英国与特定群体的合作
    print(f"\n开始分析英国与特定群体的国际合作...")
    specific_groups_df, specific_groups_plot = plot_uk_specific_groups_line_chart()
    if specific_groups_df is not None:
        print(f"特定群体合作分析完成！")
