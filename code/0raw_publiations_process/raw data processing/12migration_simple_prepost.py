# -*- coding: utf-8 -*-
"""
通俗 pre/post 双边迁移份额表 — GBR / RUS / UKR

口径:
  - 份额 = 该国走廊人数 / focal 该方向总迁移人数
  - GBR: pre 2008-2015, post 2017-2024 (略过 2016 公投年)
  - RUS/UKR: pre 2008-2021, post 2022-2024

输出 (各 focal 的 results/ 目录):
  migration_prepost_{focal}_in.csv
  migration_prepost_{focal}_out.csv
  migration_prepost_{focal}_key.csv      重点国 + 欧盟汇总
  migration_prepost_all_key.csv          三国重点国合并 (raw data processing/)
"""
import os
import numpy as np
import pandas as pd

CODE = '/Users/sunmengge/Dropbox/GitHub/sicence nationism/code'
FLOWS = os.path.join(
    CODE, '0raw_publiations_process/migration_output_mpidr/mpidr_country_flows.csv')
OUT_DIR = os.path.join(CODE, '0raw_publiations_process/raw data processing')

EU = {'DEU', 'FRA', 'ITA', 'ESP', 'NLD', 'BEL', 'POL', 'SWE', 'DNK', 'FIN',
      'IRL', 'AUT', 'PRT', 'GRC', 'CZE', 'HUN', 'ROU', 'BGR', 'SVK', 'SVN',
      'EST', 'LVA', 'LTU', 'LUX', 'MLT', 'CYP', 'HRV'}

FOCALS = {
    'GBR': dict(T0=2016, pre=(2008, 2015), post=(2017, 2024), thr=3,
                 folder='3ppml_migration_did_uk_internal_control',
                 label='United Kingdom'),
    'RUS': dict(T0=2022, pre=(2008, 2021), post=(2022, 2024), thr=2,
                 folder='3ppml_migration_did_russia_internal_control',
                 label='Russia'),
    'UKR': dict(T0=2022, pre=(2008, 2021), post=(2022, 2024), thr=1,
                 folder='3ppml_migration_did_ukraine_internal_control',
                 label='Ukraine'),
}

KEY_PARTNERS = {
    'GBR': ['DEU', 'CHN', 'USA', 'RUS', 'FRA', 'IND', 'AUS'],
    'RUS': ['DEU', 'CHN', 'USA', 'UKR', 'GBR', 'KAZ', 'BLR'],
    'UKR': ['DEU', 'CHN', 'USA', 'RUS', 'GBR', 'POL', 'TUR'],
}

PARTNER_NAME = {
    'DEU': 'Germany', 'CHN': 'China', 'USA': 'United States', 'RUS': 'Russia',
    'UKR': 'Ukraine', 'GBR': 'United Kingdom', 'FRA': 'France', 'IND': 'India',
    'AUS': 'Australia', 'KAZ': 'Kazakhstan', 'BLR': 'Belarus', 'POL': 'Poland',
    'TUR': 'Turkey',
}


def period_stats(flows, focal, direction, pre, post):
    if direction == 'in':
        sub = flows[flows.to_country == focal].rename(columns={'from_country': 'partner'})
    else:
        sub = flows[flows.from_country == focal].rename(columns={'to_country': 'partner'})
    sub = sub[sub.partner != focal]

    rows = []
    for label, y0, y1 in [('pre', *pre), ('post', *post)]:
        s = sub[(sub.year >= y0) & (sub.year <= y1)]
        ny = y1 - y0 + 1
        tot = s.n_migrations.sum() / ny
        by_p = s.groupby('partner')['n_migrations'].sum() / ny
        for p, cnt in by_p.items():
            rows.append(dict(partner=p, period=label, avg_count=cnt,
                             total=tot, share=cnt / tot if tot > 0 else np.nan))
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()
    wide = df.pivot(index='partner', columns='period', values=['avg_count', 'share', 'total'])
    wide.columns = ['cnt_pre', 'cnt_post', 'shr_pre', 'shr_post', 'tot_pre', 'tot_post']
    wide = wide.reset_index()
    # 各伙伴行上的 total 应相同; 显式写入避免 pivot 缺列错位
    pre_tot = df.loc[df.period == 'pre', 'total'].iloc[0] if (df.period == 'pre').any() else np.nan
    post_tot = df.loc[df.period == 'post', 'total'].iloc[0] if (df.period == 'post').any() else np.nan
    wide['tot_pre'] = pre_tot
    wide['tot_post'] = post_tot
    wide['shr_pre'] = wide['cnt_pre'] / wide['tot_pre']
    wide['shr_post'] = wide['cnt_post'] / wide['tot_post']
    wide['cnt_chg_pct'] = np.where(wide.cnt_pre > 0,
                                   (wide.cnt_post / wide.cnt_pre - 1) * 100, np.nan)
    wide['share_chg_pp'] = (wide['shr_post'] - wide['shr_pre']) * 100
    return wide


def eu_block(wide):
    eu = wide[wide.partner.isin(EU)].copy()
    if eu.empty:
        return None
    return pd.Series({
        'partner': '_EU27',
        'cnt_pre': eu.cnt_pre.sum(),
        'cnt_post': eu.cnt_post.sum(),
        'shr_pre': eu.cnt_pre.sum() / eu.tot_pre.iloc[0] * 100 if len(eu) else np.nan,
        'shr_post': eu.cnt_post.sum() / eu.tot_post.iloc[0] * 100 if len(eu) else np.nan,
        'tot_pre': eu.tot_pre.iloc[0],
        'tot_post': eu.tot_post.iloc[0],
    })


def format_table(wide, focal, direction, cfg):
    pre_tot = wide.tot_pre.iloc[0]
    post_tot = wide.tot_post.iloc[0]
    w = wide.copy()
    w['share_pre_pct'] = w.shr_pre * 100
    w['share_post_pct'] = w.shr_post * 100
    cols = ['partner', 'cnt_pre', 'cnt_post', 'cnt_chg_pct',
            'share_pre_pct', 'share_post_pct', 'share_chg_pp']
    w = w[cols].sort_values('share_chg_pp', key=abs, ascending=False)
    eu = eu_block(wide)
    if eu is not None:
        eu_row = dict(
            partner='_EU27',
            cnt_pre=eu['cnt_pre'], cnt_post=eu['cnt_post'],
            cnt_chg_pct=(eu['cnt_post'] / eu['cnt_pre'] - 1) * 100 if eu['cnt_pre'] > 0 else np.nan,
            share_pre_pct=eu['shr_pre'], share_post_pct=eu['shr_post'],
            share_chg_pp=eu['shr_post'] - eu['shr_pre'],
        )
        tot_row = dict(
            partner='_TOTAL',
            cnt_pre=pre_tot, cnt_post=post_tot,
            cnt_chg_pct=(post_tot / pre_tot - 1) * 100 if pre_tot > 0 else np.nan,
            share_pre_pct=100., share_post_pct=100., share_chg_pp=0.,
        )
        w = pd.concat([pd.DataFrame([tot_row, eu_row]), w], ignore_index=True)
    w.insert(0, 'focal', focal)
    w.insert(1, 'direction', direction)
    w.insert(2, 'pre_years', f"{cfg['pre'][0]}-{cfg['pre'][1]}")
    w.insert(3, 'post_years', f"{cfg['post'][0]}-{cfg['post'][1]}")
    return w


def key_table(w_in, w_out, focal, cfg):
    keys = KEY_PARTNERS[focal]
    rows = []
    for direction, w in [('in', w_in), ('out', w_out)]:
        for p in keys:
            r = w[w.partner == p]
            if len(r) == 0:
                continue
            r = r.iloc[0]
            rows.append(dict(
                focal=focal, focal_name=cfg['label'], direction=direction,
                partner=p, partner_name=PARTNER_NAME.get(p, p),
                cnt_pre=round(r.cnt_pre, 1), cnt_post=round(r.cnt_post, 1),
                cnt_chg_pct=round(r.cnt_chg_pct, 1) if pd.notna(r.cnt_chg_pct) else np.nan,
                share_pre_pct=round(r.shr_pre * 100, 2),
                share_post_pct=round(r.shr_post * 100, 2),
                share_chg_pp=round(r.share_chg_pp, 2),
                pre_years=f"{cfg['pre'][0]}-{cfg['pre'][1]}",
                post_years=f"{cfg['post'][0]}-{cfg['post'][1]}",
            ))
        eu = eu_block(w)
        if eu is not None:
            rows.append(dict(
                focal=focal, focal_name=cfg['label'], direction=direction,
                partner='_EU27', partner_name='EU-27 (aggregate)',
                cnt_pre=round(eu['cnt_pre'], 1), cnt_post=round(eu['cnt_post'], 1),
                cnt_chg_pct=round((eu['cnt_post'] / eu['cnt_pre'] - 1) * 100, 1)
                if eu['cnt_pre'] > 0 else np.nan,
                share_pre_pct=round(eu['shr_pre'], 2),
                share_post_pct=round(eu['shr_post'], 2),
                share_chg_pp=round(eu['shr_post'] - eu['shr_pre'], 2),
                pre_years=f"{cfg['pre'][0]}-{cfg['pre'][1]}",
                post_years=f"{cfg['post'][0]}-{cfg['post'][1]}",
            ))
        if len(w):
            tp, tq = w.tot_pre.iloc[0], w.tot_post.iloc[0]
            rows.append(dict(
                focal=focal, focal_name=cfg['label'], direction=direction,
                partner='_TOTAL', partner_name='All partners',
                cnt_pre=round(tp, 1), cnt_post=round(tq, 1),
                cnt_chg_pct=round((tq / tp - 1) * 100, 1),
                share_pre_pct=100., share_post_pct=100., share_chg_pp=0.,
                pre_years=f"{cfg['pre'][0]}-{cfg['pre'][1]}",
                post_years=f"{cfg['post'][0]}-{cfg['post'][1]}",
            ))
    return pd.DataFrame(rows)


def main():
    flows = pd.read_csv(FLOWS)
    all_key = []
    for focal, cfg in FOCALS.items():
        rdir = os.path.join(CODE, cfg['folder'], 'results')
        os.makedirs(rdir, exist_ok=True)
        print(f"\n{'='*60}\n{focal} ({cfg['label']})")
        print(f"  pre {cfg['pre']}  post {cfg['post']}\n")

        for direction in ['in', 'out']:
            wide = period_stats(flows, focal, direction, cfg['pre'], cfg['post'])
            wide = wide[wide.cnt_pre >= cfg['thr']].copy()
            tbl = format_table(wide, focal, direction, cfg)
            fp = os.path.join(rdir, f'migration_prepost_{focal}_{direction}.csv')
            tbl.to_csv(fp, index=False, float_format='%.2f')
            print(f"  -> {fp}  ({len(tbl)-2} partners, thr>={cfg['thr']})")

        w_in = period_stats(flows, focal, 'in', cfg['pre'], cfg['post'])
        w_out = period_stats(flows, focal, 'out', cfg['pre'], cfg['post'])
        key = key_table(w_in, w_out, focal, cfg)
        fpk = os.path.join(rdir, f'migration_prepost_{focal}_key.csv')
        key.to_csv(fpk, index=False, float_format='%.2f')
        print(f"  -> {fpk}")
        all_key.append(key)

        print(f"\n  重点国摘要 ({cfg['label']}):")
        for d, dlab in [('in', '迁入'), ('out', '迁出')]:
            sub = key[(key.direction == d) & (~key.partner.str.startswith('_'))]
            print(f"    [{dlab}]")
            for _, r in sub.iterrows():
                print(f"      {r.partner_name:16s}  "
                      f"{r.cnt_pre:6.0f}->{r.cnt_post:6.0f}  "
                      f"份额 {r.share_pre_pct:5.1f}%->{r.share_post_pct:5.1f}%  "
                      f"({r.share_chg_pp:+.1f} pp)")

    combined = pd.concat(all_key, ignore_index=True)
    fpc = os.path.join(OUT_DIR, 'migration_prepost_all_key.csv')
    combined.to_csv(fpc, index=False, float_format='%.2f')
    print(f"\n-> 三国合并: {fpc}")
    print('完成')


if __name__ == '__main__':
    main()
