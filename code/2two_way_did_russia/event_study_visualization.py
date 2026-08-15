#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件研究可视化脚本（CSV）
从 Stata 导出的 CSV（parmest 结果）读取系数，生成：
1) Pre-trends (2017-2021)
2) Main model (2017-2024)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# 设置英文字体
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/2two_way_did_russia'

def read_params_csv(path: str):
    """从 CSV 读取参数，包含 estimate, min95, max95, event_bin, rel_year 列。"""
    if not os.path.exists(path):
        print(f"找不到CSV: {path}")
        return None
    df = pd.read_csv(path)
    needed = {'estimate','min95','max95','event_bin','rel_year'}
    if not needed.issubset(df.columns):
        print(f"CSV缺少列: {needed - set(df.columns)} in {path}")
        return None
    for c in ['estimate','min95','max95','rel_year']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna(subset=['estimate','min95','max95','rel_year'])
    if len(df) == 0:
        return None
    df['coefficient'] = df['estimate']
    df['ci_lower'] = df['min95']
    df['ci_upper'] = df['max95']
    df['relative_year'] = df['rel_year'].astype(int)
    df['year'] = 2021 + df['relative_year']
    return df[['year','relative_year','coefficient','ci_lower','ci_upper']]

def create_event_study_plot(df, output_file, title, y_range=None):
    if df is None or df.empty:
        print(f'无数据: {output_file}')
        return
    df = df.sort_values('relative_year')
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 绘制散点和误差线
    ax.scatter(df['relative_year'], df['coefficient'], color='steelblue', s=80, label='Coefficient')
    ax.errorbar(df['relative_year'], df['coefficient'],
                yerr=[df['coefficient']-df['ci_lower'], df['ci_upper']-df['coefficient']],
                fmt='none', color='steelblue', alpha=0.7, capsize=4)
    
    # 添加参考线
    ax.axhline(0, color='k', ls='--', lw=1)
    ax.axvline(0, color='k', lw=1)
    
    # 设置坐标轴
    ax.set_xlabel('Event year (relative to 2021)')
    ax.set_ylabel('Coefficient (relative to 2021)')
    ax.set_title(title)
    
    # 设置横坐标标签为实际年份
    ax.set_xticks(df['relative_year'])
    ax.set_xticklabels([f'{int(y)}' for y in df['year']])
    
    # 添加网格
    ax.grid(True, alpha=0.3)
    
    
    
    plt.tight_layout()
    
    # 保存PNG格式
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f'✅ Saved (PNG): {output_file}')
    
    # 同时保存PDF格式
    pdf_file = output_file.replace('.png', '.pdf')
    plt.savefig(pdf_file, format='pdf', bbox_inches='tight')
    print(f'✅ Saved (PDF): {pdf_file}')
    
    print(f'数据点数量: {len(df)}')
    print(f'年份范围: {df["year"].min()}-{df["year"].max()}')
    print(f'相对年份范围: {df["relative_year"].min()}-{df["relative_year"].max()}')
    
    plt.close()  # 关闭图形以释放内存

def main():
    print('Event Study Visualization (CSV)')
    print('=' * 50)

    pre = read_params_csv(f"{base_dir}/pre_trends_params1.csv")
    main_df = read_params_csv(f"{base_dir}/event_study_params2.csv")

    if pre is not None:
        print(f'Pre-trends 数据: {len(pre)} 个观测值')
        print(pre[['year','relative_year','coefficient']])
        create_event_study_plot(pre, f"{base_dir}/pre_trends_event_study_python.png",
                                 title='Pre-Trends Event Study (2017–2021)', y_range=(-0.001, 0.001))
    else:
        print('⚠️ pre_trends_params1.csv 为空或缺失')

    if main_df is not None:
        print(f'Main model 数据: {len(main_df)} 个观测值')
        print(main_df[['year','relative_year','coefficient']])
        create_event_study_plot(main_df, f"{base_dir}/event_study_russia.png",
                                 title='Event-study coefficients (Main model)', y_range=(-0.001, 0.001))
    else:
        print('⚠️ event_study_params2.csv 为空或缺失')

if __name__ == '__main__':
    main()