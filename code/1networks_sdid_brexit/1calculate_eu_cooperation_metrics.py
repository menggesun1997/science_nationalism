import pandas as pd
import os
import glob
import matplotlib.pyplot as plt

def calculate_eu_cooperation_metrics():
    """
    计算EU国家每年的合作指标：
    1. EU国家与英国的合作论文数量
    2. EU国家与non-EU核心国家的合作数量
    3. 每年的总国际合作数据
    4. 计算比例：uk_num/total_international_num, non_eu_core/total_international_num
    """
    
    # 定义国家列表
    eu_countries = [
        'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
        'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
        'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
        'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
        'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
        'SPAIN', 'SWEDEN'
    ]
    
    uk_country = 'UNITED KINGDOM'
    non_eu_core_countries = ['UNITED STATES', 'CANADA', 'AUSTRALIA', 'NEW ZEALAND']
    
    # 设置文件路径
    data_dir = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_eu'
    output_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_eu/eu_uk_non_eu_west_tile.csv'
    
    print("开始计算EU合作指标...")
    
    # 获取所有年份的数据文件
    pattern = os.path.join(data_dir, 'eu_international_cooperation_*.csv')
    files = glob.glob(pattern)
    
    if not files:
        print("未找到数据文件！")
        return None
    
    # 按年份排序
    files.sort()
    print(f"找到 {len(files)} 个年份的数据文件")
    
    # 存储每年的指标
    yearly_metrics = []
    
    for file_path in files:
        # 从文件名提取年份
        filename = os.path.basename(file_path)
        year = filename.replace('eu_international_cooperation_', '').replace('.csv', '')
        
        print(f"正在处理 {year} 年的数据...")
        
        try:
            # 读取该年份的数据
            df = pd.read_csv(file_path, encoding='utf-8')
            
            if len(df) == 0:
                print(f"  - {year} 年没有数据")
                continue
            
            # 初始化计数器
            uk_cooperation_count = 0
            non_eu_core_cooperation_count = 0
            total_international_count = len(df)
            
            # 遍历每行数据
            for idx, row in df.iterrows():
                pays_str = str(row['Pays']).upper()
                countries = [c.strip() for c in pays_str.split(',') if c.strip()]
                
                # 检查是否包含EU国家
                has_eu = any(country in [c.upper() for c in eu_countries] for country in countries)
                
                if has_eu:
                    # 检查与英国的合作
                    if uk_country in countries:
                        uk_cooperation_count += 1
                    
                    # 检查与non-EU核心国家的合作
                    if any(country in [c.upper() for c in non_eu_core_countries] for country in countries):
                        non_eu_core_cooperation_count += 1
            
            # 计算比例
            uk_ratio = uk_cooperation_count / total_international_count if total_international_count > 0 else 0
            non_eu_core_ratio = non_eu_core_cooperation_count / total_international_count if total_international_count > 0 else 0
            uk_non_eu_diff = uk_ratio - non_eu_core_ratio
            
            # 记录该年份的指标
            yearly_metrics.append({
                'Year': int(year),
                'Total_International_Papers': total_international_count,
                'UK_Cooperation_Count': uk_cooperation_count,
                'Non_EU_Core_Cooperation_Count': non_eu_core_cooperation_count,
                'UK_Ratio': round(uk_ratio, 4),
                'Non_EU_Core_Ratio': round(non_eu_core_ratio, 4),
                'UK_Non_EU_Core_Diff': round(uk_non_eu_diff, 4)
            })
            
            print(f"  - 总国际合作论文数: {total_international_count}")
            print(f"  - 与英国合作论文数: {uk_cooperation_count}")
            print(f"  - 与non-EU核心国家合作论文数: {non_eu_core_cooperation_count}")
            print(f"  - 英国合作比例: {uk_ratio:.2%}")
            print(f"  - non-EU核心国家合作比例: {non_eu_core_ratio:.2%}")
            print(f"  - UK与非EU核心国家比例差值: {uk_non_eu_diff:.4f}")
            
        except Exception as e:
            print(f"处理 {year} 年数据时出错: {str(e)}")
            continue
    
    # 转换为DataFrame并保存
    if yearly_metrics:
        metrics_df = pd.DataFrame(yearly_metrics)
        metrics_df = metrics_df.sort_values('Year')
        
        # 保存结果
        metrics_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n指标计算完成！")
        print(f"结果已保存到: {output_file}")
        
        # 显示汇总统计
        print("\n年度汇总统计:")
        print(metrics_df.to_string(index=False))
        
        # 计算总体趋势
        print(f"\n总体趋势分析:")
        print(f"英国合作比例变化: {metrics_df['UK_Ratio'].min():.2%} - {metrics_df['UK_Ratio'].max():.2%}")
        print(f"non-EU核心国家合作比例变化: {metrics_df['Non_EU_Core_Ratio'].min():.2%} - {metrics_df['Non_EU_Core_Ratio'].max():.2%}")
        print(f"UK与非EU核心国家比例差值变化: {metrics_df['UK_Non_EU_Core_Diff'].min():.4f} - {metrics_df['UK_Non_EU_Core_Diff'].max():.4f}")
        
        return metrics_df
    else:
        print("没有成功处理任何年份的数据")
        return None

def plot_eu_cooperation_ratios(csv_file_path):
    """
    读取EU合作指标CSV文件并绘制三个比例指标的图表
    """
    try:
        # 读取数据
        df = pd.read_csv(csv_file_path)
        
        # 设置英文字体
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 绘制三条线
        ax.plot(df['Year'], df['UK_Ratio'], 
                marker='o', linewidth=2, markersize=6, 
                label='UK Cooperation Ratio', color='#2E8B57')
        
        ax.plot(df['Year'], df['Non_EU_Core_Ratio'], 
                marker='s', linewidth=2, markersize=6, 
                label='Non-EU Core Cooperation Ratio', color='#4169E1')
        
        ax.plot(df['Year'], df['UK_Non_EU_Core_Diff'], 
                marker='^', linewidth=2, markersize=6, 
                label='UK - Non-EU Core Difference', color='#DC143C')
        
        # 添加Brexit参考线
        ax.axvline(x=2016, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(2016.2, ax.get_ylim()[1]*0.95, 'Brexit Vote (2016)', 
                fontsize=10, color='red', alpha=0.8)
        
        # 设置图表属性
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cooperation Ratio', fontsize=12, fontweight='bold')
        ax.set_title('EU International Cooperation Ratios Over Time', fontsize=14, fontweight='bold')
        
        # 设置网格
        ax.grid(True, alpha=0.3)
        
        # 设置图例
        ax.legend(loc='best', fontsize=10)
        
        # 设置x轴刻度
        ax.set_xticks(df['Year'])
        ax.tick_params(axis='x', rotation=45)
        
        # 调整布局
        plt.tight_layout()
        
        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(csv_file_path))[0]
        plot_filename = f'{base_name}_cooperation_ratios.png'
        plot_dir = os.path.dirname(csv_file_path)
        plot_path = os.path.join(plot_dir, plot_filename)
        
        # 保存图表
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"EU合作比例图表已保存到: {plot_path}")
        
        # 显示图表
        plt.show()
        
        return plot_path
        
    except Exception as e:
        print(f"绘制图表时出错: {str(e)}")
        return None

 

if __name__ == "__main__":
    # 计算合作指标
    # metrics = calculate_eu_cooperation_metrics()
    
    # 绘制合作比例图表
    output_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/experimental_data/Data/experimental_data/cooperation_related/networks_eu/eu_uk_non_eu_west_tile.csv'
    print(f"\n开始绘制EU合作比例图表...")
    plot_path = plot_eu_cooperation_ratios(output_file)
    if plot_path:
        print(f"图表绘制完成！")
    

