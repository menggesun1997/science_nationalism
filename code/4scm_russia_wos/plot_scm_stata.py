# -*- coding: utf-8 -*-
# 绘制 Stata synth2 的 SCM 结果 (俄罗斯, WoS inflow).
# 可视化从 2008 起 (与估计窗口一致; 2005-07 为冷启动零值, 不展示).
# 供体池按 WoS 数据独立筛选, 不必与 OpenAlex 版国家名单一致.

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402

import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = str(CODE / "4scm_russia_wos")
T0 = 2022
Y0 = 2008  # 图与 pre-MSPE 筛选起点 (同 scm_russia.do 的 mspeperiod)
TRT = "RUS"

rows = []
with open(f"{DIR}/results/scm_russia_frame.csv", newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        rows.append(r)

synth_key = next(k for k in rows[0] if k.startswith("pred"))
gap_key = next(k for k in rows[0] if k.startswith("tr"))
outcome_key = "inflow"


def by_cid(cid):
    g = [r for r in rows if r["cid"] == cid]
    g.sort(key=lambda r: int(r["year"]))
    years = np.array([int(r["year"]) for r in g])
    outcome = np.array([float(r[outcome_key]) for r in g])
    synth = np.array([float(r[synth_key]) for r in g])
    gap = np.array([float(r[gap_key]) for r in g])
    p2 = {int(r["year"]): (float(r["pvalTwo"]) if r["pvalTwo"] else np.nan) for r in g}
    m = years >= Y0
    return years[m], outcome[m], synth[m], gap[m], p2


cids = sorted({r["cid"] for r in rows})
donors = [c for c in cids if c != TRT]

mspe = {}
for c in cids:
    years, _, _, gap, _ = by_cid(c)
    pre = gap[years < T0]
    mspe[c] = float(np.mean(pre ** 2)) if len(pre) else np.inf
rus_mspe = mspe[TRT]
keep = [c for c in donors if mspe[c] <= 20 * rus_mspe]

ry, ro, rs, rg, rp = by_cid(TRT)

fig, ax = plt.subplots(1, 2, figsize=(14, 5.4))

ax[0].plot(ry, ro, "o-", color="#c0392b", lw=2.4, label="Russia (actual)", zorder=5)
ax[0].plot(ry, rs, "s--", color="#2c6fbb", lw=2, label="Synthetic Russia", zorder=5)
ax[0].axvline(T0, color="gray", ls=":", lw=1.2)
ax[0].set_xlim(Y0, ry.max() + 0.5)
ax[0].set_title("SCM: Russia vs Synthetic control (WoS)")
ax[0].set_xlabel("Year")
ax[0].set_ylabel("Scholar inflow (in-migrations, persons)")
ax[0].legend()
ax[0].grid(alpha=0.25)

for c in keep:
    gy, _, _, gg, _ = by_cid(c)
    ax[1].plot(gy, gg, color="0.75", lw=0.8, alpha=0.7, zorder=2)
ax[1].plot(ry, rg, color="#c0392b", lw=2.6, label="Russia", zorder=5)
ax[1].axvline(T0, color="gray", ls=":", lw=1.2)
ax[1].axhline(0, color="black", lw=0.6, alpha=0.4)
ax[1].set_xlim(Y0, ry.max() + 0.5)
ax[1].set_title(f"In-space placebo gaps (donors with pre-MSPE \u2264 20\u00d7RUS, n={len(keep)})")
ax[1].set_xlabel("Year")
ax[1].set_ylabel("Gap: actual \u2212 synthetic (persons)")
ax[1].legend()
ax[1].grid(alpha=0.25)

post = rg[ry >= T0]
g2023 = float(rg[ry == 2023][0])
p2023 = rp.get(2023, np.nan)
txt = (f"ATT 2022-24 mean = {post.mean():,.0f}\n"
       f"2023 effect = {g2023:,.0f}\n"
       f"placebo p (2-sided, 2023) = {p2023:.3f}")
ax[1].text(0.03, 0.05, txt, transform=ax[1].transAxes, fontsize=9,
           va="bottom", bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="0.8"))

fig.suptitle("Synthetic Control Method \u2014 2022 invasion effect on Russian scholar "
             "inflow (WoS / MPIDR-replication, Stata synth2, from 2008)",
             y=1.02, fontsize=12.5)
fig.tight_layout()
for name in ["scm_russia_stata", "scm_russia_panel"]:
    for ext in ["png", "pdf"]:
        fig.savefig(f"{DIR}/results/{name}.{ext}", dpi=200, bbox_inches="tight")
print("saved:", f"{DIR}/results/scm_russia_panel.png")
print(f"ATT mean = {post.mean():.1f}; 2023 gap = {g2023:.1f}, p2={p2023}")
print(f"pre RMSPE RUS (from {Y0}) = {np.sqrt(rus_mspe):.1f}; donors kept = {len(keep)}")
