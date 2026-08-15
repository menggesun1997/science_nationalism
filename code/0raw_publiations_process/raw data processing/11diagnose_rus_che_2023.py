"""
诊断: 2023 年 RUS -> CHE 迁移尖峰(约 534 人)是否由个别超大合著论文(几百作者)造成。

思路(与 7mpidr_migration_replication.py 完全同口径地重建居住面板/迁移事件):
  1. 重建 padded 居住面板与 events 迁移事件。
  2. 取出 mig_year=2023、origin=RUS、dest=CHE 的作者集合 (mig2023)。
  3. 找这些作者 2023 年带瑞士(CHE)地址的 authorship records -> 对应论文 UID。
  4. 统计每篇论文(UID)摊到多少个这样的迁移作者 -> 若高度集中在极少数论文,即为超大合著论文伪迁移。
  5. 对 top 论文, 给出该论文全部作者数(所有国家)、是否含 RUS 地址、发表学科等旁证。

输出:
  - 控制台报告(Top 论文 + 覆盖率)
  - rus_che_2023_diagnosis.csv (Top 论文明细)

运行(服务器):
  SCI_DATA_DIR=/path/to/raw SCI_OUT_DIR=/path/to/out python3 11diagnose_rus_che_2023.py
"""

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import os
import time
import duckdb

BASE = os.environ.get(
    'SCI_DATA_DIR',
    str(CODE / "0raw_publiations_process/raw_data_2026"))
AUTHOR_FILE = os.path.join(BASE, 'article_author_cntry_brexit.txt')
PAPER_FILE = os.path.join(BASE, 'article_brexit.txt')

OUT_DIR = os.environ.get(
    'SCI_OUT_DIR',
    str(CODE / "0raw_publiations_process/raw data processing/migration_output_mpidr"))
os.makedirs(OUT_DIR, exist_ok=True)
CNTRY_CONVERT = os.environ.get(
    'SCI_CNTRY_CONVERT',
    str(CODE / "0raw_publiations_process/raw data processing/cntry_convert.csv"))
OUT_CSV = os.path.join(OUT_DIR, 'rus_che_2023_diagnosis.csv')

YEAR_MIN, YEAR_MAX = 2005, 2024
FOCAL_YEAR = 2023
ORIGIN, DEST = 'RUS', 'CHE'

TMP_DIR = os.path.join(OUT_DIR, 'duckdb_tmp')
os.makedirs(TMP_DIR, exist_ok=True)

# --- 国家名 -> ISO3 (与主脚本一致) ---
STD2ISO3 = {
    'United Kingdom': 'GBR', 'United States': 'USA', 'Russia': 'RUS', 'China': 'CHN',
    'South Korea': 'KOR', 'North Korea': 'PRK', 'Turkey': 'TUR', 'Iran': 'IRN',
    'Vietnam': 'VNM', 'Czechia': 'CZE', 'Czech Republic': 'CZE', 'Kosovo': 'XKX',
    'Taiwan': 'TWN', 'Hong Kong': 'HKG', 'Macao': 'MAC', 'Syria': 'SYR', 'Laos': 'LAO',
    'Moldova': 'MDA', 'Bolivia': 'BOL', 'Venezuela': 'VEN', 'Tanzania': 'TZA',
    'Brunei': 'BRN', 'Swaziland': 'SWZ', 'Cape Verde': 'CPV', 'East Timor': 'TLS',
    'Byelarus': 'BLR', 'Ivory Coast': 'CIV', 'Burma': 'MMR', 'Republic of Kosovo': 'XKX',
    'Serbia and Montenegro': 'SRB', 'Bosnia & Herzegovina': 'BIH', 'Antigua & Barbuda': 'ATG',
    'Netherlands-Antilles': 'ANT', 'New-Caledonia': 'NCL', 'French-Polynesia': 'PYF',
    'French-Guiana': 'GUF', 'St-Lucia': 'LCA', 'St-Kitts & Nevis': 'KNA',
    'Sao Tome & Principe': 'STP', 'Saint-Vincent-et-les-Grenadines': 'VCT',
    'SINT-MAARTEN': 'SXM', 'ST-MARTIN': 'MAF',
}
DROP_STD = {'Antarctica'}


def load_clar2std(path):
    import pandas as pd
    df = pd.read_csv(path)
    df = df[['Clarivate country', 'Country']].dropna(subset=['Clarivate country'])
    return {str(k).strip().upper(): str(v).strip()
            for k, v in zip(df['Clarivate country'], df['Country'])}


def build_iso3_map(country_names, clar2std):
    try:
        import pycountry
    except Exception:
        pycountry = None
    mapping, unmapped = {}, []
    for name in country_names:
        std = clar2std.get(name, name)
        if std in DROP_STD:
            unmapped.append(name); continue
        iso = STD2ISO3.get(std)
        if iso is None and pycountry is not None:
            try:
                res = pycountry.countries.search_fuzzy(std)
                iso = res[0].alpha_3 if res else None
            except Exception:
                iso = None
        if iso:
            mapping[name] = iso
        else:
            unmapped.append(name)
    return mapping


def main():
    t0 = time.time()
    con = duckdb.connect()
    con.execute(f"PRAGMA temp_directory='{TMP_DIR}'")
    con.execute(f"PRAGMA memory_limit='{os.environ.get('SCI_DUCKDB_MEM', '12GB')}'")
    con.execute(f"PRAGMA threads={os.environ.get('SCI_DUCKDB_THREADS', '4')}")
    con.execute("PRAGMA preserve_insertion_order=false")

    def log(m):
        print(f'[{time.time()-t0:6.0f}s] {m}', flush=True)

    log('[1] 文章年份 ...')
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE papers AS
        SELECT CAST(OST_BK AS BIGINT) AS OST_BK,
               CAST(Annee_Bibliographique AS INTEGER) AS year
        FROM read_csv_auto('{PAPER_FILE}', delim='|', header=true,
                           types={{'OST_BK':'BIGINT','Annee_Bibliographique':'INTEGER'}})
        WHERE Annee_Bibliographique IS NOT NULL
    """)

    log('[2] authorship records (含 UID/ost) ...')
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE ar_raw AS
        SELECT a.cluster_id AS author, a.OST_BK AS ost, p.year AS year,
               upper(trim(a.Pays)) AS country_raw
        FROM read_csv_auto('{AUTHOR_FILE}', delim='|', header=true,
                           types={{'OST_BK':'BIGINT','cluster_id':'BIGINT','Pays':'VARCHAR'}}) a
        JOIN papers p USING (OST_BK)
        WHERE a.cluster_id IS NOT NULL
          AND a.Pays IS NOT NULL AND trim(a.Pays) <> ''
          AND p.year BETWEEN {YEAR_MIN} AND {YEAR_MAX}
    """)

    log('[2b] 国家名 -> ISO3 ...')
    clar2std = load_clar2std(CNTRY_CONVERT)
    names = [r[0] for r in con.execute("SELECT DISTINCT country_raw FROM ar_raw").fetchall()]
    iso_map = build_iso3_map(names, clar2std)
    con.execute("CREATE OR REPLACE TEMP TABLE cmap(country_raw VARCHAR, iso3 VARCHAR)")
    con.executemany("INSERT INTO cmap VALUES (?, ?)", list(iso_map.items()))
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ar AS
        SELECT a.author, a.ost, a.year, m.iso3 AS country
        FROM ar_raw a JOIN cmap m ON a.country_raw = m.country_raw
    """)

    log('[3] 剔除单篇作者 ...')
    con.execute("""
        CREATE OR REPLACE TEMP TABLE multi_authors AS
        SELECT author FROM (SELECT author, count(DISTINCT ost) np FROM ar GROUP BY author) WHERE np >= 2
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ar2 AS
        SELECT a.author, a.year, a.country FROM ar a JOIN multi_authors m USING (author)
    """)

    log('[4] 众数居住国 ...')
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ayc AS
        SELECT author, year, country, count(*) cnt FROM ar2 GROUP BY author, year, country
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE maxc AS
        SELECT author, year, country, cnt FROM (
            SELECT author, year, country, cnt, max(cnt) OVER (PARTITION BY author, year) mx FROM ayc
        ) WHERE cnt = mx
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE nmode AS
        SELECT author, year, count(*) nm, min(country) minc, list(country) cands
        FROM maxc GROUP BY author, year
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE uniq_res AS
        SELECT author, year, minc AS country FROM nmode WHERE nm = 1
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE tie_res AS
        SELECT n.author, n.year,
               CASE WHEN list_contains(n.cands, pv.prev_country) THEN pv.prev_country
                    ELSE list_sort(n.cands)[1] END AS country
        FROM nmode n
        LEFT JOIN LATERAL (
            SELECT u.country AS prev_country FROM uniq_res u
            WHERE u.author = n.author AND u.year < n.year ORDER BY u.year DESC LIMIT 1
        ) pv ON TRUE
        WHERE n.nm > 1
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE residence_obs AS
        SELECT author, year, country FROM uniq_res
        UNION ALL SELECT author, year, country FROM tie_res
    """)

    log('[5] 两年回填 ...')
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE padded AS
        SELECT author, year, country FROM (
            SELECT author, year, country, prio,
                   row_number() OVER (PARTITION BY author, year ORDER BY prio) rn
            FROM (
                SELECT author, (year - yoff) AS year, country, yoff AS prio
                FROM residence_obs, (VALUES (0),(1),(2)) AS t(yoff)
            )
            WHERE year BETWEEN {YEAR_MIN} AND {YEAR_MAX}
        ) WHERE rn = 1
    """)

    log('[6] 迁移事件 ...')
    con.execute("""
        CREATE OR REPLACE TEMP TABLE events AS
        SELECT author, year AS mig_year, prev_c AS origin, country AS dest
        FROM (
            SELECT author, year, country, lag(country) OVER (PARTITION BY author ORDER BY year) prev_c
            FROM padded
        ) WHERE prev_c IS NOT NULL AND prev_c <> country
    """)

    # ---- 诊断 ----
    log(f'[7] 取 {FOCAL_YEAR} 年 {ORIGIN}->{DEST} 迁移作者 ...')
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE mig AS
        SELECT DISTINCT author FROM events
        WHERE mig_year = {FOCAL_YEAR} AND origin = '{ORIGIN}' AND dest = '{DEST}'
    """)
    n_mig = con.execute("SELECT count(*) FROM mig").fetchone()[0]
    print(f'\n==== {FOCAL_YEAR} 年 {ORIGIN}->{DEST} 迁移作者数 = {n_mig:,} ====', flush=True)

    # 这些作者当年(FOCAL_YEAR)带 CHE 地址的 authorship records -> 论文
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE mig_papers AS
        SELECT a.ost, a.author
        FROM ar a JOIN mig m USING (author)
        WHERE a.year = {FOCAL_YEAR} AND a.country = '{DEST}'
    """)
    # 每篇论文摊到多少个迁移作者
    con.execute("""
        CREATE OR REPLACE TEMP TABLE paper_rank AS
        SELECT ost, count(DISTINCT author) AS n_mig_authors
        FROM mig_papers GROUP BY ost
    """)

    # 论文全量作者数(所有国家去重) + 是否含 RUS 地址 + 年份/学科
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE paper_meta AS
        SELECT r.ost, r.n_mig_authors,
               (SELECT count(DISTINCT a2.author) FROM ar a2 WHERE a2.ost = r.ost) AS total_authors,
               (SELECT count(DISTINCT a3.author) FROM ar a3 WHERE a3.ost = r.ost AND a3.country = '{DEST}') AS che_authors,
               EXISTS(SELECT 1 FROM ar a4 WHERE a4.ost = r.ost AND a4.country = '{ORIGIN}') AS has_rus
        FROM paper_rank r
    """)

    print('\n--- Top 20 论文 (摊到的 RUS->CHE 迁移作者数) ---', flush=True)
    print(f'{"UID(ost)":>14} {"mig_auth":>9} {"total_auth":>11} {"che_auth":>9} {"has_RUS":>8}', flush=True)
    for r in con.execute("""
        SELECT ost, n_mig_authors, total_authors, che_authors, has_rus
        FROM paper_meta ORDER BY n_mig_authors DESC LIMIT 20
    """).fetchall():
        print(f'{r[0]:>14} {r[1]:>9,} {r[2]:>11,} {r[3]:>9,} {str(r[4]):>8}', flush=True)

    # 覆盖率: 至少出现在 top-K 论文之一里的迁移作者 / 总迁移作者
    for K in (1, 3, 5, 10):
        cov = con.execute(f"""
            SELECT count(DISTINCT author) FROM mig_papers
            WHERE ost IN (SELECT ost FROM paper_rank ORDER BY n_mig_authors DESC LIMIT {K})
        """).fetchone()[0]
        print(f'  Top-{K:<2} 论文覆盖迁移作者: {cov:,} / {n_mig:,}  = {100*cov/max(n_mig,1):5.1f}%', flush=True)

    # 论文规模分布: 有多少迁移作者来自 >=100 / >=300 作者的超大论文
    for thr in (100, 300, 500):
        cov = con.execute(f"""
            SELECT count(DISTINCT mp.author) FROM mig_papers mp
            JOIN paper_meta pm USING (ost) WHERE pm.total_authors >= {thr}
        """).fetchone()[0]
        print(f'  来自 >= {thr:>3} 作者论文 的迁移作者: {cov:,} / {n_mig:,} = {100*cov/max(n_mig,1):5.1f}%', flush=True)

    con.execute(f"""
        COPY (SELECT ost, n_mig_authors, total_authors, che_authors, has_rus
              FROM paper_meta ORDER BY n_mig_authors DESC)
        TO '{OUT_CSV}' (HEADER, DELIMITER ',')
    """)
    print(f'\n明细已导出: {OUT_CSV}', flush=True)
    con.close()


if __name__ == '__main__':
    main()
