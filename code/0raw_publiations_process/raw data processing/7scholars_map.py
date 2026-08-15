# -*- coding: utf-8 -*-
"""
世界地图: 每国已发表学者数量 (published scholars per country), 2005-2024
数据: mpidr_country_measures.csv 的 population = 逐年在册去重学者数 (mode-based padded residence)。
口径: 期间"年均在册学者数" (mean over 2005-2024), 避免逐年求和的重复计数与末年右删失。
色标: 对数 (数值跨 1 ~ 数十万)。
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter
import geopandas as gpd
import cartopy.io.shapereader as shpreader

warnings.filterwarnings('ignore')
OUT = str(CODE / "0raw_publiations_process/migration_output_mpidr")
YMIN, YMAX = 2005, 2024

# MPIDR 风格连续色系: 浅蓝 -> 绿 -> 橄榄 -> 橙 -> 红 (低->高)
MPIDR_CMAP = LinearSegmentedColormap.from_list('mpidr_scholars', [
    (0.00, '#d9e9f5'),  # 浅蓝 (低)
    (0.10, '#a9d5b0'),  # 蓝绿
    (0.20, '#7cc35f'),  # 浅绿
    (0.33, '#3f9b2f'),  # 绿
    (0.50, '#8f9a2c'),  # 橄榄
    (0.66, '#c08a2b'),  # 棕黄
    (0.83, '#d85f27'),  # 橙
    (1.00, '#df1d1d'),  # 红 (高)
])


def load_world():
    fn = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
    w = gpd.read_file(fn)
    w['iso3'] = w['ISO_A3']
    bad = (w['iso3'] == '-99') | w['iso3'].isna()
    w.loc[bad, 'iso3'] = w.loc[bad, 'ADM0_A3']
    return w[['iso3', 'ADMIN', 'geometry']]


def main():
    m = pd.read_csv(os.path.join(OUT, 'mpidr_country_measures.csv'))
    m = m[(m.year >= YMIN) & (m.year <= YMAX)]
    agg = m.groupby('country')['population'].mean().rename('scholars').reset_index()

    world = load_world()
    wm = world.merge(agg, left_on='iso3', right_on='country', how='left')

    # 线性刻度 (仿 MPIDR), vmax 贴合数据最大值并向上取整到 5 万
    dmax = float(agg.scholars.max())
    vmax = np.ceil(dmax / 50000) * 50000
    norm = Normalize(vmin=0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(16, 8.5))
    wm.plot(ax=ax, color='#f2f2f2', edgecolor='#bfbfbf', linewidth=.3)
    has = wm[wm.scholars.notna() & (wm.scholars > 0)]
    has.plot(ax=ax, column='scholars', cmap=MPIDR_CMAP, norm=norm,
             edgecolor='#8f8f8f', linewidth=.3)
    ax.set_xlim(-170, 180)
    ax.set_ylim(-58, 85)
    ax.axis('off')
    ax.set_title('Number of published scholars per country\n'
                 'mean number of WoS published researchers in the years 2005\u20132024',
                 fontsize=14, fontweight='bold', loc='left')

    sm = plt.cm.ScalarMappable(cmap=MPIDR_CMAP, norm=norm)
    sm.set_array([])
    cax = fig.add_axes([0.88, 0.18, 0.016, 0.64])
    cb = fig.colorbar(sm, cax=cax, orientation='vertical')
    cb.set_label('Number of researchers', fontsize=10)
    cb.ax.yaxis.set_major_formatter(FuncFormatter(
        lambda v, _: '0' if v == 0 else f'{v/1000:.0f}k'))

    # 左下海域放 Top-10 排行榜, 避免地图上文字重叠
    top = agg.sort_values('scholars', ascending=False).head(10).reset_index(drop=True)
    lines = ['Top 10 (avg. annual scholars)']
    for i, r in top.iterrows():
        lines.append(f"{i+1:>2}. {r.country}  {int(round(r.scholars)):>7,}")
    ax.text(-165, 3, '\n'.join(lines), fontsize=8.5, family='monospace',
            va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#888', alpha=.92))

    fig.subplots_adjust(left=0.01, right=0.86, top=0.90, bottom=0.02)
    p = os.path.join(OUT, 'scholars_per_country_map.png')
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print('->', p)
    print('\nTop 12 (avg annual scholars):')
    print(agg.sort_values('scholars', ascending=False).head(12).to_string(index=False))


if __name__ == '__main__':
    main()
