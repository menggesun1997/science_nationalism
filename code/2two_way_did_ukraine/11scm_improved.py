#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的SCM方法：使用更严格的拟合标准
目标：确保战前期的平行趋势
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy import stats
import matplotlib.pyplot as plt
import os
from sklearn.linear_model import LinearRegression

# 数据文件路径
output_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/2two_way_did_ukraine'
existing_file = f'{output_dir}/control_group_cooperation_data.xlsx'
scm_output_file = f'{output_dir}/scm_improved_results.xlsx'

# 候选控制组国家（排除乌克兰）
candidate_countries = {
    'SERBIA': ['REPUBLIC OF SERBIA'],
    'GEORGIA': ['GEORGIA'],
    'ARMENIA': ['ARMENIA'],
    'AZERBAIJAN': ['AZERBAIJAN'],
    'MOLDOVA': ['MOLDOVA'],
    'BOSNIA-HERZEGOVINA': ['BOSNIA & HERZEGOVINA'],
    'BRAZIL': ['BRAZIL'],
    'SOUTH AFRICA': ['SOUTH AFRICA'],
    'ARGENTINA': ['ARGENTINA']
}

def load_y_kt_data():
    """从已有文件加载Y_{k,t}数据"""
    print("\n" + "="*80)
    print("加载Y_{{k,t}}数据")
    print("="*80)
    
    control_group_df = pd.read_excel(existing_file, sheet_name='控制组与集合P合作汇总')
    control_y_kt = control_group_df[['year', 'country', 'coop_articles_with_P']].copy()
    control_y_kt.columns = ['year', 'country', 'Y_kt']
    
    ukraine_df = pd.read_excel(existing_file, sheet_name='乌克兰与集合P合作')
    ukraine_y_kt = ukraine_df[['year', 'ukraine_coop_with_P']].copy()
    ukraine_y_kt['country'] = 'UKRAINE'
    ukraine_y_kt.columns = ['year', 'Y_kt', 'country']
    ukraine_y_kt = ukraine_y_kt[['year', 'country', 'Y_kt']]
    
    y_kt = pd.concat([control_y_kt, ukraine_y_kt], ignore_index=True)
    y_kt['year'] = y_kt['year'].astype(int)
    y_kt['log_Y_kt'] = np.log(y_kt['Y_kt'] + 1)
    y_kt = y_kt.sort_values(['country', 'year']).reset_index(drop=True)
    
    return y_kt

def prepare_scm_data_improved(y_kt, pre_period_start=2018, pre_period_end=2021):
    """
    准备改进的SCM数据
    使用更近期的战前时期（2018-2021）来确保更好的拟合
    """
    print("\n" + "="*80)
    print("准备改进的SCM数据结构（使用近期战前时期：2018-2021）")
    print("="*80)
    
    pre_years = list(range(pre_period_start, pre_period_end + 1))
    
    ukraine_data = y_kt[y_kt['country'] == 'UKRAINE'].copy()
    ukraine_data = ukraine_data[ukraine_data['year'].isin(pre_years)]
    ukraine_data = ukraine_data.sort_values('year')
    
    control_countries_list = list(candidate_countries.keys())
    control_data_list = []
    
    for country in control_countries_list:
        country_data = y_kt[y_kt['country'] == country].copy()
        country_data = country_data[country_data['year'].isin(pre_years)]
        country_data = country_data.sort_values('year')
        
        if len(country_data) == len(pre_years):
            control_data_list.append(country_data)
        else:
            print(f"  ⚠️ {country}的数据不完整，跳过")
    
    if len(control_data_list) == 0:
        raise ValueError("没有可用的控制国家数据")
    
    print(f"\n✅ 数据准备完成")
    print(f"  战前时期: {pre_period_start}-{pre_period_end} ({len(pre_years)}年)")
    print(f"  控制国家数量: {len(control_data_list)}")
    
    Y_treated = ukraine_data['log_Y_kt'].values.reshape(-1, 1)
    Y_control = np.column_stack([df['log_Y_kt'].values for df in control_data_list])
    
    # 使用所有年份值作为预测变量
    X_treated = Y_treated.flatten()
    X_control = Y_control.T
    
    return {
        'Y_treated': Y_treated,
        'Y_control': Y_control,
        'X_treated': X_treated,
        'X_control': X_control,
        'control_countries': [df['country'].iloc[0] for df in control_data_list],
        'pre_years': pre_years,
        'ukraine_data': ukraine_data,
        'control_data_list': control_data_list
    }

def scm_objective_improved(weights, X_treated, X_control, penalty_weight=0.1):
    """
    改进的SCM目标函数
    添加惩罚项：惩罚权重过于分散的情况
    """
    # 计算合成控制组的预测值
    X_synthetic = X_control.T @ weights
    
    # 预测误差
    prediction_error = X_treated - X_synthetic
    mse = np.mean(prediction_error ** 2)
    
    # 添加惩罚项：鼓励使用更少的国家（L1正则化）
    # 但这里我们使用熵惩罚，鼓励权重更集中
    weights_nonzero = weights[weights > 1e-10]
    if len(weights_nonzero) > 0:
        entropy = -np.sum(weights_nonzero * np.log(weights_nonzero))
        # 归一化熵（最大熵是log(J)）
        max_entropy = np.log(len(weights))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        penalty = penalty_weight * normalized_entropy
    else:
        penalty = 0
    
    return mse + penalty

def scm_constraint(weights):
    """约束：权重之和必须等于1"""
    return np.sum(weights) - 1.0

def fit_synthetic_control_improved(X_treated, X_control, method='SLSQP', 
                                   penalty_weight=0.0, max_countries=None):
    """
    改进的合成控制组拟合
    可以限制使用的国家数量
    """
    print("\n" + "="*80)
    print("拟合改进的合成控制组权重")
    print("="*80)
    
    J = X_control.shape[0]
    
    # 如果指定了最大国家数，先进行初步筛选
    if max_countries is not None and max_countries < J:
        print(f"\n步骤1: 初步筛选（最多{max_countries}个国家）...")
        # 使用简单的相关性筛选
        correlations = []
        for j in range(J):
            corr = np.corrcoef(X_treated, X_control[j, :])[0, 1]
            correlations.append((j, corr))
        
        # 选择相关性最高的国家
        correlations.sort(key=lambda x: abs(x[1]), reverse=True)
        selected_indices = [x[0] for x in correlations[:max_countries]]
        
        X_control_filtered = X_control[selected_indices, :]
        J_filtered = len(selected_indices)
        
        print(f"  选择了{J_filtered}个国家")
    else:
        X_control_filtered = X_control
        J_filtered = J
        selected_indices = list(range(J))
    
    # 初始权重：均匀分布
    initial_weights = np.ones(J_filtered) / J_filtered
    
    constraints = [{'type': 'eq', 'fun': scm_constraint}]
    bounds = [(0, 1) for _ in range(J_filtered)]
    
    print(f"\n使用优化方法: {method}")
    print(f"控制国家数量: {J_filtered}")
    print(f"预测变量维度: {X_treated.shape[0]}")
    if penalty_weight > 0:
        print(f"惩罚权重: {penalty_weight}")
    
    result = minimize(
        scm_objective_improved,
        initial_weights,
        args=(X_treated, X_control_filtered, penalty_weight),
        method=method,
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 10000, 'ftol': 1e-9}
    )
    
    if result.success:
        weights_filtered = result.x
        mse = result.fun
        rmse = np.sqrt(mse)
        
        # 将权重映射回原始国家列表
        weights_full = np.zeros(J)
        for i, idx in enumerate(selected_indices):
            weights_full[idx] = weights_filtered[i]
        
        print(f"\n✅ 优化成功")
        print(f"  最小MSE: {mse:.6f}")
        print(f"  RMSE: {rmse:.6f}")
        print(f"  迭代次数: {result.nit}")
        
        return weights_full, mse, rmse, selected_indices
    else:
        print(f"\n⚠️ 优化未完全收敛")
        weights_filtered = result.x
        mse = result.fun
        rmse = np.sqrt(mse)
        
        weights_full = np.zeros(J)
        for i, idx in enumerate(selected_indices):
            weights_full[idx] = weights_filtered[i]
        
        return weights_full, mse, rmse, selected_indices

def test_pre_treatment_trends(y_kt, weights, control_countries, 
                              pre_start=2015, pre_end=2021):
    """
    检验战前期的趋势是否平行
    返回每个战前年份的gap
    """
    pre_years = list(range(pre_start, pre_end + 1))
    
    ukraine_data = y_kt[(y_kt['country'] == 'UKRAINE') & 
                       (y_kt['year'].isin(pre_years))].copy()
    ukraine_data = ukraine_data.sort_values('year')
    
    gaps = []
    for year in pre_years:
        ukraine_value = ukraine_data[ukraine_data['year'] == year]['log_Y_kt'].values
        if len(ukraine_value) > 0:
            ukraine_val = ukraine_value[0]
            
            # 计算合成控制组的值
            synthetic_val = 0
            total_weight = 0
            for country, weight in zip(control_countries, weights):
                if weight > 1e-6:
                    country_data = y_kt[(y_kt['country'] == country) & 
                                       (y_kt['year'] == year)]
                    if len(country_data) > 0:
                        synthetic_val += weight * country_data['log_Y_kt'].values[0]
                        total_weight += weight
            
            if total_weight > 0:
                synthetic_val = synthetic_val / total_weight
                gap = ukraine_val - synthetic_val
                gaps.append({'year': year, 'gap': gap})
    
    gaps_df = pd.DataFrame(gaps)
    
    # 检验gap是否显著不为0（使用t检验）
    if len(gaps_df) > 1:
        mean_gap = gaps_df['gap'].mean()
        std_gap = gaps_df['gap'].std()
        t_stat = mean_gap / (std_gap / np.sqrt(len(gaps_df))) if std_gap > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(t_stat)))
        
        return gaps_df, mean_gap, p_value
    else:
        return gaps_df, np.nan, np.nan

def main():
    print("="*80)
    print("改进的SCM控制组选择")
    print("="*80)
    
    # 加载数据
    y_kt = load_y_kt_data()
    
    # 尝试不同的配置
    configs = [
        {'pre_start': 2018, 'pre_end': 2021, 'max_countries': 3, 'penalty': 0.0},
        {'pre_start': 2019, 'pre_end': 2021, 'max_countries': 3, 'penalty': 0.0},
        {'pre_start': 2018, 'pre_end': 2021, 'max_countries': 4, 'penalty': 0.0},
        {'pre_start': 2018, 'pre_end': 2021, 'max_countries': None, 'penalty': 0.1},
    ]
    
    best_config = None
    best_score = np.inf
    best_results = None
    
    for i, config in enumerate(configs):
        print(f"\n{'='*80}")
        print(f"配置 {i+1}: 战前时期={config['pre_start']}-{config['pre_end']}, "
              f"最大国家数={config['max_countries']}, 惩罚={config['penalty']}")
        print(f"{'='*80}")
        
        try:
            # 准备数据
            scm_data = prepare_scm_data_improved(
                y_kt, 
                pre_period_start=config['pre_start'],
                pre_period_end=config['pre_end']
            )
            
            # 拟合权重
            weights, mse, rmse, selected_indices = fit_synthetic_control_improved(
                scm_data['X_treated'],
                scm_data['X_control'],
                penalty_weight=config['penalty'],
                max_countries=config['max_countries']
            )
            
            # 获取实际使用的国家
            used_countries = [scm_data['control_countries'][idx] 
                            for idx in selected_indices if weights[idx] > 1e-6]
            used_weights = [weights[idx] for idx in selected_indices if weights[idx] > 1e-6]
            
            # 检验战前趋势
            gaps_df, mean_gap, p_value = test_pre_treatment_trends(
                y_kt, weights, scm_data['control_countries'],
                pre_start=2015, pre_end=2021
            )
            
            # 计算评分：RMSE + 战前gap的惩罚
            score = rmse + abs(mean_gap) * 10 if not np.isnan(mean_gap) else rmse
            
            print(f"\n配置 {i+1} 结果:")
            print(f"  RMSE: {rmse:.6f}")
            print(f"  使用的国家: {used_countries}")
            print(f"  权重: {[f'{w:.2%}' for w in used_weights]}")
            print(f"  战前平均gap: {mean_gap:.6f}")
            print(f"  战前gap的p值: {p_value:.4f}")
            print(f"  评分: {score:.6f}")
            
            if score < best_score:
                best_score = score
                best_config = config
                best_results = {
                    'weights': weights,
                    'mse': mse,
                    'rmse': rmse,
                    'control_countries': scm_data['control_countries'],
                    'selected_indices': selected_indices,
                    'used_countries': used_countries,
                    'used_weights': used_weights,
                    'gaps_df': gaps_df,
                    'mean_gap': mean_gap,
                    'p_value': p_value,
                    'pre_start': config['pre_start'],
                    'pre_end': config['pre_end']
                }
                
        except Exception as e:
            print(f"  ⚠️ 配置 {i+1} 失败: {e}")
            continue
    
    # 显示最佳配置
    print(f"\n{'='*80}")
    print("最佳配置结果")
    print(f"{'='*80}")
    print(f"战前拟合时期: {best_results['pre_start']}-{best_results['pre_end']}")
    print(f"RMSE: {best_results['rmse']:.6f}")
    print(f"使用的国家: {best_results['used_countries']}")
    print(f"权重: {[f'{w:.2%}' for w in best_results['used_weights']]}")
    print(f"战前平均gap: {best_results['mean_gap']:.6f}")
    print(f"战前gap的p值: {best_results['p_value']:.4f}")
    
    if best_results['p_value'] > 0.05:
        print(f"\n✅ 战前趋势检验通过（p={best_results['p_value']:.4f} > 0.05）")
    else:
        print(f"\n⚠️ 战前趋势检验未通过（p={best_results['p_value']:.4f} <= 0.05）")
    
    # 保存结果
    weight_df = pd.DataFrame({
        'country': best_results['control_countries'],
        'weight': best_results['weights']
    }).sort_values('weight', ascending=False)
    
    with pd.ExcelWriter(scm_output_file, engine='openpyxl') as writer:
        weight_df.to_excel(writer, sheet_name='SCM_Weights_Improved', index=False)
        best_results['gaps_df'].to_excel(writer, sheet_name='Pre_Treatment_Gaps', index=False)
        
        summary_df = pd.DataFrame([{
            'pre_start': best_results['pre_start'],
            'pre_end': best_results['pre_end'],
            'rmse': best_results['rmse'],
            'mean_gap': best_results['mean_gap'],
            'p_value': best_results['p_value'],
            'used_countries': ', '.join(best_results['used_countries'])
        }])
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"\n✅ 结果已保存到: {scm_output_file}")
    
    return best_results

if __name__ == '__main__':
    results = main()

