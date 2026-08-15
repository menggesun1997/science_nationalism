#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用PCA将每个国家的所有年份DID系数投影到二维坐标系
每个国家的数据（rel_year从-17到2的coefficient）形成一个向量，使用PCA降维到2维
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import os

# 设置工作目录
output_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/2ppml_did_russia_internal_control'
data_file = f'{output_dir}/event_study_try/countries_result/event_study_coefficients_all_countries.csv'
pca_output_dir = f'{output_dir}/event_study_try/countries_result/pca_results'

def main():
    print("="*80)
    print("PCA分析：将每个国家的DID系数向量投影到二维坐标系")
    print("每个国家的向量由不同rel_year的coefficient组成")
    print("="*80)
    
    # 1. 读取数据
    print("\n步骤1: 读取Event Study系数数据...")
    try:
        df = pd.read_csv(data_file)
        print(f"✅ 读取成功，数据形状: {df.shape}")
        print(f"列名: {df.columns.tolist()}")
    except Exception as e:
        print(f"❌ 无法读取数据: {e}")
        print(f"请确保文件存在: {data_file}")
        return
    
    # 检查必要的列
    required_cols = ['partner_country', 'rel_year', 'coefficient']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ 缺少必要的列: {missing_cols}")
        print(f"可用列: {df.columns.tolist()}")
        return
    
    # 2. 数据预处理：将数据重塑为每个国家一行，每列代表一个rel_year
    print("\n步骤2: 数据重塑（每个国家一行，每列代表一个rel_year的coefficient）...")
    
    # 删除缺失的coefficient
    df = df.dropna(subset=['coefficient']).copy()
    
    # 只保留rel_year在-7到2之间的数据（对应2015-2024年）
    df = df[(df['rel_year'] >= -17) & (df['rel_year'] <= 2)].copy()
    print(f"✅ 筛选后数据: rel_year范围 -7到2（对应2015-2024年）")
    
    # 按国家和rel_year排序
    df = df.sort_values(['partner_country', 'rel_year'])
    
    # 透视表：每个国家一行，每列代表一个rel_year的coefficient
    df_pivot = df.pivot_table(
        index='partner_country',
        columns='rel_year',
        values='coefficient',
        fill_value=np.nan  # 缺失值保持为NaN
    )
    
    # 确保rel_year列名是整数类型，并按顺序排列（-7到2）
    df_pivot.columns = df_pivot.columns.astype(int)
    rel_years_sorted = sorted(df_pivot.columns)
    df_pivot = df_pivot[rel_years_sorted]
    
    print(f"✅ 数据重塑完成")
    print(f"  国家数: {len(df_pivot)}")
    print(f"  rel_year数量: {len(df_pivot.columns)}")
    print(f"  rel_year范围: {df_pivot.columns.min()} - {df_pivot.columns.max()}")
    
    # # 显示数据预览
    # print("\n数据预览（前5个国家，前5个rel_year）:")
    # print(df_pivot.iloc[:5, :5])
    
    # 检查每个国家的完整数据
    print("\n每个国家的数据完整性:")
    complete_data = df_pivot.notna().sum(axis=1)
    print(f"  完整数据（所有rel_year都有值）的国家数: {(complete_data == len(df_pivot.columns)).sum()}")
    print(f"  缺失数据的国家数: {(complete_data < len(df_pivot.columns)).sum()}")
    
    
    print("\n处理缺失值：用0填充（因为基准年-1的系数就是0）...")
    df_pivot = df_pivot.fillna(0)
    
    # 3. 标准化数据（可选，但通常PCA前建议标准化）
    print("\n步骤3: 数据标准化...")
    scaler = StandardScaler()
    df_scaled = pd.DataFrame(
        scaler.fit_transform(df_pivot),
        index=df_pivot.index,
        columns=df_pivot.columns
    )
    print("✅ 数据标准化完成")
    
    # 4. PCA降维
    print("\n步骤4: PCA降维...")
    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(df_scaled)
    print(pca_result)
    
    # 创建结果DataFrame
    df_pca = pd.DataFrame(
        pca_result,
        columns=['PC1', 'PC2'],
        index=df_pivot.index
    )
    
    print("✅ PCA降维完成")
    print(f"\nPCA解释的方差比例:")
    print(f"  PC1: {pca.explained_variance_ratio_[0]:.4f} ({pca.explained_variance_ratio_[0]*100:.2f}%)")
    print(f"  PC2: {pca.explained_variance_ratio_[1]:.4f} ({pca.explained_variance_ratio_[1]*100:.2f}%)")
    print(f"  累计解释方差: {pca.explained_variance_ratio_.sum():.4f} ({pca.explained_variance_ratio_.sum()*100:.2f}%)")
    
    # 5. 保存PCA结果
    print("\n步骤5: 保存PCA结果...")
    os.makedirs(pca_output_dir, exist_ok=True)
    
    # 保存PCA坐标
    output_file = f'{pca_output_dir}/pca_country_coordinates.csv'
    df_pca.to_csv(output_file)
    print(f"✅ PCA坐标已保存到: {output_file}")
    
    # 保存PCA组件（主成分载荷）
    df_components = pd.DataFrame(
        pca.components_.T,
        columns=['PC1', 'PC2'],
        index=df_pivot.columns
    )
    components_file = f'{pca_output_dir}/pca_components.csv'
    df_components.to_csv(components_file)
    print(f"✅ PCA组件（主成分载荷）已保存到: {components_file}")
    
    # 保存解释方差
    variance_file = f'{pca_output_dir}/pca_explained_variance.csv'
    df_variance = pd.DataFrame({
        'Component': ['PC1', 'PC2'],
        'Explained_Variance_Ratio': pca.explained_variance_ratio_,
        'Explained_Variance': pca.explained_variance_,
        'Cumulative_Ratio': np.cumsum(pca.explained_variance_ratio_)
    })
    df_variance.to_csv(variance_file, index=False)
    print(f"✅ PCA解释方差已保存到: {variance_file}")
    
    # 6. 可视化
    print("\n步骤6: 生成可视化图表...")
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # 绘制散点图
    scatter = ax.scatter(
        df_pca['PC1'],
        df_pca['PC2'],
        alpha=0.6,
        s=100,
        edgecolors='black',
        linewidths=0.5
    )
    
    # 添加国家标签（只显示部分，避免过于拥挤）
    # 可以选择显示所有标签，或者只显示离中心较远的国家
    for country in df_pca.index:
        ax.annotate(
            country,
            (df_pca.loc[country, 'PC1'], df_pca.loc[country, 'PC2']),
            fontsize=8,
            alpha=0.7,
            ha='center',
            va='bottom'
        )
    
    # 添加坐标轴标签
    ax.set_xlabel(
        f'PC1 ({pca.explained_variance_ratio_[0]*100:.2f}% variance explained)',
        fontsize=12,
        fontweight='bold'
    )
    ax.set_ylabel(
        f'PC2 ({pca.explained_variance_ratio_[1]*100:.2f}% variance explained)',
        fontsize=12,
        fontweight='bold'
    )
    
    # 添加标题
    ax.set_title(
        'PCA Projection: Country DID Coefficient Vectors\nEach country represented as a vector of coefficients across rel_year',
        fontsize=14,
        fontweight='bold',
        pad=20
    )
    
    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 添加原点线
    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    ax.axvline(x=0, color='gray', linestyle='-', linewidth=0.5)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    plot_file_png = f'{pca_output_dir}/pca_country_projection.png'
    plot_file_pdf = f'{pca_output_dir}/pca_country_projection.pdf'
    plt.savefig(plot_file_png, dpi=300, bbox_inches='tight')
    plt.savefig(plot_file_pdf, bbox_inches='tight')
    print(f"✅ 图表已保存:")
    print(f"  - {plot_file_png}")
    print(f"  - {plot_file_pdf}")
    
    plt.close()
    
    # 7. 生成主成分载荷图（显示每个rel_year对主成分的贡献）
    print("\n步骤7: 生成主成分载荷图...")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # PC1载荷
    rel_years = df_components.index
    ax1.bar(range(len(rel_years)), df_components['PC1'], alpha=0.7, color='steelblue')
    ax1.set_xticks(range(len(rel_years)))
    ax1.set_xticklabels(rel_years, rotation=45, ha='right')
    ax1.set_xlabel('Relative Event Year (rel_year)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('PC1 Loading', fontsize=11, fontweight='bold')
    ax1.set_title(f'PC1 Loadings ({pca.explained_variance_ratio_[0]*100:.2f}% variance)', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    # 标记基准年-1和事件年0
    baseline_idx = list(rel_years).index(-1) if -1 in rel_years else None
    event_idx = list(rel_years).index(0) if 0 in rel_years else None
    if baseline_idx is not None:
        ax1.axvline(x=baseline_idx, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Baseline (rel_year=-1)')
    if event_idx is not None:
        ax1.axvline(x=event_idx, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Event (rel_year=0)')
    if baseline_idx is not None or event_idx is not None:
        ax1.legend(fontsize=9)
    
    # PC2载荷
    ax2.bar(range(len(rel_years)), df_components['PC2'], alpha=0.7, color='coral')
    ax2.set_xticks(range(len(rel_years)))
    ax2.set_xticklabels(rel_years, rotation=45, ha='right')
    ax2.set_xlabel('Relative Event Year (rel_year)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('PC2 Loading', fontsize=11, fontweight='bold')
    ax2.set_title(f'PC2 Loadings ({pca.explained_variance_ratio_[1]*100:.2f}% variance)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    # 标记基准年-1和事件年0
    if baseline_idx is not None:
        ax2.axvline(x=baseline_idx, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Baseline (rel_year=-1)')
    if event_idx is not None:
        ax2.axvline(x=event_idx, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Event (rel_year=0)')
    if baseline_idx is not None or event_idx is not None:
        ax2.legend(fontsize=9)
    
    plt.tight_layout()
    
    # 保存载荷图
    loadings_file_png = f'{pca_output_dir}/pca_loadings.png'
    loadings_file_pdf = f'{pca_output_dir}/pca_loadings.pdf'
    plt.savefig(loadings_file_png, dpi=300, bbox_inches='tight')
    plt.savefig(loadings_file_pdf, bbox_inches='tight')
    print(f"✅ 主成分载荷图已保存:")
    print(f"  - {loadings_file_png}")
    print(f"  - {loadings_file_pdf}")
    
    plt.close()
    
    # 8. 显示结果摘要
    print("\n" + "="*80)
    print("PCA分析结果摘要")
    print("="*80)
    print(f"\n国家数量: {len(df_pca)}")
    print(f"rel_year数量: {len(df_pivot.columns)}")
    print(f"rel_year范围: {df_pivot.columns.min()} - {df_pivot.columns.max()}")
    print(f"\nPCA解释的方差:")
    print(f"  PC1: {pca.explained_variance_ratio_[0]*100:.2f}%")
    print(f"  PC2: {pca.explained_variance_ratio_[1]*100:.2f}%")
    print(f"  累计: {pca.explained_variance_ratio_.sum()*100:.2f}%")
    
    print(f"\nPC1坐标范围: [{df_pca['PC1'].min():.4f}, {df_pca['PC1'].max():.4f}]")
    print(f"PC2坐标范围: [{df_pca['PC2'].min():.4f}, {df_pca['PC2'].max():.4f}]")
    
    print(f"\nPC1坐标最大的5个国家:")
    print(df_pca.nlargest(5, 'PC1')[['PC1', 'PC2']])
    
    print(f"\nPC1坐标最小的5个国家:")
    print(df_pca.nsmallest(5, 'PC1')[['PC1', 'PC2']])
    
    print(f"\nPC2坐标最大的5个国家:")
    print(df_pca.nlargest(5, 'PC2')[['PC1', 'PC2']])
    
    print(f"\nPC2坐标最小的5个国家:")
    print(df_pca.nsmallest(5, 'PC2')[['PC1', 'PC2']])
    
    print("\n" + "="*80)
    print("✅ PCA分析完成！")
    print("="*80)
    print(f"\n所有结果已保存到: {pca_output_dir}/")

if __name__ == '__main__':
    main()

