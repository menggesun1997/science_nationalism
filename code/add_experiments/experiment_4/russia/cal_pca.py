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
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist, squareform
import warnings
warnings.filterwarnings('ignore')


PPML_DATA_FILE = "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/2ppml_did_russia_internal_control/ppml_data.xlsx"
RUSSIA_NAME = "RUSSIAN FEDERATION"
COUNTRIES_STATS_FILE = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/brexit_experimental_data/countries_yearly_statistics.csv'


# 定义时期
START_YEAR = 2005
END_YEAR = 2024
N_CLUSTERS = 6  # K-means 聚类数量（固定为 3）
CLUSTER_RANGE = (2, 15)  # 评估聚类数量的范围（最小，最大）



def load_ppml_collaboration_data():
    """从 ppml_data.xlsx 加载Russia合作国家年度合作数量"""
    print("=" * 80)
    print("步骤1: 从 ppml_data.xlsx 加载合作数量...")
    print("=" * 80)

    df = pd.read_excel(PPML_DATA_FILE)
    df.columns = [str(c).strip() for c in df.columns]
    lower_to_original = {c.lower().strip(): c for c in df.columns}


    df = df[['partner_country', 'year', 'paper_count']].rename(
        columns={"partner_country": "country", "year": "year", "paper_count": "paper_count"}
    )
    
    df["country"] = df["country"].astype(str).str.upper().str.strip()
    df["year"] = df["year"].astype(int)
    df["paper_count"] = pd.to_numeric(df["paper_count"], errors="coerce").fillna(0)

    # 只保留指定年份范围
    df = df[(df["year"] >= START_YEAR) & (df["year"] <= END_YEAR)].copy()
    # 排除Russia自身
    df = df[df["country"] != RUSSIA_NAME].copy()

    print(f"数据形状: {df.shape}")
    print(f"年份范围: {df['year'].min()} - {df['year'].max()}")

    return df


def load_country_international_stats():
    """加载各国每年国际合作文章数量，用于计算 RCA 向量"""
    print("\n" + "=" * 80)
    print("步骤1.1: 加载各国年度国际合作统计数据...")
    print("=" * 80)

    stats_df = pd.read_csv(COUNTRIES_STATS_FILE)
    stats_df["partner_country"] = stats_df["partner_country"].astype(str).str.upper().str.strip()
    stats_df["Year"] = stats_df["Year"].astype(int)

    stats_map = {
        (row["Country"], row["Year"]): row["International_Collaborations"]
        for _, row in stats_df.iterrows()
    }

    global_international_totals = (
        stats_df.groupby("Year")["International_Collaborations"].sum().to_dict()
    )

    print(f"统计数据条数: {len(stats_map)}")
    return stats_map, global_international_totals


def build_collaboration_profiles(df):
    """
    构建Russia与每个collaborator的合作profile（纯合作篇数）
    """
    print("\n" + "=" * 80)
    print("步骤2: 构建合作profile（篇数）...")
    print("=" * 80)
    
    # 统计每年与各国的合作数量（来自 ppml_data.xlsx）
    collaboration_counts = defaultdict(lambda: defaultdict(int))
    
    for _, row in df.iterrows():
        year = int(row["year"])
        country = row["country"]
        count = row["paper_count"]
        collaboration_counts[country][year] += count
    
    # 构建完整的profile矩阵
    years = list(range(START_YEAR, END_YEAR + 1))
    count_profiles = {}
    
    for country, year_counts in collaboration_counts.items():
        # 纯篇数向量
        count_profile = [year_counts.get(year, 0) for year in years]
        count_profiles[country] = count_profile
    
    print(f"找到 {len(count_profiles)} 个合作国家")
    
    return collaboration_counts, count_profiles, years


def build_rca_profiles(collaboration_counts, years, countries_filter=None):
    """
    基于合作篇数与国际合作统计，计算 RCA profile
    """
    print("\n" + "=" * 80)
    print("步骤3: 计算 RCA profile...")
    print("=" * 80)

    stats_map, global_international_totals = load_country_international_stats()

    # 预先计算每年 Russia 合作总量（用于 RCA 分母）
    russia_total_by_year = {}
    for year in years:
        russia_total_by_year[year] = sum(
            year_counts_by_country.get(year, 0)
            for year_counts_by_country in collaboration_counts.values()
        )

    rca_profiles = {}
    missing_stats_entries = 0
    missing_global_totals = 0

    countries = (
        list(countries_filter) if countries_filter is not None
        else list(collaboration_counts.keys())
    )

    for country in countries:
        year_counts = collaboration_counts.get(country, {})
        rca_profile = []
        for year in years:
            num = year_counts.get(year, 0)
            country_international = stats_map.get((country, year), 0)
            global_international = global_international_totals.get(year, 0)
            total_russia_collab = russia_total_by_year.get(year, 0)

            if country_international and country_international > 0 and global_international > 0:
                numerator_share = num / country_international
                denominator_share = total_russia_collab / global_international
                rca = numerator_share / denominator_share if denominator_share > 0 else 0.0
            else:
                rca = 0.0
                if num > 0 and (country_international == 0):
                    missing_stats_entries += 1
                if num > 0 and (global_international == 0):
                    missing_global_totals += 1
            rca_profile.append(rca)
        rca_profiles[country] = rca_profile

    if missing_stats_entries > 0:
        print(f"[WARNING] 缺少统计数据的国家-年份条目数: {missing_stats_entries}")
    if missing_global_totals > 0:
        print(f"[WARNING] 缺少全球统计的年份条目数: {missing_global_totals}")

    return rca_profiles




def filter_countries_by_min_count(profiles, min_threshold=30):
    """过滤国家：如果某国在所有年份中的最小合作数量 < min_threshold，则剔除"""
    print("\n" + "=" * 80)
    print(f"步骤3: 过滤国家（最小合作数量阈值: {min_threshold}）...")
    print("=" * 80)

    filtered_profiles = {}
    for country, profile in profiles.items():
        if len(profile) == 0:
            continue
        if min(profile) >= min_threshold:
            filtered_profiles[country] = profile

    print(f"过滤前: {len(profiles)} 个国家")
    print(f"过滤后: {len(filtered_profiles)} 个国家")

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
    baseline_years = [START_YEAR, START_YEAR + 1, START_YEAR + 2]
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
    important_countries = ['GERMANY', 'FRANCE', 'ITALY', 'SPAIN', 'NETHERLANDS', 
                          'UNITED STATES', 'CHINA', 'UKRAINE', 'POLAND', 'BELARUS']
    print("\n重要国家的normalized profile范围:")
    for country in important_countries:
        if country in normalized_profiles:
            profile = normalized_profiles[country]
            baseline_avg = baseline_avgs_dict[country]
            print(f"  {country}: baseline={baseline_avg:.2f}, "
                  f"normalized_range=[{min(profile):.2f}, {max(profile):.2f}]")
    
    return normalized_profiles


def smooth_profiles_by_first_three(profiles):
    """用前三个数的平均值平滑整个向量"""
    print("\n" + "=" * 80)
    print("步骤4: 用前三个数的平均值平滑向量...")
    print("=" * 80)

    smoothed_profiles = {}
    for country, profile in profiles.items():
        if len(profile) == 0:
            continue
        first_three = profile[:3] if len(profile) >= 3 else profile
        base_avg = np.mean(first_three) if first_three else 1.0
        if base_avg == 0:
            base_avg = 1.0
        smoothed_profiles[country] = [v / base_avg for v in profile]

    print(f"平滑后国家数量: {len(smoothed_profiles)}")
    return smoothed_profiles


def log_transform_profiles(normalized_profiles, years):
    """对 normalized profiles 做对数变换（log transformation）"""
    print("\n" + "=" * 80)
    print("步骤4.1: 对 normalized profiles 做对数变换（log1p）...")
    print("=" * 80)

    log_profiles = {}

    for country, profile in normalized_profiles.items():
        # 使用 log1p，避免 0 的对数问题：log1p(x) = log(1 + x)
        log_profile = [np.log1p(v) for v in profile]
        log_profiles[country] = log_profile

    # 简单查看分布
    all_values = [v for prof in log_profiles.values() for v in prof]
    if all_values:
        print(f"log-normalized 取值范围: min={min(all_values):.3f}, "
              f"max={max(all_values):.3f}, mean={np.mean(all_values):.3f}")

    # 打印几个重要国家的信息
    important_countries = ['GERMANY', 'FRANCE', 'ITALY', 'SPAIN', 'NETHERLANDS', 
                          'UNITED STATES', 'CHINA', 'UKRAINE', 'POLAND', 'BELARUS']
    print("\n重要国家的 log-normalized profile 范围:")
    for country in important_countries:
        if country in log_profiles:
            profile = log_profiles[country]
            print(f"  {country}: log_range=[{min(profile):.3f}, {max(profile):.3f}]")

    return log_profiles


def log_transform_profiles_signed(profiles, years):
    """
    对 profile 做带符号的 log 变换，适用于包含负值的百分比变化向量：
    log_signed(x) = sign(x) * log1p(|x|)
    """
    print("\n" + "=" * 80)
    print("步骤4.1: 对百分比向量做带符号 log 变换（log1p）...")
    print("=" * 80)

    log_profiles = {}

    for country, profile in profiles.items():
        log_profile = [np.sign(v) * np.log1p(abs(v)) for v in profile]
        log_profiles[country] = log_profile

    # 简单查看分布
    all_values = [v for prof in log_profiles.values() for v in prof]
    if all_values:
        print(f"log-transformed 取值范围: min={min(all_values):.3f}, "
              f"max={max(all_values):.3f}, mean={np.mean(all_values):.3f}")

    return log_profiles


def percent_change_profiles(profiles, years, base_years=None):
    """
    以指定基期年份（可为多个年份的均值）为基准，计算各年份的变动百分比
    percent_change = (value_t - value_base) / value_base
    """
    if base_years is None:
        base_years = [2021]

    base_years = sorted(base_years)
    print("\n" + "=" * 80)
    print(f"步骤4: 以基期均值（{base_years[0]}-{base_years[-1]}）计算变动百分比...")
    print("=" * 80)

    for y in base_years:
        if y not in years:
            raise ValueError(f"基期年份 {y} 不在年份范围 {years[0]}-{years[-1]} 中")

    base_indices = [years.index(y) for y in base_years]
    percent_profiles = {}
    missing_base = 0

    for country, profile in profiles.items():
        base_values = [profile[i] for i in base_indices]
        base_value = np.mean(base_values) if base_values else 0
        if base_value == 0:
            missing_base += 1
            percent_profile = [0.0 for _ in profile]
        else:
            percent_profile = [(v - base_value) / base_value for v in profile]
        percent_profiles[country] = percent_profile

    if missing_base > 0:
        print(f"[WARNING] 基期值为0的国家数量: {missing_base}（已置为0向量）")

    return percent_profiles


def perform_pca_full(normalized_profiles, scaler=None, already_scaled=False):
    """对profiles进行完整PCA分析（计算所有主成分）用于碎石图"""
    print("\n" + "=" * 80)
    print("步骤5: PCA分析（计算所有主成分用于碎石图）...")
    print("=" * 80)
    
    # 准备数据矩阵
    countries = list(normalized_profiles.keys())
    data_matrix = np.array([normalized_profiles[country] for country in countries])
    
    # 标准化数据（如已提前按列标准化，则跳过）
    if already_scaled:
        data_scaled = data_matrix
    else:
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data_matrix)
    
    # 执行PCA - 计算所有主成分
    n_features = data_scaled.shape[1]
    pca_full = PCA(n_components=n_features)
    pca_full.fit(data_scaled)

    # 计算所有主成分的解释方差比例
    explained_variance_all = pca_full.explained_variance_ratio_
    cumulative_variance_all = np.cumsum(explained_variance_all)

    print(f"总特征数: {n_features}")
    print("前5个主成分解释方差:")
    for i in range(min(5, len(explained_variance_all))):
        print(
            f"  PC{i+1}: {explained_variance_all[i]:.2%} "
            f"(累计: {cumulative_variance_all[i]:.2%})"
        )

    return pca_full, explained_variance_all, cumulative_variance_all, scaler


def perform_pca(normalized_profiles, n_components=2, scaler=None, already_scaled=False):
    """对profiles进行PCA分析（只保留前n_components个主成分）"""
    print("\n" + "=" * 80)
    print(f"步骤5.1: PCA分析（保留前{n_components}个主成分）...")
    print("=" * 80)

    # 准备数据矩阵
    countries = list(normalized_profiles.keys())
    data_matrix = np.array([normalized_profiles[country] for country in countries])

    # 标准化数据（如已提前按列标准化，则跳过）
    if already_scaled:
        data_scaled = data_matrix
    else:
        if scaler is None:
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(data_matrix)
        else:
            data_scaled = scaler.transform(data_matrix)

    # 执行PCA
    pca = PCA(n_components=n_components)
    pca_result = pca.fit_transform(data_scaled)
    
    # 计算解释的方差比例
    explained_variance = pca.explained_variance_ratio_
    cumulative_variance = np.cumsum(explained_variance)
    
    print(f"PC1解释方差: {explained_variance[0]:.2%}")
    print(f"PC2解释方差: {explained_variance[1]:.2%}")
    print(f"累计解释方差: {cumulative_variance[-1]:.2%}")
    if explained_variance[0] < 0.70:
        print("[WARNING] PC1 解释方差低于 70%")
    
    return pca_result, pca, countries, explained_variance


def find_optimal_clusters(pca_result, min_clusters=2, max_clusters=15):
    """
    通过轮廓系数找到最优的聚类数量
    
    参数:
    - pca_result: PCA结果矩阵
    - min_clusters: 最小聚类数量
    - max_clusters: 最大聚类数量
    
    返回:
    - optimal_n_clusters: 最优聚类数量
    - silhouette_scores: 每个聚类数量对应的轮廓系数
    """
    print("\n" + "=" * 80)
    print(f"步骤5.5: 通过轮廓系数选择最优聚类数量（范围: {min_clusters}-{max_clusters}）...")
    print("=" * 80)
    
    silhouette_scores = []
    cluster_range = range(min_clusters, max_clusters + 1)
    
    for n_clusters in cluster_range:
        # 使用K-means进行聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(pca_result)
        
        # 计算轮廓系数
        silhouette_avg = silhouette_score(pca_result, cluster_labels)
        silhouette_scores.append(silhouette_avg)
        
        print(f"  n_clusters={n_clusters:2d}: 轮廓系数 = {silhouette_avg:.4f}")
    
    # 找到最优聚类数量（轮廓系数最高）
    optimal_idx = np.argmax(silhouette_scores)
    optimal_n_clusters = cluster_range[optimal_idx]
    optimal_score = silhouette_scores[optimal_idx]
    
    print(f"\n最优聚类数量: {optimal_n_clusters} (轮廓系数 = {optimal_score:.4f})")
    
    # 返回轮廓系数数据，不单独保存图片（将在主结果图中显示）
    silhouette_dict = dict(zip(cluster_range, silhouette_scores))
    
    return optimal_n_clusters, silhouette_dict


def perform_kmeans_clustering(pca_result, n_clusters=4):
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


def plot_scree_plot(
    explained_variance_all,
    cumulative_variance_all=None,
    n_components_to_show=15,
    threshold=0.9,
):
    """
    绘制碎石图（Scree Plot）用于确定保留的主成分数量

    参数:
    - explained_variance_all: 所有主成分的解释方差比例
    - cumulative_variance_all: 累计解释方差比例（可选）
    - n_components_to_show: 显示前n个主成分
    - threshold: 累计解释方差阈值（默认90%）
    """
    n_components_to_show = min(n_components_to_show, len(explained_variance_all))
    components = range(1, n_components_to_show + 1)
    variances = explained_variance_all[:n_components_to_show]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # 左图：碎石图（每个主成分的解释方差）
    ax1.bar(components, variances, alpha=0.7, color="steelblue", edgecolor="black")
    ax1.plot(
        components,
        variances,
        "ro-",
        linewidth=2,
        markersize=6,
        label="Variance Explained",
    )
    ax1.set_xlabel("Principal Component", fontsize=12)
    ax1.set_ylabel("Proportion of Variance Explained", fontsize=12)
    ax1.set_title(
        "Scree Plot: Variance Explained by Each Component",
        fontsize=14,
        fontweight="bold",
    )
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.set_xticks(components)
    ax1.legend()

    # 添加数值标签（前5个主成分）
    for i, v in enumerate(variances):
        if i < 5:
            ax1.text(i + 1, v + 0.01, f"{v:.2%}", ha="center", va="bottom", fontsize=9)

    # 右图：累计解释方差
    if cumulative_variance_all is not None:
        cum_var = cumulative_variance_all[:n_components_to_show]
        ax2.plot(
            components,
            cum_var,
            "go-",
            linewidth=2,
            markersize=6,
            label="Cumulative Variance",
        )
        ax2.axhline(
            y=threshold,
            color="r",
            linestyle="--",
            linewidth=2,
            label=f"{threshold:.0%} Threshold",
        )
        ax2.fill_between(components, 0, cum_var, alpha=0.3, color="green")
        ax2.set_xlabel("Number of Components", fontsize=12)
        ax2.set_ylabel("Cumulative Proportion of Variance Explained", fontsize=12)
        ax2.set_title(
            "Cumulative Variance Explained", fontsize=14, fontweight="bold"
        )
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(components)
        ax2.set_ylim([0, 1.05])
        ax2.legend()

        # 找到达到阈值所需的主成分数量
        n_components_for_threshold = np.argmax(cum_var >= threshold) + 1
        if n_components_for_threshold <= n_components_to_show:
            ax2.axvline(
                x=n_components_for_threshold,
                color="orange",
                linestyle="--",
                linewidth=2,
                alpha=0.7,
                label=f"Need {n_components_for_threshold} components",
            )
            ax2.legend()
            print(
                f"\n达到{threshold:.0%}累计解释方差需要 "
                f"{n_components_for_threshold} 个主成分"
            )
            print(
                f"  累计解释方差: "
                f"{cum_var[n_components_for_threshold - 1]:.2%}"
            )

    plt.tight_layout()

    # 保存碎石图
    scree_output = (
        "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/"
        "add_experiments/experiment_4/russia/russia_pca_scree_plot.png"
    )
    plt.savefig(scree_output, dpi=300, bbox_inches="tight")
    print(f"碎石图已保存到: {scree_output}")

    plt.show()


def save_pc1_loadings(pca, years, output_path):
    """
    保存 PC1 的 loadings（对每个年份维度的权重）
    
    参数:
    - pca: 已拟合的 PCA 对象（在 2010-2024 各年份维度上）
    - years: 年份列表（特征顺序）
    - output_path: 保存的 CSV 路径
    """
    # pca.components_.shape = (n_components, n_features)
    pc1_loadings = pca.components_[0]
    loadings_df = pd.DataFrame({
        "Year": years,
        "PC1_Loading": pc1_loadings
    })
    # 方便查看，也给出按绝对值排序
    loadings_df["Abs_Loading"] = loadings_df["PC1_Loading"].abs()
    loadings_df = loadings_df.sort_values("Abs_Loading", ascending=False)
    
    loadings_df.to_csv(output_path, index=False)
    print(f"\nPC1 loadings 已保存到: {output_path}")
    print("PC1 loadings（按绝对值大小排序，前10个）：")
    print(loadings_df.head(10).to_string(index=False))
    
    return loadings_df


def plot_pc1_loadings(pca, years, output_path):
    """
    绘制 PC1 loadings 随时间的变化
    
    参数:
    - pca: 已拟合的 PCA 对象
    - years: 年份列表（特征顺序）
    - output_path: 保存图片的路径
    """
    # 获取 PC1 loadings（按原始年份顺序）
    pc1_loadings = pca.components_[0]
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 绘制折线图
    ax.plot(years, pc1_loadings, 'o-', linewidth=2, markersize=8, color='steelblue', label='PC1 Loading')
    
    # 添加零线
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    # 标注正负值区域
    ax.fill_between(years, 0, pc1_loadings, where=(pc1_loadings >= 0), 
                    alpha=0.3, color='green', label='Positive Loading')
    ax.fill_between(years, 0, pc1_loadings, where=(pc1_loadings < 0), 
                    alpha=0.3, color='red', label='Negative Loading')
    
    # 设置标签和标题
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('PC1 Loading', fontsize=12)
    ax.set_title('PC1 Loadings by Year', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    # 设置x轴刻度
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 保存图片
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"PC1 loadings 图已保存到: {output_path}")
    
    plt.show()


def save_pc2_loadings(pca, years, output_path):
    """
    保存 PC2 的 loadings（对每个年份维度的权重）
    
    参数:
    - pca: 已拟合的 PCA 对象（在 2015-2024 各年份维度上）
    - years: 年份列表（特征顺序）
    - output_path: 保存的 CSV 路径
    """
    # pca.components_.shape = (n_components, n_features)
    pc2_loadings = pca.components_[1]
    loadings_df = pd.DataFrame({
        "Year": years,
        "PC2_Loading": pc2_loadings
    })
    # 方便查看，也给出按绝对值排序
    loadings_df["Abs_Loading"] = loadings_df["PC2_Loading"].abs()
    loadings_df = loadings_df.sort_values("Abs_Loading", ascending=False)
    
    loadings_df.to_csv(output_path, index=False)
    print(f"\nPC2 loadings 已保存到: {output_path}")
    print("PC2 loadings（按绝对值大小排序，前10个）：")
    print(loadings_df.head(10).to_string(index=False))
    
    return loadings_df


def plot_pc2_loadings(pca, years, output_path):
    """
    绘制 PC2 loadings 随时间的变化
    
    参数:
    - pca: 已拟合的 PCA 对象
    - years: 年份列表（特征顺序）
    - output_path: 保存图片的路径
    """
    # 获取 PC2 loadings（按原始年份顺序）
    pc2_loadings = pca.components_[1]
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # 绘制折线图
    ax.plot(years, pc2_loadings, 'o-', linewidth=2, markersize=8, color='coral', label='PC2 Loading')
    
    # 添加零线
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    # 标注正负值区域
    ax.fill_between(years, 0, pc2_loadings, where=(pc2_loadings >= 0), 
                    alpha=0.3, color='green', label='Positive Loading')
    ax.fill_between(years, 0, pc2_loadings, where=(pc2_loadings < 0), 
                    alpha=0.3, color='red', label='Negative Loading')
    
    # 设置标签和标题
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('PC2 Loading', fontsize=12)
    ax.set_title('PC2 Loadings by Year', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)
    
    # 设置x轴刻度
    ax.set_xticks(years)
    ax.set_xticklabels(years, rotation=45, ha='right')
    
    plt.tight_layout()
    
    # 保存图片
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"PC2 loadings 图已保存到: {output_path}")
    
    plt.show()


def visualize_results(pca_result, countries, kmeans_labels, hierarchical_labels, 
                     normalized_profiles, years, explained_variance, linkage_matrix,
                     silhouette_scores=None, optimal_n_clusters=None):
    """可视化PCA和聚类结果"""
    print("\n" + "=" * 80)
    print("步骤8: 生成可视化结果...")
    print("=" * 80)

    def annotate_points(ax, xs, ys, labels):
        """标注所有节点，优先使用自动避让；不可用时回退到上下交替偏移"""
        try:
            from adjustText import adjust_text

            texts = []
            for i, country in enumerate(labels):
                texts.append(
                    ax.text(
                        xs[i],
                        ys[i],
                        country,
                        fontsize=5,
                        alpha=0.85,
                        ha="center",
                        va="center",
                    )
                )
            adjust_text(
                texts,
                ax=ax,
                only_move={"points": "y", "text": "y"},
                autoalign="y",
                expand_points=(1.1, 1.2),
                expand_text=(1.1, 1.2),
                force_text=0.3,
            )
        except Exception:
            # 回退：上下交替偏移
            for i, country in enumerate(labels):
                x, y = xs[i], ys[i]
                y_offset = 6 if i % 2 == 0 else -6
                ax.annotate(
                    country,
                    (x, y),
                    fontsize=5,
                    alpha=0.8,
                    textcoords="offset points",
                    xytext=(0, y_offset),
                    ha="center",
                    va="bottom" if y_offset > 0 else "top",
                )
    
    # 创建图形 - 1x2布局（仅PCA+Kmeans与PCA+层次聚类）
    fig = plt.figure(figsize=(14, 6))
    
    # 标注一些重要国家
    important_countries = ['GERMANY', 'FRANCE', 'ITALY', 'SPAIN', 'NETHERLANDS', 
                          'UNITED STATES', 'CHINA', 'UKRAINE', 'POLAND', 'BELARUS']
    
    # 1. PCA散点图 - K-means聚类（左）
    ax1 = plt.subplot(1, 2, 1)
    scatter1 = ax1.scatter(
        pca_result[:, 0],
        pca_result[:, 1],
        c=kmeans_labels,
        cmap="viridis",
        s=100,
        alpha=0.6,
    )
    ax1.set_xlabel(f"PC1 ({explained_variance[0]:.1%} variance)", fontsize=12)
    ax1.set_ylabel(f"PC2 ({explained_variance[1]:.1%} variance)", fontsize=12)
    ax1.set_title("PCA - K-means Clustering", fontsize=14, fontweight="bold")
    ax1.grid(True, alpha=0.3)
    plt.colorbar(scatter1, ax=ax1, label="Cluster")

    # 在 K-means PCA 散点图中标注国家名称（避免重叠）
    annotate_points(
        ax1,
        pca_result[:, 0],
        pca_result[:, 1],
        countries,
    )

    # 2. PCA散点图 - 层次聚类（右）
    ax2 = plt.subplot(1, 2, 2)
    scatter2 = ax2.scatter(
        pca_result[:, 0],
        pca_result[:, 1],
        c=hierarchical_labels,
        cmap="plasma",
        s=100,
        alpha=0.6,
    )
    ax2.set_xlabel(f"PC1 ({explained_variance[0]:.1%} variance)", fontsize=12)
    ax2.set_ylabel(f"PC2 ({explained_variance[1]:.1%} variance)", fontsize=12)
    ax2.set_title("PCA - Hierarchical Clustering", fontsize=14, fontweight="bold")
    ax2.grid(True, alpha=0.3)
    plt.colorbar(scatter2, ax=ax2, label="Cluster")

    # 在层次聚类 PCA 散点图中标注国家名称（避免重叠）
    annotate_points(
        ax2,
        pca_result[:, 0],
        pca_result[:, 1],
        countries,
    )
    
    plt.tight_layout()
    
    # 保存图片
    output_file = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/add_experiments/experiment_4/russia/russia_pca_clustering_results.png'
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
    output_file = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/add_experiments/experiment_4/russia/russia_pca_clustering_results.csv'
    results_df.to_csv(output_file, index=False)
    print(f"结果已保存到: {output_file}")
    
    return results_df


def main():
    """主函数"""
    # 1. 加载数据
    df = load_ppml_collaboration_data()
    
    # 2. 构建合作profile（篇数）
    collaboration_counts, count_profiles, years = build_collaboration_profiles(df)
    
    # 3. 过滤国家：最小合作数量 < 10 的剔除
    filtered_count_profiles = filter_countries_by_min_count(count_profiles, min_threshold=10)

    # 4. 用前三个数的平均值平滑向量
    smoothed_count_profiles = smooth_profiles_by_first_three(filtered_count_profiles)

    # 5. PCA完整分析（用于碎石图）
    (
        pca_full,
        explained_variance_all,
        cumulative_variance_all,
        scaler,
    ) = perform_pca_full(smoothed_count_profiles)

    # 5.1. 绘制碎石图（使用90%累计解释方差阈值）
    plot_scree_plot(
        explained_variance_all,
        cumulative_variance_all,
        n_components_to_show=15,
        threshold=0.9,
    )

    # 5.2. PCA分析（保留前2个主成分用于后续分析）
    pca_result, pca, countries, explained_variance = perform_pca(
        smoothed_count_profiles,
        n_components=2,
        scaler=scaler,
    )

    # 5.3. 保存并查看 PC1 的 loadings（对每个年份的权重）
    pc1_loadings_output = (
        "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/"
        "add_experiments/experiment_4/russia/russia_pc1_loadings.csv"
    )
    save_pc1_loadings(pca, years, pc1_loadings_output)
    
    # 5.3.1. 绘制 PC1 loadings 图
    pc1_loadings_plot_output = (
        "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/"
        "add_experiments/experiment_4/russia/russia_pc1_loadings.png"
    )
    plot_pc1_loadings(pca, years, pc1_loadings_plot_output)
    
    # 5.4. 保存并查看 PC2 的 loadings（对每个年份的权重）
    pc2_loadings_output = (
        "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/"
        "add_experiments/experiment_4/russia/russia_pc2_loadings.csv"
    )
    save_pc2_loadings(pca, years, pc2_loadings_output)
    
    # 5.4.1. 绘制 PC2 loadings 图
    pc2_loadings_plot_output = (
        "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/"
        "add_experiments/experiment_4/russia/russia_pc2_loadings.png"
    )
    plot_pc2_loadings(pca, years, pc2_loadings_plot_output)

    # 5.5. 通过轮廓系数选择最优聚类数量（如果N_CLUSTERS为None）
    silhouette_scores = None
    optimal_n_clusters = None
    if N_CLUSTERS is None:
        optimal_n_clusters, silhouette_scores = find_optimal_clusters(
            pca_result, 
            min_clusters=CLUSTER_RANGE[0], 
            max_clusters=CLUSTER_RANGE[1]
        )
        n_clusters = optimal_n_clusters
    else:
        n_clusters = N_CLUSTERS
        print(f"\n使用指定的聚类数量: {n_clusters}")
    
    # 6. K-means聚类
    kmeans_labels, kmeans = perform_kmeans_clustering(pca_result, n_clusters=n_clusters)
    
    # 7. 层次聚类（这里固定使用 6 个簇，便于展示更粗颗粒度的分组）
    hierarchical_n_clusters = N_CLUSTERS
    print(f"\n层次聚类将固定使用 {hierarchical_n_clusters} 个簇（不使用轮廓系数选择）")
    hierarchical_labels, linkage_matrix = perform_hierarchical_clustering(
        pca_result,
        n_clusters=hierarchical_n_clusters,
    )
    
    # 8. 可视化
    visualize_results(
        pca_result,
        countries,
        kmeans_labels,
        hierarchical_labels,
        smoothed_count_profiles,
        years,
        explained_variance,
        linkage_matrix,
        silhouette_scores=silhouette_scores,
        optimal_n_clusters=optimal_n_clusters,
    )
    
    # 9. 保存结果
    results_df = save_results(
        countries,
        smoothed_count_profiles,
        kmeans_labels,
        hierarchical_labels,
        pca_result,
        years,
    )
    
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
