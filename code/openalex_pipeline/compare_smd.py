"""Consistency / correlation analysis: my self-built OpenAlex migration data
vs. official SMD 2.0 OpenAlex country file.

Aligns on gender=all & field=all, ISO2 country code, and year (2005-2024),
then computes correlations for stock / inmigration / outmigration and plots.
"""
import os
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = r"C:\Users\91916\Dropbox\GitHub\sicence nationism"
PIPE = os.path.join(BASE, "migration_data", "openalex_pipeline")
MINE = os.path.join(PIPE, "results", "openalex_country_year_2005_2024.csv")
OFF = os.path.join(BASE, "migration_data",
                   "Global-flows-and-rates-of-international-migration-of-scholars-2026_V2",
                   "2026_V2", "openalex_2026_V2_scholarlymigration_country.parquet")
OUTDIR = os.path.join(PIPE, "results")
os.makedirs(OUTDIR, exist_ok=True)

# ---- load mine ----
mine = pd.read_csv(MINE)
mine = mine.rename(columns={
    "country": "iso2code",
    "n_researchers": "mine_pop",
    "inmigration": "mine_in",
    "outmigration": "mine_out",
    "netmigration": "mine_net",
})
mine = mine[["year", "iso2code", "mine_pop", "mine_in", "mine_out", "mine_net"]]

# ---- load official, filter to totals ----
off = pd.read_parquet(OFF)
off = off[(off["gender"] == "all") & (off["field"] == "all")].copy()
off = off.rename(columns={
    "padded_population_of_researchers": "off_pop",
    "number_of_inmigrations": "off_in",
    "number_of_outmigrations": "off_out",
    "netmigration": "off_net",
})
off = off[["year", "iso2code", "off_pop", "off_in", "off_out", "off_net"]]

print("mine rows:", len(mine), "| official(all,all) rows:", len(off))

# ---- merge on year + iso2 (2006-2024, drop 2005 baseline where in/out=0) ----
m = mine.merge(off, on=["year", "iso2code"], how="inner")
m = m[m["year"] >= 2006]
print("merged rows (2006-2024):", len(m),
      "| countries:", m["iso2code"].nunique(),
      "| years:", m["year"].min(), "-", m["year"].max())


def corr_block(a, b, label):
    x = m[a].astype(float)
    y = m[b].astype(float)
    ok = x.notna() & y.notna()
    x, y = x[ok], y[ok]
    pear = stats.pearsonr(x, y)[0]
    spear = stats.spearmanr(x, y)[0]
    # log-log pearson (add 1)
    lp = stats.pearsonr(np.log1p(x), np.log1p(y))[0]
    print(f"\n[{label}]  n={len(x)}")
    print(f"  Pearson r      = {pear:.4f}")
    print(f"  Spearman rho   = {spear:.4f}")
    print(f"  log-log Pearson= {lp:.4f}")
    return pear, spear, lp


print("\n===== correlations: mine vs official =====")
corr_block("mine_pop", "off_pop", "researcher stock")
corr_block("mine_in", "off_in", "inmigration")
corr_block("mine_out", "off_out", "outmigration")
corr_block("mine_net", "off_net", "netmigration")

# ---- per-country stock correlation (time series shape) ----
print("\n===== per-country stock Pearson (top/bottom) =====")
rows = []
for c, g in m.groupby("iso2code"):
    if len(g) >= 10 and g["mine_pop"].std() > 0 and g["off_pop"].std() > 0:
        r = stats.pearsonr(g["mine_pop"], g["off_pop"])[0]
        rows.append((c, len(g), r))
cc = pd.DataFrame(rows, columns=["iso2", "n", "pearson"]).sort_values("pearson")
print("median per-country stock r:", round(cc["pearson"].median(), 4),
      "| mean:", round(cc["pearson"].mean(), 4))
print("worst 8:\n", cc.head(8).to_string(index=False))
print("best 8:\n", cc.tail(8).to_string(index=False))

# ---- scatter plots (log-log) ----
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, (a, b, t) in zip(axes, [
    ("mine_pop", "off_pop", "Researcher stock"),
    ("mine_in", "off_in", "Inmigration"),
    ("mine_out", "off_out", "Outmigration"),
]):
    x = m[a].astype(float) + 1
    y = m[b].astype(float) + 1
    ax.scatter(x, y, s=6, alpha=0.25, edgecolors="none")
    lim = [1, max(x.max(), y.max())]
    ax.plot(lim, lim, "r--", lw=1, label="y=x")
    ax.set_xscale("log"); ax.set_yscale("log")
    r = stats.pearsonr(np.log1p(m[a]), np.log1p(m[b]))[0]
    ax.set_title(f"{t}\nlog-log Pearson={r:.3f}")
    ax.set_xlabel("Mine (self-built OpenAlex)")
    ax.set_ylabel("Official SMD 2.0 OpenAlex")
    ax.legend(loc="upper left", fontsize=8)
plt.tight_layout()
figpath = os.path.join(OUTDIR, "compare_mine_vs_smd.png")
plt.savefig(figpath, dpi=130)
print("\nsaved figure:", figpath)

# ---- save merged table for inspection ----
m.to_csv(os.path.join(OUTDIR, "merged_mine_vs_smd.csv"), index=False)
print("saved merged table:", os.path.join(OUTDIR, "merged_mine_vs_smd.csv"))
