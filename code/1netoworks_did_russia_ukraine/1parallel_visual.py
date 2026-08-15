import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.lines import Line2D

# 设置英文字体
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False

# 数据路径
data_base_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile'
russia_data_path = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile/russia_west_east_tile.csv'
ukraine_data_path = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/west_east_tile/ukraine_west_east_tile.csv'

# 控制国家列表
control_countries = ['brazil', 'south_africa', 'argentina','serbia', 'rep-of-georgia', 'armenia', 'azerbaijan','moldova','bosnia-&-herceg']

def load_data():
    """加载所有数据"""
    control_data = {}
    
    # 加载控制组数据
    for country in control_countries:
        file_path = os.path.join(data_base_dir, f"{country}_west_east_tile.csv")
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                # 计算差异和比率
                df['west_cooperation_ratio-east_cooperation_ratio'] = df['west_cooperation_ratio'] - df['east_cooperation_ratio']
                # 避免除零错误
                df['west_cooperation_ratio/east_cooperation_ratio'] = df['west_cooperation_ratio'] / (df['east_cooperation_ratio'] + 1e-8)
                control_data[country] = df
                print(f"Loaded {country} data")
            except Exception as e:
                print(f"Failed to load {country} data: {e}")
    
    # 加载处理组数据
    treatment_data = {}
    try:
        russia_df = pd.read_csv(russia_data_path)
        russia_df['west_cooperation_ratio-east_cooperation_ratio'] = russia_df['west_cooperation_ratio'] - russia_df['east_cooperation_ratio']
        # 避免除零错误
        russia_df['west_cooperation_ratio/east_cooperation_ratio'] = russia_df['west_cooperation_ratio'] / (russia_df['east_cooperation_ratio'] + 1e-8)
        treatment_data['russia'] = russia_df
        
        ukraine_df = pd.read_csv(ukraine_data_path)
        ukraine_df['west_cooperation_ratio-east_cooperation_ratio'] = ukraine_df['west_cooperation_ratio'] - ukraine_df['east_cooperation_ratio']
        # 避免除零错误
        ukraine_df['west_cooperation_ratio/east_cooperation_ratio'] = ukraine_df['west_cooperation_ratio'] / (ukraine_df['east_cooperation_ratio'] + 1e-8)
        treatment_data['ukraine'] = ukraine_df
        
        print("Loaded treatment countries data")
    except Exception as e:
        print(f"Failed to load treatment data: {e}")
    
    return control_data, treatment_data

def calculate_slopes(data, variable, start_year, end_year):
    """计算指定时间段内的斜率"""
    period_data = data[(data['year'] >= start_year) & (data['year'] <= end_year)]
    if len(period_data) >= 2:
        return np.polyfit(period_data['year'], period_data[variable], 1)[0]
    return np.nan

def plot_individual_slopes(treatment_country, variable, control_data, treatment_data, save_path=None):
    """为单个处理国家绘制斜率图"""
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # 定义变量显示名称
    var_names = {
        'west_cooperation_ratio-east_cooperation_ratio': 'West-East Cooperation Difference',
        'west_cooperation_ratio/east_cooperation_ratio': 'West/East Cooperation Ratio'
    }
    
    # 计算所有国家的斜率
    slopes_2005_2021 = {}
    slopes_2010_2021 = {}
    
    # 控制组斜率
    for country, data in control_data.items():
        slopes_2005_2021[country] = calculate_slopes(data, variable, 2005, 2021)
        slopes_2010_2021[country] = calculate_slopes(data, variable, 2010, 2021)
    
    # 处理组斜率
    for country, data in treatment_data.items():
        slopes_2005_2021[country] = calculate_slopes(data, variable, 2005, 2021)
        slopes_2010_2021[country] = calculate_slopes(data, variable, 2010, 2021)
    
    # 获取目标国家的斜率
    target_slope_2005 = slopes_2005_2021.get(treatment_country, 0)
    target_slope_2010 = slopes_2010_2021.get(treatment_country, 0)
    
    # 当前处理国家显示名（用于日志与图例）
    country_display = 'Russia' if treatment_country == 'russia' else 'Ukraine'

    # 第一步：用“斜率差异”初筛 Top5（战前：2005-2021 与 2010-2021 的平均差异）
    slope_diff = {}
    for country in control_data.keys():
        if country in slopes_2005_2021 and country in slopes_2010_2021:
            diff_2005 = abs(slopes_2005_2021[country] - target_slope_2005)
            diff_2010 = abs(slopes_2010_2021[country] - target_slope_2010)
            slope_diff[country] = (diff_2005 + diff_2010) / 2.0
        else:
            slope_diff[country] = np.inf
    top5_candidates = [c for c, _ in sorted(slope_diff.items(), key=lambda x: x[1])[:5]]
    print("\nStep 1 - Top5 by pre-war slope difference (avg of 05-21 & 10-21):")
    for rank, c in enumerate(top5_candidates, 1):
        print(f"  {rank}. {c}: avg slope diff = {slope_diff[c]:.6f}")

    # 第二步：在 Top5 内用 RMSE 最终精选 2-3 个（与当前处理国进行比较）
    baseline_df = treatment_data[treatment_country][['year', variable]].copy()
    candidate_rmse = {}
    for country in top5_candidates:
        df = control_data[country]
        merged = pd.merge(baseline_df, df[['year', variable]], on='year', how='inner', suffixes=('_treat', '_ctrl'))
        merged = merged.dropna()
        if len(merged) >= 2:
            diff = merged[f'{variable}_treat'] - merged[f'{variable}_ctrl']
            candidate_rmse[country] = float(np.sqrt(np.mean(np.square(diff))))
        else:
            candidate_rmse[country] = np.inf

    final_k = 3
    final_selected = [c for c, _ in sorted(candidate_rmse.items(), key=lambda x: x[1])[:final_k]]
    print("\nStep 2 - Final selection by RMSE within Top5 (baseline: {}):".format(country_display))
    for rank, c in enumerate(final_selected, 1):
        print(f"  {rank}. {c}: RMSE = {candidate_rmse[c]:.6f}")

    # 最终用于高亮显示的名单（保存以供后续使用）
    top_selected_names = final_selected
    
    # 绘制控制组国家 - 为每个国家分配固定颜色，Top4用形状标识
    top4_colors = ['blue', 'green', 'purple', 'orange']  # 用于区分入选组合
    top4_markers = ['s', '^', 'D', 'v']  # 形状标识
    control_palette = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#17becf', '#bcbd22']
    country_colors = {country: control_palette[i % len(control_palette)] for i, country in enumerate(control_countries)}
    
    for i, (country, data) in enumerate(control_data.items()):
        country_display_name = country.replace('_', ' ').title()
        
        # 判断是否为top4国家，设置不同的形状标记；颜色使用各自固定颜色
        base_color = country_colors.get(country, '#999999')
        if country in top_selected_names:
            # Top4国家：固定颜色 + 特殊形状标记
            marker_idx = top_selected_names.index(country) % len(top4_markers)
            marker = top4_markers[marker_idx]
            ax.plot(
                data['year'], data[variable],
                color=base_color, linewidth=2.5, alpha=0.9,
                marker=marker, markersize=8, markevery=2,
                label=f"[TOP4] {country_display_name} (05-21:{slopes_2005_2021[country]:.4f}, 10-21:{slopes_2010_2021[country]:.4f})"
            )
        else:
            # 普通国家：固定颜色 + 无标记
            ax.plot(
                data['year'], data[variable],
                color=base_color, linewidth=1.8, alpha=0.8,
                label=f"{country_display_name} (05-21:{slopes_2005_2021[country]:.4f}, 10-21:{slopes_2010_2021[country]:.4f})"
            )
        
        # 计算并显示斜率
        slope_2005_2021 = slopes_2005_2021[country]
        slope_2010_2021 = slopes_2010_2021[country]
        
        # 不再在图中单独标注文字，斜率信息已放入图例标签
    
    # 计算控制组平均值（用于平行趋势可视化）
    control_avg_data = {}
    all_years = set()
    for country, data in control_data.items():
        all_years.update(data['year'].values)
    
    for year in sorted(all_years):
        year_values = []
        for country, data in control_data.items():
            year_data = data[data['year'] == year]
            if len(year_data) > 0:
                year_values.append(year_data[variable].values[0])
        if len(year_values) > 0:
            control_avg_data[year] = np.mean(year_values)
    
    # 绘制控制组平均值线（粗线，用于对比）
    if len(control_avg_data) > 0:
        control_years = sorted(control_avg_data.keys())
        control_avg_values = [control_avg_data[y] for y in control_years]
        
        # 计算控制组平均值的斜率
        control_avg_slope_2005 = calculate_slopes(
            pd.DataFrame({'year': control_years, variable: control_avg_values}), 
            variable, 2005, 2021
        )
        control_avg_slope_2010 = calculate_slopes(
            pd.DataFrame({'year': control_years, variable: control_avg_values}), 
            variable, 2010, 2021
        )
        
        ax.plot(
            control_years, control_avg_values,
            color='gray', linewidth=3, linestyle='--', alpha=0.8,
            marker='s', markersize=8, markevery=2,
            label=f"Control Group Average (05-21:{control_avg_slope_2005:.4f}, 10-21:{control_avg_slope_2010:.4f})"
        )
    
    # 绘制目标处理国家
    # Russia: RGB(76, 92, 156), Ukraine: RGB(227, 195, 65)
    if treatment_country == 'russia':
        target_color = (76/255, 92/255, 156/255)  # 蓝灰色
    else:
        target_color = (227/255, 195/255, 65/255)  # 金黄色
    target_data = treatment_data[treatment_country]
    country_display = 'Russia' if treatment_country == 'russia' else 'Ukraine'
    
    # 计算并显示目标国家斜率（在绘制之前计算）
    treatment_slope_2005_2021 = slopes_2005_2021.get(treatment_country, np.nan)
    treatment_slope_2010_2021 = slopes_2010_2021.get(treatment_country, np.nan)
    
    ax.plot(
        target_data['year'], target_data[variable],
        color=target_color, linewidth=4, marker='o', markersize=10,
        label=f"Treatment: {country_display} (05-21:{treatment_slope_2005_2021:.4f}, 10-21:{treatment_slope_2010_2021:.4f})"
    )
    
    # 添加关键事件线
    ax.axvline(x=2022, color='red', linestyle='--', alpha=0.7, linewidth=2, label='2022: Russia-Ukraine War')
    
    # 添加处理前期间阴影区域（不加入图例，避免混乱）
    ax.axvspan(2005, 2021, alpha=0.1, color='gray', zorder=0)
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=12, fontweight='bold')
    ax.set_ylabel(var_names.get(variable, variable), fontsize=12, fontweight='bold')
    ax.set_title(f'Parallel Trends Test: {country_display} - {var_names.get(variable, variable)}\n(Pre-treatment Period: 2005-2021)', 
                fontsize=14, fontweight='bold', pad=20)
    
    # 图例：列出每条线对应的国家（含Treatment与Control）
    handles, labels = ax.get_legend_handles_labels()
    # 按标签去重，保持顺序
    unique_labels = []
    unique_handles = []
    for h, l in zip(handles, labels):
        if l not in unique_labels:
            unique_labels.append(l)
            unique_handles.append(h)
    ax.legend(unique_handles, unique_labels, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9, framealpha=0.9)
    
    # 在图例下方添加两个文本框
    # 第一个文本框：Top5斜率差异
    top5_slope_lines = ["Top 5 by Slope Difference:"]
    for i, c in enumerate(top5_candidates, 1):
        top5_slope_lines.append(f"{i}. {c.replace('_', ' ').title()}: {slope_diff[c]:.6f}")
    slope_text = "\n".join(top5_slope_lines)
    plt.figtext(0.8, 0.6, slope_text, ha='left', va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.9))
    
    # 第二个文本框：Top3 RMSE
    top3_rmse = sorted(candidate_rmse.items(), key=lambda x: x[1])[:3]
    rmse_lines = ["Top 3 by RMSE:"]
    for i, (c, val) in enumerate(top3_rmse, 1):
        rmse_lines.append(f"{i}. {c.replace('_', ' ').title()}: {val:.6f}")
    rmse_text = "\n".join(rmse_lines)
    plt.figtext(0.8, 0.5, rmse_text, ha='left', va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.9))
    
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(2005, 2024, 2))
    
    # 调整布局
    plt.subplots_adjust(right=0.75)
    
    # 保存图表（同时保存PNG和PDF格式）
    if save_path:
        try:
            # 确保输出目录存在
            save_dir = os.path.dirname(save_path)
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
            
            # 保存PNG格式
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ Chart saved (PNG): {save_path}")
            
            # 同时保存PDF格式
            pdf_path = save_path.replace('.png', '.pdf')
            try:
                plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
                print(f"✓ Chart saved (PDF): {pdf_path}")
            except Exception as pdf_error:
                print(f"⚠ Warning: Failed to save PDF to {pdf_path}: {pdf_error}")
                print("  PNG format saved successfully. PDF format may require additional dependencies.")
        except Exception as e:
            print(f"⚠ Warning: Failed to save chart to {save_path}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Warning: save_path is None, chart not saved. Please provide a valid save_path.")
    
    plt.close()  # 关闭图形以释放内存，不自动显示
    
    # 返回选定的控制国家列表，以便后续使用
    return top_selected_names

def plot_variable_with_slopes(variable, control_data, treatment_data, save_path=None):
    """绘制变量图并显示斜率"""
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # 定义变量显示名称
    var_names = {
        'west_cooperation_ratio-east_cooperation_ratio': 'West-East Cooperation Difference'
    }
    
    # 计算所有国家的斜率
    slopes_2005_2021 = {}
    slopes_2010_2021 = {}
    
    # 控制组斜率
    for country, data in control_data.items():
        slopes_2005_2021[country] = calculate_slopes(data, variable, 2005, 2021)
        slopes_2010_2021[country] = calculate_slopes(data, variable, 2010, 2021)
    
    # 处理组斜率
    for country, data in treatment_data.items():
        slopes_2005_2021[country] = calculate_slopes(data, variable, 2005, 2021)
        slopes_2010_2021[country] = calculate_slopes(data, variable, 2010, 2021)
    
    # 找出与俄罗斯和乌克兰分别最相似的前3个控制国家
    russia_slope_2005 = slopes_2005_2021.get('russia', 0)
    russia_slope_2010 = slopes_2010_2021.get('russia', 0)
    ukraine_slope_2005 = slopes_2005_2021.get('ukraine', 0)
    ukraine_slope_2010 = slopes_2010_2021.get('ukraine', 0)
    
    # 计算每个控制国家与俄罗斯的斜率差异
    russia_differences = {}
    for country in control_data.keys():
        if country in slopes_2005_2021 and country in slopes_2010_2021:
            diff_2005 = abs(slopes_2005_2021[country] - russia_slope_2005)
            diff_2010 = abs(slopes_2010_2021[country] - russia_slope_2010)
            avg_diff = (diff_2005 + diff_2010) / 2
            russia_differences[country] = avg_diff
    
    # 计算每个控制国家与乌克兰的斜率差异
    ukraine_differences = {}
    for country in control_data.keys():
        if country in slopes_2005_2021 and country in slopes_2010_2021:
            diff_2005 = abs(slopes_2005_2021[country] - ukraine_slope_2005)
            diff_2010 = abs(slopes_2010_2021[country] - ukraine_slope_2010)
            avg_diff = (diff_2005 + diff_2010) / 2
            ukraine_differences[country] = avg_diff
    
    # 找出与俄罗斯最相似的前4个国家
    top4_russia = sorted(russia_differences.items(), key=lambda x: x[1])[:4]
    top4_russia_names = [country for country, _ in top4_russia]
    
    # 找出与乌克兰最相似的前4个国家
    top4_ukraine = sorted(ukraine_differences.items(), key=lambda x: x[1])[:4]
    top4_ukraine_names = [country for country, _ in top4_ukraine]
    
    print(f"\nTop 4 control countries most similar to Russia for {variable}:")
    for i, (country, diff) in enumerate(top4_russia):
        print(f"  {i+1}. {country}: avg difference = {diff:.6f}")
    
    print(f"\nTop 4 control countries most similar to Ukraine for {variable}:")
    for i, (country, diff) in enumerate(top4_ukraine):
        print(f"  {i+1}. {country}: avg difference = {diff:.6f}")
    
    # 绘制控制组国家
    control_colors = ['steelblue', 'forestgreen', 'coral', 'gold', 'hotpink', 'gray', 'slateblue', 'seagreen', 'darkgoldenrod']
    
    for i, (country, data) in enumerate(control_data.items()):
        color = control_colors[i % len(control_colors)]
        country_display = country.replace('_', ' ').title()
        
        # 绘制数据线（统一线条样式）
        ax.plot(data['year'], data[variable], 
                color=color, linewidth=2, alpha=0.8, 
                label=country_display)
        
        # 计算并显示斜率
        slope_2005_2021 = slopes_2005_2021[country]
        slope_2010_2021 = slopes_2010_2021[country]
        
        # 在图上添加斜率信息，标识与俄罗斯和乌克兰的相似性
        text_content = f'{country_display}: 2005-2021: {slope_2005_2021:.4f}, 2010-2021: {slope_2010_2021:.4f}'
        
        # 判断是否为前4名，设置不同的文字颜色（无背景色）
        if country in top4_russia_names and country in top4_ukraine_names:
            # 同时是俄罗斯和乌克兰的前4名
            text_content = f'[R+U TOP4] {country_display}: 2005-2021: {slope_2005_2021:.4f}, 2010-2021: {slope_2010_2021:.4f}'
            text_color = 'purple'  # 紫色文字表示同时是两者的前4名
        elif country in top4_russia_names:
            # 只是俄罗斯的前4名
            text_content = f'[R TOP4] {country_display}: 2005-2021: {slope_2005_2021:.4f}, 2010-2021: {slope_2010_2021:.4f}'
            text_color = 'red'  # 俄罗斯的颜色
        elif country in top4_ukraine_names:
            # 只是乌克兰的前4名
            text_content = f'[U TOP4] {country_display}: 2005-2021: {slope_2005_2021:.4f}, 2010-2021: {slope_2010_2021:.4f}'
            text_color = 'orange'  # 乌克兰的颜色
        else:
            # 普通国家
            text_color = 'black'  # 默认黑色文字
        
        ax.text(0.02, 0.95 - i*0.04, text_content,
                transform=ax.transAxes, fontsize=9, color=text_color)
    
    # 绘制处理组国家
    # Russia: RGB(76, 92, 156), Ukraine: RGB(227, 195, 65)
    treatment_colors = {
        'russia': (76/255, 92/255, 156/255),  # 蓝灰色
        'ukraine': (227/255, 195/255, 65/255)  # 金黄色
    }
    for i, (country, data) in enumerate(treatment_data.items()):
        country_display = 'Russia' if country == 'russia' else 'Ukraine'
        country_color = treatment_colors.get(country, 'black')
        ax.plot(data['year'], data[variable], 
                color=country_color, linewidth=3, marker='o', 
                label=f'Treatment: {country_display}', markersize=8)
        
        # 计算并显示处理组斜率
        slope_2005_2021 = slopes_2005_2021[country]
        slope_2010_2021 = slopes_2010_2021[country]
        
        ax.text(0.02, 0.95 - (len(control_data) + i)*0.04, 
                f'{country_display}: 2005-2021: {slope_2005_2021:.4f}, 2010-2021: {slope_2010_2021:.4f}',
                transform=ax.transAxes, fontsize=9, color=country_color,
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # 添加关键事件线
    ax.axvline(x=2022, color='red', linestyle='--', alpha=0.7, label='2022: Russia-Ukraine War')
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel(var_names.get(variable, variable), fontsize=12)
    ax.set_title(f'{var_names.get(variable, variable)} with Slopes (2005-2021 vs 2010-2021)', fontsize=14, fontweight='bold')
    
    # 图例
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(2005, 2024, 2))
    
    # 调整布局
    plt.subplots_adjust(right=0.75)
    
    # 保存图表（同时保存PNG和PDF格式）
    if save_path:
        try:
            # 确保输出目录存在
            save_dir = os.path.dirname(save_path)
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
            
            # 保存PNG格式
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ Chart saved (PNG): {save_path}")
            
            # 同时保存PDF格式
            pdf_path = save_path.replace('.png', '.pdf')
            try:
                plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
                print(f"✓ Chart saved (PDF): {pdf_path}")
            except Exception as pdf_error:
                print(f"⚠ Warning: Failed to save PDF to {pdf_path}: {pdf_error}")
                print("  PNG format saved successfully. PDF format may require additional dependencies.")
        except Exception as e:
            print(f"⚠ Warning: Failed to save chart to {save_path}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Warning: save_path is None, chart not saved. Please provide a valid save_path.")
    
    plt.close()  # 关闭图形以释放内存，不自动显示

def plot_selected_control_trends(treatment_country, variable, control_data, treatment_data, 
                                  selected_control_countries, save_path=None):
    """
    绘制选定的控制国家与处理国家的平行趋势图
    只显示两条线：控制组平均值和处理组
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 定义变量显示名称
    var_names = {
        'west_cooperation_ratio-east_cooperation_ratio': 'West-East Cooperation Difference',
        'west_cooperation_ratio/east_cooperation_ratio': 'West/East Cooperation Ratio'
    }
    
    country_display = 'Russia' if treatment_country == 'russia' else 'Ukraine'
    
    # 颜色方案
    # Russia: RGB(76, 92, 156) -> 归一化到0-1范围
    # Ukraine: RGB(227, 195, 65) -> 归一化到0-1范围
    if treatment_country == 'russia':
        treatment_color = (76/255, 92/255, 156/255)  # 蓝灰色
    else:
        treatment_color = (227/255, 195/255, 65/255)  # 金黄色
    control_avg_color = 'gray'  # 灰色
    
    # 计算并绘制控制组平均值（仅使用选定的控制国家）
    if selected_control_countries:
        control_avg_data = {}
        all_years = set()
        for country in selected_control_countries:
            if country in control_data:
                all_years.update(control_data[country]['year'].values)
        
        for year in sorted(all_years):
            year_values = []
            for country in selected_control_countries:
                if country in control_data:
                    year_data = control_data[country][control_data[country]['year'] == year]
                    if len(year_data) > 0:
                        year_values.append(year_data[variable].values[0])
            if len(year_values) > 0:
                control_avg_data[year] = np.mean(year_values)
        
        if len(control_avg_data) > 0:
            control_years = sorted(control_avg_data.keys())
            control_avg_values = [control_avg_data[y] for y in control_years]
            
            # 绘制控制组平均值线
            ax.plot(
                control_years, control_avg_values,
                color=control_avg_color, linewidth=3.5, linestyle='--', alpha=0.9,
                marker='s', markersize=8, markevery=2,
                label='Control Group Average',
                zorder=5
            )
    
    # 绘制处理组国家
    if treatment_country in treatment_data:
        target_data = treatment_data[treatment_country]
        ax.plot(
            target_data['year'], target_data[variable],
            color=treatment_color, linewidth=4, marker='o', markersize=10,
            label=f'Treatment: {country_display}',
            zorder=10  # 确保处理组线在最上层
        )
    
    # 添加关键事件线和处理前期间阴影
    ax.axvline(x=2022, color='red', linestyle='--', alpha=0.7, linewidth=2, 
               label='2022: Russia-Ukraine War', zorder=3)
    # ax.axvspan(2005, 2021, alpha=0.1, color='gray', zorder=0)
    
    # 设置图表属性
    ax.set_xlabel('Year', fontsize=14, fontweight='bold')
    ax.set_ylabel(var_names.get(variable, variable), fontsize=14, fontweight='bold')
    ax.set_title(f'Parallel Trends: {country_display} vs Control Group Average\n{var_names.get(variable, variable)}', 
                fontsize=16, fontweight='bold', pad=20)
    
    # 准备图例标签，包含控制国家信息
    selected_countries_str = ', '.join([c.replace('_', ' ').title().replace('Rep Of Georgia', 'Georgia') 
                                       for c in selected_control_countries])
    
    # 获取现有的图例句柄和标签
    handles, labels = ax.get_legend_handles_labels()
    
    # 添加控制国家信息到控制组平均值的标签中
    for i, label in enumerate(labels):
        if 'Control Group Average' in label:
            labels[i] = f'Control Group Average\n({selected_countries_str})'
            break
    
    # 创建图例
    ax.legend(handles, labels, loc='best', fontsize=11, framealpha=0.95, fancybox=True, shadow=True)
    
    # 网格和刻度
    # ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xticks(range(2005, 2024, 2))
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表（同时保存PNG和PDF格式）
    if save_path:
        try:
            # 确保输出目录存在
            save_dir = os.path.dirname(save_path)
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
            
            # 保存PNG格式
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ Selected control trends chart saved (PNG): {save_path}")
            
            # 同时保存PDF格式
            pdf_path = save_path.replace('.png', '.pdf')
            try:
                plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
                print(f"✓ Selected control trends chart saved (PDF): {pdf_path}")
            except Exception as pdf_error:
                print(f"⚠ Warning: Failed to save PDF to {pdf_path}: {pdf_error}")
                print("  PNG format saved successfully. PDF format may require additional dependencies.")
        except Exception as e:
            print(f"⚠ Warning: Failed to save chart to {save_path}: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Warning: save_path is None, chart not saved. Please provide a valid save_path.")
    
    plt.close()  # 关闭图形以释放内存，不自动显示

def conduct_parallel_trends_test(treatment_country, variable, control_data, treatment_data, pre_period_start=2005, pre_period_end=2021):
    """
    进行平行趋势检验
    检验处理组和控制组在政策实施前的趋势是否平行
    
    方法：使用回归方法检验斜率差异（使用所有控制国家的个体数据）
    模型: Y = β0 + β1*treated + β2*year + β3*treated*year + country_FE + ε
    如果β3不显著（p > 0.05），则平行趋势假设成立
    
    注意：这里使用控制组平均值进行检验，是平行趋势检验的常见方法
    """
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    
    # 获取处理组数据（处理前期间）
    treated_data = treatment_data[treatment_country]
    treated_pre = treated_data[(treated_data['year'] >= pre_period_start) & 
                               (treated_data['year'] <= pre_period_end)].copy()
    
    if len(treated_pre) < 2:
        return None, None, None, None, None
    
    # 获取所有控制国家的数据（处理前期间）
    control_pre_list = []
    for country, data in control_data.items():
        control_pre = data[(data['year'] >= pre_period_start) & 
                          (data['year'] <= pre_period_end)].copy()
        if len(control_pre) > 0:
            control_pre['country'] = country
            control_pre_list.append(control_pre)
    
    if len(control_pre_list) == 0:
        return None, None, None, None, None
    
    # 方法1：使用控制组平均值（更简单，常用于可视化）
    # 计算控制组平均值（按年份）
    all_years = set(treated_pre['year'].values)
    for control_pre in control_pre_list:
        all_years.update(control_pre['year'].values)
    all_years = sorted(list(all_years))
    
    # 计算每年控制组的平均值
    control_means_by_year = {}
    for year in all_years:
        year_values = []
        for control_pre in control_pre_list:
            year_data = control_pre[control_pre['year'] == year]
            if len(year_data) > 0:
                year_values.append(year_data[variable].values[0])
        if len(year_values) > 0:
            control_means_by_year[year] = np.mean(year_values)
    
    if len(control_means_by_year) < 2:
        return None, None, None, None, None
    
    # 构建回归数据
    # 处理组数据
    treated_reg_data = []
    for _, row in treated_pre.iterrows():
        treated_reg_data.append({
            'year': row['year'],
            'value': row[variable],
            'treated': 1,
            'country': treatment_country
        })
    
    # 控制组数据（使用平均值，标记为单个"控制组"）
    control_reg_data = []
    for year, mean_value in control_means_by_year.items():
        control_reg_data.append({
            'year': year,
            'value': mean_value,
            'treated': 0,
            'country': 'control_avg'
        })
    
    # 合并数据
    reg_df = pd.DataFrame(treated_reg_data + control_reg_data)
    
    if len(reg_df) < 4:
        return None, None, None, None, None
    
    # 中心化年份变量（减少多重共线性，并便于解释）
    year_mean = reg_df['year'].mean()
    reg_df['year_centered'] = reg_df['year'] - year_mean
    
    # 构建交互项
    reg_df['treated_year'] = reg_df['treated'] * reg_df['year_centered']
    
    # 回归：value = β0 + β1*treated + β2*year_centered + β3*treated*year_centered + ε
    # β3的显著性检验平行趋势假设
    # H0: β3 = 0 (平行趋势成立)
    # 如果β3不显著（p > 0.05），则不能拒绝H0，平行趋势假设成立
    X = reg_df[['treated', 'year_centered', 'treated_year']]
    X = sm.add_constant(X)
    y = reg_df['value']
    
    try:
        model = sm.OLS(y, X).fit()
        
        # 提取交互项系数（斜率差异）
        if 'treated_year' in model.params:
            slope_diff = model.params['treated_year']
            slope_diff_se = model.bse['treated_year']
            t_stat = model.tvalues['treated_year']
            p_value = model.pvalues['treated_year']
            
            return slope_diff, slope_diff_se, t_stat, p_value, model
        else:
            return None, None, None, None, None
    except Exception as e:
        print(f"  回归分析出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None

def main():
    """Main function"""
    # 创建输出目录
    output_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/1netoworks_did_russia_ukraine/parallel trends'
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 80)
    print("平行趋势检验分析")
    print("=" * 80)
    print("Loading data...")
    control_data, treatment_data = load_data()
    
    if not control_data or not treatment_data:
        print("Data loading failed")
        return
    
    print(f"Loaded {len(control_data)} control countries and {len(treatment_data)} treatment countries")
    
    # Two variables
    variables = ['west_cooperation_ratio-east_cooperation_ratio']  # 'west_cooperation_ratio/east_cooperation_ratio'
    
    # Draw individual charts for Russia and Ukraine only
    treatment_countries = ['russia', 'ukraine']
    
    # 存储平行趋势检验结果
    parallel_trends_results = []
    
    for treatment_country in treatment_countries:
        print(f"\n{'=' * 80}")
        print(f"分析 {treatment_country.title()} 的平行趋势")
        print(f"{'=' * 80}")
        
        for variable in variables:
            print(f"\n变量: {variable}")
            print("-" * 60)
            
            # 进行平行趋势检验
            slope_diff, slope_diff_se, t_stat, p_value, model = conduct_parallel_trends_test(
                treatment_country, variable, control_data, treatment_data, 
                pre_period_start=2005, pre_period_end=2021
            )
            
            if slope_diff is not None:
                print(f"\n平行趋势检验结果:")
                print(f"  处理前斜率差异 (β3): {slope_diff:.6f}")
                print(f"  标准误: {slope_diff_se:.6f}")
                print(f"  t统计量: {t_stat:.4f}")
                print(f"  p值: {p_value:.4f}")
                
                if p_value > 0.05:
                    print("  ✓ 平行趋势假设成立 (p > 0.05) - 处理组和控制组在处理前趋势平行")
                elif p_value > 0.10:
                    print("  ⚠ 平行趋势假设在10%水平上不成立，但在5%水平上成立")
                else:
                    print("  ⚠ 平行趋势假设可能不成立 (p <= 0.05) - 需要谨慎解释DID结果")
                
                if model is not None:
                    print(f"\n回归模型摘要:")
                    print(model.summary().tables[1])
                
                parallel_trends_results.append({
                    'treatment_country': treatment_country,
                    'variable': variable,
                    'slope_difference': slope_diff,
                    'std_error': slope_diff_se,
                    't_statistic': t_stat,
                    'p_value': p_value,
                    'parallel_trends_holds_5pct': p_value > 0.05,
                    'parallel_trends_holds_10pct': p_value > 0.10
                })
            else:
                print("  ⚠ 无法进行平行趋势检验（数据不足）")
            
            # 绘制完整图表（包含所有控制国家）
            print(f"\n正在绘制完整图表: {treatment_country.title()} - {variable}")
            
            # 生成文件名（处理特殊字符）
            safe_var = variable.replace('/', '_div_').replace('-', '_minus_').replace(' ', '_')
            save_path = os.path.join(output_dir, f"parallel_trends_{treatment_country}_{safe_var}.png")
            
            # 绘制完整图表并获取选定的控制国家
            selected_control_countries = plot_individual_slopes(treatment_country, variable, control_data, treatment_data, save_path)
            
            # 图表已保存（PNG和PDF格式），保存信息已在函数内部打印
            
            # 绘制选定控制国家的简洁图表
            if selected_control_countries and len(selected_control_countries) > 0:
                print(f"\n正在绘制选定控制国家图表: {treatment_country.title()} - {variable}")
                selected_save_path = os.path.join(output_dir, f"parallel_trends_selected_{treatment_country}_{safe_var}.png")
                plot_selected_control_trends(
                    treatment_country, variable, control_data, treatment_data,
                    selected_control_countries, selected_save_path
                )
                print(f"✓ 选定控制国家图表已保存")
        
        print(f"\n完成 {treatment_country.title()} 的所有分析")
    
    # 保存平行趋势检验结果
    if parallel_trends_results:
        results_df = pd.DataFrame(parallel_trends_results)
        results_file = os.path.join(output_dir, 'parallel_trends_test_results.csv')
        results_df.to_csv(results_file, index=False)
        print(f"\n平行趋势检验结果已保存到: {results_file}")
        print("\n结果摘要:")
        print(results_df.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("所有平行趋势检验完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
