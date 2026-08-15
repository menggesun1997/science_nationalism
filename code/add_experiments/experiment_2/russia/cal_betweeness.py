import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from collections import defaultdict
from typing import List, Tuple, Dict
import networkx as nx
import numpy as np

PAPERS_FILE = "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/eu_articles/eu_articles.txt"
EU_COUNTRIES = [
    'AUSTRIA', 'BELGIUM', 'BULGARIA', 'CROATIA', 'CYPRUS', 
    'CZECHIA', 'DENMARK', 'ESTONIA', 'FINLAND', 'FRANCE', 
    'GERMANY', 'GREECE', 'HUNGARY', 'IRELAND', 'ITALY', 
    'LATVIA', 'LITHUANIA', 'LUXEMBOURG', 'MALTA', 'NETHERLANDS', 
    'POLAND', 'PORTUGAL', 'ROMANIA', 'SLOVAK REPUBLIC', 'SLOVENIA', 
    'SPAIN', 'SWEDEN'
]
EU_NAME = "EU"  # 网络中EU节点的名称
COUNTRIES_STATS_FILE = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/0raw_publiations_process/brexit_experimental_data/countries_yearly_statistics.csv'

# 定义两个时期
PERIOD_1_START = 2014
PERIOD_1_END = 2016
PERIOD_2_START = 2022
PERIOD_2_END = 2024


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


def load_papers_data(file_path: str, start_year: int, end_year: int) -> pd.DataFrame:
    """加载指定时期的论文数据"""
    print(f"正在加载 {start_year}-{end_year} 年的数据...")
    
    df = pd.read_csv(
        file_path,
        dtype={'OST_BK': str, 'Annee_Bibliographique': int, 'countries': str}
    )
    
    # 重命名列
    df.columns = ['article_id', 'year', 'countries']
    
    # 筛选指定年份
    df = df[(df['year'] >= start_year) & (df['year'] <= end_year)]
    
    # 删除缺失值
    df = df.dropna(subset=['countries', 'year'])
    
    # 解析国家列表
    df['country_list'] = df['countries'].apply(parse_countries)
    
    # 只保留包含EU国家且是国际合作的文章
    # 只要包含任意一个EU国家就算包含EU
    df['has_eu'] = df['country_list'].apply(lambda x: any(country in EU_COUNTRIES for country in x))
    df['is_international'] = df['country_list'].apply(lambda x: len(x) > 1)
    
    eu_international_df = df[(df['has_eu']) & (df['is_international'])].copy()
    
    print(f"找到 {len(eu_international_df)} 篇包含EU国家的国际合作文章")
    
    return eu_international_df


def load_countries_stats(file_path: str) -> Dict[str, int]:
    """加载国家统计数据，返回每个国家的International_Collaborations总和"""
    print("正在加载国家统计数据...")
    
    df = pd.read_csv(file_path)
    
    # 计算每个国家的International_Collaborations总和（所有年份）
    country_totals = df.groupby('Country')['International_Collaborations'].sum().to_dict()
    
    # 计算EU整体的统计数据（所有EU国家的总和）
    eu_total = sum(country_totals.get(country, 0) for country in EU_COUNTRIES)
    country_totals[EU_NAME] = eu_total
    
    print(f"加载了 {len(country_totals)} 个国家的统计数据")
    print(f"EU整体的International_Collaborations总和: {eu_total}")
    
    return country_totals


def build_ego_centric_network(df: pd.DataFrame, country_stats: Dict[str, int]) -> nx.Graph:
    """
    构建EU的ego-centric网络
    
    网络包含：
    - EU节点（作为整体）
    - 所有与EU合作的国家（collaborators，不包括EU国家）
    - EU与每个collaborator的边
    - collaborator之间的边（如果它们之间有合作）
    
    权重计算：Papers_ij / sqrt(TotalPapers_i × TotalPapers_j)
    其中TotalPapers是International_Collaborations字段之和
    """
    print("正在构建ego-centric网络...")
    
    G = nx.Graph()
    
    # 找到所有与EU合作的国家（collaborators，不包括EU国家）
    collaborators = set()
    for country_list in df['country_list']:
        for country in country_list:
            if country not in EU_COUNTRIES:
                collaborators.add(country)
    
    print(f"找到 {len(collaborators)} 个collaborators")
    
    # 统计EU与每个collaborator的合作论文数
    # 只要论文中包含任意一个EU国家和collaborator，就算合作
    eu_collaborator_papers = defaultdict(int)
    for country_list in df['country_list']:
        has_eu_country = any(country in EU_COUNTRIES for country in country_list)
        if has_eu_country:
            for country in country_list:
                if country not in EU_COUNTRIES:
                    eu_collaborator_papers[country] += 1
    
    # 统计collaborator之间的合作论文数（不包括EU国家）
    collaborator_pairs_papers = defaultdict(int)
    for country_list in df['country_list']:
        # 找到所有collaborator对（不包括EU国家）
        collaborators_in_paper = [c for c in country_list if c not in EU_COUNTRIES]
        for i in range(len(collaborators_in_paper)):
            for j in range(i + 1, len(collaborators_in_paper)):
                pair = tuple(sorted([collaborators_in_paper[i], collaborators_in_paper[j]]))
                collaborator_pairs_papers[pair] += 1
    
    # 添加EU节点
    G.add_node(EU_NAME)
    
    # 添加collaborator节点
    for collaborator in collaborators:
        G.add_node(collaborator)
    
    # 添加EU与collaborator之间的边（权重）
    eu_total = country_stats.get(EU_NAME, 0)
    if eu_total == 0:
        print(f"警告: EU ({EU_NAME}) 在国家统计数据中未找到或International_Collaborations为0")
        eu_total = 1  # 避免除以零
    
    for collaborator, papers_count in eu_collaborator_papers.items():
        collab_total = country_stats.get(collaborator, 0)
        if collab_total == 0:
            print(f"警告: {collaborator} 在国家统计数据中未找到或International_Collaborations为0，跳过")
            continue
        
        # 计算权重：Papers_ij / sqrt(TotalPapers_i × TotalPapers_j)
        denominator = np.sqrt(eu_total * collab_total)
        if denominator == 0:
            print(f"警告: {collaborator} 的权重计算分母为0，跳过")
            continue
        
        strength = papers_count / denominator  # 合作强度
        # 存储强度（用于后续分析）
        G.add_edge(EU_NAME, collaborator, strength=strength, weight=strength)
        if len(eu_collaborator_papers) <= 50:  # 只打印前50个，避免输出过多
            print(f"EU-{collaborator}: {papers_count} papers, strength={strength:.6f}")
    
    # 添加collaborator之间的边（权重）
    for (c1, c2), papers_count in collaborator_pairs_papers.items():
        c1_total = country_stats.get(c1, 0)
        c2_total = country_stats.get(c2, 0)
        
        if c1_total == 0 or c2_total == 0:
            continue  # 跳过没有统计数据的国家对
        
        # 计算权重：Papers_ij / sqrt(TotalPapers_i × TotalPapers_j)
        denominator = np.sqrt(c1_total * c2_total)
        if denominator == 0:
            continue
        
        strength = papers_count / denominator  # 合作强度
        # 存储强度（用于后续分析）
        G.add_edge(c1, c2, strength=strength, weight=strength)
    
    print(f"网络构建完成：{G.number_of_nodes()} 个节点，{G.number_of_edges()} 条边")
    
    return G


def calculate_betweenness_from_eu(G: nx.Graph) -> Dict[str, float]:
    """
    从EU的角度计算每个collaborator的betweenness centrality
    
    使用有权网络的betweenness centrality
    """
    print("正在计算betweenness centrality...")
    
    # 检查网络是否为空或只有EU节点
    if G.number_of_nodes() <= 1 or G.number_of_edges() == 0:
        print("警告: 网络为空或没有边，无法计算betweenness")
        return {}
    
    # 使用有权网络的betweenness centrality
    # 注意：NetworkX的betweenness_centrality将weight解释为距离（权重越大，距离越远）
    # 但我们的weight代表合作强度（强度越大，合作越强），所以需要转换为距离
    # 距离 = 1 / 强度，这样强度越大，距离越小，路径越短
    # 为了避免除以零，我们使用一个小的epsilon值
    epsilon = 1e-10
    
    # 创建一个新的图，其中边的权重是距离（1/强度）
    G_distance = G.copy()
    for u, v, data in G_distance.edges(data=True):
        strength = data.get('strength', data.get('weight', 1.0))
        if strength > epsilon:
            # 距离 = 1 / 强度，强度越大，距离越小
            G_distance[u][v]['weight'] = 1.0 / strength
        else:
            # 如果强度太小，设置一个很大的距离
            G_distance[u][v]['weight'] = 1.0 / epsilon
    
    try:
        betweenness = nx.betweenness_centrality(G_distance, weight='weight')
    except Exception as e:
        print(f"计算betweenness时出错: {e}")
        # 如果出错，尝试不使用权重
        try:
            betweenness = nx.betweenness_centrality(G)
        except Exception as e2:
            print(f"不使用权重计算betweenness也出错: {e2}")
            return {}
    
    # 只返回collaborator的betweenness（不包括EU）
    collaborator_betweenness = {
        node: betweenness[node] 
        for node in G.nodes() 
        if node != EU_NAME
    }
    
    print(f"计算了 {len(collaborator_betweenness)} 个collaborator的betweenness")
    
    return collaborator_betweenness


def analyze_period(start_year: int, end_year: int, country_stats: Dict[str, int]) -> Tuple[nx.Graph, Dict[str, float]]:
    """分析一个时期的网络和betweenness"""
    print(f"\n{'='*60}")
    print(f"分析时期: {start_year}-{end_year}")
    print(f"{'='*60}\n")
    
    # 加载数据
    df = load_papers_data(PAPERS_FILE, start_year, end_year)
    
    # 构建网络
    G = build_ego_centric_network(df, country_stats)
    
    # 计算betweenness
    betweenness = calculate_betweenness_from_eu(G)
    
    return G, betweenness


def visualize_network(G: nx.Graph, betweenness: Dict[str, float], period_label: str, output_file: str):
    """
    可视化网络图
    
    参数:
    - G: 网络图
    - betweenness: betweenness centrality字典
    - period_label: 时期标签（用于标题）
    - output_file: 输出文件路径
    """
    print(f"\n正在生成网络可视化图...")
    print(f"网络节点数: {G.number_of_nodes()}, 边数: {G.number_of_edges()}")
    
    # 显示所有节点
    G_sub = G.copy()
    betweenness_sub = betweenness
    
    # 计算布局
    print("正在计算网络布局...")
    pos = nx.spring_layout(G_sub, k=1, iterations=50, seed=42)
    
    # 计算节点大小（基于度数）
    degrees = dict(G_sub.degree())
    max_degree = max(degrees.values()) if degrees else 1
    node_sizes = [degrees.get(node, 0) * 300 / max_degree + 100 for node in G_sub.nodes()]
    
    # 计算边宽度（基于强度）
    edge_widths = []
    for u, v in G_sub.edges():
        strength = G_sub[u][v].get('strength', G_sub[u][v].get('weight', 1.0))
        edge_widths.append(max(strength * 5, 0.5))  # 最小宽度0.5
    
    # 节点颜色：EU用特殊颜色，其他基于betweenness
    node_colors = []
    max_betweenness = max(betweenness_sub.values()) if betweenness_sub else 1
    for node in G_sub.nodes():
        if node == EU_NAME:
            node_colors.append('#FF6B6B')  # 红色，EU节点
        else:
            btwn = betweenness_sub.get(node, 0.0)
            # 使用colormap，betweenness越高颜色越深
            intensity = btwn / max_betweenness if max_betweenness > 0 else 0
            node_colors.append(plt.cm.Blues(0.3 + intensity * 0.7))
    
    # 绘制网络
    plt.figure(figsize=(20, 16))
    
    # 绘制边
    nx.draw_networkx_edges(
        G_sub, pos,
        width=edge_widths,
        alpha=0.3,
        edge_color='gray'
    )
    
    # 绘制节点
    nx.draw_networkx_nodes(
        G_sub, pos,
        node_size=node_sizes,
        node_color=node_colors,
        alpha=0.9,
        edgecolors='black',
        linewidths=1.5
    )
    
    # 添加标签（只显示重要的节点）
    # EU节点和betweenness最高的前15个节点
    if G_sub.has_node(EU_NAME):
        labels_to_show = {EU_NAME: EU_NAME}
        top_betweenness = sorted(betweenness_sub.items(), key=lambda x: x[1], reverse=True)[:15]
        labels_to_show.update({node: node for node, _ in top_betweenness})
    else:
        top_betweenness = sorted(betweenness_sub.items(), key=lambda x: x[1], reverse=True)[:15]
        labels_to_show = {node: node for node, _ in top_betweenness}
    
    # 简化标签名称
    labels_to_show_simplified = {}
    for node, label in labels_to_show.items():
        if len(label) > 15:
            # 简化长名称
            parts = label.split()
            if len(parts) > 1:
                simplified = ' '.join([p[:4] for p in parts])
            else:
                simplified = label[:15]
            labels_to_show_simplified[node] = simplified
        else:
            labels_to_show_simplified[node] = label
    
    nx.draw_networkx_labels(
        G_sub, pos,
        labels=labels_to_show_simplified,
        font_size=8,
        font_weight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none')
    )
    
    plt.title(
        f'EU Ego-Centric Collaboration Network ({period_label})\n'
        f'Node size = Degree, Node color = Betweenness Centrality, Edge width = Collaboration Strength',
        fontsize=16,
        fontweight='bold',
        pad=20
    )
    plt.axis('off')
    plt.tight_layout()
    
    # 保存图片
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"网络可视化图已保存到: {output_file}")
    plt.close()


def main():
    """主函数"""
    print("开始分析EU的ego-centric网络和betweenness centrality")
    print(f"EU国家数量: {len(EU_COUNTRIES)}")
    print(f"EU节点名称: {EU_NAME}")
    print(f"时期1: {PERIOD_1_START}-{PERIOD_1_END}")
    print(f"时期2: {PERIOD_2_START}-{PERIOD_2_END}\n")
    
    # 加载国家统计数据
    country_stats = load_countries_stats(COUNTRIES_STATS_FILE)
    
    # 分析两个时期
    G1, betweenness1 = analyze_period(PERIOD_1_START, PERIOD_1_END, country_stats)
    G2, betweenness2 = analyze_period(PERIOD_2_START, PERIOD_2_END, country_stats)
    
    # 合并结果
    all_collaborators = set(betweenness1.keys()) | set(betweenness2.keys())
    
    results = []
    for collab in sorted(all_collaborators):
        results.append({
            'Collaborator': collab,
            f'Betweenness_{PERIOD_1_START}_{PERIOD_1_END}': betweenness1.get(collab, 0.0),
            f'Betweenness_{PERIOD_2_START}_{PERIOD_2_END}': betweenness2.get(collab, 0.0),
            'Difference': betweenness2.get(collab, 0.0) - betweenness1.get(collab, 0.0)
        })
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('Difference', ascending=False)
    
    # 保存结果
    output_file = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/add_experiments/experiment_2/eu/eu_betweenness_results.csv'
    results_df.to_csv(output_file, index=False)
    print(f"\n结果已保存到: {output_file}")
    
    # 打印前20个collaborator的结果
    print("\n前20个collaborator的betweenness变化:")
    print(results_df.head(20).to_string(index=False))
    
    # 可视化
    plt.figure(figsize=(14, 8))
    
    # 选择betweenness变化最大的前20个
    top_20 = results_df.head(20)
    
    x = np.arange(len(top_20))
    width = 0.35
    
    plt.bar(x - width/2, top_20[f'Betweenness_{PERIOD_1_START}_{PERIOD_1_END}'], 
            width, label=f'{PERIOD_1_START}-{PERIOD_1_END}', alpha=0.8)
    plt.bar(x + width/2, top_20[f'Betweenness_{PERIOD_2_START}_{PERIOD_2_END}'], 
            width, label=f'{PERIOD_2_START}-{PERIOD_2_END}', alpha=0.8)
    
    plt.xlabel('Collaborator', fontsize=12)
    plt.ylabel('Betweenness Centrality', fontsize=12)
    plt.title('EU Collaborators Betweenness Centrality Comparison', fontsize=14, fontweight='bold')
    plt.xticks(x, top_20['Collaborator'], rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    
    plot_file = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/add_experiments/experiment_2/eu/eu_betweenness_comparison.png'
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"\n可视化图表已保存到: {plot_file}")
    
    # 绘制差异图
    plt.figure(figsize=(12, 8))
    top_20_diff = results_df.head(20).copy()
    colors = ['red' if x < 0 else 'green' for x in top_20_diff['Difference']]
    plt.barh(range(len(top_20_diff)), top_20_diff['Difference'], color=colors, alpha=0.7)
    plt.yticks(range(len(top_20_diff)), top_20_diff['Collaborator'])
    plt.xlabel('Betweenness Difference (2022-2024 - 2014-2016)', fontsize=12)
    plt.title('EU Collaborators Betweenness Centrality Change', fontsize=14, fontweight='bold')
    plt.axvline(x=0, color='black', linestyle='--', linewidth=1)
    plt.tight_layout()
    
    diff_plot_file = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/add_experiments/experiment_2/eu/eu_betweenness_difference.png'
    plt.savefig(diff_plot_file, dpi=300, bbox_inches='tight')
    print(f"差异图表已保存到: {diff_plot_file}")
    
    # 可视化第二时期的网络
    print("\n" + "="*60)
    print("生成第二时期的网络可视化")
    print("="*60)
    network_plot_file = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/add_experiments/experiment_2/eu/eu_network_visualization_2022_2024.png'
    visualize_network(G2, betweenness2, f'{PERIOD_2_START}-{PERIOD_2_END}', network_plot_file)


if __name__ == "__main__":
    main()
