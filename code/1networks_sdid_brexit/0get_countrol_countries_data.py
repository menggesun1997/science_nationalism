
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import pandas as pd
import os

# 数据文件路径
raw_data = str(LEGACY_BREXIT / "article_pays_list.txt")

# 控制国家列表
control_countries = ['BRAZIL','TURKIYE','SOUTH AFRICA','CHINA','MEXICO','INDIA']

# 输出目录
output_dir = str(LEGACY_BREXIT / "networks_countrol_countries_brexit")

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

def main():
    print("开始读取数据文件...")
    
    try:
        # 读取数据文件
        df = pd.read_csv(raw_data, sep='\t', encoding='utf-8')
        print(f"成功读取数据，共 {len(df)} 行")
        print(f"列名: {list(df.columns)}")
        
        # 检查Pays列是否存在
        if 'Pays' not in df.columns:
            print("错误：未找到Pays列")
            print(f"可用的列: {list(df.columns)}")
            return
        
        
        # 创建一个函数来检查一行数据是否包含任何control_country
        def contains_control_country(pays_str):
            if pd.isna(pays_str):
                return False
            pays_str = str(pays_str).upper()  # 转换为大写字符串
            return any(country.upper() in pays_str for country in control_countries)
        
        # 筛选出包含任何control_country的数据
        mask = df['Pays'].apply(contains_control_country)
        filtered_df = df[mask]
        print(f"筛选出 {len(filtered_df)} 行包含control_countries的数据")
        
        # 为每个control_country创建数据框
        country_dataframes = {}
        for country in control_countries:
            country_dataframes[country] = []
        
        # 遍历筛选后的数据，将每行分配给相应的国家
        for idx, row in filtered_df.iterrows():
            pays_str = str(row['Pays']).upper()
            for country in control_countries:
                if country.upper() in pays_str:
                    country_dataframes[country].append(row)
        
        # 保存每个国家的数据
        for country in control_countries:
            print(f"正在处理 {country} 的数据...")
            
            if country_dataframes[country]:
                # 将列表转换为DataFrame
                country_df = pd.DataFrame(country_dataframes[country])
                
                # 生成文件名（将空格替换为下划线）
                filename = country.replace(' ', '_').lower() + '_articles.csv'
                filepath = os.path.join(output_dir, filename)
                
                # 保存为CSV文件
                country_df.to_csv(filepath, index=False, encoding='utf-8')
                print(f"  - 保存了 {len(country_df)} 行数据到 {filename}")
            else:
                print(f"  - 警告：未找到 {country} 的数据")
        
        print("\n所有国家的数据处理完成！")
        
        # 显示每个国家的数据统计
        print("\n数据统计:")
        for country in control_countries:
            if country_dataframes[country]:
                print(f"{country}: {len(country_dataframes[country])} 行")
            else:
                print(f"{country}: 0 行")
            
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        print("请检查文件路径和格式是否正确")

if __name__ == "__main__":
    main()

