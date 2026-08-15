# -*- coding: utf-8 -*-
"""
单边走廊迁移 event study — GBR / RUS / UKR
与 _mig_es_partner_core.do 同模型; Python 估计 + 出图

运行: python3 13migration_partner_eventstudy.py [GBR|RUS|UKR|all]
"""
import os
import sys
import warnings
import numpy as np
import pandas as pd
from scipy.stats import norm
import statsmodels.api as sm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')
CODE = '/Users/sunmengge/Dropbox/GitHub/sicence nationism/code'
REL_MIN, REF = -6, -1
PARTNER_LABEL = {
    'DEU': 'Germany', 'CHN': 'China', 'USA': 'United States',
    'RUS': 'Russia', 'UKR': 'Ukraine', 'GBR': 'United Kingdom', 'POL': 'Poland',
}
FOCAL_CFG = {
    'GBR': dict(
        folder='3ppml_migration_did_uk_internal_control',
        thr=3, T0=2016, rel_max=8,
        partners=['DEU', 'CHN', 'USA', 'RUS'],
        title='United Kingdom',
        event='Brexit (2016)',
        in_lbl='Immigration: partner → UK',
        out_lbl='Emigration: UK → partner',
    ),
    'RUS': dict(
        folder='3ppml_migration_did_russia_internal_control',
        thr=2, T0=2022, rel_max=2,
        partners=['DEU', 'CHN', 'USA', 'UKR'],
        title='Russia',
        event='Full-scale invasion (2022)',
        in_lbl='Immigration: partner → Russia',
        out_lbl='Emigration: Russia → partner',
    ),
    'UKR': dict(
        folder='3ppml_migration_did_ukraine_internal_control',
        thr=1, T0=2022, rel_max=2,
        partners=['DEU', 'CHN', 'USA', 'RUS'],
        title='Ukraine',
        event='Full-scale invasion (2022)',
        in_lbl='Immigration: partner → Ukraine',
        out_lbl='Emigration: Ukraine → partner',
    ),
}


def _design(d, es_cols):
    X = d[es_cols + ['ln_total_pub']].astype(float).copy()
    X = pd.concat([X,
                   pd.get_dummies(d['partner_country'], prefix='p', drop_first=True, dtype=float),
                   pd.get_dummies(d['year'], prefix='y', drop_first=True, dtype=float)], axis=1)
    return sm.add_constant(X.astype(float), has_constant='add')


def fit_partner_es(df, partner, thr, rel_max):
    d = df[(df.avg_pre >= thr) & (df.rel_year >= REL_MIN) & (df.rel_year <= rel_max)].copy()
    d['treated'] = (d.partner_country == partner).astype(int)
    rels = [r for r in range(REL_MIN, rel_max + 1) if r != REF]
    es_cols = []
    for r in rels:
        c = f'es_{r}'
        d[c] = ((d.rel_year == r) & (d.treated == 1)).astype(float)
        es_cols.append(c)
    X = _design(d, es_cols)
    y = d['paper_count'].astype(float).values
    res = sm.GLM(y, X, family=sm.families.Poisson()).fit(
        cov_type='cluster', cov_kwds={'groups': d['partner_country'].values})
    pre_cols = [c for c in es_cols if int(c.split('_')[1]) < 0]
    wald = res.wald_test(pre_cols, use_f=False) if pre_cols else None
    pretrend_p = float(wald.pvalue) if wald is not None else np.nan
    rows = []
    for r in range(REL_MIN, rel_max + 1):
        if r == REF:
            rows.append(dict(rel_year=r, coef=0., se=0., ci_lo=0., ci_hi=0., pval=np.nan))
            continue
        nm = f'es_{r}'
        if nm not in res.params.index:
            continue
        b, se = float(res.params[nm]), float(res.bse[nm])
        z = b / se if se > 0 else np.nan
        p = 2 * (1 - norm.cdf(abs(z))) if np.isfinite(z) else np.nan
        rows.append(dict(rel_year=r, coef=b, se=se, ci_lo=b - 1.96 * se, ci_hi=b + 1.96 * se, pval=p))
    return pd.DataFrame(rows), pretrend_p


def run_focal(focal):
    cfg = FOCAL_CFG[focal]
    rdir = os.path.join(CODE, cfg['folder'], 'results')
    os.makedirs(rdir, exist_ok=True)
    es_rows, pt_rows = [], []
    print(f'\n=== {focal} ({cfg["title"]}) ===')
    for direction in ['in', 'out']:
        df = pd.read_csv(os.path.join(CODE, cfg['folder'], f'ppml_data_{direction}.csv'))
        for p in cfg['partners']:
            if p == focal:
                continue
            print(f'  {direction} / {p} ...', end=' ', flush=True)
            try:
                est, pp = fit_partner_es(df, p, cfg['thr'], cfg['rel_max'])
                est['focal'] = focal
                est['direction'] = direction
                est['partner'] = p
                est['pretrend_p'] = pp
                es_rows.append(est)
                pt_rows.append(dict(focal=focal, direction=direction, partner=p,
                                    pretrend_p=pp, n_pre=5))
                print(f'pretrend p={pp:.4f}')
            except Exception as e:
                print(f'FAIL: {e}')
    es = pd.concat(es_rows, ignore_index=True)
    pt = pd.DataFrame(pt_rows)
    es.to_csv(os.path.join(rdir, 'eventstudy_partners.csv'), index=False)
    pt.to_csv(os.path.join(rdir, 'eventstudy_partners_pretrend.csv'), index=False)
    print('->', os.path.join(rdir, 'eventstudy_partners.csv'))
    return es, pt, cfg


def plot_partner_es(es, cfg, focal, out_base):
    partners = cfg['partners']
    rel_max = cfg['rel_max']
    dir_title = {'in': cfg['in_lbl'], 'out': cfg['out_lbl']}
    fig, axes = plt.subplots(2, len(partners), figsize=(4 * len(partners), 7), sharex=True)
    if len(partners) == 1:
        axes = np.array([[axes[0]], [axes[1]]])
    for col, p in enumerate(partners):
        for row, d in enumerate(['in', 'out']):
            ax = axes[row, col]
            s = es[(es.partner == p) & (es.direction == d)].sort_values('rel_year')
            if s.empty:
                ax.set_visible(False)
                continue
            pp = s['pretrend_p'].dropna()
            pp = pp.iloc[0] if len(pp) else np.nan
            ax.fill_between(s.rel_year, s.ci_lo, s.ci_hi, color='#4c72b0', alpha=0.2)
            ax.plot(s.rel_year, s.coef, 'o-', color='#1f3a5f', ms=4, lw=1.5)
            ax.axhline(0, color='k', lw=0.8)
            ax.axvline(-0.5, color='gray', ls='--', lw=0.8)
            if row == 0:
                ax.set_title(PARTNER_LABEL.get(p, p), fontsize=12, fontweight='bold')
            if col == 0:
                ax.set_ylabel(f'{dir_title[d]}\ncoef (log share)', fontsize=9)
            pp_txt = f'pre-trend p={pp:.3f}' if pd.notna(pp) else 'pre-trend p=.'
            ax.text(0.03, 0.97, pp_txt, transform=ax.transAxes, va='top', fontsize=7.5,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85))
            ax.set_xlim(REL_MIN - 0.5, rel_max + 0.5)
            ax.tick_params(labelsize=8)
    for ax in axes[1]:
        ax.set_xlabel(f'Years relative to {cfg["event"]}', fontsize=9)
    fig.suptitle(f'{cfg["title"]} bilateral migration: partner-level event studies (PPML)',
                 fontsize=13, fontweight='bold', y=1.02)
    fig.tight_layout()
    for ext in ('png', 'pdf'):
        out = f'{out_base}.{ext}'
        fig.savefig(out, dpi=200, bbox_inches='tight', facecolor='white')
        print('->', out)
    plt.close(fig)


def print_pretrend(pt, partners):
    print('\n平行趋势 Wald p:')
    for p in partners:
        print(f"  {PARTNER_LABEL.get(p, p)}:")
        for d in ['in', 'out']:
            r = pt[(pt.partner == p) & (pt.direction == d)]
            if len(r):
                print(f"    {d}: {r.pretrend_p.iloc[0]:.4f}")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    focals = list(FOCAL_CFG) if which == 'all' else [which.upper()]
    for focal in focals:
        if focal not in FOCAL_CFG:
            raise SystemExit(f'未知 focal: {focal}; 可选 GBR RUS UKR all')
        es, pt, cfg = run_focal(focal)
        print_pretrend(pt, cfg['partners'])
        rdir = os.path.join(CODE, cfg['folder'], 'results')
        plot_partner_es(es, cfg, focal, os.path.join(rdir, f'eventstudy_partners_{focal}'))


if __name__ == '__main__':
    main()
