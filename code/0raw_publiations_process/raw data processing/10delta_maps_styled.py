# -*- coding: utf-8 -*-
"""
delta_k 迁移份额地图 — 绘图逻辑与 event_study/visualize_map.py 完全一致
(仅换数据源与 MPIDR 绿-红色带; 数值用 log delta, SymLogNorm ±1.6)

每个 focal 国三张图:
  delta_inflow_{focal}.png
  delta_outflow_{focal}.png
  delta_nettilt_{focal}.png
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
from matplotlib.colors import SymLogNorm, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Patch
import geopandas as gpd
import cartopy.io.shapereader as shpreader

warnings.filterwarnings('ignore')
CODE = str(CODE)
FIGSIZE = (20, 12)
CB_VMIN, CB_VMAX = -1.6, 1.6
LINTHRESH, LINSCALE = 0.01, 0.1
SIG_P = 0.10   # 10% 水平即视为显著 (与合作图一致)

FOCALS = {
    'GBR': dict(folder='3ppml_migration_did_uk_internal_control'),
    'RUS': dict(folder='3ppml_migration_did_russia_internal_control'),
    'UKR': dict(folder='3ppml_migration_did_ukraine_internal_control'),
}
CMAP = LinearSegmentedColormap.from_list('mpidr_scholars', [
    (0.00, '#d9e9f5'), (0.10, '#a9d5b0'), (0.20, '#7cc35f'), (0.33, '#3f9b2f'),
    (0.50, '#8f9a2c'), (0.66, '#c08a2b'), (0.83, '#d85f27'), (1.00, '#df1d1d'),
])


def load_world():
    fn = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
    w = gpd.read_file(fn)
    w['iso3'] = w['ISO_A3']
    bad = (w['iso3'] == '-99') | w['iso3'].isna()
    w.loc[bad, 'iso3'] = w.loc[bad, 'ADM0_A3']
    return w



def get_tables(focal):
    fo = FOCALS[focal]['folder']
    rdir = os.path.join(CODE, fo, 'results')
    i = pd.read_csv(os.path.join(rdir, 'partner_coefficients_in.csv'))
    o = pd.read_csv(os.path.join(rdir, 'partner_coefficients_out.csv'))
    inflow = i[['partner_country', 'delta', 'pval']].rename(columns={'delta': 'coef'})
    outflow = o[['partner_country', 'delta', 'pval']].rename(columns={'delta': 'coef'})
    m = o[['partner_country', 'delta', 'se']].merge(
        i[['partner_country', 'delta', 'se']], on='partner_country', suffixes=('_out', '_in'))
    dn = m['delta_in'] - m['delta_out']
    se = np.sqrt(m['se_in']**2 + m['se_out']**2)
    z = dn / se
    from math import erf, sqrt
    pv = np.array([2 * (1 - 0.5 * (1 + erf(abs(v) / sqrt(2)))) for v in z])
    net = pd.DataFrame({
        'partner_country': m['partner_country'],
        'coef': dn,
        'pval': pv,
    })
    return inflow, outflow, net


def _is_significant(pval):
    return pd.notna(pval) & (pval <= SIG_P)


def draw_map(world, tab, cbar_label, outpath):
    """与 event_study/visualize_map.py 步骤6 相同图层与版式。"""
    tab = tab.copy()
    tab['iso3'] = tab['partner_country']
    tab['is_significant'] = _is_significant(tab['pval'])
    df_sig = tab[tab['is_significant']].copy()

    world_merged = world.merge(
        tab[['iso3', 'coef', 'is_significant']],
        on='iso3', how='left',
    )
    world_sig = world_merged[world_merged['is_significant'] == True].copy()
    world_nonsig = world_merged[world_merged['is_significant'] != True].copy()
    world_nodata = world_merged[world_merged['coef'].isna()].copy()

    norm = SymLogNorm(linthresh=LINTHRESH, linscale=LINSCALE, vmin=CB_VMIN, vmax=CB_VMAX)

    fig, ax = plt.subplots(figsize=FIGSIZE)

    # 第一层: 全球白底黑边
    world.plot(ax=ax, color='white', edgecolor='black', linewidth=1, zorder=1)

    # 第二层: 无估计国家留白
    if len(world_nodata):
        world_nodata.plot(ax=ax, color='white', edgecolor='darkgray', linewidth=0.2, zorder=2)

    # 第三层: 有估计但不显著 → 浅灰
    if len(world_nonsig):
        world_nonsig.plot(ax=ax, color='#F2F2F2', edgecolor='darkgray', linewidth=0.5, zorder=3)

    # 第四层: 显著国家着色
    if len(world_sig):
        world_sig.plot(
            ax=ax, column='coef', cmap=CMAP, norm=norm,
            edgecolor='black', linewidth=0.8, legend=False, zorder=4,
            missing_kwds={'color': 'lightgray'},
        )

    ax.set_xlim(-180, 180)
    ax.set_ylim(-60, 85)

    if len(df_sig):
        sm = ScalarMappable(cmap=CMAP, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.02, aspect=20, shrink=0.5)
        cbar.set_label(cbar_label, fontsize=14, fontweight='bold')
        cbar.ax.tick_params(labelsize=12)
        cbar.set_ticks([-1.6, -1.0, -0.5, 0.0, 0.5, 1.0, 1.6])

    legend_elements = [
        Patch(facecolor=CMAP(0.7), edgecolor='gray', linewidth=0.3,
              label='Positive Change (Significant)'),
        Patch(facecolor=CMAP(0.3), edgecolor='gray', linewidth=0.3,
              label='Negative Change (Significant)'),
        Patch(facecolor='white', edgecolor='lightgray', linewidth=0.3,
              label='Not Significant (p>0.1)'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=10, frameon=True,
              framealpha=0.9, edgecolor='black', fancybox=True,
              ncol=3, columnspacing=1.0, handlelength=1.5, handletextpad=0.5)

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print('->', outpath)


def make_focal(focal, world):
    inflow, outflow, net = get_tables(focal)
    rdir = os.path.join(CODE, FOCALS[focal]['folder'], 'results')
    draw_map(world, inflow, 'Percentage Change in Inflow Share',
             os.path.join(rdir, f'delta_inflow_{focal}.png'))
    draw_map(world, outflow, 'Percentage Change in Outflow Share',
             os.path.join(rdir, f'delta_outflow_{focal}.png'))
    draw_map(world, net, 'Percentage Change in Net Migration Share',
             os.path.join(rdir, f'delta_nettilt_{focal}.png'))


def main():
    world = load_world()
    for focal in FOCALS:
        make_focal(focal, world)
    print('完成')


if __name__ == '__main__':
    main()
