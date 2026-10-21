
import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent

import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')



# 数据路径
data_base_dir = str(HERE / "west_east_tile")
russia_data_path = str(HERE / "west_east_tile/russia_west_east_tile.csv")
ukraine_data_path = str(HERE / "west_east_tile/ukraine_west_east_tile.csv")



def get_country_data_path(country):
    """根据国家名称获取数据路径"""
    if country == 'russia':
        return russia_data_path
    elif country == 'ukraine':
        return ukraine_data_path
    else:
        raise ValueError(f"不支持的国家: {country}")

def get_variable_display_name(dependent_variable):
    """获取因变量的显示名称"""
    if dependent_variable == 'west_cooperation_ratio':
        return 'West Cooperation Ratio'
    elif dependent_variable == 'east_cooperation_ratio':
        return 'East Cooperation Ratio'
    elif dependent_variable == 'west_cooperation_ratio-east_cooperation_ratio':
        return 'West-East Cooperation Difference'
    elif dependent_variable == 'west_cooperation_ratio/east_cooperation_ratio':
        return 'West/East Cooperation Ratio'
    else:
        return dependent_variable

def get_safe_filename(treated_country, treat_year, dependent_variable):
    """生成安全的文件名，将特殊字符替换为安全的字符"""
    safe_var = dependent_variable.replace('/', '_div_').replace('-', '_minus_').replace(' ', '_')
    return f'did_analysis_results_{treated_country}_{treat_year}_{safe_var}.png'

def calculate_dependent_variable(data, dependent_variable):
    """根据dependent_variable设置计算因变量值"""
    if dependent_variable == 'west_cooperation_ratio':
        return data['west_cooperation_ratio']
    elif dependent_variable == 'east_cooperation_ratio':
        return data['east_cooperation_ratio']
    elif dependent_variable == 'west_cooperation_ratio-east_cooperation_ratio':
        return data['west_cooperation_ratio'] - data['east_cooperation_ratio']
    elif dependent_variable == 'west_cooperation_ratio/east_cooperation_ratio':
        # 避免除零错误
        return data['west_cooperation_ratio'] / (data['east_cooperation_ratio'] + 1e-8)
    else:
        return data[dependent_variable]

def load_and_prepare_data(treated_country, treat_year, dependent_variable):
    """加载并准备DID分析所需的数据"""
    
    # 获取控制组国家列表
    control_countries = get_control_countries(treated_country)
    
    # 加载处理国家数据
    treated_data_path = get_country_data_path(treated_country)
    if not os.path.exists(treated_data_path):
        raise FileNotFoundError(f"处理国家数据文件不存在: {treated_data_path}")
    
    treated_data = pd.read_csv(treated_data_path)
    treated_data['country'] = treated_country
    treated_data['treated'] = 1
    
    # 计算因变量
    treated_data['dependent_var'] = calculate_dependent_variable(treated_data, dependent_variable)
    print(f"  加载处理组数据: {treated_country} ({len(treated_data)} 条记录)")
    
    # 加载控制国家数据
    control_data_list = []
    for control_country in control_countries:
        data_path = os.path.join(data_base_dir, f'{control_country}_west_east_tile.csv')
        if os.path.exists(data_path):
            data = pd.read_csv(data_path)
            data['country'] = control_country
            data['treated'] = 0
            # 计算因变量
            data['dependent_var'] = calculate_dependent_variable(data, dependent_variable)
            control_data_list.append(data)
            print(f"  加载控制组数据: {control_country} ({len(data)} 条记录)")
        else:
            print(f"  ⚠ 警告: 控制国家数据文件不存在，跳过: {data_path}")
    
    if len(control_data_list) == 0:
        raise ValueError(f"未找到任何控制国家数据！请检查数据文件路径: {data_base_dir}")
    
    # 合并所有数据
    all_data = pd.concat([treated_data] + control_data_list, ignore_index=True)
    
    # 创建时间虚拟变量
    all_data['post_treatment'] = (all_data['year'] >= treat_year).astype(int)
    
    # 创建交互项
    all_data['did'] = all_data['treated'] * all_data['post_treatment']
    
    return all_data

def conduct_did_analysis(data, treated_country, treat_year, dependent_variable):
    """执行DID分析 - 使用OLS回归获取所有参数"""
    import statsmodels.api as sm
    from statsmodels.formula.api import ols
    
    # 获取控制组国家列表
    control_countries = get_control_countries(treated_country)
    
    print("=" * 60)
    print("DID模型分析结果")
    print("=" * 60)
    print(f"处理组: {treated_country.title()} (treated=1)")
    print(f"控制组: {', '.join(control_countries)} (treated=0)")
    print(f"处理年份: {treat_year}年")
    print(f"因变量: {dependent_variable}")
    print("=" * 60)
    
    # 创建年份虚拟变量
    data['year_factor'] = data['year'].astype('category')
    
    # 创建国家虚拟变量
    data['country_factor'] = data['country'].astype('category')
    
    # 构建DID回归模型
    # 模型: Y = β0 + β1*treated + β2*post_treatment + β3*treated*post_treatment + 年份固定效应 + 国家固定效应 + ε
    formula = f'dependent_var ~ treated + post_treatment + did + C(year_factor) + C(country_factor)'
    
    print(f"\n回归模型: {formula}")
    print("-" * 40)
    
    # 执行回归
    model = ols(formula, data=data)
    results = model.fit()
    
    # 打印完整回归结果
    print("\n完整回归结果:")
    print(results.summary())
    
    # 提取关键参数
    did_coef = results.params['did']
    did_se = results.bse['did']
    did_pvalue = results.pvalues['did']
    did_ci_lower = results.conf_int().loc['did', 0]
    did_ci_upper = results.conf_int().loc['did', 1]
    
    # 显著性判断
    if did_pvalue < 0.01:
        significance = "***"
    elif did_pvalue < 0.05:
        significance = "**"
    elif did_pvalue < 0.1:
        significance = "*"
    else:
        significance = ""
    
    print(f"\nDID系数 (β3): {did_coef:.4f}")
    print(f"标准误: {did_se:.4f}")
    print(f"p值: {did_pvalue:.4f}")
    print(f"95%置信区间: [{did_ci_lower:.4f}, {did_ci_upper:.4f}]")
    print(f"显著性: {significance}")
    
    # 提取其他关键参数
    treated_coef = results.params['treated']  # β1
    post_coef = results.params['post_treatment']  # β2
    
    print(f"\n其他关键参数:")
    print(f"处理组效应 (β1): {treated_coef:.4f}")
    print(f"时间效应 (β2): {post_coef:.4f}")
    
    return {
        'did_estimate': did_coef,
        'std_error': did_se,
        'ci_lower': did_ci_lower,
        'ci_upper': did_ci_upper,
        't_stat': did_coef / did_se,
        'p_value': did_pvalue,
        'significance': significance,
        'treated_coef': treated_coef,
        'post_coef': post_coef,
        'full_results': results
    }

def create_visualizations(data, results, treated_country, treat_year, dependent_variable, output_dir):
    """创建可视化图表 - 显示DID模型所有关键参数结果"""
    
    # 设置图表样式
    plt.style.use('default')
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # 创建DID模型参数结果图
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    # 准备参数数据
    param_names = ['β₀ (Intercept)', 'β₁ (Treated)', 'β₂ (Post)', 'β₃ (DID)']
    param_values = [
        results['full_results'].params['Intercept'] if 'Intercept' in results['full_results'].params else 0,
        results['treated_coef'],
        results['post_coef'],
        results['did_estimate']
    ]
    param_errors = [
        results['full_results'].bse['Intercept'] if 'Intercept' in results['full_results'].bse else 0,
        results['full_results'].bse['treated'],
        results['full_results'].bse['post_treatment'],
        results['std_error']
    ]
    param_pvalues = [
        results['full_results'].pvalues['Intercept'] if 'Intercept' in results['full_results'].pvalues else 1,
        results['full_results'].pvalues['treated'],
        results['full_results'].pvalues['post_treatment'],
        results['p_value']
    ]
    
    # 绘制所有参数
    colors = ['blue', 'green', 'orange', 'red']
    x_positions = range(len(param_names))
    
    for i, (name, value, error, pval) in enumerate(zip(param_names, param_values, param_errors, param_pvalues)):
        # 根据显著性设置颜色深浅
        alpha = 1.0 if pval < 0.05 else 0.6
        marker_size = 12 if i == 3 else 8  # DID参数更大
        
        ax.errorbar(i, value, yerr=error, 
                   fmt='o', color=colors[i], markersize=marker_size, 
                   capsize=8, capthick=2, alpha=alpha)
        
        # 添加参数标签
        significance = ""
        if pval < 0.01:
            significance = "***"
        elif pval < 0.05:
            significance = "**"
        elif pval < 0.1:
            significance = "*"
        
        ax.text(i, value + error + 0.01, f"{value:.3f}{significance}", 
               ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 设置坐标轴
    ax.set_xlim(-0.5, len(param_names) - 0.5)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(param_names, rotation=45, ha='right')
    ax.set_ylabel(f'Coefficient Value ({get_variable_display_name(dependent_variable)})', fontsize=12)
    
    # 标题
    # title_text = f'DID Model All Parameters\nTreatment: {treated_country.title()}, Year: {treat_year}'
    # ax.set_title(title_text, fontsize=14, fontweight='bold')
    
    # 添加图例说明到图片外面左下方
    legend_text = "Significance: *** p<0.01, ** p<0.05, * p<0.1"
    plt.figtext(0.02, 0.02, legend_text, fontsize=9, 
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
    
    ax.grid(True, alpha=0.3)
    
    # 调整布局，为左下方和右侧文字留出空间
    plt.subplots_adjust(bottom=0.15)
    
    # 保存图片到输出目录（同时保存PNG和PDF格式）
    output_path = os.path.join(output_dir, get_safe_filename(treated_country, treat_year, dependent_variable))
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存PNG格式
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ 图表已保存 (PNG): {output_path}")
        
        # 同时保存PDF格式
        pdf_path = output_path.replace('.png', '.pdf')
        plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
        print(f"✓ 图表已保存 (PDF): {pdf_path}")
    except Exception as e:
        print(f"⚠ Warning: Failed to save chart: {e}")
        import traceback
        traceback.print_exc()
    
    plt.close()  # 关闭图形以释放内存

def get_control_countries(treat_country):
    """根据处理国家获取对应的控制组国家"""
    if treat_country == 'russia':
        return ['south_africa', 'rep-of-georgia','azerbaijan']
    elif treat_country == 'ukraine':
        return ['argentina', 'rep-of-georgia','serbia']
    else:
        raise ValueError(f"不支持的国家: {treat_country}")
    

if __name__ == "__main__":
    # 分析设置变量 - 可以灵活切换
    TREAT_YEAR = 2022  # 处理年份，可选: 2021, 2022等
    
    # 输出目录
    output_base_dir = str(HERE / "did_results")
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 存储所有结果
    all_results = []
    
    # 循环处理所有组合
    for TREATED_COUNTRY in ['russia', 'ukraine']:
        for DEPENDENT_VARIABLE in ['west_cooperation_ratio-east_cooperation_ratio']:
            print("\n" + "=" * 80)
            print(f"开始分析: {TREATED_COUNTRY.title()} - {DEPENDENT_VARIABLE}")
            print("=" * 80)
            
            try:
                # 显示分析设置
                print("=" * 60)
                print("DID分析设置")
                print("=" * 60)
                print(f"处理国家: {TREATED_COUNTRY.title()}")
                print(f"处理年份: {TREAT_YEAR}年")
                print(f"因变量: {DEPENDENT_VARIABLE}")
                print(f"显示名称: {get_variable_display_name(DEPENDENT_VARIABLE)}")
                print("=" * 60)
                
                # 加载数据
                print("\n正在加载数据...")
                data = load_and_prepare_data(TREATED_COUNTRY, TREAT_YEAR, DEPENDENT_VARIABLE)
                
                print(f"\n数据加载完成！")
                print(f"  总观测数: {len(data)}")
                print(f"  时间范围: {data['year'].min()} - {data['year'].max()}")
                print(f"  国家数量: {data['country'].nunique()}")
                print(f"  处理组国家: {TREATED_COUNTRY}")
                print(f"  控制组国家: {', '.join(get_control_countries(TREATED_COUNTRY))}")
                
                print("\n数据预览:")
                print(data[['country', 'year', 'treated', 'post_treatment', 'did', 'dependent_var']].head(10))
                
                # 执行DID分析
                results = conduct_did_analysis(data, TREATED_COUNTRY, TREAT_YEAR, DEPENDENT_VARIABLE)
                
                # 添加分析信息到结果
                results['treated_country'] = TREATED_COUNTRY
                results['treat_year'] = TREAT_YEAR
                results['dependent_variable'] = DEPENDENT_VARIABLE
                all_results.append(results)
                
                # 创建可视化
                print("\n正在生成可视化图表...")
                create_visualizations(data, results, TREATED_COUNTRY, TREAT_YEAR, DEPENDENT_VARIABLE, output_base_dir)
                
                # 总结
                print("\n" + "=" * 60)
                print("分析总结:")
                print("=" * 60)
                if results['p_value'] < 0.05:
                    print(f"{TREAT_YEAR}年对{TREATED_COUNTRY.title()}的{get_variable_display_name(DEPENDENT_VARIABLE)}产生了显著影响")
                    print(f"影响方向: {'正向' if results['did_estimate'] > 0 else '负向'}")
                    print(f"影响大小: {abs(results['did_estimate']):.4f}")
                else:
                    print(f"{TREAT_YEAR}年对{TREATED_COUNTRY.title()}的{get_variable_display_name(DEPENDENT_VARIABLE)}没有产生显著影响")
                
                print(f"置信度: 95%")
                print(f"置信区间: [{results['ci_lower']:.4f}, {results['ci_upper']:.4f}]")
                
            except Exception as e:
                print(f"\n✗ 分析 {TREATED_COUNTRY} - {DEPENDENT_VARIABLE} 时出错: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    # 保存所有结果
    if all_results:
        print("\n" + "=" * 80)
        print("保存所有分析结果...")
        print("=" * 80)
        
        # 准备结果DataFrame
        results_summary = []
        for r in all_results:
            results_summary.append({
                'treated_country': r['treated_country'],
                'treat_year': r['treat_year'],
                'dependent_variable': r['dependent_variable'],
                'did_estimate': r['did_estimate'],
                'std_error': r['std_error'],
                'ci_lower': r['ci_lower'],
                'ci_upper': r['ci_upper'],
                'p_value': r['p_value'],
                'significance': r['significance'],
                'treated_coef': r['treated_coef'],
                'post_coef': r['post_coef']
            })
        
        results_df = pd.DataFrame(results_summary)
        results_file = os.path.join(output_base_dir, 'did_results.csv')
        results_df.to_csv(results_file, index=False)
        print(f"所有结果已保存到: {results_file}")
        
        print("\n结果摘要:")
        print(results_df.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("所有分析完成！")
    print("=" * 80)
    print("\n使用说明:")
    print("如需修改分析设置，请修改代码中的相应变量:")
    print("   TREAT_YEAR = 2022  # 处理年份，可选: 2021, 2022等")
    print("   TREATED_COUNTRY = 'russia'  # 处理国家，可选: 'russia', 'ukraine'")
    print("   DEPENDENT_VARIABLE = 'west_cooperation_ratio-east_cooperation_ratio'  # 因变量，可选:")
    print("      'west_cooperation_ratio'  # 西方合作比例")
    print("      'east_cooperation_ratio'  # 东方合作比例")
    print("      'west_cooperation_ratio-east_cooperation_ratio'  # 西方-东方合作差异")
    print("      'west_cooperation_ratio/east_cooperation_ratio'  # 西方/东方合作比例")
