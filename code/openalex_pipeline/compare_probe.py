"""Probe the official SMD 2.0 OpenAlex country parquet: list files, schema, sample."""
import glob
import os
import pandas as pd

pd.set_option("display.max_columns", 200)
pd.set_option("display.width", 200)

ROOT = r"C:\Users\91916\Dropbox\GitHub\sicence nationism\migration_data"

print("=== all parquet files under migration_data ===")
for p in glob.glob(os.path.join(ROOT, "**", "*.parquet"), recursive=True):
    print(f"  {os.path.getsize(p)/1e6:8.2f} MB  {p}")

# the country-level official file
cands = glob.glob(os.path.join(ROOT, "**", "*country*.parquet"), recursive=True)
print("\n=== country-level candidates ===")
for c in cands:
    print("  ", c)

if cands:
    f = cands[0]
    print(f"\n=== reading: {f} ===")
    df = pd.read_parquet(f)
    print("shape:", df.shape)
    print("\ncolumns & dtypes:")
    print(df.dtypes)
    print("\nhead:")
    print(df.head(8).to_string())
    # try to find year / country / migration columns
    print("\nunique years (if any):")
    for col in df.columns:
        lc = col.lower()
        if "year" in lc:
            print("  ", col, sorted(df[col].dropna().unique())[:30])
