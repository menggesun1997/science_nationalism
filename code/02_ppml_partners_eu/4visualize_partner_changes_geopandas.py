#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化EU-27与各合作伙伴国家的合作变化（使用GeoPandas和Natural Earth数据）
使用静态地图展示正向增长（红色）和负向增长（蓝色）
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

HERE = Path(__file__).resolve().parent


import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm, SymLogNorm
from matplotlib.cm import ScalarMappable
import os

# 数据文件路径
output_dir = str(HERE)
coefficients_file = f'{output_dir}/partner_coefficients.csv'
visualization_output_dir = f'{output_dir}/visualization_results'

# EU-27合作数据文件路径（用于统计95%的国家）
eu_data_file = f'{output_dir}/control_group_cooperation_data.xlsx'
eu_sheet_name = 'EU-27与合作伙伴详细合作'

def get_country_iso3(country_name):
    """获取国家的ISO3代码"""
    # 国家名称到ISO3代码的映射（从EU分析脚本中复制并扩展）
    country_to_iso3 = {
        'UNITED STATES': 'USA',
        'UNITED KINGDOM': 'GBR',
        'RUSSIA': 'RUS',
        'RUSSIAN FEDERATION': 'RUS',
        'CHINA': 'CHN',
        'GERMANY': 'DEU',
        'FRANCE': 'FRA',
        'ITALY': 'ITA',
        'JAPAN': 'JPN',
        'SOUTH KOREA': 'KOR',
        'KOREA, REP.': 'KOR',
        'KOREA': 'KOR',
        'INDIA': 'IND',
        'BRAZIL': 'BRA',
        'CANADA': 'CAN',
        'AUSTRALIA': 'AUS',
        'SPAIN': 'ESP',
        'NETHERLANDS': 'NLD',
        'SWEDEN': 'SWE',
        'SWITZERLAND': 'CHE',
        'BELGIUM': 'BEL',
        'POLAND': 'POL',
        'TURKEY': 'TUR',
        'TURKIYE': 'TUR',
        'SAUDI ARABIA': 'SAU',
        'ISRAEL': 'ISR',
        'SOUTH AFRICA': 'ZAF',
        'ARGENTINA': 'ARG',
        'MEXICO': 'MEX',
        'INDONESIA': 'IDN',
        'THAILAND': 'THA',
        'VIETNAM': 'VNM',
        'VIET NAM': 'VNM',
        'SINGAPORE': 'SGP',
        'MALAYSIA': 'MYS',
        'PHILIPPINES': 'PHL',
        'EGYPT': 'EGY',
        'IRAN': 'IRN',
        'IRAN, ISLAMIC REP.': 'IRN',
        'PAKISTAN': 'PAK',
        'BANGLADESH': 'BGD',
        'NIGERIA': 'NGA',
        'KENYA': 'KEN',
        'CHILE': 'CHL',
        'COLOMBIA': 'COL',
        'PERU': 'PER',
        'VENEZUELA': 'VEN',
        'UKRAINE': 'UKR',
        'ROMANIA': 'ROU',
        'CZECH REPUBLIC': 'CZE',
        'CZECHIA': 'CZE',
        'HUNGARY': 'HUN',
        'GREECE': 'GRC',
        'PORTUGAL': 'PRT',
        'DENMARK': 'DNK',
        'FINLAND': 'FIN',
        'NORWAY': 'NOR',
        'IRELAND': 'IRL',
        'AUSTRIA': 'AUT',
        'NEW ZEALAND': 'NZL',
        'ALGERIA': 'DZA',
        'MOROCCO': 'MAR',
        'TUNISIA': 'TUN',
        'IRAQ': 'IRQ',
        'UAE': 'ARE',
        'UNITED ARAB EMIRATES': 'ARE',
        'KUWAIT': 'KWT',
        'QATAR': 'QAT',
        'OMAN': 'OMN',
        'BAHRAIN': 'BHR',
        'JORDAN': 'JOR',
        'LEBANON': 'LBN',
        'SYRIA': 'SYR',
        'YEMEN': 'YEM',
        'AFGHANISTAN': 'AFG',
        'KAZAKHSTAN': 'KAZ',
        'UZBEKISTAN': 'UZB',
        'TURKMENISTAN': 'TKM',
        'KYRGYZSTAN': 'KGZ',
        'TAJIKISTAN': 'TJK',
        'MONGOLIA': 'MNG',
        'NEPAL': 'NPL',
        'SRI LANKA': 'LKA',
        'MYANMAR': 'MMR',
        'BURMA': 'MMR',
        'CAMBODIA': 'KHM',
        'LAOS': 'LAO',
        'BRUNEI': 'BRN',
        'BRUNEI DARUSSALAM': 'BRN',
        'GEORGIA': 'GEO',
        'ARMENIA': 'ARM',
        'AZERBAIJAN': 'AZE',
        'MOLDOVA': 'MDA',
        'BELARUS': 'BLR',
        'BYELARUS': 'BLR',
        'SERBIA': 'SRB',
        'REPUBLIC OF SERBIA': 'SRB',
        'CROATIA': 'HRV',
        'BOSNIA & HERZEGOVINA': 'BIH',
        'BOSNIA-HERZEGOVINA': 'BIH',
        'BOSNIA AND HERZEGOVINA': 'BIH',
        'MACEDONIA': 'MKD',
        'NORTH MACEDONIA': 'MKD',
        'ALBANIA': 'ALB',
        'MONTENEGRO': 'MNE',
        'BULGARIA': 'BGR',
        'SLOVAKIA': 'SVK',
        'SLOVAK REPUBLIC': 'SVK',
        'SLOVENIA': 'SVN',
        'ESTONIA': 'EST',
        'LATVIA': 'LVA',
        'LITHUANIA': 'LTU',
        'CYPRUS': 'CYP',
        'MALTA': 'MLT',
        'LUXEMBOURG': 'LUX',
        'ICELAND': 'ISL',
        'ANGOLA': 'AGO',
        'MOZAMBIQUE': 'MOZ',
        'ZIMBABWE': 'ZWE',
        'ZAMBIA': 'ZMB',
        'BOTSWANA': 'BWA',
        'NAMIBIA': 'NAM',
        'GHANA': 'GHA',
        'SENEGAL': 'SEN',
        'IVORY COAST': 'CIV',
        'COTE D IVOIRE': 'CIV',
        'CAMEROON': 'CMR',
        'UGANDA': 'UGA',
        'TANZANIA': 'TZA',
        'ETHIOPIA': 'ETH',
        'SUDAN': 'SDN',
        'LIBYA': 'LBY',
        'ECUADOR': 'ECU',
        'BOLIVIA': 'BOL',
        'PARAGUAY': 'PRY',
        'URUGUAY': 'URY',
        'GUYANA': 'GUY',
        'SURINAME': 'SUR',
        'CUBA': 'CUB',
        'DOMINICAN REPUBLIC': 'DOM',
        'GUATEMALA': 'GTM',
        'HONDURAS': 'HND',
        'EL SALVADOR': 'SLV',
        'NICARAGUA': 'NIC',
        'COSTA RICA': 'CRI',
        'PANAMA': 'PAN',
        'JAMAICA': 'JAM',
        'TRINIDAD AND TOBAGO': 'TTO',
        'BAHAMAS': 'BHS',
        'BARBADOS': 'BRB',
        'BELIZE': 'BLZ',
        'HAITI': 'HTI',
        'FIJI': 'FJI',
        'PAPUA NEW GUINEA': 'PNG',
        'NEW CALEDONIA': 'NCL',
        'NEW-CALEDONIA': 'NCL',
        'SOLOMON ISLANDS': 'SLB',
        'VANUATU': 'VUT',
        'FRENCH POLYNESIA': 'PYF',
        'NORTH KOREA': 'PRK',
        'KOREA, DEM. REP.': 'PRK',
        'EAST TIMOR': 'TLS',
        'TIMOR-LESTE': 'TLS',
        'PALESTINE': 'PSE',
        'PALESTINIAN TERRITORY': 'PSE',
        'DEMOCRATIC REPUBLIC OF CONGO': 'COD',
        'CONGO, DEM. REP.': 'COD',
        'CONGO': 'COG',
        'CONGO, REP.': 'COG',
        'SOUTH SUDAN': 'SSD',
        'CENTRAL AFRICAN REPUBLIC': 'CAF',
        'SWAZILAND': 'SWZ',
        'ESWATINI': 'SWZ',
        'CAPE VERDE': 'CPV',
        'SAO TOME AND PRINCIPE': 'STP',
        'SAO TOME & PRINCIPE': 'STP',
        'GUINEA-BISSAU': 'GNB',
        'EQUATORIAL GUINEA': 'GNQ',
        'GAMBIA': 'GMB',
        'BURKINA FASO': 'BFA',
        'SIERRA LEONE': 'SLE',
        'LIBERIA': 'LBR',
        'TOGO': 'TGO',
        'BENIN': 'BEN',
        'MALI': 'MLI',
        'NIGER': 'NER',
        'CHAD': 'TCD',
        'MAURITANIA': 'MRT',
        'DJIBOUTI': 'DJI',
        'ERITREA': 'ERI',
        'SOMALIA': 'SOM',
        'RWANDA': 'RWA',
        'BURUNDI': 'BDI',
        'MALAWI': 'MWI',
        'LESOTHO': 'LSO',
        'MADAGASCAR': 'MDG',
        'MAURITIUS': 'MUS',
        'SEYCHELLES': 'SYC',
        'COMOROS': 'COM',
        'GUINEA': 'GIN',
        'MALDIVES': 'MDV',
        'BHUTAN': 'BTN',
        'TONGA': 'TON',
        'SAMOA': 'WSM',
        'KIRIBATI': 'KIR',
        'MICRONESIA': 'FSM',
        'FEDERATED STATES OF MICRONESIA': 'FSM',
        'MARSHALL ISLANDS': 'MHL',
        'PALAU': 'PLW',
        'NAURU': 'NRU',
        'TUVALU': 'TUV',
        'ANDORRA': 'AND',
        'LIECHTENSTEIN': 'LIE',
        'MONACO': 'MCO',
        'SAN MARINO': 'SMR',
        'VATICAN': 'VAT',
        'VATICAN CITY': 'VAT',
        'HOLY SEE': 'VAT',
        'ST. KITTS AND NEVIS': 'KNA',
        'SAINT KITTS AND NEVIS': 'KNA',
        'ST-KITTS & NEVIS': 'KNA',
        'ST. LUCIA': 'LCA',
        'SAINT LUCIA': 'LCA',
        'ST. VINCENT AND THE GRENADINES': 'VCT',
        'SAINT VINCENT AND THE GRENADINES': 'VCT',
        'SAINT-VINCENT-ET-LES-GRENADINES': 'VCT',
        'GRENADA': 'GRD',
        'ANTIGUA AND BARBUDA': 'ATG',
        'ANTIGUA & BARBUDA': 'ATG',
        'DOMINICA': 'DMA',
        'FRENCH GUIANA': 'GUF',
        'FRENCH-GUIANA': 'GUF',
        'FRENCH GUYANA': 'GUF',
        'GREENLAND': 'GRL',
        'FAEROE ISLANDS': 'FRO',
        'FAROE ISLANDS': 'FRO',
        'GIBRALTAR': 'GIB',
        'MONTSERRAT': 'MSR',
        'ANGUILLA': 'AIA',
        'BRITISH VIRGIN ISLANDS': 'VGB',
        'CAYMAN ISLANDS': 'CYM',
        'TURKS AND CAICOS ISLANDS': 'TCA',
        'BERMUDA': 'BMU',
        'PUERTO RICO': 'PRI',
        'US VIRGIN ISLANDS': 'VIR',
        'AMERICAN SAMOA': 'ASM',
        'GUAM': 'GUM',
        'NORTHERN MARIANA ISLANDS': 'MNP',
        'COOK ISLANDS': 'COK',
        'NIUE': 'NIU',
        'TOKELAU': 'TKL',
        'PITCAIRN': 'PCN',
        'WALLIS AND FUTUNA': 'WLF',
        'MAYOTTE': 'MYT',
        'REUNION': 'REU',
        'SAINT HELENA': 'SHN',
        'FALKLAND ISLANDS': 'FLK',
        'FRENCH SOUTHERN TERRITORIES': 'ATF',
        'BRITISH INDIAN OCEAN TERRITORY': 'IOT',
        'CHRISTMAS ISLAND': 'CXR',
        'COCOS ISLANDS': 'CCK',
        'NORFOLK ISLAND': 'NFK',
        'HEARD ISLAND': 'HMD',
        'MACAU': 'MAC',
        'MACAO': 'MAC',
        'HONG KONG': 'HKG',
        'TAIWAN': 'TWN',
        'TAIWAN, PROVINCE OF CHINA': 'TWN',
        'GABON': 'GAB',
        'REPUBLIC OF KOSOVO': 'XKX',
        'KOSOVO': 'XKX',
        'SINT-MAARTEN': 'SXM',
        'SINT MAARTEN': 'SXM',
        'ST. MAARTEN': 'SXM',
        'ST MAARTEN': 'SXM',
    }
    
    country_upper = country_name.upper().strip()
    return country_to_iso3.get(country_upper, None)

def load_world_map():
    """加载世界地图数据（Natural Earth）"""
    # 优先使用cartopy的数据（包含ISO3代码）
    try:
        import cartopy.io.shapereader as shpreader
        shpfilename = shpreader.natural_earth(resolution='110m',
                                              category='cultural',
                                              name='admin_0_countries')
        world = gpd.read_file(shpfilename)
        print("✅ 使用cartopy的Natural Earth数据")
        return world
    except Exception as e:
        print(f"⚠️ 无法使用cartopy数据: {e}")
        print("尝试其他数据源...")
    
    # 备用方法：尝试从在线资源下载Natural Earth数据
    try:
        import urllib.request
        import zipfile
        import tempfile
        import os
        
        print("尝试下载Natural Earth数据...")
        url = 'https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/110m/cultural/ne_110m_admin_0_countries.zip'
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, 'ne_110m_admin_0_countries.zip')
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            # 查找shp文件
            shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
            if shp_files:
                world = gpd.read_file(os.path.join(tmpdir, shp_files[0]))
                print("✅ 使用下载的Natural Earth数据")
                return world
    except Exception as e:
        print(f"⚠️ 无法下载数据: {e}")
    
    # 最后备用：使用本地ne_110m_land数据（注意：这个数据可能没有ISO3代码）
    try:
        world = gpd.read_file(f'{output_dir}/ne_110m_land/ne_110m_land.shp')
        print("⚠️ 使用本地ne_110m_land数据（可能没有ISO3代码）")
        return world
    except Exception as e:
        print(f"❌ 无法加载本地数据: {e}")
    
    raise Exception("无法加载任何地图数据源")

def get_top_95_percent_countries():
    """
    从EU-27合作数据中统计累计达到95%的国家
    返回这些国家的集合（大写）
    """
    print("\n" + "="*80)
    print("统计EU-27累计达到95%合作的国家")
    print("="*80)
    
    try:
        # 读取EU-27与合作伙伴详细合作数据
        print(f"\n读取文件: {eu_data_file}")
        print(f"Sheet名称: {eu_sheet_name}")
        
        df_eu = pd.read_excel(eu_data_file, sheet_name=eu_sheet_name)
        print(f"✅ 读取成功，数据形状: {df_eu.shape}")
        print(f"列名: {df_eu.columns.tolist()}")
        
        # 检查必要的列
        if 'partner_country' not in df_eu.columns or 'coop_articles' not in df_eu.columns:
            print(f"❌ 缺少必要的列。可用列: {df_eu.columns.tolist()}")
            return set()
        
        # 统计每个国家的总合作数量
        print("\n步骤1: 统计每个国家的总合作数量...")
        country_totals = df_eu.groupby('partner_country')['coop_articles'].sum().reset_index()
        country_totals.columns = ['partner_country', 'total_coop']
        
        # 按合作数量从高到低排序
        country_totals = country_totals.sort_values('total_coop', ascending=False)
        
        # 计算总合作数量
        total_coop = country_totals['total_coop'].sum()
        print(f"总合作数量: {total_coop:,}")
        
        # 计算百分比和累计百分比
        country_totals['percentage'] = country_totals['total_coop'] / total_coop * 100
        country_totals['cumulative_percentage'] = country_totals['percentage'].cumsum()
        
        # 找到累计达到95%的国家
        # 包括最后一个使累计百分比超过95%的国家
        top_95_mask = country_totals['cumulative_percentage'] <= 95
        if top_95_mask.sum() < len(country_totals):
            # 如果最后一个95%以内的国家累计不到95%，则包含下一个国家
            top_95_mask.iloc[top_95_mask.sum()] = True
        
        top_95_countries = country_totals[top_95_mask].copy()
        
        print(f"\n步骤2: 累计达到95%的国家统计")
        print(f"  国家数量: {len(top_95_countries)}")
        print(f"  累计百分比: {top_95_countries['cumulative_percentage'].max():.2f}%")
        print(f"  这些国家的总合作数量: {top_95_countries['total_coop'].sum():,}")
        
        print(f"\n前20个国家:")
        print(top_95_countries.head(20)[['partner_country', 'total_coop', 'percentage', 'cumulative_percentage']].to_string(index=False))
        
        # 返回国家名称集合（转换为大写以便匹配）
        top_95_set = set(top_95_countries['partner_country'].str.upper().str.strip())
        print(f"\n✅ 成功识别 {len(top_95_set)} 个国家（累计达到95%）")
        
        return top_95_set
        
    except Exception as e:
        print(f"❌ 读取EU-27合作数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return set()

def main():
    print("="*80)
    print("可视化EU-27与各合作伙伴国家的合作变化（GeoPandas静态地图）")
    print("="*80)
    
    # 1. 读取系数数据
    print("\n步骤1: 读取系数数据...")
    try:
        df = pd.read_csv(coefficients_file)
        print(f"✅ 读取到 {len(df)} 个国家的数据")
    except Exception as e:
        print(f"❌ 无法读取系数数据: {e}")
        print("请先运行3extract_partner_coefficients.do生成数据")
        return
    
    print("\n数据预览:")
    print(df.head(10))
    
    # 检查必要的列是否存在
    required_cols = ['partner_country', 'coef']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ 缺少必要的列: {missing_cols}")
        print(f"可用列: {df.columns.tolist()}")
        return
    
    # 2. 添加ISO3代码
    print("\n步骤2: 添加ISO3国家代码...")
    df['iso3'] = df['partner_country'].apply(get_country_iso3)
    
    # 统计
    matched = df['iso3'].notna().sum()
    unmatched = df['iso3'].isna().sum()
    print(f"成功匹配ISO3代码: {matched}/{len(df)} 个国家")
    
    # 显示未匹配的国家（前20个）
    if unmatched > 0:
        print(f"\n未匹配的国家（共{unmatched}个，显示前20个）:")
        unmatched_countries = df[df['iso3'].isna()]['partner_country'].unique()[:20]
        for country in unmatched_countries:
            print(f"  - {country}")
        if unmatched > 20:
            print(f"  ... 还有 {unmatched - 20} 个国家未显示")
    
    # 3. 加载世界地图
    print("\n步骤3: 加载世界地图数据...")
    try:
        world = load_world_map()
        print(f"✅ 地图数据加载成功，包含 {len(world)} 个地理单元")
        print(f"地图数据列名: {world.columns.tolist()}")
    except Exception as e:
        print(f"❌ 无法加载地图数据: {e}")
        return
    
    # 检查是否有ISO3列（优先使用ISO_A3，但如果包含太多缺失值则使用ADM0_A3）
    iso3_col = None
    backup_iso3_col = None
    
    if 'ISO_A3' in world.columns:
        iso3_col = 'ISO_A3'
        # 检查是否有ADM0_A3作为备用
        if 'ADM0_A3' in world.columns:
            backup_iso3_col = 'ADM0_A3'
    elif 'iso_a3' in world.columns:
        iso3_col = 'iso_a3'
        if 'adm0_a3' in world.columns:
            backup_iso3_col = 'adm0_a3'
    elif 'iso3' in world.columns:
        iso3_col = 'iso3'
    elif 'ADM0_A3' in world.columns:
        iso3_col = 'ADM0_A3'
        print("⚠️ 使用ADM0_A3列（可能不完全匹配ISO3）")
    
    if not iso3_col:
        print("❌ 错误：地图数据没有ISO3代码列")
        print(f"可用列: {world.columns.tolist()}")
        return
    
    print(f"✅ 使用ISO3列: {iso3_col}")
    if backup_iso3_col:
        print(f"✅ 备用ISO3列: {backup_iso3_col}")
    
    # 在合并前，创建一个合并的ISO3列，优先使用主列，如果主列是-99或缺失则使用备用列
    if backup_iso3_col:
        # 创建合并的ISO3列
        world['iso3_merged'] = world[iso3_col].copy()
        # 将-99或缺失值替换为备用列的值
        mask = (world[iso3_col] == '-99') | (world[iso3_col] == -99) | world[iso3_col].isna()
        world.loc[mask, 'iso3_merged'] = world.loc[mask, backup_iso3_col]
        iso3_col = 'iso3_merged'
        print(f"✅ 已创建合并的ISO3列（优先使用主列，缺失时使用{backup_iso3_col}）")
    else:
        # 清理ISO3列中的缺失值标记（-99）
        world[iso3_col] = world[iso3_col].replace('-99', None)
        world[iso3_col] = world[iso3_col].replace(-99, None)
    
    # 4. 获取累计达到95%的国家列表
    print("\n步骤4: 获取累计达到95%的国家列表...")
    top_95_countries_set = get_top_95_percent_countries()
    
    if len(top_95_countries_set) == 0:
        print("⚠️ 警告：未能获取95%国家列表，将显示所有国家")
        # 如果获取失败，使用所有国家
        df['is_top_95'] = True
    else:
        # 标记哪些国家在95%列表中
        df['is_top_95'] = df['partner_country'].str.upper().str.strip().isin(top_95_countries_set)
        print(f"系数数据中属于95%国家的数量: {df['is_top_95'].sum()} / {len(df)}")
    
    # 5. 准备数据：分离显著和不显著的国家（仅针对95%的国家）
    print("\n步骤5: 准备数据（仅针对95%的国家）...")
    # 只保留95%以内的国家进行可视化
    df_all = df[(df['iso3'].notna()) & (df['is_top_95'] == True)].copy()
    df_all['abs_coef'] = df_all['coef'].abs()
    
    # 检查是否有pvalue列，如果没有则假设所有结果都显著
    if 'pvalue' in df_all.columns:
        df_all['is_significant'] = df_all['pvalue'] <= 0.1
    elif 'sig_10' in df_all.columns:
        df_all['is_significant'] = df_all['sig_10'] == 1
    else:
        # 如果没有显著性信息，假设所有结果都显著
        df_all['is_significant'] = True
        print("⚠️ 未找到pvalue或sig_10列，假设所有结果都显著")
    
    print(f"95%以内的国家数: {len(df_all)}")
    print(f"显著结果数量: {df_all['is_significant'].sum()} / {len(df_all)}")
    
    if len(df_all) == 0:
        print("⚠️ 没有数据可以显示在地图上")
        return
    
    # 分离显著和不显著的数据
    df_significant = df_all[df_all['is_significant']].copy()
    df_not_significant = df_all[~df_all['is_significant']].copy()
    
    # 6. 合并地图数据和系数数据
    print("\n步骤6: 合并地图数据和系数数据...")
    if iso3_col:
        # 合并系数数据（仅95%以内的国家有数据）
        world_merged = world.merge(
            df_all[['iso3', 'coef', 'is_significant', 'abs_coef']],
            left_on=iso3_col,
            right_on='iso3',
            how='left'
        )
        
        # 标记哪些国家不在95%列表中（需要留白）
        if len(top_95_countries_set) > 0:
            # 从df中获取95%国家的ISO3映射
            df_with_iso3 = df[df['iso3'].notna()].copy()
            top_95_iso3_set = set(df_with_iso3[df_with_iso3['is_top_95'] == True]['iso3'].unique())
            world_merged['is_in_top_95'] = world_merged['iso3'].isin(top_95_iso3_set)
        else:
            world_merged['is_in_top_95'] = True  # 如果获取失败，显示所有国家
        
    else:
        print("❌ 无法合并：缺少ISO3代码列")
        return
    
    print(f"合并后地图数据: {len(world_merged)} 个地理单元")
    print(f"成功匹配（95%以内）: {world_merged['coef'].notna().sum()} 个国家")
    print(f"不在95%列表中的国家（将留白）: {(~world_merged['is_in_top_95']).sum()} 个国家")
    
    # 7. 创建地图可视化（使用图层叠加法，仅显示95%的国家）
    print("\n步骤7: 创建地图可视化（图层叠加法，仅显示95%的国家）...")
    
    # 使用固定的颜色条范围：-1.6 到 1.6（标准化范围，可以显示所有满足条件的国家）
    colorbar_vmin = -1.6
    colorbar_vmax = 1.6
    
    # 计算实际数据范围（用于SymLogNorm）
    if len(df_significant) > 0:
        min_coef = df_significant['coef'].min()
        max_coef = df_significant['coef'].max()
    else:
        min_coef = df_all['coef'].min() if len(df_all) > 0 else -1.6
        max_coef = df_all['coef'].max() if len(df_all) > 0 else 1.6
    
    # 使用matplotlib内置的'PuOr_r' (Purple-Orange reversed) diverging colormap
    # PuOr_r: 紫色（负值）-> 白色（0值）-> 橙色（正值）
    # 这是PuOr的反转版本，适合显示正负变化
    import matplotlib.cm as cm
    cmap = cm.get_cmap('PuOr_r')
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(20, 12))
    
    # 分离显著和不显著的国家
    world_significant = world_merged[world_merged['is_significant'] == True].copy()
    world_not_significant = world_merged[world_merged['is_significant'] != True].copy()
    
    # ============================================================
    # 第一层（底图）：画出所有国家的轮廓（加深边界线）
    # ============================================================
    print("  绘制第一层：所有国家的轮廓（底图，加深边界线）...")
    world.plot(
        ax=ax,
        color='white',  # 底图背景色
        edgecolor='black',
        linewidth=1,  # 增加线宽，加深边界线
        zorder=1
    )
    
    # ============================================================
    # 第二层（不在95%列表中的国家）：留白（白色）
    # ============================================================
    print("  绘制第二层：不在95%列表中的国家（留白）...")
    world_not_in_top_95 = world_merged[~world_merged['is_in_top_95']].copy()
    if len(world_not_in_top_95) > 0:
        world_not_in_top_95.plot(
            ax=ax,
            color='white',  # 留白
            edgecolor='darkgray',  # 使用更深的灰色
            linewidth=0.8,  # 增加线宽
            zorder=2
        )
        print(f"    已留白 {len(world_not_in_top_95)} 个国家（不在95%列表中）")
    else:
        print("    所有国家都在95%列表中")
    
    # ============================================================
    # 第三层（不显著）：画出95%以内但 p > 0.1 的国家（白色）
    # ============================================================
    print("  绘制第三层：95%以内但不显著的国家（p > 0.1，白色）...")
    if len(world_not_significant) > 0:
        # 不显著的国家也使用白色，与不在95%列表中的国家保持一致
        world_not_significant.plot(
            ax=ax,
            color='white',  # 白色，与不在95%列表中的国家一致
            edgecolor='darkgray',  # 使用更深的灰色
            linewidth=0.8,  # 增加线宽
            zorder=3
        )
        print(f"    已绘制 {len(world_not_significant)} 个不显著的国家（白色）")
    else:
        print("    没有不显著的国家需要绘制")
    
    # ============================================================
    # 第四层（显著）：画出95%以内且 p <= 0.1 的国家，应用PuOr_r色彩映射
    # ============================================================
    print("  绘制第四层：95%以内且显著的国家（p <= 0.1），应用PuOr_r色彩映射...")
    if len(world_significant) > 0:
        # 使用SymLogNorm（对称对数归一化）拉近小负值和大负值的距离
        # linthresh: 线性阈值，小于这个绝对值的范围使用线性缩放
        # 设置较小的linthresh（如0.01），让-0.05和-1.0都在对数区域，从而拉近它们的距离
        # 使用固定的 -1.6 到 1.6 范围，确保颜色条标准化，可以显示所有满足条件的国家
        linthresh = 0.01  # 线性阈值，接近0的小值使用线性缩放
        linscale = 0.1    # 线性缩放比例
        
        norm = SymLogNorm(linthresh=linthresh, linscale=linscale, vmin=colorbar_vmin, vmax=colorbar_vmax)
        
        world_significant.plot(
            ax=ax,
            column='coef',
            cmap=cmap,
            norm=norm,
            edgecolor='black',  # 使用黑色边界线，更明显
            linewidth=0.8,  # 增加线宽
            legend=False,
            zorder=4,
            missing_kwds={'color': 'lightgray'}  # 处理缺失值
        )
        print(f"    已绘制 {len(world_significant)} 个显著的国家")
        print(f"    注意：颜色条范围固定为 [{colorbar_vmin}, {colorbar_vmax}]，超出范围的值会被裁剪")
    else:
        print("    没有显著的国家需要绘制")
    
    # 设置地图范围（排除南极）
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)  # 排除南极（-90到-60）
    
    # 添加颜色条（放在右边，仅用于显著的国家）
    if len(df_significant) > 0:
        # 使用相同的SymLogNorm确保颜色条正确显示
        # 使用固定的 -1.6 到 1.6 范围，确保颜色条标准化，可以显示所有满足条件的国家
        linthresh = 0.01
        linscale = 0.1
        sm = ScalarMappable(cmap=cmap, norm=SymLogNorm(linthresh=linthresh, linscale=linscale, vmin=colorbar_vmin, vmax=colorbar_vmax))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=20, shrink=0.5)
        cbar.set_label('Coefficient (Change in Cooperation)', fontsize=14, fontweight='bold')
        cbar.ax.tick_params(labelsize=12)
        # SymLogNorm会在接近0的地方使用线性缩放，在远离0的地方使用对数缩放
        # 这样可以拉近-0.05和-1.0在颜色条上的距离，加深美国的颜色
        # 设置颜色条的刻度为 -1.6, -1.0, -0.5, 0, 0.5, 1.0, 1.6，以匹配新的范围
        cbar.set_ticks([-1.6, -1.0, -0.5, 0.0, 0.5, 1.0, 1.6])
    
    # 创建图例（使用PuOr_r colormap的颜色）
    from matplotlib.patches import Patch
    # PuOr_r colormap: 紫色（负值）-> 白色（0值）-> 橙色（正值）
    # 获取PuOr_r colormap的典型颜色值
    puor_cmap = cm.get_cmap('PuOr_r')
    # 负值（紫色）：使用colormap的0.3位置（更明显的紫色）
    purple_color = puor_cmap(0.3)
    # 正值（橙色）：使用colormap的0.7位置（更明显的橙色）
    orange_color = puor_cmap(0.7)
    
    legend_elements = [
        Patch(facecolor=orange_color, edgecolor='gray', linewidth=0.3, label='Positive Change (Significant, p≤0.1)'),
        Patch(facecolor=purple_color, edgecolor='gray', linewidth=0.3, label='Negative Change (Significant, p≤0.1)'),
        Patch(facecolor='white', edgecolor='lightgray', linewidth=0.3, label='Not Significant (p>0.1) or Not in Top 95%')
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=10, frameon=True, 
             framealpha=0.9, edgecolor='black', fancybox=True,
             ncol=3, columnspacing=1.0, handlelength=1.5, handletextpad=0.5)
    
    # 移除坐标轴刻度
    ax.set_xticks([])
    ax.set_yticks([])
    
    # 移除边框
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # 确保输出目录存在
    os.makedirs(visualization_output_dir, exist_ok=True)
    
    plt.tight_layout()
    
    # 保存图片
    output_png = f'{visualization_output_dir}/eu_cooperation_changes_geopandas.png'
    plt.savefig(output_png, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ PNG地图已保存到: {output_png}")
    
    output_pdf = f'{visualization_output_dir}/eu_cooperation_changes_geopandas.pdf'
    plt.savefig(output_pdf, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ PDF地图已保存到: {output_pdf}")
    
    plt.close()
    
    # 8. 统计摘要
    print("\n" + "="*80)
    print("统计摘要")
    print("="*80)
    print(f"\n注意：地图仅显示累计达到95%合作的国家（共 {len(top_95_countries_set)} 个国家）")
    print(f"其他 {len(df) - len(df_all)} 个国家留白（未显示）")
    
    print("\n合作变化统计（95%以内的国家）:")
    print(f"  正向增长国家数: {(df_all['coef'] > 0).sum()}")
    print(f"  负向增长国家数: {(df_all['coef'] < 0).sum()}")
    print(f"  无变化国家数: {(df_all['coef'] == 0).sum()}")
    
    print("\n合作变化统计（所有数据，包括95%以外的国家）:")
    print(f"  正向增长国家数: {(df['coef'] > 0).sum()}")
    print(f"  负向增长国家数: {(df['coef'] < 0).sum()}")
    print(f"  无变化国家数: {(df['coef'] == 0).sum()}")
    
    print("\n显著结果统计（pvalue <= 0.1）:")
    if len(df_significant) > 0:
        print(f"  显著正向增长国家数: {(df_significant['coef'] > 0).sum()}")
        print(f"  显著负向增长国家数: {(df_significant['coef'] < 0).sum()}")
        print(f"  显著结果总数: {len(df_significant)}")
        
        print(f"\n显著正向增长国家（前20名）:")
        top_positive = df_significant[df_significant['coef'] > 0].nlargest(20, 'coef')[['partner_country', 'coef']]
        if 'pvalue' in top_positive.columns:
            top_positive = top_positive[['partner_country', 'coef', 'pvalue']]
        if len(top_positive) > 0:
            print(top_positive.to_string(index=False))
        else:
            print("  无")
        
        print(f"\n显著负向增长国家（前20名）:")
        top_negative = df_significant[df_significant['coef'] < 0].nsmallest(20, 'coef')[['partner_country', 'coef']]
        if 'pvalue' in top_negative.columns:
            top_negative = top_negative[['partner_country', 'coef', 'pvalue']]
        if len(top_negative) > 0:
            print(top_negative.to_string(index=False))
        else:
            print("  无")
    else:
        print("  无显著结果")
    
    print(f"\n不显著结果统计（pvalue > 0.1，仅95%以内的国家）:")
    print(f"  不显著国家数: {len(df_not_significant)}")
    print(f"  注意：不显著的国家和95%以外的国家在地图上都显示为白色（留白）")
    print(f"  注意：只有显著的国家（p≤0.1）会显示颜色")
    
    print(f"\n✅ 可视化完成！")
    print(f"  PNG文件: {output_png}")
    print(f"  PDF文件: {output_pdf}")

if __name__ == '__main__':
    main()

