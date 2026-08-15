# Build scm_panel.csv for Russia SCM from WoS MPIDR-replication measures.
# Donor pool is selected independently on WoS data (need NOT match OpenAlex list).
# Rules (same logic, own sample):
#   pre (2005-2021) mean population in [1/5, 5x] of RUS;
#   mean |netmig| >= 50; exclude UKR/BLR.
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "0raw_publiations_process" / "raw data processing" / "migration_output_mpidr" / "mpidr_country_measures.csv"
OUT = ROOT / "scm_panel.csv"

rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
by = defaultdict(list)
for r in rows:
    by[r["country"]].append({
        "country": r["country"], "year": int(r["year"]),
        "population": float(r["population"]),
        "inmig": float(r["inmig"]), "outmig": float(r["outmig"]), "netmig": float(r["netmig"]),
    })
for c in by:
    by[c].sort(key=lambda x: x["year"])


def pre(c):
    return [x for x in by[c] if 2005 <= x["year"] <= 2021]


rus_pop = st.mean([x["population"] for x in pre("RUS")])
lo, hi = rus_pop / 5, rus_pop * 5
exclude = {"UKR", "BLR"}
keep = {"RUS"}
for c in by:
    if c in exclude or c == "RUS":
        continue
    p = pre(c)
    if len(p) < 17:
        continue
    mp = st.mean([x["population"] for x in p])
    mn = st.mean([abs(x["netmig"]) for x in p])
    if lo <= mp <= hi and mn >= 50:
        keep.add(c)

panel = []
for c in sorted(keep):
    m = {x["year"]: x for x in by[c]}
    for y in range(2005, 2025):
        x = m[y]
        panel.append({
            "country": c, "year": y,
            "netmigration": int(x["netmig"]),
            "number_of_inmigrations": int(x["inmig"]),
            "number_of_outmigrations": int(x["outmig"]),
            "researchers": int(x["population"]),
        })

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(panel[0].keys()))
    w.writeheader()
    w.writerows(panel)

print(f"wrote {OUT} | units={len(keep)} donors={len(keep)-1}")
print("countries:", ", ".join(sorted(keep)))
