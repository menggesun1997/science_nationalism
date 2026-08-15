"""
校验/映射: 把本项目用 WoS 自建的迁移测量 (7mpidr_migration_replication.py 的输出)
与 MPIDR 公开发布的 Scholarly Migration Database (2026 V2, OpenAlex) 在 2005-2022 重叠期对齐,
计算相关性, 以证明自建口径与 MPIDR "完全一致" (算法一致, 库不同 -> 用相关性背书)。

思路 (对应 Akbaritabar et al. 2024 Sci Data 的技术验证 Fig.5 / Table 5):
  1) 国家年度层: 比较 研究者人口 (population) 与 净迁移率 (nmr) 的相关 (Pearson + Kendall tau)。
  2) 双边流层:   比较 (origin, dest, year) 的迁移人数相关。
  3) 重点国家 (RUS/UKR/GBR) 的逐年时间序列对照, 并出散点图。

校准成功后, 即可名正言顺地把自建测量外推到 MPIDR 够不到的 2023-2024。

依赖: pandas, pyarrow, matplotlib; (可选) scipy / pycountry。
"""

import os
import pandas as pd

OUT_DIR = os.environ.get(
    'SCI_OUT_DIR',
    '/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw data processing/migration_output_mpidr')
OUR_MEASURES = os.path.join(OUT_DIR, 'mpidr_country_measures.csv')
OUR_FLOWS = os.path.join(OUT_DIR, 'mpidr_country_flows.csv')

# MPIDR 2026 V2 参考数据 (本地 CSV, 由用户提供; 含 OpenAlex 与 Scopus 两个来源)
MPIDR_DATA_DIR = os.environ.get(
    'SCI_MPIDR_DIR',
    '/Users/sunmengge/Dropbox/GitHub/sicence nationism/data/'
    'Global-flows-and-rates-of-international-migration-of-scholars-2026_V2/data_processed/2026_V2')

# 每个来源: (国家年度指标文件, 双边流文件)
MPIDR_SOURCES = {
    'openalex': (os.path.join(MPIDR_DATA_DIR, 'openalex_2026_V2_scholarlymigration_country.csv'),
                 os.path.join(MPIDR_DATA_DIR, 'openalex_2026_V2_scholarlymigration_countryflows.csv')),
    'scopus':   (os.path.join(MPIDR_DATA_DIR, 'scopus_2026_V2_scholarlymigration_country.csv'),
                 os.path.join(MPIDR_DATA_DIR, 'scopus_2026_V2_scholarlymigration_countryflows.csv')),
}

OVERLAP_MIN, OVERLAP_MAX = 2005, 2022   # 本数据起点 与 MPIDR 可靠终点 的交集
FOCAL = ['RUS', 'UKR', 'GBR']           # 7mpidr 已输出 ISO3

# 本项目 WoS 国家全称 -> ISO3 (用于与 MPIDR iso3code 对齐)。
# 仅需覆盖出现的国家; 未命中的会尝试 pycountry 模糊匹配, 仍失败则在校验中报告并跳过。
NAME2ISO3 = {
    'RUSSIAN FEDERATION': 'RUS', 'UKRAINE': 'UKR', 'UNITED KINGDOM': 'GBR',
    'UNITED STATES': 'USA', 'GERMANY': 'DEU', 'FRANCE': 'FRA', 'CHINA': 'CHN',
    'ITALY': 'ITA', 'SPAIN': 'ESP', 'POLAND': 'POL', 'NETHERLANDS': 'NLD',
    'SWEDEN': 'SWE', 'SWITZERLAND': 'CHE', 'BELGIUM': 'BEL', 'AUSTRIA': 'AUT',
    'DENMARK': 'DNK', 'FINLAND': 'FIN', 'NORWAY': 'NOR', 'PORTUGAL': 'PRT',
    'GREECE': 'GRC', 'IRELAND': 'IRL', 'CZECHIA': 'CZE', 'CZECH REPUBLIC': 'CZE',
    'HUNGARY': 'HUN', 'ROMANIA': 'ROU', 'BULGARIA': 'BGR', 'SLOVAKIA': 'SVK',
    'SLOVAK REPUBLIC': 'SVK', 'SLOVENIA': 'SVN', 'CROATIA': 'HRV', 'ESTONIA': 'EST',
    'LATVIA': 'LVA', 'LITHUANIA': 'LTU', 'CYPRUS': 'CYP', 'MALTA': 'MLT',
    'LUXEMBOURG': 'LUX', 'ICELAND': 'ISL',
    'CANADA': 'CAN', 'AUSTRALIA': 'AUS', 'NEW ZEALAND': 'NZL', 'JAPAN': 'JPN',
    'SOUTH KOREA': 'KOR', 'KOREA': 'KOR', 'KOREA, REP.': 'KOR',
    'SINGAPORE': 'SGP', 'INDIA': 'IND', 'BRAZIL': 'BRA', 'TURKEY': 'TUR',
    'ISRAEL': 'ISR', 'IRAN': 'IRN', 'IRAN, ISLAMIC REP.': 'IRN',
    'UNITED ARAB EMIRATES': 'ARE', 'SAUDI ARABIA': 'SAU', 'SOUTH AFRICA': 'ZAF',
    'ARGENTINA': 'ARG', 'CHILE': 'CHL', 'MEXICO': 'MEX', 'TAIWAN': 'TWN',
    'VIETNAM': 'VNM', 'VIET NAM': 'VNM', 'BELARUS': 'BLR', 'MOLDOVA': 'MDA',
    'GEORGIA': 'GEO', 'ARMENIA': 'ARM', 'AZERBAIJAN': 'AZE', 'KAZAKHSTAN': 'KAZ',
    'SERBIA': 'SRB', 'REPUBLIC OF SERBIA': 'SRB',
    'BOSNIA & HERZEGOVINA': 'BIH', 'INDONESIA': 'IDN', 'PAKISTAN': 'PAK',
    'EGYPT': 'EGY', 'THAILAND': 'THA', 'COLOMBIA': 'COL',
}

try:
    import pycountry
    _HAS_PYCOUNTRY = True
except Exception:
    _HAS_PYCOUNTRY = False


def to_iso3(name):
    if not isinstance(name, str):
        return None
    key = name.strip().upper()
    if key in NAME2ISO3:
        return NAME2ISO3[key]
    if _HAS_PYCOUNTRY:
        try:
            m = pycountry.countries.search_fuzzy(name)
            if m:
                return m[0].alpha_3
        except Exception:
            pass
    return None


def kendall(a, b):
    s = pd.DataFrame({'a': a, 'b': b}).dropna()
    if len(s) < 3:
        return float('nan'), len(s)
    return s['a'].corr(s['b'], method='kendall'), len(s)


def pearson(a, b):
    s = pd.DataFrame({'a': a, 'b': b}).dropna()
    if len(s) < 3:
        return float('nan'), len(s)
    return s['a'].corr(s['b'], method='pearson'), len(s)


def load_mpidr(measures_csv, flows_csv):
    """读取 MPIDR 本地 CSV, 仅取 gender=all & field=all 的总体口径。
    返回 (国家年度指标 df, 双边流 df), 列名统一为脚本内部使用的形式。"""
    ref_m = pd.read_csv(measures_csv)
    ref_m = ref_m[(ref_m['gender'] == 'all') & (ref_m['field'] == 'all')].copy()

    ref_f = pd.read_csv(flows_csv)
    ref_f = ref_f[(ref_f['gender'] == 'all') & (ref_f['field'] == 'all')].copy()
    # 双边流列名: iso3codefrom/iso3codeto -> from_iso3/to_iso3
    ref_f = ref_f.rename(columns={'iso3codefrom': 'from_iso3', 'iso3codeto': 'to_iso3'})
    return ref_m, ref_f


def validate_source(name, ref_m, ref_f, our_m, our_f):
    """对单一 MPIDR 来源 (openalex / scopus) 做三层校验, 返回 (merged, fmerged, stats)。"""
    print(f'\n########## MPIDR 来源: {name.upper()} ##########')

    # ---------- 国家年度层对齐 ----------
    om = our_m[(our_m['year'].between(OVERLAP_MIN, OVERLAP_MAX)) & our_m['iso3'].notna()]
    rm = ref_m[ref_m['year'].between(OVERLAP_MIN, OVERLAP_MAX)]
    merged = om.merge(
        rm[['year', 'iso3code', 'padded_population_of_researchers', 'netmigrationrate']],
        left_on=['iso3', 'year'], right_on=['iso3code', 'year'], how='inner',
        suffixes=('_ours', '_mpidr')
    )

    print('\n================ 国家年度层校验 (2005-2022) ================')
    print(f'匹配到的 国家-年 观测数: {len(merged):,}')
    kp, np_ = kendall(merged['population'], merged['padded_population_of_researchers'])
    pp, _ = pearson(merged['population'], merged['padded_population_of_researchers'])
    print(f'  研究者人口 population : Kendall tau={kp:.3f}  Pearson r={pp:.3f}  (N={np_:,})')
    kn, nn = kendall(merged['nmr'], merged['netmigrationrate'])
    pn, _ = pearson(merged['nmr'], merged['netmigrationrate'])
    print(f'  净迁移率   nmr        : Kendall tau={kn:.3f}  Pearson r={pn:.3f}  (N={nn:,})')

    # ---------- 双边流层对齐 ----------
    of = our_f[(our_f['year'].between(OVERLAP_MIN, OVERLAP_MAX)) &
               our_f['from_iso3'].notna() & our_f['to_iso3'].notna()]
    mf = ref_f[ref_f['year'].between(OVERLAP_MIN, OVERLAP_MAX)]
    fmerged = of.merge(
        mf[['from_iso3', 'to_iso3', 'year', 'n_migrations']],
        on=['from_iso3', 'to_iso3', 'year'], how='inner',
        suffixes=('_ours', '_mpidr')
    )
    print('\n================ 双边流层校验 (2005-2022) ================')
    print(f'匹配到的 国家对-年 观测数: {len(fmerged):,}')
    kf, nf = kendall(fmerged['n_migrations_ours'], fmerged['n_migrations_mpidr'])
    pf, _ = pearson(fmerged['n_migrations_ours'], fmerged['n_migrations_mpidr'])
    print(f'  双边迁移人数 : Kendall tau={kf:.3f}  Pearson r={pf:.3f}  (N={nf:,})')

    # ---------- 重点国家逐年对照 ----------
    print('\n================ 重点国家 净迁移率 逐年对照 ================')
    for iso in FOCAL:
        sub = merged[merged['iso3'] == iso].sort_values('year')
        if sub.empty:
            print(f'  {iso}: 无匹配'); continue
        kc, _ = kendall(sub['nmr'], sub['netmigrationrate'])
        print(f'  {iso}: 逐年 nmr Kendall tau={kc:.3f}, N={len(sub)}')

    # ---------- 散点图 ----------
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
        axes[0].scatter(merged['padded_population_of_researchers'], merged['population'], s=6, alpha=0.4)
        axes[0].set(xscale='log', yscale='log', xlabel=f'{name} population', ylabel='Ours population',
                    title=f'Population (tau={kp:.2f})')
        axes[1].scatter(merged['netmigrationrate'], merged['nmr'], s=6, alpha=0.4)
        axes[1].set(xlabel=f'{name} NMR', ylabel='Ours NMR', title=f'Net migration rate (tau={kn:.2f})')
        axes[2].scatter(fmerged['n_migrations_mpidr'], fmerged['n_migrations_ours'], s=6, alpha=0.4)
        axes[2].set(xscale='log', yscale='log', xlabel=f'{name} flow', ylabel='Ours flow',
                    title=f'Bilateral flows (tau={kf:.2f})')
        for ax in axes:
            ax.grid(True, alpha=0.3)
        fig.suptitle(f'Validation against MPIDR ({name})')
        fig.tight_layout()
        figpath = os.path.join(OUT_DIR, f'validation_against_mpidr_{name}.png')
        fig.savefig(figpath, dpi=150)
        print(f'\n散点图已保存: {figpath}')
    except Exception as e:
        print(f'[跳过绘图] {e}')

    merged.to_csv(os.path.join(OUT_DIR, f'validation_country_year_merged_{name}.csv'), index=False)
    fmerged.to_csv(os.path.join(OUT_DIR, f'validation_flows_merged_{name}.csv'), index=False)
    print(f'\n[{name}] 合并明细已导出, 可进一步人工核查。')


def main():
    # ---------- 读取本项目自建结果 ----------
    # 7mpidr_migration_replication.py 已直接输出 ISO3, 故这里的国家列即 ISO3。
    our_m = pd.read_csv(OUR_MEASURES)
    our_f = pd.read_csv(OUR_FLOWS)
    our_m['iso3'] = our_m['country']
    our_f['from_iso3'] = our_f['from_country']
    our_f['to_iso3'] = our_f['to_country']

    for name, (measures_csv, flows_csv) in MPIDR_SOURCES.items():
        if not (os.path.exists(measures_csv) and os.path.exists(flows_csv)):
            print(f'[跳过 {name}] 文件缺失: {measures_csv} / {flows_csv}')
            continue
        ref_m, ref_f = load_mpidr(measures_csv, flows_csv)
        validate_source(name, ref_m, ref_f, our_m, our_f)


if __name__ == '__main__':
    main()
