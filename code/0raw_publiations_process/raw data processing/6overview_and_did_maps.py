# -*- coding: utf-8 -*-
"""
机制二 迁移可视化 (不按阵营划分)
  图1  migration_overview.png : 三国 研究者流入/流出/净迁移 整体概览 (MPIDR 风格)
  图2  did_map_<FOCAL>.png    : PPML-DiD 逐伙伴 delta 世界地图 (流出|流入两面板)
底图: cartopy Natural Earth 110m (ADM0_A3 = ISO3)。数据已是 ISO3。
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
from matplotlib.colors import TwoSlopeNorm
import geopandas as gpd
import cartopy.io.shapereader as shpreader

warnings.filterwarnings('ignore')

OUT = str(CODE / "0raw_publiations_process/migration_output_mpidr")
CODE = str(CODE)
YMIN, YMAX = 2008, 2024

FOCALS = {
    'GBR': dict(name='United Kingdom', T0=2016, ev='Brexit referendum (2016)',
                folder='3ppml_migration_did_uk_internal_control'),
    'RUS': dict(name='Russia', T0=2022, ev='Full-scale invasion (2022)',
                folder='3ppml_migration_did_russia_internal_control'),
    'UKR': dict(name='Ukraine', T0=2022, ev='Full-scale invasion (2022)',
                folder='3ppml_migration_did_ukraine_internal_control'),
}
FCOLOR = {'GBR': '#1f4e79', 'RUS': '#8b1a1a', 'UKR': '#b8860b'}


def load_world():
    fn = shpreader.natural_earth(resolution='110m', category='cultural', name='admin_0_countries')
    w = gpd.read_file(fn)
    w['iso3'] = w['ISO_A3']
    bad = (w['iso3'] == '-99') | w['iso3'].isna()
    w.loc[bad, 'iso3'] = w.loc[bad, 'ADM0_A3']
    return w[['iso3', 'ADMIN', 'geometry']]


# ------------------------------------------------------------------ 图1 概览
def fig_overview():
    m = pd.read_csv(os.path.join(OUT, 'mpidr_country_measures.csv'))
    m = m[(m.year >= YMIN) & (m.year <= YMAX)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharex=True)
    for ax, (iso, cfg) in zip(axes, FOCALS.items()):
        d = m[m.country == iso].sort_values('year')
        yrs = d.year.values
        inflow, outflow, net = d.inmig.values, d.outmig.values, d.netmig.values
        ax.bar(yrs, inflow, color='#2ca02c', alpha=.75, label='Inflow (immigration)')
        ax.bar(yrs, -outflow, color='#d62728', alpha=.75, label='Outflow (emigration)')
        ax.plot(yrs, net, '-o', color='black', ms=4, lw=1.6, label='Net migration')
        ax.axhline(0, color='k', lw=.8)
        ax.axvline(cfg['T0'] - 0.5, color='purple', ls='--', lw=1.6)
        ax.text(cfg['T0'] - 0.4, ax.get_ylim()[1] * 0.92, cfg['ev'],
                rotation=90, va='top', fontsize=8, color='purple')
        ax.set_title(f"{cfg['name']} ({iso})", fontsize=12, color=FCOLOR[iso], fontweight='bold')
        ax.set_xlabel('Year')
        ax.grid(axis='y', alpha=.25)
    axes[0].set_ylabel('Number of migrating researchers\n(inflow +, outflow -)')
    axes[0].legend(loc='upper left', fontsize=8, framealpha=.9)
    fig.suptitle('Academic researcher migration: inflow, outflow and net balance (WoS-derived, MPIDR methodology)',
                 fontsize=13, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(OUT, 'migration_overview.png')
    fig.savefig(p, dpi=160)
    plt.close(fig)
    print('图1 ->', p)


# ------------------------------------------------------------------ 图2 DiD 地图
def _draw_map(ax, world, coef, focal, title):
    wm = world.merge(coef[['partner_country', 'pct_pctpts', 'pval']],
                     left_on='iso3', right_on='partner_country', how='left')
    lim = np.nanpercentile(np.abs(coef.pct_pctpts), 90)
    lim = float(np.clip(lim, 30, 150))
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)
    # 底色: 无数据国家浅灰
    wm.plot(ax=ax, color='#f0f0f0', edgecolor='white', linewidth=.3)
    has = wm[wm.pct_pctpts.notna()]
    has.plot(ax=ax, column='pct_pctpts', cmap='RdBu_r', norm=norm,
             edgecolor='white', linewidth=.3)
    # 显著国家 (p<0.05) 加深描边
    sig = has[has.pval < 0.05]
    if len(sig):
        sig.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=.7)
    # focal 国高亮: 金色 + 斜纹 + 粗黑边, 明确区分"分析主体, 非数据值"
    f = wm[wm.iso3 == focal]
    if len(f):
        f.plot(ax=ax, color='#ffd21f', edgecolor='black', linewidth=1.3, hatch='///')
    ax.set_xlim(-170, 180)
    ax.set_ylim(-58, 85)
    ax.axis('off')
    ax.set_title(title, fontsize=11)
    return norm


def fig_did_map(focal):
    cfg = FOCALS[focal]
    world = load_world()
    fig, axes = plt.subplots(2, 1, figsize=(13, 12))
    labels = {'out': f'Emigration share change: {focal} \u2192 partner',
              'in':  f'Immigration share change: partner \u2192 {focal}'}
    last_norm = None
    for ax, d in zip(axes, ['out', 'in']):
        fp = os.path.join(CODE, cfg['folder'], 'results', f'partner_coefficients_{d}.csv')
        coef = pd.read_csv(fp)
        last_norm = _draw_map(ax, world, coef, focal, labels[d])
    sm = plt.cm.ScalarMappable(cmap='RdBu_r', norm=last_norm)
    sm.set_array([])
    cax = fig.add_axes([0.25, 0.055, 0.5, 0.017])
    cb = fig.colorbar(sm, cax=cax, orientation='horizontal')
    cb.set_label('% change in bilateral migration share after shock  '
                 '(red = gained share, blue = lost share; black outline: p<0.05)', fontsize=9)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor='#ffd21f', edgecolor='black', hatch='///',
                              label=f'{focal} (focal country)')],
               loc='lower left', bbox_to_anchor=(0.03, 0.045), fontsize=9, framealpha=.9)
    fig.suptitle(f"{cfg['name']} ({focal}) \u2014 partner-level DiD of researcher migration\n"
                 f"internal-control PPML, share re-composition (offset = {focal} total flow); {cfg['ev']}",
                 fontsize=13, fontweight='bold', y=0.97)
    fig.tight_layout(rect=[0, 0.08, 1, 0.94])
    p = os.path.join(CODE, cfg['folder'], 'results', f'did_map_{focal}.png')
    fig.savefig(p, dpi=160)
    plt.close(fig)
    print('图2 ->', p)


def main():
    fig_overview()
    for focal in FOCALS:
        fig_did_map(focal)
    print('完成')


if __name__ == '__main__':
    main()
