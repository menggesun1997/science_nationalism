# -*- coding: utf-8 -*-
"""
机制二 迁移流 PPML 结果可视化 (三国 x 两方向)
读取各文件夹 results/ 下的 Stata 输出, 生成:
  results/eventstudy_plot.png    阵营层事件研究 (West/East, 流出/流入)
  results/partner_delta_top.png  逐伙伴 delta Top/Bottom
  results/robustness_plot.png    阵营层 delta 跨设定稳健性
并输出跨国汇总 migration_ppml_summary.csv
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CODE_DIR = '/Users/sunmengge/Dropbox/GitHub/sicence nationism/code'
FOLDERS = {
    'GBR (Brexit 2016)': ('3ppml_migration_did_uk_internal_control', 2016),
    'RUS (War 2022)':    ('3ppml_migration_did_russia_internal_control', 2022),
    'UKR (War 2022)':    ('3ppml_migration_did_ukraine_internal_control', 2022),
}
DIRLAB = {'out': 'Emigration (focal->partner)', 'in': 'Immigration (partner->focal)'}
BLOC_C = {'West': '#1f77b4', 'East': '#d62728'}


def event_plot(folder, title):
    fp = os.path.join(CODE_DIR, folder, 'results', 'eventstudy.csv')
    if not os.path.exists(fp):
        return
    es = pd.read_csv(fp)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    for ax, d in zip(axes, ['out', 'in']):
        for bl in ['West', 'East']:
            s = es[(es.direction == d) & (es.bloc == bl)].sort_values('rel_year')
            if s.empty:
                continue
            pp = s['pretrend_p'].dropna().iloc[0] if s['pretrend_p'].notna().any() else np.nan
            ax.plot(s.rel_year, s.coef, '-o', color=BLOC_C[bl], ms=4,
                    label=f'{bl} (pre-trend p={pp:.3f})')
            ax.fill_between(s.rel_year, s.ci_lo, s.ci_hi, color=BLOC_C[bl], alpha=0.15)
        ax.axhline(0, color='k', lw=.8)
        ax.axvline(-0.5, color='gray', ls='--', lw=.8)
        ax.set_title(DIRLAB[d], fontsize=10)
        ax.set_xlabel('Relative year (0 = event)')
        ax.set_ylabel('Event-study coef (log share)')
        ax.legend(fontsize=8)
    fig.suptitle(f'{title}: bloc-level event study (internal-control PPML)', fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(CODE_DIR, folder, 'results', 'eventstudy_plot.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('  ', out)


def partner_plot(folder, title):
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, d in zip(axes, ['out', 'in']):
        fp = os.path.join(CODE_DIR, folder, 'results', f'partner_coefficients_{d}.csv')
        if not os.path.exists(fp):
            continue
        c = pd.read_csv(fp)
        c = c.sort_values('pct')
        top = pd.concat([c.head(10), c.tail(10)]).drop_duplicates('partner_country')
        colors = ['#d62728' if v < 0 else '#2ca02c' for v in top.pct_pctpts]
        ax.barh(top.partner_country, top.pct_pctpts, color=colors)
        ax.axvline(0, color='k', lw=.8)
        ax.set_title(DIRLAB[d], fontsize=10)
        ax.set_xlabel('% change in bilateral share (exp(delta)-1)')
    fig.suptitle(f'{title}: partner-level DiD (top/bottom 10)', fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(CODE_DIR, folder, 'results', 'partner_delta_top.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('  ', out)


def robust_plot(folder, title):
    fp = os.path.join(CODE_DIR, folder, 'results', 'robustness.csv')
    if not os.path.exists(fp):
        return
    r = pd.read_csv(fp)
    specs = ['baseline', 'no_control', 'no_offset', 'vce_robust', 'thr_hi', 'winsor', 'placebo']
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, d in zip(axes, ['out', 'in']):
        x = np.arange(len(specs))
        for i, bl in enumerate(['West', 'East']):
            vals, errs = [], []
            for sp in specs:
                row = r[(r.direction == d) & (r.bloc == bl) & (r.spec == sp)]
                if row.empty:
                    vals.append(np.nan); errs.append(0)
                else:
                    vals.append(row.pct_pctpts.iloc[0])
                    errs.append(row.se.iloc[0] * 100)
            ax.errorbar(x + (i - 0.5) * 0.15, vals, yerr=errs, fmt='o', color=BLOC_C[bl],
                        capsize=3, label=bl)
        ax.axhline(0, color='k', lw=.8)
        ax.set_xticks(x)
        ax.set_xticklabels(specs, rotation=45, ha='right', fontsize=8)
        ax.set_title(DIRLAB[d], fontsize=10)
        ax.set_ylabel('% change (bloc DiD)')
        ax.legend(fontsize=8)
    fig.suptitle(f'{title}: robustness of bloc-level DiD across specifications', fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(CODE_DIR, folder, 'results', 'robustness_plot.png')
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('  ', out)


def main():
    rows = []
    for title, (folder, T0) in FOLDERS.items():
        print(title)
        event_plot(folder, title)
        partner_plot(folder, title)
        robust_plot(folder, title)
        # 汇总: baseline 阵营层 delta
        fp = os.path.join(CODE_DIR, folder, 'results', 'robustness.csv')
        if os.path.exists(fp):
            r = pd.read_csv(fp)
            base = r[r.spec == 'baseline']
            for _, x in base.iterrows():
                rows.append(dict(focal=x.focal, direction=x.direction, bloc=x.bloc,
                                 pct=round(x.pct_pctpts, 1), pval=round(x.pval, 4),
                                 n_treated=int(x.n_treated), n_obs=int(x.n_obs)))
    summ = pd.DataFrame(rows)
    out = os.path.join(CODE_DIR, '0raw_publiations_process', 'raw data processing',
                       'migration_ppml_summary.csv')
    summ.to_csv(out, index=False)
    print('\n跨国汇总 (baseline 阵营层 delta):')
    print(summ.to_string(index=False))
    print('\n->', out)


if __name__ == '__main__':
    main()
