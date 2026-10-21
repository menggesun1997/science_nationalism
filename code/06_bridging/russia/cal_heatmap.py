
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent



import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from collections import defaultdict
from typing import List, Tuple, Dict

AGGREGATED_ARTICLES_FILE = str(CODE / "00_data_processing/brexit_experimental_data/article_countries_aggregated.txt")
RUSSIA_NAME = "RUSSIAN FEDERATION"
COUNTRIES_STATS_FILE = str(CODE / "00_data_processing/brexit_experimental_data/countries_yearly_statistics.csv")

RUSSIA_NAME = "RUSSIAN FEDERATION"
FOCAL_COUNTRY = RUSSIA_NAME
FOCAL_LABEL = "Russia"
FOCAL_FILE_PREFIX = "russia"

base_dir = str(HERE)


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


def load_aggregated_articles(
    aggregated_file: str = AGGREGATED_ARTICLES_FILE,
    start_year: int = None,
    end_year: int = None,
) -> pd.DataFrame:
    """
    读取聚合后的文章-国家数据，只保留年份和国家字段。
    """
    df = pd.read_csv(
        aggregated_file,
        dtype={"OST_BK": "Int64", "Annee_Bibliographique": "Int64", "countries": "string"},
    )
    df = df[["Annee_Bibliographique", "countries"]].rename(
        columns={"Annee_Bibliographique": "year"}
    )
    df = df.dropna(subset=["countries"])
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    if start_year is not None:
        df = df[df["year"] >= start_year]
    if end_year is not None:
        df = df[df["year"] <= end_year]
    return df


def load_country_total_publications(
    start_year: int,
    end_year: int,
    stats_file: str = COUNTRIES_STATS_FILE,
) -> Dict[str, int]:
    """
    读取各国 Total_Publications，并按年份区间求和。
    """
    stats_df = pd.read_csv(stats_file)
    stats_df["Country"] = stats_df["Country"].astype(str).str.upper().str.strip()
    stats_df["Year"] = stats_df["Year"].astype(int)
    stats_df["Total_Publications"] = pd.to_numeric(
        stats_df["Total_Publications"], errors="coerce"
    ).fillna(0)

    period_df = stats_df[
        (stats_df["Year"] >= start_year) & (stats_df["Year"] <= end_year)
    ].copy()
    total_pubs = (
        period_df.groupby("Country")["Total_Publications"].sum().to_dict()
    )
    return total_pubs


def get_top_collaborators_all_years(
    df: pd.DataFrame,
    top_n: int = 30,
) -> List[str]:
    """
    在所有年份中，计算与 Russia 合作次数最多的前 top_n 个国家。

    参数：
    - df: 数据框
    - top_n: 取前 top_n 个合作者

    返回：
    - 合作者列表（按合作次数从高到低排序）
    """
    # 使用所有年份的数据
    all_years_df = df.copy()
    all_years_df["country_list"] = all_years_df["countries"].apply(parse_countries)

    # 只保留包含 Russia 的文章
    all_years_df = all_years_df[all_years_df["country_list"].apply(lambda lst: RUSSIA_NAME in lst)]

    co_counts: Dict[str, int] = defaultdict(int)
    for countries in all_years_df["country_list"]:
        for c in countries:
            if c != RUSSIA_NAME:
                co_counts[c] += 1

    # 按合作次数排序，取前 top_n
    sorted_collabs = sorted(co_counts.items(), key=lambda x: x[1], reverse=True)
    top_collabs = [c for c, _ in sorted_collabs[:top_n]]

    return top_collabs


def build_collaborator_heatmap(
    period_df: pd.DataFrame,
    collaborators: List[str],
    total_publications: Dict[str, int],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    构建合作者之间的 heatmap（S_C = Observed / Expected）。
    
    公式：
    - Observed_{RUS,C,B}：包含 RUS、行 C、列 B 的论文数
    - Expected_{RUS,C,B} = N_{RUS,C} * N_{B,C} / N_C
      其中 N_C 来自 Total_Publications
    """
    observed_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    russia_pair_counts: Dict[str, int] = defaultdict(int)
    pair_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for countries in period_df["country_list"]:
        countries_set = set(countries)
        collabs_in_paper = [c for c in countries_set if c in collaborators]
        if not collabs_in_paper:
            continue

        # N_{B,C}: 所有论文中 B 与 C 的共同出现
        for i in range(len(collabs_in_paper)):
            a = collabs_in_paper[i]
            for j in range(i + 1, len(collabs_in_paper)):
                b = collabs_in_paper[j]
                pair_counts[a][b] += 1
                pair_counts[b][a] += 1

        # Observed_{RUS,C,B} 与 N_{RUS,C}
        if RUSSIA_NAME not in countries_set:
            continue
        for c in collabs_in_paper:
            russia_pair_counts[c] += 1
        for c in collabs_in_paper:
            for b in collabs_in_paper:
                if b == c:
                    continue
                observed_counts[c][b] += 1

    # Observed 矩阵
    counts_data = []
    for c in collaborators:
        row = []
        for b in collaborators:
            if b == c:
                row.append(russia_pair_counts.get(c, 0))
            else:
                row.append(observed_counts[c].get(b, 0))
        counts_data.append(row)
    counts_df = pd.DataFrame(counts_data, index=collaborators, columns=collaborators)

    # 计算 S_C = Observed / Expected
    data = []
    for c in collaborators:
        row = []
        n_rus_c = russia_pair_counts.get(c, 0)
        n_c = total_publications.get(c, 0)
        for b in collaborators:
            if b == c:
                n_b_c = n_c
            else:
                n_b_c = pair_counts[c].get(b, 0)
            expected = (n_rus_c * n_b_c / n_c) if n_c > 0 else 0.0
            observed = counts_df.at[c, b]
            val = observed / expected if expected > 0 else 0.0
            row.append(val)
        data.append(row)

    heatmap_df = pd.DataFrame(data, index=collaborators, columns=collaborators)
    
    # 调试信息：确认矩阵维度
    print(f"  [DEBUG] Heatmap矩阵维度: {len(heatmap_df.index)} 行 x {len(heatmap_df.columns)} 列")
    print(f"  [DEBUG] 行（第三国家）数量: {len(heatmap_df.index)}")
    print(f"  [DEBUG] 列（合作者）数量: {len(heatmap_df.columns)}")
    
    # N_{B,C} 矩阵
    pair_data = []
    for c in collaborators:
        row = []
        for b in collaborators:
            row.append(pair_counts[c].get(b, 0))
        pair_data.append(row)
    pair_df = pd.DataFrame(pair_data, index=collaborators, columns=collaborators)

    # N_{RUS,C} 与 N_C 向量
    n_rus_c_series = pd.Series(russia_pair_counts).reindex(collaborators, fill_value=0)
    n_c_series = pd.Series(total_publications).reindex(collaborators, fill_value=0)

    return heatmap_df, counts_df, pair_df, n_rus_c_series.to_frame(name="N_RUS_C"), n_c_series.to_frame(name="N_C")


def plot_heatmap(
    heatmap_df: pd.DataFrame,
    title: str,
    output_path: str,
    use_log: bool = False,
    use_diverging: bool = True,
    center_value: float = 1.0,
) -> None:
    """
    使用 seaborn 绘制 heatmap 并保存为图片。
    行的label写在上面（使用xticklabels显示行标签）。
    """
    plt.figure(figsize=(max(12, len(heatmap_df.columns) * 0.4), max(10, len(heatmap_df.index) * 0.4)))

    plot_df = heatmap_df
    cbar_label = "Observed / Expected (S_C)"
    if use_log:
        # 对两个时间段的可视化取 log（避免 0 导致 -inf）
        plot_df = np.log1p(heatmap_df)
        cbar_label = "log1p(S_C)"
    
    # 计算数据的最大值和最小值，并缩放到70%作为colorbar范围
    raw_min = plot_df.min().min()
    raw_max = plot_df.max().max()
    vmin = raw_min * 0.7
    vmax = raw_max * 0.7
    # 避免极端情况下vmin==vmax导致报错
    if vmin == vmax:
        vmin = None
        vmax = None

    cmap = "viridis"
    norm = None
    if use_diverging:
        # 以 1 作为分界线（log时使用 log1p(1)）
        center = np.log1p(center_value) if use_log else center_value
        if vmin is not None and vmax is not None: 
            # 确保 vmin < vcenter < vmax
            vmin = min(vmin, center)
            vmax = max(vmax, center)
            if vmin == center:
                vmin = center - 1e-6
            if vmax == center:
                vmax = center + 1e-6
            norm = colors.TwoSlopeNorm(vmin=vmin, vcenter=center, vmax=vmax)
        cmap = "RdBu_r"
    
    # 绘制heatmap，行标签显示在上面（使用xticklabels='top'）
    ax = sns.heatmap(
        plot_df,
        cmap=cmap,
        cbar_kws={"label": cbar_label},
        vmin=None if norm is not None else vmin,
        vmax=None if norm is not None else vmax,
        norm=norm,
        xticklabels=True,
        yticklabels=True,
    )
    
    # 将x轴标签移到上方
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    
    # 旋转x轴标签以便阅读
    plt.setp(ax.get_xticklabels(), rotation=90, ha='left')
    plt.setp(ax.get_yticklabels(), rotation=0)
    
    plt.title(title, pad=20)
    plt.xlabel("Collaborator (with Russia)", labelpad=10)  # x轴是列（collab_col），即合作者
    plt.ylabel("Third country (collaborator)", labelpad=10)  # y轴是行（collab_row），即第三国家
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def run_for_period(
    start_year: int,
    end_year: int,
    df: pd.DataFrame,
    unified_collaborators: List[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    """
    针对指定年份区间，计算合作者之间的 S_C heatmap，并输出图片。

    参数：
    - start_year, end_year: 年份区间
    - df: 数据框
    - unified_collaborators: 统一的合作者列表

    返回：
    - heatmap_df: S_C 矩阵（维度为 len(collaborators) x len(collaborators)）
    - counts_df: Observed_{RUS,C,B} 计数矩阵（与heatmap_df同维度）
    - total_publications: 每个国家 N_C（来自 Total_Publications）
    """
    # 使用统一的合作者列表
    period_df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    period_df["country_list"] = period_df["countries"].apply(parse_countries)

    collaborators = unified_collaborators
    total_publications = load_country_total_publications(start_year, end_year)

    # 构建heatmap：只在这30个合作者之间计算 S_C
    print(f"  [INFO] 输入的合作者数量: {len(collaborators)}")
    print(f"  [INFO] Total_Publications中有值的合作者数量: {len([c for c in collaborators if total_publications.get(c, 0) > 0])}")
    
    heatmap_df, counts_df, pair_df, n_rus_c_df, n_c_df = build_collaborator_heatmap(
        period_df, collaborators, total_publications
    )

    title = f"Russia collaborator S_C heatmap ({start_year}-{end_year})"
    output_path = (
        f"{base_dir}"
        f"russia_collaborator_heatmap_{start_year}_{end_year}.png"
    )
    plot_heatmap(heatmap_df, title, output_path, use_log=False)
    print(f"Saved heatmap to: {output_path}")
    print(f"  Heatmap dimensions: {len(heatmap_df.index)} 行 x {len(heatmap_df.columns)} 列 (应该是30x30)")
    print(f"  行索引（第三国家）: {list(heatmap_df.index)[:5]}..." if len(heatmap_df.index) > 5 else f"  行索引（第三国家）: {list(heatmap_df.index)}")
    print(f"  列索引（合作者）: {list(heatmap_df.columns)[:5]}..." if len(heatmap_df.columns) > 5 else f"  列索引（合作者）: {list(heatmap_df.columns)}")

    period_label = f"{start_year}_{end_year}"
    counts_df.to_csv(f"{base_dir}russia_observed_RUS_C_B_{period_label}.csv")
    pair_df.to_csv(f"{base_dir}russia_pair_counts_B_C_{period_label}.csv")
    n_rus_c_df.to_csv(f"{base_dir}russia_N_RUS_C_{period_label}.csv")
    n_c_df.to_csv(f"{base_dir}russia_N_C_{period_label}.csv")

    return heatmap_df, counts_df, pair_df, n_rus_c_df, n_c_df, total_publications


def calculate_difference_matrix(
    heatmap1: pd.DataFrame, 
    heatmap2: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    计算两个时间段 heatmap 的差值矩阵（用于桥接效应分析）。
    
    注意：这里**严格保持原有行列顺序**，假定 `heatmap1` 和 `heatmap2`
    都是用同一个 `collaborators` 列表（即 `top_collabs`）构建的。
    
    参数：
    - heatmap1: 第一个时间段的heatmap（n×n矩阵）
    - heatmap2: 第二个时间段的heatmap（n×n矩阵）
    
    返回：
    - diff_df: 差值矩阵（period2 - period1），正值表示桥接能力增强，负值表示减弱
    - h1_aligned: 与 diff_df 同索引/列顺序的第一个时间段heatmap
    - h2_aligned: 与 diff_df 同索引/列顺序的第二个时间段heatmap
    """
    # 直接按原顺序对齐（假定两个矩阵的索引和列相同且顺序一致）
    h1_aligned = heatmap1.copy()
    h2_aligned = heatmap2.reindex(index=h1_aligned.index, columns=h1_aligned.columns, fill_value=0.0)

    diff_df = h2_aligned - h1_aligned
    
    return diff_df, h1_aligned, h2_aligned


def plot_difference_heatmap(
    diff_df: pd.DataFrame, title: str, output_path: str,
    period1: Tuple[int, int], period2: Tuple[int, int],
) -> None:
    """
    绘制差值 heatmap（用于可视化桥接效应的变化）。
    行的label写在上面。
    """
    plt.figure(figsize=(max(12, len(diff_df.columns) * 0.4), max(10, len(diff_df.index) * 0.4)))
    
    # 计算数据的最大值和最小值，并缩放到70%作为colorbar范围
    raw_min = diff_df.min().min()
    raw_max = diff_df.max().max()
    vmin = raw_min * 0.7
    vmax = raw_max * 0.7
    # 避免极端情况下vmin==vmax导致报错
    if vmin == vmax:
        vmin = None
        vmax = None
    
    # 绘制heatmap，行标签显示在上面
    period1_label = f"{period1[0]}-{period1[1]}"
    period2_label = f"{period2[0]}-{period2[1]}"
    ax = sns.heatmap(
        diff_df,
        cmap="RdBu_r",
        center=0,
        cbar_kws={"label": f"Change in S_C ({period2_label}) - ({period1_label})"},
        vmin=vmin,
        vmax=vmax,
        xticklabels=True,
        yticklabels=True,
    )
    
    # 将x轴标签移到上方
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    
    # 旋转x轴标签以便阅读
    plt.setp(ax.get_xticklabels(), rotation=90, ha='left')
    plt.setp(ax.get_yticklabels(), rotation=0)
    
    plt.title(title, pad=20)
    plt.xlabel("Collaborator (with Russia)", labelpad=10)  # x轴是列（collab_col），即合作者
    plt.ylabel("Third country (collaborator)", labelpad=10)  # y轴是行（collab_row），即第三国家
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def analyze_bridging_effect(
    diff_df: pd.DataFrame, 
    heatmap1: pd.DataFrame, 
    heatmap2: pd.DataFrame
) -> Dict:
    """
    分析合作者概率的变化，找出变化最大的合作者对。
    区分真正的概率变化和新出现/消失的连接。
    
    参数：
    - diff_df: 差值矩阵（行是合作者，列是第三国家）
    - heatmap1: 第一个时间段的heatmap
    - heatmap2: 第二个时间段的heatmap
    
    返回：
    - 包含各种统计信息的字典
    """
    # 将矩阵转换为长格式（便于分析）
    diff_long = diff_df.stack().reset_index()
    diff_long.columns = ['Third_Country', 'Collaborator', 'Difference']
    
    # 同时获取两个时间段的原始值
    h1_long = heatmap1.reindex(
        index=diff_df.index, 
        columns=diff_df.columns, 
        fill_value=0.0
    ).stack().reset_index()
    h1_long.columns = ['Third_Country', 'Collaborator', 'Value_Period1']
    
    h2_long = heatmap2.reindex(
        index=diff_df.index, 
        columns=diff_df.columns, 
        fill_value=0.0
    ).stack().reset_index()
    h2_long.columns = ['Third_Country', 'Collaborator', 'Value_Period2']
    
    # 合并数据
    analysis_df = diff_long.merge(h1_long, on=['Third_Country', 'Collaborator'])
    analysis_df = analysis_df.merge(h2_long, on=['Third_Country', 'Collaborator'])
    
    # 分类：真正的变化 vs 新出现/消失
    # 真正的概率变化：两个时间段都有值（>0）
    analysis_df['Both_Periods_Have_Value'] = (
        (analysis_df['Value_Period1'] > 0) & (analysis_df['Value_Period2'] > 0)
    )
    analysis_df['New_Bridge'] = (
        (analysis_df['Value_Period1'] == 0) & (analysis_df['Value_Period2'] > 0)
    )
    analysis_df['Lost_Bridge'] = (
        (analysis_df['Value_Period1'] > 0) & (analysis_df['Value_Period2'] == 0)
    )
    
    # 移除差值为0的（没有变化）
    diff_nonzero = analysis_df[analysis_df['Difference'] != 0].copy()
    
    # 找出真正的概率增强最大的前10个（两个时间段都有值）
    real_increases = diff_nonzero[
        diff_nonzero['Both_Periods_Have_Value'] & (diff_nonzero['Difference'] > 0)
    ].nlargest(10, 'Difference')
    
    # 找出真正的概率减弱最大的前10个（两个时间段都有值）
    real_decreases = diff_nonzero[
        diff_nonzero['Both_Periods_Have_Value'] & (diff_nonzero['Difference'] < 0)
    ].nsmallest(10, 'Difference')
    
    # 找出新出现的连接（第一个时间段为0，第二个时间段有值）
    new_bridges = diff_nonzero[diff_nonzero['New_Bridge']].nlargest(10, 'Value_Period2')
    
    # 找出消失的连接（第一个时间段有值，第二个时间段为0）
    lost_bridges = diff_nonzero[diff_nonzero['Lost_Bridge']].nlargest(10, 'Value_Period1')
    
    # 为了兼容性，保留原来的top_increases和top_decreases
    top_increases = diff_nonzero.nlargest(10, 'Difference')
    top_decreases = diff_nonzero.nsmallest(10, 'Difference')
    
    # 按合作者汇总统计
    collaborator_stats = diff_long.groupby('Collaborator').agg({
        'Difference': ['mean', 'std', 'max', 'min', 'count']
    }).round(2)
    collaborator_stats.columns = ['Mean_Change', 'Std_Change', 'Max_Increase', 'Max_Decrease', 'Num_Connections']
    collaborator_stats = collaborator_stats.sort_values('Mean_Change', ascending=False)
    
    # 按第三国家汇总统计
    third_country_stats = diff_long.groupby('Third_Country').agg({
        'Difference': ['mean', 'std', 'max', 'min', 'count']
    }).round(2)
    third_country_stats.columns = ['Mean_Change', 'Std_Change', 'Max_Increase', 'Max_Decrease', 'Num_Connections']
    third_country_stats = third_country_stats.sort_values('Mean_Change', ascending=False)
    
    # 整体统计
    overall_stats = {
        'Total_Cells': len(diff_long),
        'Non_Zero_Changes': len(diff_nonzero),
        'Positive_Changes': len(diff_nonzero[diff_nonzero['Difference'] > 0]),
        'Negative_Changes': len(diff_nonzero[diff_nonzero['Difference'] < 0]),
        'Mean_Difference': diff_long['Difference'].mean(),
        'Std_Difference': diff_long['Difference'].std(),
        'Max_Increase': diff_long['Difference'].max(),
        'Max_Decrease': diff_long['Difference'].min(),
    }
    
    return {
        'top_increases': top_increases,
        'top_decreases': top_decreases,
        'real_increases': real_increases,
        'real_decreases': real_decreases,
        'new_bridges': new_bridges,
        'lost_bridges': lost_bridges,
        'collaborator_stats': collaborator_stats,
        'third_country_stats': third_country_stats,
        'overall_stats': overall_stats,
        'full_data': analysis_df,
    }


def save_to_excel(
    diff_df: pd.DataFrame,
    heatmap1: pd.DataFrame,
    heatmap2: pd.DataFrame,
    counts1: pd.DataFrame,
    counts2: pd.DataFrame,
    analysis: Dict,
    output_path: str,
    period1_label: str,
    period2_label: str,
) -> None:
    """
    将差值矩阵、原始heatmap和统计分析保存到Excel文件。
    
    参数：
    - diff_df: 差值矩阵
    - heatmap1: 第一个时间段的heatmap（对齐后）
    - heatmap2: 第二个时间段的heatmap（对齐后）
    - analysis: 统计分析结果
    - output_path: Excel文件保存路径
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: 差值矩阵
        diff_df.to_excel(writer, sheet_name='Difference_Matrix', index=True)
        
        # Sheet 2: 第一个时间段heatmap（对齐后，百分比）
        heatmap1.to_excel(writer, sheet_name=f'{period1_label}_Heatmap', index=True)
        
        # Sheet 3: 第二个时间段heatmap（对齐后，百分比）
        heatmap2.to_excel(writer, sheet_name=f'{period2_label}_Heatmap', index=True)
        
        # Sheet 4: 第一个时间段的真实论文数矩阵（对齐后）
        counts1.to_excel(writer, sheet_name=f'{period1_label}_Counts', index=True)
        
        # Sheet 5: 第二个时间段的真实论文数矩阵（对齐后）
        counts2.to_excel(writer, sheet_name=f'{period2_label}_Counts', index=True)
        
        # Sheet 6: 真正的概率增强（两个时间段都有值）
        if len(analysis['real_increases']) > 0:
            analysis['real_increases'].head(20).to_excel(
                writer, sheet_name='Real_Increases', index=False
            )
        
        # Sheet 7: 真正的概率减弱（两个时间段都有值）
        if len(analysis['real_decreases']) > 0:
            analysis['real_decreases'].head(20).to_excel(
                writer, sheet_name='Real_Decreases', index=False
            )
        
        # Sheet 8: 所有变化（包括新出现和消失）
        analysis['real_increases'].head(20).to_excel(writer, sheet_name='All_Top_Increases', index=False)
        analysis['real_decreases'].head(20).to_excel(writer, sheet_name='All_Top_Decreases', index=False)
        
        # Sheet 9: 按合作者（行）汇总统计
        analysis['collaborator_stats'].to_excel(
            writer, sheet_name='Collaborator_Stats', index=True
        )
        
        # Sheet 10: 按第三国家（列）汇总统计
        analysis['third_country_stats'].to_excel(
            writer, sheet_name='Third_Country_Stats', index=True
        )
        
        # Sheet 11: 完整数据（长格式，包含两个时间段的原始值）
        analysis['full_data'].to_excel(writer, sheet_name='Full_Data', index=False)
        
        # Sheet 12: 整体统计摘要
        overall_df = pd.DataFrame([analysis['overall_stats']])
        overall_df.to_excel(writer, sheet_name='Summary_Stats', index=False)
    
    print(f"Saved Excel file to: {output_path}")


def main():
    df = load_aggregated_articles(start_year=2019, end_year=2024)

    period1 = (2019, 2021)
    period2 = (2022, 2024)
    period1_label = f"{period1[0]}-{period1[1]}"
    period2_label = f"{period2[0]}-{period2[1]}"

    # 在 2019-2024 中计算 top30 合作者
    top_collabs = get_top_collaborators_all_years(df, top_n=30)
    print(f"\nTop 30 合作者（基于所有年份数据，共 {len(top_collabs)} 个国家）:")
    print(f"  这些合作者将作为heatmap的行和列，计算 S_C（Observed/Expected）")
    print(f"  {', '.join(top_collabs[:10])}..." if len(top_collabs) > 10 else f"  {', '.join(top_collabs)}")
    print()

    # 使用top30合作者集合计算两个时间段的 heatmap 和真实论文数矩阵
    heatmap1, counts1, pair1, n_rus_c1, n_c1, base_counts1 = run_for_period(
        period1[0], period1[1], df, top_collabs
    )
    print()
    heatmap2, counts2, pair2, n_rus_c2, n_c2, base_counts2 = run_for_period(
        period2[0], period2[1], df, top_collabs
    )
    print()

    # 计算差值矩阵（用于桥接效应分析）
    diff_df, h1_aligned, h2_aligned = calculate_difference_matrix(heatmap1, heatmap2)

    # 将真实论文数矩阵按相同索引/列对齐
    counts1_aligned = counts1.reindex(index=h1_aligned.index, columns=h1_aligned.columns, fill_value=0.0)
    counts2_aligned = counts2.reindex(index=h2_aligned.index, columns=h2_aligned.columns, fill_value=0.0)
    diff_output = (
        f"{base_dir}"
        f"russia_collaborator_difference_{period1_label}_vs_{period2_label}.png"
    )
    plot_difference_heatmap(
        diff_df,
        f"Russia Collaborator Probability Change: ({period2_label}) - ({period1_label})",
        diff_output,
        period1,
        period2,
    )
    print(f"Saved difference heatmap to: {diff_output}")
    print("\n差值矩阵说明：")
    print("  - 行：合作者（与Russia合作的国家）")
    print("  - 列：第三国家（也是这30个合作者之一）")
    print("  - 值：S_C 变化（period2 - period1）")
    print("  - 正值（红色）：S_C 增加")
    print("  - 负值（蓝色）：S_C 减少")
    print("  - 接近0：S_C 基本不变")
    
    # 进行合作者概率变化分析
    print("\n" + "="*60)
    print("合作者概率变化分析")
    print("="*60)
    analysis = analyze_bridging_effect(diff_df, h1_aligned, h2_aligned)
    
    # 打印整体统计
    print("\n整体统计：")
    stats = analysis['overall_stats']
    print(f"  总单元格数: {stats['Total_Cells']}")
    print(f"  有变化的单元格数: {stats['Non_Zero_Changes']}")
    print(f"  概率增加的数量: {stats['Positive_Changes']}")
    print(f"  概率减少的数量: {stats['Negative_Changes']}")
    print(f"  平均变化: {stats['Mean_Difference']:.2f}")
    print(f"  标准差: {stats['Std_Difference']:.2f}")
    print(f"  最大增加: {stats['Max_Increase']:.2f}")
    print(f"  最大减少: {stats['Max_Decrease']:.2f}")
    
    # 打印真正的概率增强最大的前5个（两个时间段都有值）
    print("\n真正的概率增强最大的前5个（两个时间段都有值）：")
    if len(analysis['real_increases']) > 0:
        for idx, row in analysis['real_increases'].head(5).iterrows():
            print(f"  {row['Collaborator']} (行) → {row['Third_Country']} (列): "
                  f"{row['Value_Period1']:.2f} → {row['Value_Period2']:.2f} "
                  f"(+{row['Difference']:.2f})")
    else:
        print("  （无）")
    
    # 打印新出现的连接（第一个时间段为0，第二个时间段有值）
    print("\n新出现的连接（第一个时间段为0，第二个时间段有值）前5个：")
    if len(analysis['new_bridges']) > 0:
        for idx, row in analysis['new_bridges'].head(5).iterrows():
            print(f"  {row['Collaborator']} (行) → {row['Third_Country']} (列): "
                  f"0 → {row['Value_Period2']:.2f} (新出现)")
    else:
        print("  （无）")
    
    # 打印真正的概率减弱最大的前5个（两个时间段都有值）
    print("\n真正的概率减弱最大的前5个（两个时间段都有值）：")
    if len(analysis['real_decreases']) > 0:
        for idx, row in analysis['real_decreases'].head(5).iterrows():
            print(f"  {row['Collaborator']} (行) → {row['Third_Country']} (列): "
                  f"{row['Value_Period1']:.2f} → {row['Value_Period2']:.2f} "
                  f"({row['Difference']:.2f})")
    else:
        print("  （无）")
    
    # 打印概率平均增强最大的前5个合作者（作为行）
    print("\n概率平均增强最大的前5个合作者（作为行）：")
    top_collabs = analysis['collaborator_stats'].head(5)
    for collab, row in top_collabs.iterrows():
        print(f"  {collab}: 平均变化 {row['Mean_Change']:.2f}, "
              f"连接了 {int(row['Num_Connections'])} 个其他合作者")
    
    # 保存到Excel
    excel_output = (
        f"{base_dir}"
        f"russia_collaborator_analysis_{period1_label}_vs_{period2_label}.xlsx"
    )
    save_to_excel(
        diff_df,
        h1_aligned,
        h2_aligned,
        counts1_aligned,
        counts2_aligned,
        analysis,
        excel_output,
        period1_label,
        period2_label,
    )
    print("\n" + "="*60)


if __name__ == "__main__":
    main()