import pandas as pd
from collections import Counter, defaultdict

path = r"C:\Users\91916\Dropbox\GitHub\sicence nationism\code\00_data_processing\eu_articles\eu_articles.txt"

TARGET = "FRANCE"

# 国名清洗
ALIASES = {
    "CZECH REPUBLIC": "CZECHIA", "SLOVAKIA": "SLOVAK REPUBLIC",
    "FRENCH-POLYNESIA": "FRANCE", "GUADELOUPE": "FRANCE",
    "FRENCH-GUIANA": "FRANCE", "SERBIA AND MONTENEGRO": "REPUBLIC OF SERBIA",
    "BYELARUS": "BELARUS", "IRAN, ISLAMIC REP.": "IRAN",
    "KOREA, REP.": "SOUTH KOREA", "UK": "UNITED KINGDOM",
    "GREAT BRITAIN": "UNITED KINGDOM", "ENGLAND": "UNITED KINGDOM",
    "SCOTLAND": "UNITED KINGDOM", "WALES": "UNITED KINGDOM",
    "NORTHERN IRELAND": "UNITED KINGDOM", "NORTH-IRELAND": "UNITED KINGDOM",
}
SPECIAL_SUFFIXES = ("REP.", "ISLAMIC REP.")


def parse_countries(s: str) -> list[str]:
    """split 后修复含逗号的国名、统一大写并做别名归并。"""
    if not s:
        return []
    parts = [p.strip().upper() for p in s.split(",")]
    out, i = [], 0
    while i < len(parts):
        p = parts[i]
        if not p or p == "NAN":
            i += 1
            continue
        if i + 1 < len(parts) and parts[i + 1] in SPECIAL_SUFFIXES:
            p = f"{p}, {parts[i + 1]}"
            i += 2
        else:
            i += 1
        out.append(ALIASES.get(p, p))
    return out

# 文件约 890 万行，分块读取避免内存爆掉
partner_counts = Counter()                       # 伙伴国 -> 与 France 共同发文总量
partner_year = defaultdict(Counter)              # 伙伴国 -> {年份 -> 共同发文量}
france_year = Counter()                           # 年份 -> France 发文量
france_total = 0                                  # France 参与的文章总数

for chunk in pd.read_csv(
    path, usecols=["Annee_Bibliographique", "countries"], chunksize=200_000
):
    for year, cell in zip(chunk["Annee_Bibliographique"], chunk["countries"]):
        if pd.isna(cell):
            continue
        countries = set(parse_countries(str(cell)))   # 清洗 + 去重
        if TARGET not in countries:
            continue
        france_total += 1
        france_year[year] += 1
        for c in countries:                            # 计伙伴国
            if c != TARGET:
                partner_counts[c] += 1
                partner_year[c][year] += 1

print(f"France 参与的文章总数: {france_total:,}\n")

print("France 逐年发文量:")
for year in sorted(france_year):
    print(f"  {int(year)}: {france_year[year]:,}")

top10 = [c for c, _ in partner_counts.most_common(10)]
print("\n与 France 合作发文量前 10 的国家:")
for rank, country in enumerate(top10, 1):
    print(f"{rank:>2}. {country:<20} {partner_counts[country]:,}")

# Top10 伙伴国逐年共同发文量，导出为宽表
years = sorted(france_year)
table = pd.DataFrame(
    {country: [partner_year[country].get(y, 0) for y in years] for country in top10},
    index=[int(y) for y in years],
)
table.index.name = "year"
print("\nTop10 合作国逐年共同发文量:")
print(table.to_string())

out_csv = "france_top10_by_year.csv"
table.to_csv(out_csv)
print(f"\n已保存: {out_csv}")

# 比例：各伙伴国共同发文量 / France 当年总发文量
france_year_series = pd.Series(
    {int(y): france_year[y] for y in years}, name="france_total"
)
ratio = table.div(france_year_series, axis=0)
print("\nTop10 合作国逐年合作比例 (共同发文量 / France 当年总发文量):")
print(ratio.to_string(float_format="%.4f"))

ratio_csv = "france_top10_ratio_by_year.csv"
ratio.to_csv(ratio_csv)
print(f"\n已保存: {ratio_csv}")
