
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from collections import defaultdict
from typing import List, Tuple, Dict
import networkx as nx

AGGREGATED_ARTICLES_FILE = str(CODE / "0raw_publiations_process/brexit_experimental_data/article_countries_aggregated.txt")
# RUSSIA_NAME = "RUSSIAN FEDERATION"
# COUNTRIES_STATS_FILE = str(CODE / "0raw_publiations_process/brexit_experimental_data/countries_yearly_statistics.csv")

# russia_articles_file = str(CODE / "0raw_publiations_process/russia_articles/russia_articles.txt")

RUSSIA_NAME = "RUSSIAN FEDERATION"
FOCAL_COUNTRY = RUSSIA_NAME
FOCAL_LABEL = "Russia"
FOCAL_FILE_PREFIX = "russia"

base_dir = str(CODE / "add_experiments/null_model/russia")
OUTPUT_DIR = os.path.join(base_dir, "outputs")
EDGE_WEIGHT_THRESHOLD = 10


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
    aggregated_file: str,
    start_year: int = None,
    end_year: int = None,
) -> pd.DataFrame:
    """
    读取全局文章-国家数据，并解析国家列表。
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
    df["country_list"] = df["countries"].apply(parse_countries)
    print(f"Loaded {len(df)} articles for {start_year}-{end_year}")
    return df


def build_weighted_edges(period_df: pd.DataFrame) -> Dict[Tuple[str, str], int]:
    """
    计算加权无向边 w_ij：国家 i 与 j 在同一篇论文中共同出现的次数。
    """
    edge_weights: Dict[Tuple[str, str], int] = defaultdict(int)
    for countries in period_df["country_list"]:
        countries_set = sorted(set(countries))
        for i in range(len(countries_set)):
            for j in range(i + 1, len(countries_set)):
                edge_weights[(countries_set[i], countries_set[j])] += 1
    return edge_weights


def get_focal_edge_weights(
    edge_weights: Dict[Tuple[str, str], int],
    focal_country: str,
) -> Dict[str, int]:
    """
    提取 focal_country 与其他国家之间的权重。
    """
    focal_weights: Dict[str, int] = {}
    for (i, j), w in edge_weights.items():
        if i == focal_country:
            focal_weights[j] = w
        elif j == focal_country:
            focal_weights[i] = w
    return focal_weights


def get_focal_edge_ratios(
    edge_weights: Dict[Tuple[str, str], int],
    focal_country: str,
) -> Dict[str, float]:
    """
    提取 focal_country 与其他国家之间的 w_ij / E[w_ij]。
    """
    strengths = compute_strengths(edge_weights)
    total_weight = float(sum(edge_weights.values()))
    ratios: Dict[str, float] = {}

    for (i, j), w in edge_weights.items():
        if focal_country not in (i, j):
            continue
        expected = (strengths[i] * strengths[j] / (2 * total_weight)) if total_weight > 0 else 0.0
        ratio = (w / expected) if expected > 0 else 0.0
        partner = j if i == focal_country else i
        ratios[partner] = ratio

    return ratios


def filter_edges_by_threshold(
    edge_weights: Dict[Tuple[str, str], int],
    threshold: int,
) -> Dict[Tuple[str, str], int]:
    """
    仅保留 w_ij > threshold 的边。
    """
    return {pair: w for pair, w in edge_weights.items() if w > threshold}


def compute_strengths(edge_weights: Dict[Tuple[str, str], int]) -> Dict[str, int]:
    """
    计算每个国家的 strength s_i = sum_j w_ij。
    """
    strengths: Dict[str, int] = defaultdict(int)
    for (i, j), w in edge_weights.items():
        strengths[i] += w
        strengths[j] += w
    return strengths


def build_null_model_tables(
    edge_weights: Dict[Tuple[str, str], int],
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    基于 Chung-Lu null model 计算期望权重。
    返回：
    - pair_df: 每对国家的 observed_w / expected_w（含未观测到的边）
    - strength_df: 各国家 strength
    - summary: 统计量
    """
    strengths = compute_strengths(edge_weights)
    nodes = sorted(strengths.keys())
    total_weight = float(sum(edge_weights.values()))

    records = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            observed = edge_weights.get((a, b), 0)
            expected = (strengths[a] * strengths[b] / (2 * total_weight)) if total_weight > 0 else 0.0
            ratio = (observed / expected) if expected > 0 else 0.0
            records.append(
                {
                    "country_i": a,
                    "country_j": b,
                    "observed_w": observed,
                    "expected_w": expected,
                    "ratio_w": ratio,
                }
            )

    pair_df = pd.DataFrame(records)
    strength_df = pd.DataFrame(
        [{"country": c, "strength": s} for c, s in strengths.items()]
    ).sort_values("strength", ascending=False)

    summary = {
        "node_count": float(len(nodes)),
        "edge_count": float(len(edge_weights)),
        "total_weight": total_weight,
    }
    return pair_df, strength_df, summary


def visualize_network(
    edge_weights: Dict[Tuple[str, str], int],
    output_path: str,
) -> None:
    """
    绘制加权合作网络并保存图像。
    """
    if not edge_weights:
        return

    strengths = compute_strengths(edge_weights)
    total_weight = float(sum(edge_weights.values()))

    G = nx.Graph()
    for (i, j), w in edge_weights.items():
        if FOCAL_COUNTRY not in (i, j):
            continue
        expected = (strengths[i] * strengths[j] / (2 * total_weight)) if total_weight > 0 else 0.0
        ratio = (w / expected) if expected > 0 else 0.0
        G.add_edge(i, j, weight=ratio)
    nodes = list(G.nodes())
    node_sizes = [max(strengths.get(n, 1), 1) for n in nodes]
    max_size = max(node_sizes) if node_sizes else 1
    node_sizes = [100 + 1200 * (s / max_size) for s in node_sizes]

    node_colors = []
    for n in nodes:
        if n == FOCAL_COUNTRY:
            node_colors.append("#666666")
            continue
        ratio = G[FOCAL_COUNTRY][n]["weight"] if G.has_edge(FOCAL_COUNTRY, n) else 0.0
        node_colors.append("#E45756" if ratio > 1 else "#4C78A8")

    edge_ratios = [G[u][v]["weight"] for u, v in G.edges()]
    max_ratio = max(edge_ratios) if edge_ratios else 1
    edge_widths = [0.5 + 3.0 * (r / max_ratio) for r in edge_ratios]
    edge_colors = ["#E45756" if r > 1 else "#4C78A8" for r in edge_ratios]

    node_count = max(len(G.nodes()), 1)
    k = 2.5 / np.sqrt(node_count)
    pos = nx.spring_layout(G, seed=42, k=k, iterations=200)
    plt.figure(figsize=(12, 10))
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.85)
    nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color="#B0B0B0", alpha=0.6)
    nx.draw_networkx_labels(G, pos, font_size=8)
    plt.margins(0.2)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def run_null_model_for_period(
    df: pd.DataFrame,
    start_year: int,
    end_year: int,
    threshold: int = EDGE_WEIGHT_THRESHOLD,
) -> None:
    """
    计算指定年份区间的 null model 并输出结果。
    """
    period_df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    edge_weights = build_weighted_edges(period_df)
    filtered_edges = filter_edges_by_threshold(edge_weights, threshold=threshold)

    pair_df, strength_df, summary = build_null_model_tables(filtered_edges)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    period_tag = f"{start_year}-{end_year}"
    pair_df.to_csv(
        os.path.join(OUTPUT_DIR, f"null_model_pairs_{period_tag}.csv"),
        index=False,
    )
    strength_df.to_csv(
        os.path.join(OUTPUT_DIR, f"null_model_strengths_{period_tag}.csv"),
        index=False,
    )
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(
        os.path.join(OUTPUT_DIR, f"null_model_summary_{period_tag}.csv"),
        index=False,
    )

    visualize_network(
        filtered_edges,
        os.path.join(OUTPUT_DIR, f"null_model_network_{period_tag}.png"),
    )


def save_and_plot_russia_weight_changes(
    df: pd.DataFrame,
    start_year_a: int,
    end_year_a: int,
    start_year_b: int,
    end_year_b: int,
) -> None:
    """
    输出 Russia 与合作国家的权重变化，并绘制前20显著增加/下降柱状图。
    """
    period_a = df[(df["year"] >= start_year_a) & (df["year"] <= end_year_a)].copy()
    period_b = df[(df["year"] >= start_year_b) & (df["year"] <= end_year_b)].copy()

    edges_a = build_weighted_edges(period_a)
    edges_b = build_weighted_edges(period_b)

    russia_a = get_focal_edge_weights(edges_a, FOCAL_COUNTRY)
    russia_b = get_focal_edge_weights(edges_b, FOCAL_COUNTRY)
    ratio_a = get_focal_edge_ratios(edges_a, FOCAL_COUNTRY)
    ratio_b = get_focal_edge_ratios(edges_b, FOCAL_COUNTRY)

    all_partners = sorted(
        set(russia_a.keys()) | set(russia_b.keys()) | set(ratio_a.keys()) | set(ratio_b.keys())
    )
    records = []
    for country in all_partners:
        w_a = russia_a.get(country, 0)
        w_b = russia_b.get(country, 0)
        delta = w_b - w_a
        pct_change = (delta / w_a) if w_a > 0 else np.nan
        r_a = ratio_a.get(country, 0.0)
        r_b = ratio_b.get(country, 0.0)
        delta_ratio = r_b - r_a
        records.append(
            {
                "country": country,
                f"w_{start_year_a}_{end_year_a}": w_a,
                f"w_{start_year_b}_{end_year_b}": w_b,
                "delta": delta,
                "pct_change": pct_change,
                f"ratio_{start_year_a}_{end_year_a}": r_a,
                f"ratio_{start_year_b}_{end_year_b}": r_b,
                "delta_ratio": delta_ratio,
            }
        )

    change_df = pd.DataFrame(records).sort_values("delta_ratio", ascending=False)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    change_df.to_csv(
        os.path.join(
            OUTPUT_DIR,
            f"russia_weight_change_{start_year_a}-{end_year_a}_vs_{start_year_b}-{end_year_b}.csv",
        ),
        index=False,
    )

    top_increase = change_df.sort_values("delta_ratio", ascending=False).head(20)
    top_decrease = change_df.sort_values("delta_ratio", ascending=True).head(20)

    plt.figure(figsize=(12, 8))
    plt.bar(top_increase["country"], top_increase["delta_ratio"], color="#E45756")
    plt.xticks(rotation=70, ha="right", fontsize=8)
    plt.ylabel("Delta w_ij / E[w_ij]")
    plt.title("Top 20 Increases (Russia)")
    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            f"russia_weight_increase_top20_{start_year_a}-{end_year_a}_vs_{start_year_b}-{end_year_b}.png",
        ),
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(12, 8))
    plt.bar(top_decrease["country"], top_decrease["delta_ratio"], color="#4C78A8")
    plt.xticks(rotation=70, ha="right", fontsize=8)
    plt.ylabel("Delta w_ij / E[w_ij]")
    plt.title("Top 20 Decreases (Russia)")
    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            f"russia_weight_decrease_top20_{start_year_a}-{end_year_a}_vs_{start_year_b}-{end_year_b}.png",
        ),
        dpi=300,
    )
    plt.close()


if __name__ == "__main__":
    articles_df = load_aggregated_articles(
        AGGREGATED_ARTICLES_FILE,
        start_year=2019,
        end_year=2024,
    )
    run_null_model_for_period(articles_df, 2019, 2021)
    run_null_model_for_period(articles_df, 2022, 2024)
    save_and_plot_russia_weight_changes(articles_df, 2019, 2021, 2022, 2024)

