
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import List, Tuple, Dict
import networkx as nx
import numpy as np
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist, squareform
import warnings
warnings.filterwarnings('ignore')

PAPERS_FILE = str(CODE / "0raw_publiations_process/eu_articles/eu_articles.txt")
eu_countries = [
            'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
            'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
            'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
            'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
            'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
            'SPAIN', 'SWEDEN'
        ]

# 将 EU 国家列表转换为集合，便于快速查找
EU_COUNTRIES_SET = set(eu_countries)


def has_eu_country(countries_list: List[str]) -> bool:
    """
    判断国家列表中是否包含任意一个 EU 国家。
    """
    return bool(set(countries_list) & EU_COUNTRIES_SET)

# 定义时期
START_YEAR = 2010
END_YEAR = 2024
MIN_COLLABORATION_THRESHOLD = 50  # 最小连续合作数量阈值


def parse_countries(country_str):
    """
    解析国家字符串，提取所有国家
    处理可能的引号、逗号分隔等情况
    注意：需要处理国家名称中包含逗号的情况，如 "KOREA, REP." 和 "IRAN, ISLAMIC REP."
    """
    if pd.isna(country_str) or country_str == '' or str(country_str).upper() == 'NAN':
        return []
    
    # 转换为字符串并去除首尾空白
    countries_str = str(country_str).strip().upper()
    
    # 如果字符串以引号开始和结束，去除引号
    if countries_str.startswith('"') and countries_str.endswith('"'):
        countries_str = countries_str[1:-1]
    elif countries_str.startswith("'") and countries_str.endswith("'"):
        countries_str = countries_str[1:-1]
    
    # 智能分割：处理国家名称中包含逗号的情况
    # 已知包含逗号的国家名称后缀
    special_suffixes = ['REP.', 'ISLAMIC REP.', 'DEM. REP.']
    
    # 先按逗号分割
    parts = countries_str.split(',')
    countries = []
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        if not part:
            i += 1
            continue
        
        # 检查下一个部分是否是当前部分的后缀（如 ", REP." 或 ", ISLAMIC REP."）
        if i + 1 < len(parts):
            next_part = parts[i + 1].strip()
            # 如果下一个部分是特殊后缀，合并它们（保留空格）
            if next_part in special_suffixes:
                countries.append((part + ', ' + next_part).strip())
                i += 2
                continue
        
        countries.append(part)
        i += 1
    
    # 过滤空字符串和NAN
    countries = [c for c in countries if c and c != 'NAN' and c.strip() != '']
    
    return list(set(countries))  # 去重


def load_and_process_data():
    """加载并处理EU文章数据"""
    print("=" * 80)
    print("步骤1: 加载数据...")
    print("=" * 80)
    
    # 读取数据
    df = pd.read_csv(
        PAPERS_FILE,
        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'countries': str}
    )
    df.columns = ['article_id', 'year', 'countries']
    
    # 过滤缺失值并转换年份
    df = df.dropna(subset=['countries', 'year'])
    df['year'] = df['year'].astype(int)
    
    # 只保留2010-2024年的数据
    df = df[(df['year'] >= START_YEAR) & (df['year'] <= END_YEAR)].copy()
    
    print(f"数据形状: {df.shape}")
    print(f"年份范围: {df['year'].min()} - {df['year'].max()}")
    
    # 解析国家列表
    df['country_list'] = df['countries'].apply(parse_countries)
    
    # 只保留包含EU国家且是国际合作的文章
    df['has_eu'] = df['country_list'].apply(has_eu_country)
    df['is_international'] = df['country_list'].apply(lambda x: len(x) > 1)
    
    eu_international_df = df[(df['has_eu']) & (df['is_international'])].copy()
    print(f"包含EU国家的国际合作文章数: {len(eu_international_df)}")
    
    return eu_international_df


def build_collaboration_profiles(df):
    """构建EU与每个collaborator的合作profile"""
    print("\n" + "=" * 80)
    print("步骤2: 构建合作profile...")
    print("=" * 80)
    
    # 统计每年与各国的合作数量
    collaboration_counts = defaultdict(lambda: defaultdict(int))
    
    for _, row in df.iterrows():
        year = row['year']
        countries = row['country_list']
        
        # 找到所有与EU合作的国家（排除EU国家自己）
        for country in countries:
            if country not in EU_COUNTRIES_SET:
                collaboration_counts[country][year] += 1
    
    # 构建完整的profile矩阵
    years = list(range(START_YEAR, END_YEAR + 1))
    profiles = {}
    
    for country, year_counts in collaboration_counts.items():
        profile = [year_counts.get(year, 0) for year in years]
        profiles[country] = profile
    
    print(f"找到 {len(profiles)} 个合作国家")
    
    return profiles, years


def filter_countries_by_threshold(profiles, threshold=MIN_COLLABORATION_THRESHOLD, min_consecutive_years=3):
    """过滤小国家：只保留在至少连续min_consecutive_years年内合作数量都超过阈值的国家"""
    print("\n" + "=" * 80)
    print(f"步骤3: 过滤国家（阈值: {threshold}, 至少连续{min_consecutive_years}年）...")
    print("=" * 80)
    
    filtered_profiles = {}
    
    for country, profile in profiles.items():
        # 检查是否有至少连续min_consecutive_years年的合作数量都超过阈值
        max_consecutive = 0
        current_consecutive = 0
        
        for count in profile:
            if count >= threshold:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        # 如果最大连续合作年数达到要求，保留这个国家
        if max_consecutive >= min_consecutive_years:
            filtered_profiles[country] = profile
    
    print(f"过滤前: {len(profiles)} 个国家")
    print(f"过滤后: {len(filtered_profiles)} 个国家")
    
    # 打印被过滤掉的国家（前10个）
    excluded_countries = set(profiles.keys()) - set(filtered_profiles.keys())
    if excluded_countries:
        print(f"\n被过滤掉的国家示例（前10个）: {list(excluded_countries)[:10]}")
    
    return filtered_profiles


def normalize_profiles(profiles, years):
    """Normalize profile向量：用前三年平均值作为分母"""
    print("\n" + "=" * 80)
    print("步骤4: Normalize profile向量...")
    print("=" * 80)
    
    normalized_profiles = {}
    
    # 前三年是2010, 2011, 2012
    baseline_years = [2010, 2011, 2012]
    baseline_indices = [years.index(y) for y in baseline_years]
    
    baseline_avgs_dict = {}
    for country, profile in profiles.items():
        # 计算前三年平均值
        baseline_values = [profile[i] for i in baseline_indices]
        baseline_avg = np.mean(baseline_values) if baseline_values else 1.0
        
        # 避免除零
        if baseline_avg == 0:
            baseline_avg = 1.0
        
        baseline_avgs_dict[country] = baseline_avg
        
        # Normalize: 每年的值除以baseline平均值
        normalized_profile = [count / baseline_avg for count in profile]
        normalized_profiles[country] = normalized_profile
    
    # 打印统计信息
    baseline_avgs = list(baseline_avgs_dict.values())
    print(f"Normalized {len(normalized_profiles)} 个国家的profile")
    print(f"Baseline平均值统计: min={min(baseline_avgs):.2f}, "
          f"max={max(baseline_avgs):.2f}, mean={np.mean(baseline_avgs):.2f}")
    
    # 打印几个重要国家的信息
    important_countries = ['UNITED STATES', 'CHINA', 'UNITED KINGDOM', 
                          'JAPAN', 'SOUTH KOREA', 'CANADA', 'AUSTRALIA', 'BRAZIL']
    print("\n重要国家的normalized profile范围:")
    for country in important_countries:
        if country in normalized_profiles:
            profile = normalized_profiles[country]
            baseline_avg = baseline_avgs_dict[country]
            print(f"  {country}: baseline={baseline_avg:.2f}, "
                  f"normalized_range=[{min(profile):.2f}, {max(profile):.2f}]")
    
    return normalized_profiles


def perform_pca(normalized_profiles, n_components=2):
    """对normalized profiles进行PCA分析"""
    print("\n" + "=" * 80)
    print(f"步骤5: PCA分析（n_components={n_components}）...")
    print("=" * 80)
    
    # 准备数据矩阵
    countries = list(normalized_profiles.keys())
    data_matrix = np.array([normalized_profiles[country] for country in countries])
    
    # 标准化数据（可选，但通常对PCA有帮助）
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_matrix)
    
    # 执行PCA
    pca = PCA(n_components=n_components)
    pca_result = pca.fit_transform(data_scaled)
    
    # 计算解释的方差比例
    explained_variance = pca.explained_variance_ratio_
    cumulative_variance = np.cumsum(explained_variance)
    
    print(f"PC1解释方差: {explained_variance[0]:.2%}")
    print(f"PC2解释方差: {explained_variance[1]:.2%}")
    print(f"累计解释方差: {cumulative_variance[-1]:.2%}")
    
    return pca_result, pca, countries, explained_variance


def perform_kmeans_clustering(pca_result, n_clusters=3):
    """使用K-means进行聚类"""
    print("\n" + "=" * 80)
    print(f"步骤6: K-means聚类（n_clusters={n_clusters}）...")
    print("=" * 80)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(pca_result)
    
    print(f"聚类完成，共 {n_clusters} 个簇")
    for i in range(n_clusters):
        count = np.sum(cluster_labels == i)
        print(f"  簇 {i}: {count} 个国家")
    
    return cluster_labels, kmeans


def perform_hierarchical_clustering(pca_result, n_clusters=3):
    """使用层次聚类"""
    print("\n" + "=" * 80)
    print(f"步骤7: 层次聚类（n_clusters={n_clusters}）...")
    print("=" * 80)
    
    # 计算距离矩阵
    linkage_matrix = linkage(pca_result, method='ward')
    
    # 获取聚类标签
    cluster_labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')
    
    print(f"层次聚类完成，共 {n_clusters} 个簇")
    for i in range(1, n_clusters + 1):
        count = np.sum(cluster_labels == i)
        print(f"  簇 {i}: {count} 个国家")
    
    return cluster_labels, linkage_matrix


def visualize_results(pca_result, countries, kmeans_labels, hierarchical_labels, 
                     normalized_profiles, years, explained_variance, linkage_matrix):
    """可视化PCA和聚类结果"""
    print("\n" + "=" * 80)
    print("步骤8: 生成可视化结果...")
    print("=" * 80)
    
    # 创建图形 - 只保留3个子图
    fig = plt.figure(figsize=(18, 6))
    
    # 1. PCA散点图 - K-means聚类
    ax1 = plt.subplot(1, 3, 1)
    scatter1 = ax1.scatter(pca_result[:, 0], pca_result[:, 1], 
                          c=kmeans_labels, cmap='viridis', s=100, alpha=0.6)
    ax1.set_xlabel(f'PC1 ({explained_variance[0]:.1%} variance)', fontsize=12)
    ax1.set_ylabel(f'PC2 ({explained_variance[1]:.1%} variance)', fontsize=12)
    ax1.set_title('PCA - K-means Clustering', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    plt.colorbar(scatter1, ax=ax1, label='Cluster')
    
    # 标注一些重要国家
    important_countries = ['UNITED STATES', 'CHINA', 'UNITED KINGDOM', 
                          'JAPAN', 'SOUTH KOREA', 'CANADA', 'AUSTRALIA', 'BRAZIL']
    for i, country in enumerate(countries):
        if country in important_countries:
            ax1.annotate(country, (pca_result[i, 0], pca_result[i, 1]), 
                        fontsize=8, alpha=0.7)
    
    # 2. PCA散点图 - 层次聚类
    ax2 = plt.subplot(1, 3, 2)
    scatter2 = ax2.scatter(pca_result[:, 0], pca_result[:, 1], 
                          c=hierarchical_labels, cmap='plasma', s=100, alpha=0.6)
    ax2.set_xlabel(f'PC1 ({explained_variance[0]:.1%} variance)', fontsize=12)
    ax2.set_ylabel(f'PC2 ({explained_variance[1]:.1%} variance)', fontsize=12)
    ax2.set_title('PCA - Hierarchical Clustering', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    plt.colorbar(scatter2, ax=ax2, label='Cluster')
    
    for i, country in enumerate(countries):
        if country in important_countries:
            ax2.annotate(country, (pca_result[i, 0], pca_result[i, 1]), 
                        fontsize=8, alpha=0.7)
    
    # 3. 层次聚类树状图
    ax3 = plt.subplot(1, 3, 3)
    # 由于国家太多，只显示部分树状图
    dendrogram(linkage_matrix, ax=ax3, truncate_mode='level', p=5)
    ax3.set_title('Hierarchical Clustering Dendrogram', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Country', fontsize=12)
    ax3.set_ylabel('Distance', fontsize=12)
    
    plt.tight_layout()
    
    # 保存图片
    output_file = str(CODE / "add_experiments/experiment_4/eu/eu_pca_clustering_results.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"可视化结果已保存到: {output_file}")
    
    plt.show()


def save_results(countries, normalized_profiles, kmeans_labels, hierarchical_labels, 
                pca_result, years):
    """保存分析结果到CSV文件"""
    print("\n" + "=" * 80)
    print("步骤9: 保存结果...")
    print("=" * 80)
    
    # 创建结果DataFrame
    results_data = {
        'Country': countries,
        'KMeans_Cluster': kmeans_labels,
        'Hierarchical_Cluster': hierarchical_labels,
        'PC1': pca_result[:, 0],
        'PC2': pca_result[:, 1]
    }
    
    # 添加每年的normalized值
    for i, year in enumerate(years):
        results_data[f'Normalized_{year}'] = [normalized_profiles[c][i] for c in countries]
    
    results_df = pd.DataFrame(results_data)
    
    # 保存到CSV
    output_file = str(CODE / "add_experiments/experiment_4/eu/eu_pca_clustering_results.csv")
    results_df.to_csv(output_file, index=False)
    print(f"结果已保存到: {output_file}")
    
    return results_df


def main():
    """主函数"""
    # 1. 加载数据
    df = load_and_process_data()
    
    # 2. 构建合作profile
    profiles, years = build_collaboration_profiles(df)
    
    # 3. 过滤小国家
    filtered_profiles = filter_countries_by_threshold(profiles)
    
    # 4. Normalize profiles
    normalized_profiles = normalize_profiles(filtered_profiles, years)
    
    # 5. PCA分析
    pca_result, pca, countries, explained_variance = perform_pca(normalized_profiles, n_components=2)
    
    # 6. K-means聚类
    kmeans_labels, kmeans = perform_kmeans_clustering(pca_result, n_clusters=10)
    
    # 7. 层次聚类
    hierarchical_labels, linkage_matrix = perform_hierarchical_clustering(pca_result, n_clusters=10)
    
    # 8. 可视化
    visualize_results(pca_result, countries, kmeans_labels, hierarchical_labels,
                     normalized_profiles, years, explained_variance, linkage_matrix)
    
    # 9. 保存结果
    results_df = save_results(countries, normalized_profiles, kmeans_labels, 
                             hierarchical_labels, pca_result, years)
    
    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)
    
    # 打印每个簇的国家列表
    print("\nK-means聚类结果:")
    for cluster_id in range(len(np.unique(kmeans_labels))):
        cluster_countries = [countries[i] for i in range(len(countries)) 
                            if kmeans_labels[i] == cluster_id]
        print(f"\n簇 {cluster_id} ({len(cluster_countries)} 个国家):")
        print(", ".join(sorted(cluster_countries)))
    
    print("\n层次聚类结果:")
    for cluster_id in range(1, len(np.unique(hierarchical_labels)) + 1):
        cluster_countries = [countries[i] for i in range(len(countries)) 
                            if hierarchical_labels[i] == cluster_id]
        print(f"\n簇 {cluster_id} ({len(cluster_countries)} 个国家):")
        print(", ".join(sorted(cluster_countries)))


if __name__ == "__main__":
    main()