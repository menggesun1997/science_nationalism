# -*- coding: utf-8 -*-
"""
Small-multiples: 每年 流入 / 流出 / 净迁移 (流入-流出), 双 y 轴, 按大洲分组
对象: 每年在册学者 >= 5000 的国家 (2008-2024, 共 49 国), 仿 MPIDR 网格样式。
左轴: inflow (inmig, 绿) / outflow (outmig, 红) 人数
右轴: net = inmig - outmig (黑), 含 0 参考线
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
from matplotlib.ticker import MaxNLocator, FuncFormatter
from matplotlib.lines import Line2D

warnings.filterwarnings('ignore')
OUT = str(CODE / "0raw_publiations_process/migration_output_mpidr")
YMIN, YMAX = 2008, 2024
THR = 10000
NCOL = 6

CONT = {  # ISO3 -> (大洲码, 显示名)
    'EGY': ('AF', 'Egypt'), 'NGA': ('AF', 'Nigeria'), 'TUN': ('AF', 'Tunisia'), 'ZAF': ('AF', 'South Africa'),
    'CHN': ('AS', 'China'), 'IND': ('AS', 'India'), 'IRN': ('AS', 'Iran'), 'ISR': ('AS', 'Israel'),
    'JPN': ('AS', 'Japan'), 'KOR': ('AS', 'South Korea'), 'MYS': ('AS', 'Malaysia'), 'PAK': ('AS', 'Pakistan'),
    'SGP': ('AS', 'Singapore'), 'THA': ('AS', 'Thailand'), 'TWN': ('AS', 'Taiwan'), 'TUR': ('AS', 'Turkiye'),
    'AUT': ('EU', 'Austria'), 'BEL': ('EU', 'Belgium'), 'CHE': ('EU', 'Switzerland'), 'CZE': ('EU', 'Czechia'),
    'DEU': ('EU', 'Germany'), 'DNK': ('EU', 'Denmark'), 'ESP': ('EU', 'Spain'), 'FIN': ('EU', 'Finland'),
    'FRA': ('EU', 'France'), 'GBR': ('EU', 'United Kingdom'), 'GRC': ('EU', 'Greece'), 'HRV': ('EU', 'Croatia'),
    'HUN': ('EU', 'Hungary'), 'IRL': ('EU', 'Ireland'), 'ITA': ('EU', 'Italy'), 'NLD': ('EU', 'Netherlands'),
    'NOR': ('EU', 'Norway'), 'POL': ('EU', 'Poland'), 'PRT': ('EU', 'Portugal'), 'ROU': ('EU', 'Romania'),
    'RUS': ('EU', 'Russia'), 'SRB': ('EU', 'Serbia'), 'SVK': ('EU', 'Slovakia'), 'SWE': ('EU', 'Sweden'),
    'UKR': ('EU', 'Ukraine'),
    'CAN': ('NA', 'Canada'), 'MEX': ('NA', 'Mexico'), 'USA': ('NA', 'United States'),
    'AUS': ('OC', 'Australia'), 'NZL': ('OC', 'New Zealand'),
    'ARG': ('SA', 'Argentina'), 'BRA': ('SA', 'Brazil'), 'CHL': ('SA', 'Chile'),
}
CONT_ORDER = {'AF': 0, 'AS': 1, 'EU': 2, 'NA': 3, 'OC': 4, 'SA': 5}
C_IN, C_OUT, C_NET = '#2ca02c', '#d62728', '#1f1f1f'


def kfmt(v, _):
    if abs(v) >= 1000:
        return f'{v/1000:.0f}k'
    return f'{v:.0f}'


def main():
    m = pd.read_csv(os.path.join(OUT, 'mpidr_country_measures.csv'))
    m = m[(m.year >= YMIN) & (m.year <= YMAX)]
    keep = m.groupby('country')['population'].min()
    countries = [c for c in keep[keep >= THR].index if c in CONT]
    countries.sort(key=lambda c: (CONT_ORDER[CONT[c][0]], CONT[c][1]))

    ncol = NCOL
    nrow = int(np.ceil(len(countries) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.4 * ncol, 3.2 * nrow), sharex=True)
    axes = axes.ravel()

    for i, iso in enumerate(countries):
        ax = axes[i]
        d = m[m.country == iso].sort_values('year')
        yrs = d.year.values
        ax.plot(yrs, d.inmig.values, color=C_IN, lw=1.5)
        ax.plot(yrs, d.outmig.values, color=C_OUT, lw=1.5)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MaxNLocator(3))
        ax.yaxis.set_major_formatter(FuncFormatter(kfmt))
        ax.tick_params(axis='y', labelsize=10, colors=C_OUT)
        ax.tick_params(axis='x', labelsize=9)

        ax2 = ax.twinx()
        ax2.axhline(0, color='gray', lw=1.6, ls=':')
        ax2.plot(yrs, d.netmig.values, color=C_NET, lw=1.3)
        # 净迁移趋势斜率 (人/年): netmig ~ a + b*year 的 OLS 斜率
        b = np.polyfit(yrs, d.netmig.values, 1)[0]
        ax.text(0.04, 0.05, f'{b:+.0f}/yr', transform=ax.transAxes,
                fontsize=11, fontweight='bold', va='bottom', ha='left',
                color=('#1a7d1a' if b >= 0 else '#c1121f'),
                bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                          edgecolor='none', alpha=.75))
        ax2.yaxis.set_major_locator(MaxNLocator(3))
        ax2.yaxis.set_major_formatter(FuncFormatter(kfmt))
        ax2.tick_params(axis='y', labelsize=10, colors=C_NET)

        cont, name = CONT[iso]
        ax.set_title(f'{cont}: {name}', fontsize=13, fontweight='bold', pad=3)
        ax.set_xlim(YMIN, YMAX)
        ax.set_xticks([2010, 2015, 2020])
        ax.margins(x=0)

    for j in range(len(countries), len(axes)):
        axes[j].axis('off')

    handles = [Line2D([0], [0], color=C_IN, lw=2, label='Inflow (immigration)'),
               Line2D([0], [0], color=C_OUT, lw=2, label='Outflow (emigration)'),
               Line2D([0], [0], color=C_NET, lw=2, label='Net = inflow \u2212 outflow (right axis)')]
    fig.legend(handles=handles, loc='upper center', ncol=3, fontsize=11,
               bbox_to_anchor=(0.5, 0.998), framealpha=.95)
    fig.suptitle('Annual researcher migration by country (in / out / net), 2008\u20132024\n'
                 'countries with \u2265 10,000 active scholars per year   '
                 '(left axis: inflow/outflow counts; right axis: net; '
                 'number = OLS slope of net migration, persons/yr)',
                 fontsize=14, fontweight='bold', y=0.965)
    fig.text(0.5, 0.005, 'Year', ha='center', fontsize=12)
    fig.tight_layout(rect=[0.0, 0.012, 1.0, 0.94])
    p = os.path.join(OUT, 'migration_smallmultiples_10k.png')
    fig.savefig(p, dpi=150)
    plt.close(fig)
    print('->', p, '  countries:', len(countries))


if __name__ == '__main__':
    main()
