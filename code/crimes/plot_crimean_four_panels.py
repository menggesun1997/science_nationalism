#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制四个子图的水平点状图（Lollipop Chart）：
1. Russia - Total publications
2. Ukraine - Total publications
3. Russia - Ratio of international publications
4. Ukraine - Ratio of international publications
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from pathlib import Path

# 设置字体
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 基础路径
base_dir = Path(str(CODE / "crimes"))


def draw_lollipop_subplot(ax, countries, values, title):
    """在给定的 ax 上绘制一个水平点状子图，风格参考 plot_png.py"""

    # 按数值从大到小排序
    data = list(zip(countries, values))
    data.sort(key=lambda x: x[1], reverse=True)
    countries_sorted = [d[0] for d in data]
    values_sorted = [d[1] for d in data]

    # 生成蓝到黄的渐变色（参考 plot_png.py）
    cmap = LinearSegmentedColormap.from_list('blue_yellow', ['#2196F3', '#FFD600'], N=len(countries_sorted))
    colors = [cmap(i/(len(countries_sorted)-1)) if len(countries_sorted) > 1 else cmap(0) for i in range(len(countries_sorted))]

    # 横向lollipop
    for i, (cat, val, color) in enumerate(zip(countries_sorted, values_sorted, colors)):
        # 画横向小圆点链（参考 plot_png.py 的方式）
        # 由于值是小数（0.425等），需要转换为合适的点数
        num_dots = max(int(val * 100), 10)  # 根据值的大小动态调整点数
        x_dots = np.linspace(0, val, num_dots)
        ax.scatter(x_dots, np.full_like(x_dots, i), s=10, color=color, zorder=1)
        
        # 画大圆
        ax.scatter(val, i, s=700, color=color, zorder=2)
        
        # 圆圈右侧标数字（转换为百分比格式）
        percentage_val = val * 100
        ax.text(val + 0.01, i, f'{percentage_val:.1f}%', va='center', ha='left', 
                fontsize=12, fontweight='bold', color='black')

    # 设置y轴
    ax.set_yticks(range(len(countries_sorted)))
    ax.set_yticklabels([c.upper() for c in countries_sorted], fontsize=12, fontweight='bold')
    ax.set_ylim(-0.5, len(countries_sorted) - 0.5)  # 上下各留0.5空隙
    
    # 根据values的最大值动态设置x轴范围（参考 plot_png.py）
    max_value = max(values_sorted)
    # 向上取整到最近的0.1的倍数
    x_max = ((max_value * 10) // 1 + 1) / 10
    ax.set_xlim(0, x_max)
    
    # 动态生成x轴刻度
    x_ticks = np.arange(0, x_max + 0.05, 0.1)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([f'{t:.1f}' for t in x_ticks], fontweight='bold', fontsize=10)
    
    ax.invert_yaxis()
    ax.tick_params(left=False, bottom=False, labelsize=10, width=2)
    
    # 添加子图标题
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    
    ax.set_facecolor("white")


def main():
    """主函数：绘制四个子图"""
    print("=" * 60)
    print("绘制 Russia / Ukraine 的 total publications 与 ratio 图（四个子图）")
    print("=" * 60)

    # 四个子图的数据（按你给的数值）
    russia_total_countries = ["Japan", "Bulgaria", "Romania", "Mexico"]
    russia_total_values = [0.67, 0.204, 0.083, 0.043]

    ukraine_total_countries = ["costa_rica", "Japan", "Lithuania"]
    ukraine_total_values = [0.466, 0.444, 0.091]

    russia_ratio_countries = ["Turkiye", "Thailand","Romania","Poland"]
    russia_ratio_values = [0.264, 0.215, 0.186, 0.183]

    ukraine_ratio_countries = ["Thailand", "Croatia", "Poland", "China"]
    ukraine_ratio_values = [0.268, 0.18, 0.134, 0.117]

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes = axes.flatten()  # 将2D数组展平为1D数组，方便索引

    # 子图数据列表
    subplot_data = [
        {
            'countries': russia_total_countries,
            'values': russia_total_values,
            'title': 'Russia - Total publications'
        },
        {
            'countries': ukraine_total_countries,
            'values': ukraine_total_values,
            'title': 'Ukraine - Total publications'
        },
        {
            'countries': russia_ratio_countries,
            'values': russia_ratio_values,
            'title': 'Russia - Ratio of international publications'
        },
        {
            'countries': ukraine_ratio_countries,
            'values': ukraine_ratio_values,
            'title': 'Ukraine - Ratio of international publications'
        }
    ]

    # 为每个数据集创建子图
    for idx, data in enumerate(subplot_data):
        draw_lollipop_subplot(
            axes[idx],
            data['countries'],
            data['values'],
            title=data['title']
        )

    plt.tight_layout()

    output_file_png = base_dir / "russia_ukraine_total_ratio_lollipop_crimean.png"
    plt.savefig(output_file_png, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"✅ 已保存: {output_file_png}")

    output_file_pdf = base_dir / "russia_ukraine_total_ratio_lollipop_crimean.pdf"
    plt.savefig(output_file_pdf, bbox_inches="tight", facecolor="white")
    print(f"✅ 已保存: {output_file_pdf}")

    plt.close()
    print("\n✅ 完成！")


if __name__ == "__main__":
    main()


