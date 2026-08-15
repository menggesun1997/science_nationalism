#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化avg_effect数据
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# 基础路径
base_dir = Path('/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES')

# 读取数据
df = pd.read_excel(base_dir / '学科avg_effect汇总.xlsx', sheet_name='详细数据')

# 统一变量类型名称
df['变量类型'] = df['变量类型'].replace('initil_ratio', 'intil_ratio')

# 学科名称映射（用于显示）
discipline_names = {
    'arts': 'Arts',
    'biology': 'Biology',
    'biomedical': 'Biomedical',
    'chemistry': 'Chemistry',
    'clinical': 'Clinical',
    'earth': 'Earth Sciences',
    'engineering': 'Engineering',
    'health': 'Health',
    'humanities': 'Humanities',
    'mathematics': 'Mathematics',
    'physics': 'Physics',
    'professional': 'Professional',
    'psychology': 'Psychology',
    'social_science': 'Social Science'
}

def plot_brexit():
    """绘制Brexit事件的两个变量图"""
    brexit_df = df[df['事件'] == 'Brexit'].copy()
    
    # 为每个变量类型创建图表
    for var_type in ['intil_ratio', 'total_publications']:
        var_df = brexit_df[brexit_df['变量类型'] == var_type].copy()
        
        # 创建透视表
        pivot_df = var_df.pivot_table(
            index='学科',
            columns='国家',
            values='Effect值',
            aggfunc='first'
        )
        
        # 确保EU和UK列存在
        if 'EU' not in pivot_df.columns:
            pivot_df['EU'] = np.nan
        if 'UK' not in pivot_df.columns:
            pivot_df['UK'] = np.nan
        
        # 按照UK的效应值从大到小排序（如果UK有缺失值，则用EU的值）
        # 优先使用UK的值，如果UK为NaN则使用EU的值
        pivot_df['sort_value'] = pivot_df['UK'].fillna(pivot_df['EU'])
        
        # 按效应值从大到小排序，并重置索引
        pivot_df = pivot_df.sort_values('sort_value', ascending=False).reset_index()
        
        # 获取排序后的学科列表
        disciplines = pivot_df['学科'].tolist()
        
        # 移除临时列，并设置学科为索引
        pivot_df = pivot_df.drop('sort_value', axis=1).set_index('学科')
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(16, 9))
        
        x = np.arange(len(disciplines))
        width = 0.35
        
        # 绘制柱状图 - 使用指定的RGB颜色
        # EU: RGB(0, 51, 154), UK: RGB(201, 6, 43)
        eu_color = (0/255, 51/255, 154/255)
        uk_color = (201/255, 6/255, 43/255)
        bars1 = ax.bar(x - width/2, pivot_df['EU'], width, label='EU', color=eu_color, alpha=0.85, edgecolor='black', linewidth=0.5)
        bars2 = ax.bar(x + width/2, pivot_df['UK'], width, label='UK', color=uk_color, alpha=0.85, edgecolor='black', linewidth=0.5)
        
        # 添加零线
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
        
        # 设置标签和标题
        ax.set_xlabel('Discipline', fontsize=13, fontweight='bold')
        ylabel = 'International Cooperation Ratio Effect' if var_type == 'intil_ratio' else 'Total Publications Effect'
        ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
        title = f'Brexit Effect on {ylabel}'
        ax.set_title(title, fontsize=15, fontweight='bold', pad=20)
        
        # 设置x轴标签
        ax.set_xticks(x)
        ax.set_xticklabels([discipline_names.get(d, d.replace('_', ' ').title()) for d in disciplines], 
                           rotation=45, ha='right', fontsize=11)
        
        # 添加图例
        ax.legend(loc='best', fontsize=12, framealpha=0.95, shadow=True)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--', axis='y', zorder=0)
        ax.set_axisbelow(True)
        
        # 设置背景色
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('white')
        
        # 调整布局
        plt.tight_layout()
        
        # 保存PNG图片
        output_file_png = base_dir / f'brexit_{var_type}_effects.png'
        plt.savefig(output_file_png, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Saved: {output_file_png}")
        
        # 保存PDF图片
        output_file_pdf = base_dir / f'brexit_{var_type}_effects.pdf'
        plt.savefig(output_file_pdf, bbox_inches='tight', facecolor='white')
        print(f"Saved: {output_file_pdf}")
        
        plt.close()

def plot_crimes():
    """绘制Crimes和Crimes_2014事件的两个变量图（分开绘制）"""
    crimes_df = df[df['事件'].isin(['Crimes', 'Crimes_2014'])].copy()
    
    # 分别处理每个事件
    for event_name in ['Crimes', 'Crimes_2014']:
        event_df = crimes_df[crimes_df['事件'] == event_name].copy()
        
        # 为每个变量类型创建图表
        for var_type in ['intil_ratio', 'total_publications']:
            var_df = event_df[event_df['变量类型'] == var_type].copy()
            
            # 创建透视表
            pivot_df = var_df.pivot_table(
                index='学科',
                columns='国家',
                values='Effect值',
                aggfunc='first'
            )
            
            # 确保Russia和Ukraine列存在
            if 'Russia' not in pivot_df.columns:
                pivot_df['Russia'] = np.nan
            if 'Ukraine' not in pivot_df.columns:
                pivot_df['Ukraine'] = np.nan
            
            # 按照Ukraine的效应值从大到小排序（如果Ukraine有缺失值，则用Russia的值）
            # 优先使用Ukraine的值，如果Ukraine为NaN则使用Russia的值
            pivot_df['sort_value'] = pivot_df['Ukraine'].fillna(pivot_df['Russia'])
            
            # 按效应值从大到小排序，并重置索引
            pivot_df = pivot_df.sort_values('sort_value', ascending=False).reset_index()
            
            # 获取排序后的学科列表
            disciplines = pivot_df['学科'].tolist()
            
            # 移除临时列，并设置学科为索引
            pivot_df = pivot_df.drop('sort_value', axis=1).set_index('学科')
            
            # 创建图表
            fig, ax = plt.subplots(figsize=(16, 9))
            
            x = np.arange(len(disciplines))
            width = 0.35
            
            # 绘制柱状图 - 使用指定的RGB颜色
            # Ukraine: RGB(227, 195, 65), Russia: RGB(76, 92, 156)
            ukraine_color = (227/255, 195/255, 65/255)
            russia_color = (76/255, 92/255, 156/255)
            bars1 = ax.bar(x - width/2, pivot_df['Russia'], width, 
                          label='Russia', color=russia_color, alpha=0.85, edgecolor='black', linewidth=0.5)
            bars2 = ax.bar(x + width/2, pivot_df['Ukraine'], width, 
                          label='Ukraine', color=ukraine_color, alpha=0.85, edgecolor='black', linewidth=0.5)
            
            # 添加零线
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
            
            # 设置标签和标题
            ax.set_xlabel('Discipline', fontsize=13, fontweight='bold')
            ylabel = 'International Cooperation Ratio Effect' if var_type == 'intil_ratio' else 'Total Publications Effect'
            ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
            # 转换事件名称显示
            event_display_name = 'Crimean Crisis' if event_name == 'Crimes_2014' else 'Russia Ukraine War'
            title = f'{event_display_name} Effect on {ylabel}'
            ax.set_title(title, fontsize=15, fontweight='bold', pad=20)
            
            # 设置x轴标签
            ax.set_xticks(x)
            ax.set_xticklabels([discipline_names.get(d, d.replace('_', ' ').title()) for d in disciplines], 
                               rotation=45, ha='right', fontsize=11)
            
            # 添加图例
            ax.legend(loc='best', fontsize=12, framealpha=0.95, shadow=True)
            
            # 添加网格
            ax.grid(True, alpha=0.3, linestyle='--', axis='y', zorder=0)
            ax.set_axisbelow(True)
            
            # 设置背景色
            ax.set_facecolor('#fafafa')
            fig.patch.set_facecolor('white')
            
            # 调整布局
            plt.tight_layout()
            
            # 保存PNG图片（使用事件名称的小写和下划线格式）
            event_file_name = event_name.lower().replace('_', '_')
            output_file_png = base_dir / f'{event_file_name}_{var_type}_effects.png'
            plt.savefig(output_file_png, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"Saved: {output_file_png}")
            
            # 保存PDF图片
            output_file_pdf = base_dir / f'{event_file_name}_{var_type}_effects.pdf'
            plt.savefig(output_file_pdf, bbox_inches='tight', facecolor='white')
            print(f"Saved: {output_file_pdf}")
            
            plt.close()

def main():
    """主函数"""
    print("开始生成可视化图表...")
    
    # 绘制Brexit图表
    print("\n生成Brexit图表...")
    plot_brexit()
    
    # 绘制Crimes图表
    print("\n生成Crimes图表...")
    plot_crimes()
    
    print("\n完成！所有图表已保存。")

if __name__ == '__main__':
    main()

