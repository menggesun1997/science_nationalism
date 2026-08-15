#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化乌克兰与各合作伙伴国家的合作变化（使用GeoPandas和Natural Earth数据）
使用静态地图展示正向增长（红色）和负向增长（蓝色）
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable
import os

# 数据文件路径
output_dir = str(CODE / "2two_way_did_ukraine")
coefficients_file = f'{output_dir}/partner_coefficients.csv'
visualization_output_dir = f'{output_dir}/visualization_results'

def get_country_iso3(country_name):
    """获取国家的ISO3代码"""
    # 国家名称到ISO3代码的映射（从Plotly脚本中复制）
    country_to_iso3 = {
        'UNITED STATES': 'USA',
        'UNITED KINGDOM': 'GBR',
        'RUSSIA': 'RUS',
        'CHINA': 'CHN',
        'GERMANY': 'DEU',
        'FRANCE': 'FRA',
        'ITALY': 'ITA',
        'JAPAN': 'JPN',
        'SOUTH KOREA': 'KOR',
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
        'SAUDI ARABIA': 'SAU',
        'ISRAEL': 'ISR',
        'SOUTH AFRICA': 'ZAF',
        'ARGENTINA': 'ARG',
        'MEXICO': 'MEX',
        'INDONESIA': 'IDN',
        'THAILAND': 'THA',
        'VIETNAM': 'VNM',
        'SINGAPORE': 'SGP',
        'MALAYSIA': 'MYS',
        'PHILIPPINES': 'PHL',
        'EGYPT': 'EGY',
        'IRAN': 'IRN',
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
        'CAMBODIA': 'KHM',
        'LAOS': 'LAO',
        'BRUNEI': 'BRN',
        'GEORGIA': 'GEO',
        'ARMENIA': 'ARM',
        'AZERBAIJAN': 'AZE',
        'MOLDOVA': 'MDA',
        'BELARUS': 'BLR',
        'SERBIA': 'SRB',
        'CROATIA': 'HRV',
        'BOSNIA & HERZEGOVINA': 'BIH',
        'BOSNIA-HERZEGOVINA': 'BIH',
        'MACEDONIA': 'MKD',
        'ALBANIA': 'ALB',
        'MONTENEGRO': 'MNE',
        'BULGARIA': 'BGR',
        'SLOVAKIA': 'SVK',
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
        'SOLOMON ISLANDS': 'SLB',
        'VANUATU': 'VUT',
        'FRENCH POLYNESIA': 'PYF',
        'UNITED ARAB EMIRATES': 'ARE',
        'KOREA, REP.': 'KOR',
        'KOREA': 'KOR',
        'NORTH KOREA': 'PRK',
        'KOREA, DEM. REP.': 'PRK',
        'IRAN, ISLAMIC REP.': 'IRN',
        'RUSSIAN FEDERATION': 'RUS',
        'CZECHIA': 'CZE',
        'SLOVAK REPUBLIC': 'SVK',
        'TURKIYE': 'TUR',
        'VIET NAM': 'VNM',
        'REPUBLIC OF SERBIA': 'SRB',
        'BOSNIA AND HERZEGOVINA': 'BIH',
        'NORTH MACEDONIA': 'MKD',
        'BURMA': 'MMR',
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
        'BRUNEI DARUSSALAM': 'BRN',
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
        'BYELARUS': 'BLR',
        'GABON': 'GAB',
        'NEW-CALEDONIA': 'NCL',
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
    print("可视化乌克兰与各合作伙伴国家的合作变化（GeoPandas静态地图）")
    print("="*80)
    
    # 1. 读取系数数据
    print("\n步骤1: 读取系数数据...")
    try:
        df = pd.read_csv(coefficients_file)
        print(f"✅ 读取到 {len(df)} 个国家的数据")
    except Exception as e:
        print(f"❌ 无法读取系数数据: {e}")
        print("请先运行4ppml_did_analysis.do生成数据")
        return
    
    print("\n数据预览:")
    print(df.head(10))
    
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
    
    # 检查是否有ISO3列（优先使用ISO_A3，这是Natural Earth的标准列名）
    iso3_col = None
    if 'ISO_A3' in world.columns:
        iso3_col = 'ISO_A3'
    elif 'iso_a3' in world.columns:
        iso3_col = 'iso_a3'
    elif 'iso3' in world.columns:
        iso3_col = 'iso3'
    elif 'ADM0_A3' in world.columns:
        # 备用：使用ADM0_A3（管理代码）
        iso3_col = 'ADM0_A3'
        print("⚠️ 使用ADM0_A3列（可能不完全匹配ISO3）")
    
    if not iso3_col:
        print("❌ 错误：地图数据没有ISO3代码列")
        print(f"可用列: {world.columns.tolist()}")
        return
    
    # 4. 准备数据：分离显著和不显著的国家
    print("\n步骤4: 准备数据...")
    df_all = df[df['iso3'].notna()].copy()
    df_all['abs_coef'] = df_all['coef'].abs()
    df_all['is_significant'] = df_all['pvalue'] <= 0.1
    
    print(f"总国家数: {len(df_all)}")
    print(f"显著结果数量: {df_all['is_significant'].sum()} / {len(df_all)}")
    
    if len(df_all) == 0:
        print("⚠️ 没有数据可以显示在地图上")
        return
    
    # 分离显著和不显著的数据
    df_significant = df_all[df_all['is_significant']].copy()
    df_not_significant = df_all[~df_all['is_significant']].copy()
    
    # 5. 合并地图数据和系数数据
    print("\n步骤5: 合并地图数据和系数数据...")
    if iso3_col:
        world_merged = world.merge(
            df_all[['iso3', 'coef', 'pvalue', 'is_significant', 'abs_coef']],
            left_on=iso3_col,
            right_on='iso3',
            how='left'
        )
    else:
        print("❌ 无法合并：缺少ISO3代码列")
        return
    
    print(f"合并后地图数据: {len(world_merged)} 个地理单元")
    print(f"成功匹配: {world_merged['coef'].notna().sum()} 个国家")
    
    # 6. 创建地图可视化
    print("\n步骤6: 创建地图可视化...")
    
    # 计算颜色范围
    max_abs_coef = df_significant['coef'].abs().max() if len(df_significant) > 0 else 1.0
    
    # 创建diverging colormap（RdBu风格，但确保红色为正，蓝色为负）
    # 使用LinearSegmentedColormap创建自定义colormap
    # 颜色从深蓝（负值）->浅蓝->白色->浅红->深红（正值）
    cmap = LinearSegmentedColormap.from_list('RdBu_custom', 
                                             ['#0000cc', '#3333ff', '#6666ff', '#9999ff', 
                                              '#ccccff', '#ffffff', '#ffcccc', '#ff9999', 
                                              '#ff6666', '#ff3333', '#ff0000', '#cc0000'],
                                             N=256)
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(20, 12))
    
    # 分离显著和不显著的国家
    world_significant = world_merged[world_merged['is_significant'] == True].copy()
    world_not_significant = world_merged[world_merged['is_significant'] != True].copy()
    
    # 先绘制不显著的国家（白色背景）
    if len(world_not_significant) > 0:
        world_not_significant.plot(
            ax=ax,
            color='white',
            edgecolor='lightgray',
            linewidth=0.3,
            zorder=1
        )
    
    # 再绘制显著的国家（使用颜色映射，在上层）
    if len(world_significant) > 0:
        # 创建颜色映射
        norm = Normalize(vmin=-max_abs_coef, vmax=max_abs_coef)
        
        world_significant.plot(
            ax=ax,
            column='coef',
            cmap=cmap,
            norm=norm,
            edgecolor='gray',
            linewidth=0.3,
            legend=False,
            zorder=2,
            missing_kwds={'color': 'lightgray'}  # 处理缺失值
        )
    
    # 设置地图范围（排除南极）
    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)  # 排除南极（-90到-60）
    
    # 添加颜色条（放在右边）
    if len(df_significant) > 0:
        sm = ScalarMappable(cmap=cmap, norm=Normalize(vmin=-max_abs_coef, vmax=max_abs_coef))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=20, shrink=0.5)
        cbar.set_label('Coefficient (Change in Cooperation)', fontsize=14, fontweight='bold')
        cbar.ax.tick_params(labelsize=12)
    
    # 设置标题
    # ax.set_title('Impact of Russia-Ukraine War on International Cooperation',fontsize=16, fontweight='bold', pad=20)
    
    # 创建图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#cc0000', edgecolor='gray', linewidth=0.3, label='Positive Change (Significant)'),
        Patch(facecolor='#0000cc', edgecolor='gray', linewidth=0.3, label='Negative Change (Significant)'),
        Patch(facecolor='white', edgecolor='lightgray', linewidth=0.3, label='Not Significant (p>0.1)')
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=10, frameon=True, 
             framealpha=0.9, edgecolor='black', fancybox=True,
             ncol=3, columnspacing=1.0, handlelength=1.5, handletextpad=0.5)
    
    # ax.set_xlabel('Longitude', fontsize=12)
    # ax.set_ylabel('Latitude', fontsize=12)
    
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
    output_png = f'{visualization_output_dir}/ukraine_cooperation_changes_geopandas.png'
    plt.savefig(output_png, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ PNG地图已保存到: {output_png}")
    
    output_pdf = f'{visualization_output_dir}/ukraine_cooperation_changes_geopandas.pdf'
    plt.savefig(output_pdf, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ PDF地图已保存到: {output_pdf}")
    
    plt.close()
    
    # 7. 统计摘要
    print("\n" + "="*80)
    print("统计摘要")
    print("="*80)
    print("\n合作变化统计（所有数据）:")
    print(f"  正向增长国家数: {(df['coef'] > 0).sum()}")
    print(f"  负向增长国家数: {(df['coef'] < 0).sum()}")
    print(f"  无变化国家数: {(df['coef'] == 0).sum()}")
    
    print("\n显著结果统计（pvalue <= 0.1）:")
    if len(df_significant) > 0:
        print(f"  显著正向增长国家数: {(df_significant['coef'] > 0).sum()}")
        print(f"  显著负向增长国家数: {(df_significant['coef'] < 0).sum()}")
        print(f"  显著结果总数: {len(df_significant)}")
        
        print(f"\n显著正向增长国家（前10名）:")
        top_positive = df_significant[df_significant['coef'] > 0].nlargest(10, 'coef')[['partner_country', 'coef', 'pvalue']]
        if len(top_positive) > 0:
            print(top_positive.to_string(index=False))
        else:
            print("  无")
        
        print(f"\n显著负向增长国家（前10名）:")
        top_negative = df_significant[df_significant['coef'] < 0].nsmallest(10, 'coef')[['partner_country', 'coef', 'pvalue']]
        if len(top_negative) > 0:
            print(top_negative.to_string(index=False))
        else:
            print("  无")
    else:
        print("  无显著结果")
    
    print(f"\n不显著结果统计（pvalue > 0.1）:")
    print(f"  不显著国家数: {len(df_not_significant)}")
    print(f"  注意：不显著的国家在地图上显示为白色")
    
    print(f"\n✅ 可视化完成！")
    print(f"  PNG文件: {output_png}")
    print(f"  PDF文件: {output_pdf}")

if __name__ == '__main__':
    main()

