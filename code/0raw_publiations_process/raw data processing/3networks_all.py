import pandas as pd
import numpy as np
import os
import networkx as nx


# base_dir = '/root/autodl-tmp/disciplines_brexit'
base_dir = '/Users/sunmengge/Dropbox/brexit/cooperation_related'

def extract_years_cooperation_data():
    # 读取原始数据
    article_df = pd.read_csv(os.path.join(base_dir, 'article_pays_list.txt'), 
                        sep='\t',
                        names=['OST_BK', 'Annee_Bibliographique', 'Code_Discipline', 'Pays'],
                        dtype={'OST_BK': str, 'Annee_Bibliographique': str, 'Code_Discipline': str, 'Pays': str})
    print(f"成功读取数据，文章数据共 {len(article_df)} 行")

    # 处理Pays列中的NaN值
    article_df['Pays'] = article_df['Pays'].fillna('')
    print("已处理Pays列中的空值")

    # 去掉第一行（列名行）
    article_df = article_df.iloc[1:]
    print("已去掉第一行列名")
    
    return article_df

def calculate_network_metrics(df):
    """计算每年的合作网络指标"""
    yearly_metrics = []
    
    for year, year_group in df.groupby('Annee_Bibliographique'):
        print(year)
        # 创建该年的合作网络
        G = nx.Graph()
        
        # 处理每篇文章的合作关系
        for pays in year_group['Pays']:
            partners = pays.split(',')
            partners = [p.strip() for p in partners if p.strip()]  # 去除空值
            
            # 添加所有可能的合作对
            for i in range(len(partners)):
                for j in range(i+1, len(partners)):
                    if G.has_edge(partners[i], partners[j]):
                        G[partners[i]][partners[j]]['weight'] += 1
                    else:
                        G.add_edge(partners[i], partners[j], weight=1)
        
        # 计算网络指标
        metrics = {
            'Year': year,
            'Number_of_Nodes': G.number_of_nodes(),
            'Number_of_Edges': G.number_of_edges(),
            'Network_Density': nx.density(G),
            'Average_Degree': sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
            'Average_Clustering': nx.average_clustering(G) if G.number_of_nodes() > 0 and G.number_of_edges() > 0 else 0,
            'Average_Shortest_Path': nx.average_shortest_path_length(G) if G.number_of_nodes() > 0 and nx.is_connected(G) else float('inf')
        }
        print(metrics)
        
        # 计算中心性指标
        if G.number_of_nodes() > 0:
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            
            # 添加中心性指标的平均值
            metrics['Average_Degree_Centrality'] = sum(degree_centrality.values()) / len(degree_centrality)
            metrics['Average_Betweenness_Centrality'] = sum(betweenness_centrality.values()) / len(betweenness_centrality)
        else:
            metrics['Average_Degree_Centrality'] = 0
            metrics['Average_Betweenness_Centrality'] = 0
        
        yearly_metrics.append(metrics)
    
    return pd.DataFrame(yearly_metrics)

def analyze_network_metrics():
    """分析网络指标"""
    # 读取数据
    df = extract_years_cooperation_data()
    
    # 计算网络指标
    metrics_df = calculate_network_metrics(df)
    
    # 保存结果
    output_file = os.path.join(base_dir, 'network_metrics.xlsx')
    metrics_df.to_excel(output_file, index=False)
    print(f"网络指标分析结果已保存到: {output_file}")
    

if __name__ == "__main__":
    analyze_network_metrics()
    