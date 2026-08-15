# -*- coding: utf-8 -*-
# 绘制 Stata synth2 的 SCM 结果 (乌克兰, inflow).
# 左图路径 + AVG EFFECT: nested 主估计
# 右图 placebo gaps + MSPE-ratio p: placebo 步

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
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

DIR = str(CODE / "4scm_ukraine_openalex")
T0 = 2022
TRT = "UKR"
NESTED_FRAME = f"{DIR}/results/scm_ukraine_nested_frame.csv"
PLACEBO_FRAME = f"{DIR}/results/scm_ukraine_frame.csv"


def load_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def keys(rows):
    synth_key = next(k for k in rows[0] if k.startswith("pred"))
    gap_key = next(k for k in rows[0] if k.startswith("tr"))
    return synth_key, gap_key


def by_cid(rows, cid, synth_key, gap_key, outcome_key="inflow"):
    g = [r for r in rows if r["cid"] == cid]
    g.sort(key=lambda r: int(r["year"]))
    years = np.array([int(r["year"]) for r in g])
    outcome = np.array([float(r[outcome_key]) for r in g])
    synth = np.array([float(r[synth_key]) for r in g])
    gap = np.array([float(r[gap_key]) for r in g])
    return years, outcome, synth, gap


placebo_rows = load_rows(PLACEBO_FRAME)
nested_rows = load_rows(NESTED_FRAME)
p_synth, p_gap = keys(placebo_rows)
n_synth, n_gap = keys(nested_rows)

cids = sorted({r["cid"] for r in placebo_rows})
donors = [c for c in cids if c != TRT]

pre_mspe, post_mspe = {}, {}
for c in cids:
    years, _, _, gap = by_cid(placebo_rows, c, p_synth, p_gap)
    pre_mspe[c] = float(np.mean(gap[years < T0] ** 2))
    post_mspe[c] = float(np.mean(gap[years >= T0] ** 2))
trt_mspe = pre_mspe[TRT]
keep = [c for c in donors if pre_mspe[c] <= 5 * trt_mspe]

ratio = {c: post_mspe[c] / pre_mspe[c] if pre_mspe[c] > 0 else np.nan for c in cids}
trt_ratio = ratio[TRT]
p_mspe = sum(1 for c in cids if ratio[c] >= trt_ratio) / len(cids)

ry, ro, rs, rg = by_cid(nested_rows, TRT, n_synth, n_gap)
avg_effect = float(np.mean(rg[ry >= T0]))

fig, ax = plt.subplots(1, 2, figsize=(14, 5.4))

ax[0].plot(ry, ro, "o-", color="#c0392b", lw=2.4, label="Ukraine (actual)", zorder=5)
ax[0].plot(ry, rs, "s--", color="#2c6fbb", lw=2, label="Synthetic Ukraine", zorder=5)
ax[0].axvline(T0, color="gray", ls=":", lw=1.2)
ax[0].set_title("SCM: Ukraine vs Synthetic control (nested)")
ax[0].set_xlabel("Year")
ax[0].set_ylabel("Scholar inflow (in-migrations, persons)")
ax[0].legend()
ax[0].grid(alpha=0.25)

for c in keep:
    gy, _, _, gg = by_cid(placebo_rows, c, p_synth, p_gap)
    ax[1].plot(gy, gg, color="0.75", lw=0.8, alpha=0.7, zorder=2)
_, _, _, rg_p = by_cid(placebo_rows, TRT, p_synth, p_gap)
gy, _, _, _ = by_cid(placebo_rows, TRT, p_synth, p_gap)
ax[1].plot(gy, rg_p, color="#c0392b", lw=2.6, label="Ukraine", zorder=5)
ax[1].axvline(T0, color="gray", ls=":", lw=1.2)
ax[1].axhline(0, color="black", lw=0.6, alpha=0.4)
ax[1].set_title(f"In-space placebo gaps (donors with pre-MSPE \u2264 5\u00d7UKR, n={len(keep)})")
ax[1].set_xlabel("Year")
ax[1].set_ylabel("Gap: actual \u2212 synthetic (persons)")
ax[1].legend()
ax[1].grid(alpha=0.25)

ymin, ymax = int(ry.min()), int(ry.max())
xticks = list(range(ymin if ymin % 2 == 0 else ymin + 1, ymax + 1, 2))
for a in ax:
    a.set_xticks(xticks)
    a.xaxis.set_major_locator(MultipleLocator(2))
    a.xaxis.set_major_formatter(FormatStrFormatter("%d"))
    a.set_xlim(ymin - 0.3, ymax + 0.3)

txt = f"AVG EFFECT = {avg_effect:,.0f}\np-value (two-sided) = {p_mspe:.3f}"
ax[1].text(0.03, 0.05, txt, transform=ax[1].transAxes, fontsize=9,
           va="bottom", bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="0.8"))

fig.suptitle("Synthetic Control Method \u2014 2022 invasion effect on Ukrainian scholar "
             "inflow (OpenAlex, Stata synth2)", y=1.02, fontsize=12.5)
fig.tight_layout()
for name in ["scm_ukraine_stata", "scm_ukraine_panel"]:
    for ext in ["png", "pdf"]:
        fig.savefig(f"{DIR}/results/{name}.{ext}", dpi=200, bbox_inches="tight")
print("saved:", f"{DIR}/results/scm_ukraine_panel.png")
print(f"AVG EFFECT (nested) = {avg_effect:.1f}")
print(f"p-value (placebo MSPE-ratio) = {p_mspe:.3f}")
