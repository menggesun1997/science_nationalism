#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化俄罗斯与各合作伙伴国家的合作变化（使用GeoPandas和Natural Earth数据）
使用静态地图展示正向增长（红色）和负向增长（蓝色）
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm, SymLogNorm
from matplotlib.cm import ScalarMappable
import os

# 数据文件路径
output_dir = '/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES/2ppml_did_russia_internal_control'
coefficients_file = f'{output_dir}/event_study_try/did_all_countries_results_stata.csv'
visualization_output_dir = f'{output_dir}/event_study_try/visualization_results'
threshold = 10


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


def main():
    print("="*80)
    print("可视化英国与各合作伙伴国家的合作变化（GeoPandas静态地图）")
    print("="*80)
    
    # 1. 读取系数数据
    print("\n步骤1: 读取系数数据...")
    try:
        df = pd.read_csv(coefficients_file)
        print(f"✅ 读取到 {len(df)} 个国家的数据")
    except Exception as e:
        print(f"❌ 无法读取系数数据: {e}")
        print("请先运行event_study_try.do生成数据")
        return
    
    print("\n数据预览:")
    print(df.head(10))
    
    # 检查必要的列是否存在
    # 新数据文件使用 coefficient 而不是 coef
    if 'coefficient' in df.columns:
        df['coef'] = df['coefficient']  # 创建coef列以兼容后续代码
    elif 'coef' not in df.columns:
        print(f"❌ 缺少必要的列: coefficient 或 coef")
        print(f"可用列: {df.columns.tolist()}")
        return
    
    required_cols = ['partner_country']
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
    
    
    # 4. 准备数据：分离显著和不显著的国家
    print("\n步骤4: 准备数据：分离显著和不显著的国家...")
    
    # 只保留有ISO3代码的国家
    df = df[df['iso3'].notna()].copy()
    
    if len(df) == 0:
        print("⚠️ 没有数据可以显示在地图上")
        return
    
    # 使用sig_stars列来判断显著性（如果sig_stars不为空，则为显著）
    if 'sig_stars' in df.columns:
        df['is_significant'] = df['sig_stars'].notna() & (df['sig_stars'] != '')
        print(f"✅ 使用sig_stars列判断显著性")
        print(f"  显著国家数（sig_stars不为空）: {df['is_significant'].sum()}")
    elif 'sig_10' in df.columns:
        df['is_significant'] = df['sig_10'] == 1
        print("✅ 使用sig_10列判断显著性")
    else:
        # 如果没有sig_stars或sig_10列，尝试使用pvalue <= 0.05作为替代
        if 'pvalue' in df.columns:
            df['is_significant'] = df['pvalue'] <= 0.05
            print("⚠️ 未找到sig_stars或sig_10列，使用pvalue <= 0.05作为替代")
        else:
            # 如果都没有，假设所有结果都显著
            df['is_significant'] = True
            print("⚠️ 未找到sig_stars、sig_10或pvalue列，假设所有结果都显著")
    
    # 分离显著和不显著的数据
    df_significant = df[df['is_significant']].copy()
    df_not_significant = df[~df['is_significant']].copy()
    
    # 5. 合并地图数据和系数数据
    print("\n步骤5: 合并地图数据和系数数据...")
    if iso3_col:
        # 合并系数数据（不在df中的国家将自动留白）
        world_merged = world.merge(
            df[['iso3', 'coef', 'is_significant']],
            left_on=iso3_col,
            right_on='iso3',
            how='left'
        )
    else:
        print("❌ 无法合并：缺少ISO3代码列")
        return
    
    print(f"合并后地图数据: {len(world_merged)} 个地理单元")
    print(f"成功匹配（在df中）: {world_merged['coef'].notna().sum()} 个国家")
    print(f"不在df中的国家（将留白，代表每年合作数量不足{threshold}）: {world_merged['coef'].isna().sum()} 个国家")
    
    # 6. 创建地图可视化
    print("\n步骤6: 创建地图可视化...")
    
    # 使用固定的颜色条范围：-1.6 到 1.6（标准化范围）
    colorbar_vmin = -1.6
    colorbar_vmax = 1.6
    
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
    # 第二层（不在df中的国家）：留白（白色）
    # ============================================================
    print(f"  绘制第二层：不在df中的国家（留白，代表每年合作数量不足{threshold}）...")
    world_not_in_df = world_merged[world_merged['coef'].isna()].copy()
    if len(world_not_in_df) > 0:
        world_not_in_df.plot(
            ax=ax,
            color='white',  # 留白
            edgecolor='darkgray',  # 使用更深的灰色
            linewidth=0.8,  # 增加线宽
            zorder=2
        )
        print(f"    已留白 {len(world_not_in_df)} 个国家（不在df中，每年合作数量不足{threshold}）")
    else:
        print("    所有国家都在df中")
    
    # ============================================================
    # 第三层（不显著）：画出df中但不显著的国家（白色）
    # ============================================================
    print("  绘制第三层：df中但不显著的国家（sig_stars为空，白色）...")
    if len(world_not_significant) > 0:
        world_not_significant.plot(
            ax=ax,
            color='white',  # 白色
            edgecolor='darkgray',  # 使用更深的灰色
            linewidth=0.8,  # 增加线宽
            zorder=3
        )
        print(f"    已绘制 {len(world_not_significant)} 个不显著的国家（白色）")
    else:
        print("    没有不显著的国家需要绘制")
    
    # ============================================================
    # 第四层（显著）：画出df中且显著的国家，应用PuOr色彩映射
    # ============================================================
    print("  绘制第四层：df中且显著的国家（sig_stars不为空），应用PuOr色彩映射...")
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
        # norm已在此处定义
    else:
        print("    没有显著的国家需要绘制")
        # 如果没有显著国家，也需要定义norm用于颜色条
        linthresh = 0.01
        linscale = 0.1
        norm = SymLogNorm(linthresh=linthresh, linscale=linscale, vmin=colorbar_vmin, vmax=colorbar_vmax)
    
    # 设置地图范围（排除南极）
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)  # 排除南极（-90到-60）
    
    # 添加颜色条（放在右边，仅用于显著的国家）
    if len(df_significant) > 0:
        # 使用固定的 -1.6 到 1.6 范围，确保颜色条标准化，可以显示所有满足条件的国家
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=20, shrink=0.5)
        cbar.set_label('Percentage Change in Cooperation', fontsize=14, fontweight='bold')
        cbar.ax.tick_params(labelsize=12)
        # 设置颜色条的刻度为 -1.6, -1.0, -0.5, 0, 0.5, 1.0, 1.6，以匹配新的范围
        cbar.set_ticks([-1.6, -1.0, -0.5, 0.0, 0.5, 1.0, 1.6])
        # TwoSlopeNorm会自动将0值映射到colormap的中间点（白色），颜色条会正确显示
    
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
        Patch(facecolor=orange_color, edgecolor='gray', linewidth=0.3, label='Positive Change (Significant)'),
        Patch(facecolor=purple_color, edgecolor='gray', linewidth=0.3, label='Negative Change (Significant)'),
        Patch(facecolor='white', edgecolor='lightgray', linewidth=0.3, label=f'Not Significant')
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
    output_png = f'{visualization_output_dir}/russia_cooperation_changes_geopandas.png'
    plt.savefig(output_png, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ PNG地图已保存到: {output_png}")
    
    output_pdf = f'{visualization_output_dir}/russia_cooperation_changes_geopandas.pdf'
    plt.savefig(output_pdf, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ PDF地图已保存到: {output_pdf}")
    
    plt.close()
    
    # 8. 统计摘要和显著国家列表
    print("\n" + "="*80)
    print("统计摘要和显著国家列表")
    print("="*80)
    print(f"\n注意：地图仅显示df中的国家（共 {len(df)} 个国家，每年合作数量 >= 100）")
    print(f"不在df中的国家留白（代表每年合作数量不足100）")
    
    print("\n合作变化统计（df中的所有国家）:")
    print(f"  正向增长国家数: {(df['coef'] > 0).sum()}")
    print(f"  负向增长国家数: {(df['coef'] < 0).sum()}")
    print(f"  无变化国家数: {(df['coef'] == 0).sum()}")
    
    print("\n显著结果统计（sig_stars不为空，即显著）:")
    if len(df_significant) > 0:
        print(f"  显著正向增长国家数: {(df_significant['coef'] > 0).sum()}")
        print(f"  显著负向增长国家数: {(df_significant['coef'] < 0).sum()}")
        print(f"  显著结果总数: {len(df_significant)}")
        
        # 准备输出数据：包含国家名称、系数、p值等信息
        output_significant = df_significant[['partner_country', 'coef']].copy()
        
        # 添加sig_stars和p值（如果存在）
        if 'sig_stars' in df_significant.columns:
            output_significant['sig_stars'] = df_significant['sig_stars']
        if 'pvalue' in df_significant.columns:
            output_significant['pvalue'] = df_significant['pvalue']
        
        # 添加其他可能有用的列
        if 'std_error' in df_significant.columns:
            output_significant['std_error'] = df_significant['std_error']
        elif 'se' in df_significant.columns:
            output_significant['se'] = df_significant['se']
        if 'coefficient_log' in df_significant.columns:
            output_significant['coefficient_log'] = df_significant['coefficient_log']
        
        # 分离正向和负向
        positive_countries = output_significant[output_significant['coef'] > 0].copy()
        negative_countries = output_significant[output_significant['coef'] < 0].copy()
        
        # 正向国家按系数从大到小排序
        if len(positive_countries) > 0:
            positive_countries = positive_countries.sort_values('coef', ascending=False)
            print(f"\n" + "-"*80)
            print(f"显著正向增长国家（共 {len(positive_countries)} 个，按系数从大到小排序）:")
            print("-"*80)
            display_cols = ['partner_country', 'coef']
            if 'sig_stars' in positive_countries.columns:
                display_cols.append('sig_stars')
            if 'pvalue' in positive_countries.columns:
                display_cols.append('pvalue')
            if 'coefficient_pct' in positive_countries.columns:
                display_cols.append('coefficient_pct')
            print(positive_countries[display_cols].to_string(index=False))
        
        # 负向国家按系数从小到大排序（绝对值从大到小）
        if len(negative_countries) > 0:
            negative_countries = negative_countries.sort_values('coef', ascending=True)
            print(f"\n" + "-"*80)
            print(f"显著负向增长国家（共 {len(negative_countries)} 个，按系数从小到大排序）:")
            print("-"*80)
            display_cols = ['partner_country', 'coef']
            if 'sig_stars' in negative_countries.columns:
                display_cols.append('sig_stars')
            if 'pvalue' in negative_countries.columns:
                display_cols.append('pvalue')
            if 'coefficient_pct' in negative_countries.columns:
                display_cols.append('coefficient_pct')
            print(negative_countries[display_cols].to_string(index=False))
        
        # 统计摘要
        print(f"\n" + "-"*80)
        print("显著性统计摘要:")
        print("-"*80)
        if 'sig_stars' in output_significant.columns:
            sig_3stars = (output_significant['sig_stars'] == '***').sum()
            sig_2stars = (output_significant['sig_stars'] == '**').sum()
            sig_1star = (output_significant['sig_stars'] == '*').sum()
            print(f"  1%水平显著（***）: {sig_3stars} 个国家")
            print(f"  5%水平显著（**）: {sig_2stars} 个国家")
            print(f"  10%水平显著（*）: {sig_1star} 个国家")
        if 'pvalue' in output_significant.columns:
            sig_01 = (output_significant['pvalue'] <= 0.01).sum()
            sig_05 = (output_significant['pvalue'] <= 0.05).sum()
            sig_10 = (output_significant['pvalue'] <= 0.10).sum()
            print(f"  基于p值统计:")
            print(f"    1%水平显著（p <= 0.01）: {sig_01} 个国家")
            print(f"    5%水平显著（p <= 0.05）: {sig_05} 个国家")
            print(f"    10%水平显著（p <= 0.10）: {sig_10} 个国家")
    else:
        print("  无显著结果")
    
    print(f"\n不显著结果统计（sig_stars为空）:")
    print(f"  不显著国家数: {len(df_not_significant)}")
    print(f"  注意：不显著的国家和不在df中的国家在地图上都显示为白色（留白）")
    print(f"  注意：只有显著的国家（sig_stars不为空）会显示颜色")
    
    print(f"\n✅ 可视化完成！")
    print(f"  PNG文件: {output_png}")
    print(f"  PDF文件: {output_pdf}")

if __name__ == '__main__':
    main()