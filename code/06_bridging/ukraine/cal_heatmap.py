
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent



import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import List, Tuple, Dict


PAPERS_FILE = str(CODE / "00_data_processing/ukraine_articles/ukraine_articles.txt")
UKRAINE_NAME = "UKRAINE"
FOCAL_COUNTRY = UKRAINE_NAME
FOCAL_LABEL = "Ukraine"
FOCAL_FILE_PREFIX = "ukraine"

base_dir = str(HERE)


def load_data(papers_file: str = PAPERS_FILE) -> pd.DataFrame:
    """
    读取原始 Ukraine 文章数据，只保留年份和国家字段。
    """
    df = pd.read_csv(
        papers_file,
        dtype={"OST_BK": "Int64", "Annee_Bibliographique": "Int64", "countries": "string"},
    )
    # 确保字段名一致
    df = df[["Annee_Bibliographique", "countries"]].rename(
        columns={"Annee_Bibliographique": "year"}
    )
    # 去掉缺失/空的国家字段
    df = df.dropna(subset=["countries"])
    return df


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


def get_top_collaborators_all_years(
    df: pd.DataFrame,
    top_n: int = 30,
) -> List[str]:
    """
    在所有年份中，计算与 Ukraine 合作次数最多的前 top_n 个国家。

    参数：
    - df: 数据框
    - top_n: 取前 top_n 个合作者

    返回：
    - 合作者列表（按合作次数从高到低排序）
    """
    # 使用所有年份的数据
    all_years_df = df.copy()
    all_years_df["country_list"] = all_years_df["countries"].apply(parse_countries)

    # 只保留包含 Ukraine 的文章
    all_years_df = all_years_df[all_years_df["country_list"].apply(lambda lst: UKRAINE_NAME in lst)]

    co_counts: Dict[str, int] = defaultdict(int)
    for countries in all_years_df["country_list"]:
        for c in countries:
            if c != UKRAINE_NAME:
                co_counts[c] += 1

    # 按合作次数排序，取前 top_n
    sorted_collabs = sorted(co_counts.items(), key=lambda x: x[1], reverse=True)
    top_collabs = [c for c, _ in sorted_collabs[:top_n]]

    return top_collabs


def build_collaborator_heatmap(
    period_df: pd.DataFrame,
    collaborators: List[str],
    base_counts: Dict[str, int],
) -> pd.DataFrame:
    """
    构建合作者之间的heatmap矩阵。
    
    参数：
    - 行（collab_row）：合作者（作为第三国家）
    - 列（collab_col）：合作者（作为合作者）
    - 值：概率（百分比）
      - 非对角线：对于合作者A（行）和合作者B（列），计算在"Ukraine + B"的文章中，A也出现的比例。
        例如：China是列，US是行，则值 = (Ukraine+China+US的文章数) / (Ukraine+China的文章数) * 100
      - 对角线：对于合作者A（行=列），计算在"Ukraine + A"的文章中，只有Ukraine和A两个国家的情况占比。
        例如，China-China位置的值表示在"Ukraine+China"的合作中，只有China占的比例（即只有Ukraine和China两个国家的文章占比）。
    
    返回：
    - heatmap DataFrame，维度为 len(collaborators) x len(collaborators)
    """
    # 对于每个合作者B（列），统计其他合作者A（行）作为第三国家出现的次数
    # 注意：同一篇论文若包含多个第三国家，则每个第三国家都会单独统计一次
    third_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for countries in period_df["country_list"]:
        if UKRAINE_NAME not in countries:
            continue

        countries_set = set(countries)
        # 对于每个合作者B（列）
        for collab_col in collaborators:
            # 只在同时包含 Ukraine 和该合作者B的文章中统计
            if collab_col not in countries_set:
                continue
            
            # 找到同时出现的第三国家（限定在 collaborators 集合内，且排除 Ukraine 与 collab_col）
            other_collabs = countries_set - {UKRAINE_NAME, collab_col}
            third_list = [c for c in other_collabs if c in collaborators]

            if not third_list:
                # 对角线：如果没有第三国家，则表示"只有 Ukraine 和 collab_col"
                third_counts[collab_col][collab_col] += 1
            else:
                for third in third_list:
                    third_counts[third][collab_col] += 1

    # 构建矩阵：百分比（0-100）
    # 行（collab_row）：合作者（作为第三国家）
    # 列（collab_col）：合作者（作为合作者）
    # 值：在"Ukraine + collab_col"的文章中，collab_row也出现的比例
    # 例如：China是列，US是行，则值 = (Ukraine+China+US的文章数) / (Ukraine+China的文章数) * 100
    # 对角线上的值：在"Ukraine + 合作者"的文章中，只有Ukraine和该合作者两个国家的情况占比
    data = []
    for collab_row in collaborators:
        row = []
        for collab_col in collaborators:
            base = base_counts.get(collab_col, 0)  # "Ukraine + collab_col"的文章总数
            if base == 0:
                val = 0.0
            else:
                cnt = third_counts[collab_row].get(collab_col, 0)  # "Ukraine + collab_col + collab_row"的文章数
                val = cnt / base * 100.0  # 比例 = (Ukraine+col+row的文章数) / (Ukraine+col的文章数) * 100
            row.append(val)
        data.append(row)

    heatmap_df = pd.DataFrame(data, index=collaborators, columns=collaborators)
    
    # 调试信息：确认矩阵维度
    print(f"  [DEBUG] Heatmap矩阵维度: {len(heatmap_df.index)} 行 x {len(heatmap_df.columns)} 列")
    print(f"  [DEBUG] 行（第三国家）数量: {len(heatmap_df.index)}")
    print(f"  [DEBUG] 列（合作者）数量: {len(heatmap_df.columns)}")
    
    return heatmap_df


def plot_heatmap(heatmap_df: pd.DataFrame, title: str, output_path: str) -> None:
    """
    使用 seaborn 绘制 heatmap 并保存为图片。
    行的label写在上面（使用xticklabels显示行标签）。
    """
    plt.figure(figsize=(max(12, len(heatmap_df.columns) * 0.4), max(10, len(heatmap_df.index) * 0.4)))
    
    # 计算数据的最大值和最小值，并缩放到70%作为colorbar范围
    raw_min = heatmap_df.min().min()
    raw_max = heatmap_df.max().max()
    vmin = raw_min * 0.7
    vmax = raw_max * 0.7
    # 避免极端情况下vmin==vmax导致报错
    if vmin == vmax:
        vmin = None
        vmax = None
    
    # 绘制heatmap，行标签显示在上面（使用xticklabels='top'）
    ax = sns.heatmap(
        heatmap_df,
        cmap="viridis",
        cbar_kws={"label": "Probability (%)"},
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
    plt.xlabel("Collaborator (with Ukraine)", labelpad=10)  # x轴是列（collab_col），即合作者
    plt.ylabel("Third country (collaborator)", labelpad=10)  # y轴是行（collab_row），即第三国家
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def run_for_period(
    start_year: int,
    end_year: int,
    df: pd.DataFrame,
    unified_collaborators: List[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    """
    针对指定年份区间，计算合作者之间的heatmap，并输出图片。

    参数：
    - start_year, end_year: 年份区间
    - df: 数据框
    - unified_collaborators: 统一的合作者列表

    返回：
    - heatmap_df: 概率矩阵（维度为 len(collaborators) x len(collaborators)）
    - counts_df: 真实论文篇数矩阵（与heatmap_df同维度）
    - base_counts: 每个合作者（列）对应的"Ukraine+合作者"论文总数
    """
    # 使用统一的合作者列表
    period_df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    period_df["country_list"] = period_df["countries"].apply(parse_countries)
    period_df = period_df[period_df["country_list"].apply(lambda lst: UKRAINE_NAME in lst)]

    # 计算统一列表中每个合作者在该时间段的合作篇数
    co_counts: Dict[str, int] = defaultdict(int)
    for countries in period_df["country_list"]:
        for c in countries:
            if c != UKRAINE_NAME and c in unified_collaborators:
                co_counts[c] += 1

    collaborators = unified_collaborators
    base_counts = {c: co_counts[c] for c in collaborators}
    print(base_counts)

    # 构建heatmap：只在这30个合作者之间计算概率
    print(f"  [INFO] 输入的合作者数量: {len(collaborators)}")
    print(f"  [INFO] base_counts中有值的合作者数量: {len([c for c in collaborators if base_counts.get(c, 0) > 0])}")
    
    heatmap_df = build_collaborator_heatmap(period_df, collaborators, base_counts)

    # 根据概率矩阵和base_counts反推真实论文数矩阵
    counts_df = pd.DataFrame(0.0, index=collaborators, columns=collaborators)
    for collab_col in collaborators:
        base = base_counts.get(collab_col, 0)
        if base == 0:
            continue
        # heatmap_df中是百分比，需要 /100 再乘以base
        counts_df[collab_col] = heatmap_df[collab_col] * base / 100.0

    title = f"Ukraine collaborator probability heatmap ({start_year}-{end_year})"
    output_path = (
        f"{base_dir}"
        f"ukraine_collaborator_heatmap_{start_year}_{end_year}.png"
    )
    plot_heatmap(heatmap_df, title, output_path)
    print(f"Saved heatmap to: {output_path}")
    print(f"  Heatmap dimensions: {len(heatmap_df.index)} 行 x {len(heatmap_df.columns)} 列 (应该是30x30)")
    print(f"  行索引（第三国家）: {list(heatmap_df.index)[:5]}..." if len(heatmap_df.index) > 5 else f"  行索引（第三国家）: {list(heatmap_df.index)}")
    print(f"  列索引（合作者）: {list(heatmap_df.columns)[:5]}..." if len(heatmap_df.columns) > 5 else f"  列索引（合作者）: {list(heatmap_df.columns)}")

    return heatmap_df, counts_df, base_counts


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
        cbar_kws={"label": f"Change in % ({period2_label}) - ({period1_label})"},
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
    plt.xlabel("Collaborator (with Ukraine)", labelpad=10)  # x轴是列（collab_col），即合作者
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
    df = load_data(PAPERS_FILE)

    period1 = (2019, 2021)
    period2 = (2022, 2024)
    period1_label = f"{period1[0]}-{period1[1]}"
    period2_label = f"{period2[0]}-{period2[1]}"

    # 在所有年份中计算top30合作者
    top_collabs = get_top_collaborators_all_years(df, top_n=30)
    print(f"\nTop 30 合作者（基于所有年份数据，共 {len(top_collabs)} 个国家）:")
    print(f"  这些合作者将作为heatmap的行和列，计算彼此作为合作者或第三国家的概率")
    print(f"  {', '.join(top_collabs[:10])}..." if len(top_collabs) > 10 else f"  {', '.join(top_collabs)}")
    print()

    # 使用top30合作者集合计算两个时间段的 heatmap 和真实论文数矩阵
    heatmap1, counts1, base_counts1 = run_for_period(period1[0], period1[1], df, top_collabs)
    print()
    heatmap2, counts2, base_counts2 = run_for_period(period2[0], period2[1], df, top_collabs)
    print()

    # 计算差值矩阵（用于桥接效应分析）
    diff_df, h1_aligned, h2_aligned = calculate_difference_matrix(heatmap1, heatmap2)

    # 将真实论文数矩阵按相同索引/列对齐
    counts1_aligned = counts1.reindex(index=h1_aligned.index, columns=h1_aligned.columns, fill_value=0.0)
    counts2_aligned = counts2.reindex(index=h2_aligned.index, columns=h2_aligned.columns, fill_value=0.0)
    diff_output = (
        f"{base_dir}"
        f"ukraine_collaborator_difference_{period1_label}_vs_{period2_label}.png"
    )
    plot_difference_heatmap(
        diff_df,
        f"Ukraine Collaborator Probability Change: ({period2_label}) - ({period1_label})",
        diff_output,
        period1,
        period2,
    )
    print(f"Saved difference heatmap to: {diff_output}")
    print("\n差值矩阵说明：")
    print("  - 行：合作者（与Ukraine合作的国家）")
    print("  - 列：第三国家（也是这30个合作者之一）")
    print("  - 值：概率变化（period2 - period1）")
    print("  - 正值（红色）：概率增加（该合作者作为第三国家出现的概率增加）")
    print("  - 负值（蓝色）：概率减少")
    print("  - 接近0：概率基本不变")
    
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
    print(f"  平均变化: {stats['Mean_Difference']:.2f}%")
    print(f"  标准差: {stats['Std_Difference']:.2f}%")
    print(f"  最大增加: {stats['Max_Increase']:.2f}%")
    print(f"  最大减少: {stats['Max_Decrease']:.2f}%")
    
    # 打印真正的概率增强最大的前5个（两个时间段都有值）
    print("\n真正的概率增强最大的前5个（两个时间段都有值）：")
    if len(analysis['real_increases']) > 0:
        for idx, row in analysis['real_increases'].head(5).iterrows():
            print(f"  {row['Collaborator']} (行) → {row['Third_Country']} (列): "
                  f"{row['Value_Period1']:.2f}% → {row['Value_Period2']:.2f}% "
                  f"(+{row['Difference']:.2f}%)")
    else:
        print("  （无）")
    
    # 打印新出现的连接（第一个时间段为0，第二个时间段有值）
    print("\n新出现的连接（第一个时间段为0，第二个时间段有值）前5个：")
    if len(analysis['new_bridges']) > 0:
        for idx, row in analysis['new_bridges'].head(5).iterrows():
            print(f"  {row['Collaborator']} (行) → {row['Third_Country']} (列): "
                  f"0% → {row['Value_Period2']:.2f}% (新出现)")
    else:
        print("  （无）")
    
    # 打印真正的概率减弱最大的前5个（两个时间段都有值）
    print("\n真正的概率减弱最大的前5个（两个时间段都有值）：")
    if len(analysis['real_decreases']) > 0:
        for idx, row in analysis['real_decreases'].head(5).iterrows():
            print(f"  {row['Collaborator']} (行) → {row['Third_Country']} (列): "
                  f"{row['Value_Period1']:.2f}% → {row['Value_Period2']:.2f}% "
                  f"({row['Difference']:.2f}%)")
    else:
        print("  （无）")
    
    # 打印概率平均增强最大的前5个合作者（作为行）
    print("\n概率平均增强最大的前5个合作者（作为行）：")
    top_collabs = analysis['collaborator_stats'].head(5)
    for collab, row in top_collabs.iterrows():
        print(f"  {collab}: 平均变化 {row['Mean_Change']:.2f}%, "
              f"连接了 {int(row['Num_Connections'])} 个其他合作者")
    
    # 保存到Excel
    excel_output = (
        f"{base_dir}"
        f"ukraine_collaborator_analysis_{period1_label}_vs_{period2_label}.xlsx"
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