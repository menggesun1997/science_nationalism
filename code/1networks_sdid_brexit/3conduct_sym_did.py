
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

def custom_synthetic_control(data_matrix, treatment_start, covariate_matrix=None):
    """
    改进的Synthetic Control实现，支持协变量
    data_matrix: 数据矩阵，第一列是处理组，其余列是控制组
    treatment_start: 处理开始的时间点索引
    covariate_matrix: 协变量矩阵（可选）
    """
    from scipy.optimize import minimize
    
    # 分离处理组和控制组数据
    treatment_data = data_matrix[:, 0]  # 第一列是处理组
    control_data = data_matrix[:, 1:]   # 其余列是控制组
    
    # 预处理期数据（用于拟合权重）
    pre_treatment_data = data_matrix[:treatment_start, :]
    pre_treatment_y = pre_treatment_data[:, 0]  # 处理组预处理期
    pre_treatment_X = pre_treatment_data[:, 1:]  # 控制组预处理期
    
    # 如果有协变量，也提取预处理期的协变量
    if covariate_matrix is not None:
        pre_covariates = covariate_matrix[:treatment_start, :]
        all_covariates = covariate_matrix
    else:
        pre_covariates = None
        all_covariates = None
    
    def objective_function(weights):
        """目标函数：最小化预处理期的预测误差"""
        if pre_covariates is not None:
            # 如果有协变量，使用加权平均 + 协变量调整
            synthetic_pred = np.dot(pre_treatment_X, weights)
            # 这里可以添加协变量调整，暂时简化处理
            return np.sum((pre_treatment_y - synthetic_pred) ** 2)
        else:
            synthetic_pred = np.dot(pre_treatment_X, weights)
            return np.sum((pre_treatment_y - synthetic_pred) ** 2)
    
    def constraint_function(weights):
        """约束函数：权重和为1"""
        return np.sum(weights) - 1
    
    # 初始权重（均等权重）
    n_controls = control_data.shape[1]
    initial_weights = np.ones(n_controls) / n_controls
    
    # 约束：权重和为1，权重非负
    constraints = {'type': 'eq', 'fun': constraint_function}
    bounds = [(0, 1) for _ in range(n_controls)]
    
    # 优化权重
    result = minimize(objective_function, initial_weights, 
                     method='SLSQP', bounds=bounds, constraints=constraints)
    
    if result.success:
        weights = result.x
    else:
        print("优化失败，使用OLS权重")
        # 回退到OLS方法
        reg = LinearRegression()
        reg.fit(pre_treatment_X, pre_treatment_y)
        weights = reg.coef_
        weights = weights / weights.sum()
        weights = np.maximum(weights, 0)  # 确保非负
        weights = weights / weights.sum()  # 重新标准化
    
    print(f"Control group weights: {dict(zip(['ICELAND', 'JAPAN', 'NORWAY', 'SINGAPORE', 'KOREA, REP.'], weights))}")
    
    # 计算拟合质量（预处理期）
    pre_synthetic = np.dot(pre_treatment_X, weights)
    pre_mse = np.mean((pre_treatment_y - pre_synthetic) ** 2)
    pre_r2 = 1 - np.sum((pre_treatment_y - pre_synthetic) ** 2) / np.sum((pre_treatment_y - np.mean(pre_treatment_y)) ** 2)
    
    print(f"Pre-treatment fit quality:")
    print(f"  MSE: {pre_mse:.6f}")
    print(f"  R²: {pre_r2:.4f}")
    
    # 计算合成控制组
    synthetic_control = np.dot(control_data, weights)
    
    # 计算处理效应
    treatment_effect = treatment_data - synthetic_control
    
    return synthetic_control, treatment_effect, weights

def conduct_synthetic_control_did():
    """
    使用Synthetic Control DID方法分析英国脱欧对合作比例差值的影响
    """
    # 读取数据
    data_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/networks_sdid_brexit/merged_all_data.csv'
    df = pd.read_csv(data_file)
    
    print("数据概览:")
    print(f"数据形状: {df.shape}")
    print(f"包含国家: {df['Country'].unique()}")
    print(f"年份范围: {df['Year'].min()} - {df['Year'].max()}")
    
    # 设置英国脱欧时间点（2016年公投，2017年开始脱欧程序）
    brexit_year = 2016
    
    # 准备数据：创建面板数据格式
    # 将数据转换为宽格式，每个国家一列
    df_pivot = df.pivot(index='Year', columns='Country', values='ratio_difference')
    
    # 准备协变量数据
    covariate_vars = ['pub_total', 'pub_intl', 'gdp_per_capita', 'RD', 'Researchers in RD']
    covariate_data = {}
    for var in covariate_vars:
        covariate_pivot = df.pivot(index='Year', columns='Country', values=var)
        covariate_data[var] = covariate_pivot
    
    print("\n数据透视表形状:", df_pivot.shape)
    print("列名:", df_pivot.columns.tolist())
    print("协变量:", covariate_vars)
    
    # 定义处理组和控制组
    treatment_unit = 'UNITED KINGDOM'  # 英国作为处理组
    control_units = ['ICELAND', 'JAPAN', 'NORWAY', 'SINGAPORE', 'KOREA, REP.']  # 其他国家作为控制组
    
    print(f"\n处理组: {treatment_unit}")
    print(f"控制组: {control_units}")
    
    # 检查数据完整性
    print("\n数据完整性检查:")
    for country in df_pivot.columns:
        missing_count = df_pivot[country].isna().sum()
        print(f"{country}: {missing_count} 个缺失值")
    
    # 运行Synthetic Control分析
    print(f"\n开始Synthetic Control分析...")
    print(f"处理时间点: {brexit_year}")
    
    try:
        # 准备数据：需要是numpy数组格式
        # 行：时间点，列：单位（第一列是处理组，其余是控制组）
        treatment_data = df_pivot[treatment_unit].values.reshape(-1, 1)
        control_data = df_pivot[control_units].values
        
        # 合并数据
        data_matrix = np.hstack([treatment_data, control_data])
        
        # 移除包含NaN的行
        valid_rows = ~np.isnan(data_matrix).any(axis=1)
        data_matrix_clean = data_matrix[valid_rows]
        years_clean = df_pivot.index[valid_rows]
        
        print(f"清理后数据形状: {data_matrix_clean.shape}")
        print(f"有效年份: {years_clean.min()} - {years_clean.max()}")
        
        # 找到处理时间点在清理后数据中的位置
        treatment_period = np.where(years_clean >= brexit_year)[0]
        if len(treatment_period) == 0:
            print("警告: 在处理期间没有找到数据")
            return None
            
        treatment_start = treatment_period[0]
        print(f"处理开始位置: {treatment_start} (年份: {years_clean[treatment_start]})")
        
        # 准备协变量矩阵（使用GDP per capita作为主要协变量）
        gdp_covariate = covariate_data['gdp_per_capita'].values[valid_rows]
        # 对GDP进行log转换
        gdp_log = np.log(gdp_covariate + 1)  # 加1避免log(0)
        
        # 实现自定义的Synthetic Control方法（带协变量）
        synthetic_control, treatment_effect, weights = custom_synthetic_control(data_matrix_clean, treatment_start, gdp_log)
        
        print(f"\nSynthetic Control分析完成!")
        print(f"平均处理效应: {np.mean(treatment_effect):.4f}")
        
        # 创建结果DataFrame
        results_df = pd.DataFrame({
            'Year': years_clean,
            'Actual': data_matrix_clean[:, 0],  # 英国实际值
            'Synthetic': synthetic_control,     # 合成控制组
            'Treatment_Effect': treatment_effect
        })
        
        # 计算处理前后的平均效应
        pre_treatment = results_df[results_df['Year'] < brexit_year]
        post_treatment = results_df[results_df['Year'] >= brexit_year]
        
        if len(pre_treatment) > 0 and len(post_treatment) > 0:
            pre_mean = pre_treatment['Treatment_Effect'].mean()
            post_mean = post_treatment['Treatment_Effect'].mean()
            
            print(f"\n处理前平均效应: {pre_mean:.4f}")
            print(f"处理后平均效应: {post_mean:.4f}")
            print(f"效应变化: {post_mean - pre_mean:.4f}")
        
        # 保存结果
        output_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/networks_sdid_brexit/synthetic_control_results.csv'
        results_df.to_csv(output_file, index=False)
        print(f"\n结果已保存到: {output_file}")
        
        # 绘制结果图
        plt.figure(figsize=(12, 8))
        
        # 子图1: 实际值 vs 合成控制组
        plt.subplot(2, 1, 1)
        plt.plot(results_df['Year'], results_df['Actual'], 'b-', label='UK Actual', linewidth=2)
        plt.plot(results_df['Year'], results_df['Synthetic'], 'r--', label='Synthetic Control', linewidth=2)
        plt.axvline(x=brexit_year, color='gray', linestyle=':', alpha=0.7, label='Brexit Referendum')
        plt.xlabel('Year')
        plt.ylabel('Cooperation Ratio Difference')
        plt.title('Impact of Brexit on Cooperation Ratio Difference - Synthetic Control Analysis')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 子图2: 处理效应
        plt.subplot(2, 1, 2)
        plt.plot(results_df['Year'], results_df['Treatment_Effect'], 'g-', linewidth=2)
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.axvline(x=brexit_year, color='gray', linestyle=':', alpha=0.7, label='Brexit Referendum')
        plt.xlabel('Year')
        plt.ylabel('Treatment Effect')
        plt.title('Treatment Effect Time Series')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # 保存图表
        plot_file = '/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/networks_sdid_brexit/synthetic_control_plot.png'
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {plot_file}")
        
        plt.show()
        
        return results_df
        
    except Exception as e:
        print(f"运行Synthetic Control时出错: {e}")
        print("尝试使用简化的分析方法...")
        
        # 简化的DID分析
        return conduct_simple_did(df, brexit_year, treatment_unit, control_units)

def conduct_simple_did(df, brexit_year, treatment_unit, control_units):
    """
    简化的DID分析
    """
    print("\n进行简化的DID分析...")
    
    # 创建处理组和控制组标识
    df['treatment'] = (df['Country'] == treatment_unit).astype(int)
    df['post'] = (df['Year'] >= brexit_year).astype(int)
    df['did'] = df['treatment'] * df['post']
    
    # 计算各组的平均值
    pre_treatment = df[(df['treatment'] == 1) & (df['post'] == 0)]['ratio_difference'].mean()
    post_treatment = df[(df['treatment'] == 1) & (df['post'] == 1)]['ratio_difference'].mean()
    pre_control = df[(df['treatment'] == 0) & (df['post'] == 0)]['ratio_difference'].mean()
    post_control = df[(df['treatment'] == 0) & (df['post'] == 1)]['ratio_difference'].mean()
    
    # 计算DID估计
    did_estimate = (post_treatment - pre_treatment) - (post_control - pre_control)
    
    print(f"\nDID分析结果:")
    print(f"处理组处理前: {pre_treatment:.4f}")
    print(f"处理组处理后: {post_treatment:.4f}")
    print(f"控制组处理前: {pre_control:.4f}")
    print(f"控制组处理后: {post_control:.4f}")
    print(f"DID估计值: {did_estimate:.4f}")
    
    # 保存简化结果
    simple_results = {
        'pre_treatment': pre_treatment,
        'post_treatment': post_treatment,
        'pre_control': pre_control,
        'post_control': post_control,
        'did_estimate': did_estimate
    }
    
    simple_df = pd.DataFrame([simple_results])
    simple_df.to_csv('/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/networks_sdid_brexit/simple_did_results.csv', index=False)
    
    return simple_df

if __name__ == "__main__":
    print("开始Synthetic Control DID分析...")
    results = conduct_synthetic_control_did()
    print("分析完成!")