"""
忠实复刻 MPIDR (Scholarly Migration Database) 的迁移测量算法, 应用于本项目的 WoS/OST 数据。

参考: Akbaritabar, Theile & Zagheni (2024) "Bilateral flows and rates of international
migration of scholars for 210 countries for the period 1998-2020", Scientific Data 11, 816.
https://doi.org/10.1038/s41597-024-03655-9 (Methods 节)

与之前的 6article_author_processing.py (allflows + 笛卡尔积) 不同, 本脚本严格按 MPIDR 口径:

  (1) 范围: 仅 Article/Review (上游已过滤); 仅作者机构地址; 作者需被消歧 (cluster_id)。
  (2) 单篇剔除: 整个生涯只有 1 篇论文的作者, 既不计入分母, 也不可能迁移 -> 直接剔除。
  (3) 众数居住国 (mode-based): 每个 (作者, 年), 取该年出现在最多"不同论文"中的国家。
        计票单位为不同论文数 (count(DISTINCT 论文)), 同一篇论文内同一国家的多个地址
        (如 中国-1/中国-2) 只算 1 票, 避免篇内重复地址系统性拉偏众数。
        - 众数并列时: 优先选 = 上一(已确定)居住国 的候选; 否则取字母序最小者。
          [MPIDR 原文此处为"随机", 我们改为确定性取字母序最小, 以保证可复现; 这是唯一的细微偏离。]
  (4) 两年回填 (backward fill): 论文发表存在滞后, 一篇 Y 年、众数国 C 的记录,
        将 Y-1, Y-2 两个空缺年也填为 C (本人当年有观测的年份优先, 距离近的回填优先)。
        => 迁移因此被"提前两年"判定, 与 MPIDR 的 padded population 及迁移年定义一致。
  (5) 迁移事件: 沿每个作者填充后的居住序列, 众数国家发生变化的那一年记一次迁移
        (origin=旧国, dest=新国, 迁移年=新国首次出现的填充年)。
  (6) 分母 N_{i,t}: 某国某年填充后的活跃学者数 (已剔除单篇作者)。
  (7) 指标: EMR=E/N, IMR=I/N, NM=I-E, NMR=(I-E)/N; 双边流按 (origin, dest, year) 汇总迁移作者数。

注意: "完全一致" 指算法一致; 底层数据库不同 (WoS vs Scopus/OpenAlex), 故最终需用
      8validate_against_mpidr.py 在重叠期与 MPIDR 公开数据做相关性校验来证明一致性。

数据 schema:
  article_author_cntry_brexit.txt : OST_BK|UID|cluster_id|author_seq|Addr_No|Pays   (~1.99 亿行)
  article_brexit.txt              : OST_BK|UID|Annee_Bibliographique|Code_Discipline|Cit_ALL_iac (~3260 万行)
  其中 Pays 为国家全称 (大写, 如 RUSSIAN FEDERATION / UNITED KINGDOM / UKRAINE)。
"""

import os
import time
import duckdb

# ---------------------------------------------------------------------------
# 国家名标准化 -> ISO3。两段式, 与本项目其它分析保持口径一致:
#   (1) Clarivate/WoS 原始名 -> 标准 Country 名: 用项目既有的 cntry_convert 映射
#       (与 0process.py 一致)。该表已把 ENGLAND/SCOTLAND/WALES/NORTH-IRELAND 及一众
#       英属领地、海峡群岛等并入 "United Kingdom", USSR->Russia, HONG-KONG/MACAO->China,
#       从而保证英国等口径统一, 也与 MPIDR 的 GBR 对齐。
#   (2) 标准 Country 名 -> ISO3: 用下方手工覆盖(pycountry 易错的) + pycountry 模糊匹配兜底。
# ---------------------------------------------------------------------------
# Clarivate->标准名 映射文件 (由 cntry_convert.xlsx 导出的两列 csv: Clarivate country, Country)
CNTRY_CONVERT = os.environ.get(
    'SCI_CNTRY_CONVERT',
    '/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw data processing/cntry_convert.csv')

# 标准 Country 名 -> ISO3: 仅覆盖 pycountry 容易认错/认不出的 (尤其 Turkey 在新版 pycountry 模糊匹配会失败)
STD2ISO3 = {
    'United Kingdom': 'GBR', 'United States': 'USA', 'Russia': 'RUS', 'China': 'CHN',
    'South Korea': 'KOR', 'North Korea': 'PRK', 'Turkey': 'TUR', 'Iran': 'IRN',
    'Vietnam': 'VNM', 'Czechia': 'CZE', 'Czech Republic': 'CZE', 'Kosovo': 'XKX',
    'Taiwan': 'TWN', 'Hong Kong': 'HKG', 'Macao': 'MAC', 'Syria': 'SYR', 'Laos': 'LAO',
    'Moldova': 'MDA', 'Bolivia': 'BOL', 'Venezuela': 'VEN', 'Tanzania': 'TZA',
    'Brunei': 'BRN', 'Swaziland': 'SWZ', 'Cape Verde': 'CPV', 'East Timor': 'TLS',
    # --- cntry_convert 标准名中 pycountry 无法识别的写法 ---
    'Byelarus': 'BLR', 'Ivory Coast': 'CIV', 'Burma': 'MMR', 'Republic of Kosovo': 'XKX',
    'Serbia and Montenegro': 'SRB', 'Bosnia & Herzegovina': 'BIH', 'Antigua & Barbuda': 'ATG',
    'Netherlands-Antilles': 'ANT', 'New-Caledonia': 'NCL', 'French-Polynesia': 'PYF',
    'French-Guiana': 'GUF', 'St-Lucia': 'LCA', 'St-Kitts & Nevis': 'KNA',
    'Sao Tome & Principe': 'STP', 'Saint-Vincent-et-les-Grenadines': 'VCT',
    # --- 不在 cntry_convert 表中的原始名(保持原大写形式) ---
    'SINT-MAARTEN': 'SXM', 'ST-MARTIN': 'MAF',
}
# 无意义/无法归属 -> 丢弃
DROP_STD = {'Antarctica'}


def load_clar2std(path):
    """读取 cntry_convert (csv): 返回 {CLARIVATE名(大写): 标准Country名}。"""
    import pandas as pd
    df = pd.read_csv(path)
    df = df[['Clarivate country', 'Country']].dropna(subset=['Clarivate country'])
    return {str(k).strip().upper(): str(v).strip()
            for k, v in zip(df['Clarivate country'], df['Country'])}


def build_iso3_map(country_names, clar2std):
    """数据中出现的(大写)国家名 -> ISO3。先经 cntry_convert 标准化, 再到 ISO3。"""
    try:
        import pycountry
    except Exception:
        pycountry = None
    mapping, unmapped = {}, []
    for name in country_names:
        std = clar2std.get(name, name)          # (1) Clarivate -> 标准名 (缺失则保留原名)
        if std in DROP_STD:
            unmapped.append(name)
            continue
        iso = STD2ISO3.get(std)                 # (2) 标准名 -> ISO3 (手工覆盖优先)
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
    if unmapped:
        print(f'      [国家映射] 未能映射(将丢弃, 多为微型地区/历史实体): {len(unmapped)} 个 -> {unmapped}', flush=True)
    return mapping

# 路径可用环境变量覆盖, 方便在服务器上运行 (默认指向本地 Mac 路径)
BASE = os.environ.get(
    'SCI_DATA_DIR',
    '/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw_data_2026')
AUTHOR_FILE = os.path.join(BASE, 'article_author_cntry_brexit.txt')
PAPER_FILE = os.path.join(BASE, 'article_brexit.txt')

OUT_DIR = os.environ.get(
    'SCI_OUT_DIR',
    '/Users/sunmengge/Dropbox/GitHub/sicence nationism/code/0raw_publiations_process/raw data processing/migration_output_mpidr')
os.makedirs(OUT_DIR, exist_ok=True)

FLOWS_CSV = os.path.join(OUT_DIR, 'mpidr_country_flows.csv')         # from_country, to_country, year, n_migrations
MEASURES_CSV = os.path.join(OUT_DIR, 'mpidr_country_measures.csv')   # country, year, population, inmig, outmig, netmig, imr, emr, nmr
RESIDENCE_CSV = os.path.join(OUT_DIR, 'mpidr_padded_residence_sample.csv')  # 抽样, 供人工检查回填逻辑

# 分析年份窗口 (本项目 WoS 数据 2005-2024; 头尾两年因左/右删失需谨慎解读)
YEAR_MIN = 2005
YEAR_MAX = 2024

TMP_DIR = os.path.join(OUT_DIR, 'duckdb_tmp')
os.makedirs(TMP_DIR, exist_ok=True)


def main():
    t0 = time.time()
    con = duckdb.connect()
    con.execute(f"PRAGMA temp_directory='{TMP_DIR}'")
    con.execute(f"PRAGMA memory_limit='{os.environ.get('SCI_DUCKDB_MEM', '12GB')}'")
    con.execute(f"PRAGMA threads={os.environ.get('SCI_DUCKDB_THREADS', '4')}")
    con.execute("PRAGMA preserve_insertion_order=false")

    def log(msg):
        print(f'[{time.time()-t0:6.0f}s] {msg}', flush=True)

    # ------------------------------------------------------------------
    # [1] 文章 -> 年份
    # ------------------------------------------------------------------
    log('[1/8] 读取文章年份表 ...')
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE papers AS
        SELECT CAST(OST_BK AS BIGINT) AS OST_BK,
               CAST(Annee_Bibliographique AS INTEGER) AS year
        FROM read_csv_auto('{PAPER_FILE}', delim='|', header=true,
                           types={{'OST_BK':'BIGINT','Annee_Bibliographique':'INTEGER'}})
        WHERE Annee_Bibliographique IS NOT NULL
    """)

    # ------------------------------------------------------------------
    # [2] authorship records: (author, paper, year, country) —— 保留重复以便取众数
    #     country 统一为大写去空白的全称
    # ------------------------------------------------------------------
    log('[2/8] 关联作者-国家, 构建 authorship records (原始国家名) ...')
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE ar_raw AS
        SELECT a.cluster_id            AS author,
               a.OST_BK                AS ost,
               p.year                  AS year,
               upper(trim(a.Pays))     AS country_raw
        FROM read_csv_auto('{AUTHOR_FILE}', delim='|', header=true,
                           types={{'OST_BK':'BIGINT','cluster_id':'BIGINT','Pays':'VARCHAR'}}) a
        JOIN papers p USING (OST_BK)
        WHERE a.cluster_id IS NOT NULL
          AND a.Pays IS NOT NULL AND trim(a.Pays) <> ''
          AND p.year BETWEEN {YEAR_MIN} AND {YEAR_MAX}
    """)

    # 国家名 -> ISO3 (经 cntry_convert 标准化, 英国四地合并为 GBR; 与 MPIDR 对齐)
    log('[2b/8] 构建 国家名->ISO3 映射并标准化 (cntry_convert) ...')
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

    # ------------------------------------------------------------------
    # [3] 单篇剔除: 仅保留整个生涯 >= 2 篇不同论文的作者
    # ------------------------------------------------------------------
    log('[3/8] 剔除单篇作者 ...')
    con.execute("""
        CREATE OR REPLACE TEMP TABLE multi_authors AS
        SELECT author
        FROM (SELECT author, count(DISTINCT ost) AS np FROM ar GROUP BY author)
        WHERE np >= 2
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ar2 AS
        SELECT a.author, a.ost, a.year, a.country
        FROM ar a JOIN multi_authors m USING (author)
    """)

    # ------------------------------------------------------------------
    # [4] 众数居住国 (mode), 含并列处理
    # ------------------------------------------------------------------
    log('[4/8] 计算每个(作者,年)的众数居住国 ...')
    # 每个 (author, year, country) 的计数, 以"不同论文数"为单位:
    # 同一篇论文里同一国家的多个地址(如 中国-1/中国-2)只算 1 票, 避免篇内多地址
    # 对众数居住国的系统性拉偏 (不同国家挂多个本国地址的倾向不同, 属有方向的偏差)。
    con.execute("""
        CREATE OR REPLACE TEMP TABLE ayc AS
        SELECT author, year, country, count(DISTINCT ost) AS cnt
        FROM ar2 GROUP BY author, year, country
    """)
    # 仅保留达到该(作者,年)最大计数的候选国
    con.execute("""
        CREATE OR REPLACE TEMP TABLE maxc AS
        SELECT author, year, country, cnt
        FROM (
            SELECT author, year, country, cnt,
                   max(cnt) OVER (PARTITION BY author, year) AS mx
            FROM ayc
        )
        WHERE cnt = mx
    """)
    # 每个(作者,年): 候选数 nm + 候选列表 cands + 字母序最小 minc
    con.execute("""
        CREATE OR REPLACE TEMP TABLE nmode AS
        SELECT author, year,
               count(*)        AS nm,
               min(country)    AS minc,
               list(country)   AS cands
        FROM maxc GROUP BY author, year
    """)
    # 唯一众数年 (骨干)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE uniq_res AS
        SELECT author, year, minc AS country FROM nmode WHERE nm = 1
    """)
    # 并列年: 用上一个"唯一众数年"的居住国做 tie-break, 否则取字母序最小
    #   (相关子查询取该作者最近的更早唯一众数年; 引用其它并列年的情况极少, 可接受)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE tie_res AS
        SELECT n.author, n.year,
               CASE WHEN list_contains(n.cands, pv.prev_country) THEN pv.prev_country
                    ELSE list_sort(n.cands)[1] END AS country
        FROM nmode n
        LEFT JOIN LATERAL (
            SELECT u.country AS prev_country
            FROM uniq_res u
            WHERE u.author = n.author AND u.year < n.year
            ORDER BY u.year DESC LIMIT 1
        ) pv ON TRUE
        WHERE n.nm > 1
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE residence_obs AS
        SELECT author, year, country FROM uniq_res
        UNION ALL
        SELECT author, year, country FROM tie_res
    """)

    # ------------------------------------------------------------------
    # [5] 两年回填 (backward fill): 每个观测年 Y 向 Y-1, Y-2 回填
    #     prio: 0=本人当年观测 (优先), 1=回填自 Y+1, 2=回填自 Y+2
    # ------------------------------------------------------------------
    log('[5/8] 两年回填, 构建居住面板 ...')
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE padded AS
        SELECT author, year, country
        FROM (
            SELECT author, year, country, prio,
                   row_number() OVER (PARTITION BY author, year ORDER BY prio) AS rn
            FROM (
                SELECT author, (year - yoff) AS year, country, yoff AS prio
                FROM residence_obs, (VALUES (0),(1),(2)) AS t(yoff)
            )
            WHERE year BETWEEN {YEAR_MIN} AND {YEAR_MAX}
        )
        WHERE rn = 1
    """)

    # 抽样导出居住面板供人工核查 (前若干作者)
    con.execute(f"""
        COPY (
            SELECT * FROM padded
            WHERE author IN (SELECT author FROM padded GROUP BY author HAVING count(*) >= 4 LIMIT 200)
            ORDER BY author, year
        ) TO '{RESIDENCE_CSV}' (HEADER, DELIMITER ',')
    """)

    # ------------------------------------------------------------------
    # [6] 迁移事件: 居住序列中众数国变化 -> 一次迁移 (按新国出现年)
    # ------------------------------------------------------------------
    log('[6/8] 识别迁移事件 ...')
    con.execute("""
        CREATE OR REPLACE TEMP TABLE events AS
        SELECT author, year AS mig_year, prev_c AS origin, country AS dest
        FROM (
            SELECT author, year, country,
                   lag(country) OVER (PARTITION BY author ORDER BY year) AS prev_c
            FROM padded
        )
        WHERE prev_c IS NOT NULL AND prev_c <> country
    """)

    # ------------------------------------------------------------------
    # [7] 聚合: 双边流 + 国家年度指标
    # ------------------------------------------------------------------
    log('[7/8] 聚合双边流与国家年度指标 ...')
    con.execute("""
        CREATE OR REPLACE TEMP TABLE pop AS
        SELECT country, year, count(DISTINCT author) AS population
        FROM padded GROUP BY country, year
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE emig AS
        SELECT origin AS country, mig_year AS year, count(DISTINCT author) AS outmig
        FROM events GROUP BY origin, mig_year
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE immig AS
        SELECT dest AS country, mig_year AS year, count(DISTINCT author) AS inmig
        FROM events GROUP BY dest, mig_year
    """)

    # ------------------------------------------------------------------
    # [8] 导出
    # ------------------------------------------------------------------
    log('[8/8] 导出 CSV ...')
    con.execute(f"""
        COPY (
            SELECT origin AS from_country, dest AS to_country, mig_year AS year,
                   count(DISTINCT author) AS n_migrations
            FROM events
            GROUP BY origin, dest, mig_year
            ORDER BY year, n_migrations DESC
        ) TO '{FLOWS_CSV}' (HEADER, DELIMITER ',')
    """)
    con.execute(f"""
        COPY (
            SELECT p.country, p.year,
                   p.population,
                   COALESCE(i.inmig, 0)  AS inmig,
                   COALESCE(e.outmig, 0) AS outmig,
                   COALESCE(i.inmig, 0) - COALESCE(e.outmig, 0) AS netmig,
                   COALESCE(i.inmig, 0)::DOUBLE / NULLIF(p.population, 0) AS imr,
                   COALESCE(e.outmig, 0)::DOUBLE / NULLIF(p.population, 0) AS emr,
                   (COALESCE(i.inmig, 0) - COALESCE(e.outmig, 0))::DOUBLE / NULLIF(p.population, 0) AS nmr
            FROM pop p
            LEFT JOIN immig i ON i.country = p.country AND i.year = p.year
            LEFT JOIN emig  e ON e.country = p.country AND e.year = p.year
            ORDER BY p.country, p.year
        ) TO '{MEASURES_CSV}' (HEADER, DELIMITER ',')
    """)

    # ---- 控制台快报 ----
    n_events = con.execute("SELECT count(*) FROM events").fetchone()[0]
    log(f'迁移事件总数: {n_events:,}')
    print('\n--- 跨年 Top 15 迁移走廊 (作者去重) ---', flush=True)
    for r in con.execute("""
        SELECT origin, dest, count(DISTINCT author) AS n
        FROM events GROUP BY origin, dest ORDER BY n DESC LIMIT 15
    """).fetchall():
        print(f'  {r[0]:>22} -> {r[1]:<22}  authors={r[2]:>8,}', flush=True)

    print('\n--- 俄/乌/英 逐年净迁移 (检查信号) ---', flush=True)
    for r in con.execute("""
        SELECT country, year, population, inmig, outmig, netmig, round(nmr,4) AS nmr
        FROM (
            SELECT p.country, p.year, p.population,
                   COALESCE(i.inmig,0) inmig, COALESCE(e.outmig,0) outmig,
                   COALESCE(i.inmig,0)-COALESCE(e.outmig,0) netmig,
                   (COALESCE(i.inmig,0)-COALESCE(e.outmig,0))::DOUBLE/NULLIF(p.population,0) nmr
            FROM pop p
            LEFT JOIN immig i ON i.country=p.country AND i.year=p.year
            LEFT JOIN emig e ON e.country=p.country AND e.year=p.year
        )
        WHERE country IN ('RUS','UKR','GBR') AND year >= 2018
        ORDER BY country, year
    """).fetchall():
        print(f'  {r[0]:>20} {r[1]}  N={r[2]:>8,}  in={r[3]:>6,} out={r[4]:>6,} net={r[5]:>6,} nmr={r[6]}', flush=True)

    log('完成')
    print(f'\n  双边流  : {FLOWS_CSV}')
    print(f'  国家指标: {MEASURES_CSV}')
    print(f'  居住面板抽样: {RESIDENCE_CSV}')
    con.close()


if __name__ == '__main__':
    main()
