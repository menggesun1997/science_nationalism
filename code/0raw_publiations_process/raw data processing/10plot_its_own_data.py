# -*- coding: utf-8 -*-
# Academic-style ITS visualization using the project's OWN (WoS-based) data.
# For each focal (RUS/GBR/UKR): net inflow series with
#   - pre-event fitted trend (solid)
#   - post-event fitted level+trend (solid)
#   - counterfactual = pre trend extrapolated into post (dashed)
#   - beta1 (level break) annotated as the vertical gap at t=0
#   - event year marked, 95% CI band around fits
# Output: results/its_own_data_panel.png (+ .pdf) in each *_mpidr sibling? -> saved centrally.

import sys
from pathlib import Path

# Resolve repository paths without hard-coding any absolute directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402


import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

ROOT = str(CODE)
OUT = os.path.join(ROOT, "0raw_publiations_process", "raw data processing", "its_own_data")
os.makedirs(OUT, exist_ok=True)

FOCALS = [("uk", "GBR", 2016, "United Kingdom — Brexit referendum (2016)"),
          ("russia", "RUS", 2022, "Russia — full-scale invasion (2022)"),
          ("ukraine", "UKR", 2022, "Ukraine — full-scale invasion (2022)")]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
})


def load_series(tag, t0):
    d = f"{ROOT}/3ppml_migration_did_{tag}_internal_control"
    i = (pd.read_csv(f"{d}/ppml_data_in.csv")
         .groupby(["year", "rel_year"], as_index=False).paper_count.sum()
         .rename(columns={"paper_count": "inflow"}))
    o = (pd.read_csv(f"{d}/ppml_data_out.csv")
         .groupby("year", as_index=False).paper_count.sum()
         .rename(columns={"paper_count": "outflow"}))
    m = i.merge(o, on="year").sort_values("year").reset_index(drop=True)
    m["net_inflow"] = m.inflow - m.outflow
    m["post"] = (m.year >= t0).astype(int)
    return m


C_PRE, C_POST, C_CF, C_EVT = "#2c6fbb", "#c0392b", "#7f8c8d", "#c0392b"


def fit_and_plot(ax, m, t0, title):
    res = smf.ols("net_inflow ~ post + rel_year", data=m).fit()
    b0, b1, b2 = res.params["Intercept"], res.params["post"], res.params["rel_year"]
    p1, p2 = res.pvalues["post"], res.pvalues["rel_year"]
    se1 = res.bse["post"]

    # 诊断: pre 期点数/线性 R^2, post 点数, 自相关稳健 p (Newey-West lag1)
    pre_df = m[m.post == 0]
    n_post = int((m.post == 1).sum())
    r2_pre = smf.ols("net_inflow ~ rel_year", data=pre_df).fit().rsquared
    hac = smf.ols("net_inflow ~ post + rel_year", data=m).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1})
    p1_hac = hac.pvalues["post"]
    # ITS 可信度门槛: 断点在自相关稳健标准误下显著 + post 点数足够.
    # (pre 线性 R^2 仅作诊断标注; 低 R^2 若源于近零斜率并不损害外推)
    credible = (n_post >= 3) and (p1_hac < 0.10)

    t = m.rel_year.values
    yhat = res.predict(m)
    pre = m[m.post == 0]
    post = m[m.post == 1]

    # scatter observed
    ax.scatter(pre.rel_year, pre.net_inflow, s=34, color=C_PRE, zorder=5,
               label="Observed (pre)")
    ax.scatter(post.rel_year, post.net_inflow, s=34, color=C_POST, zorder=5,
               label="Observed (post)")

    # fitted pre segment
    tt_pre = np.linspace(t.min(), -0.001, 50)
    ax.plot(tt_pre, b0 + b2 * tt_pre, color=C_PRE, lw=2, zorder=4,
            label="Fitted trend (pre)")
    # fitted post segment (level break + trend)
    tt_post = np.linspace(0, t.max(), 50)
    ax.plot(tt_post, b0 + b1 + b2 * tt_post, color=C_POST, lw=2, zorder=4,
            label="Fitted trend (post)")
    # counterfactual: pre trend extrapolated
    tt_cf = np.linspace(0, t.max(), 50)
    ax.plot(tt_cf, b0 + b2 * tt_cf, color=C_CF, lw=1.8, ls="--", zorder=3,
            label="Counterfactual (no event)")

    # event line
    ax.axvline(0, color=C_EVT, lw=1.1, ls=":", alpha=0.7)
    ax.axhline(0, color="black", lw=0.6, alpha=0.4)

    # beta1 gap: double arrow at t=0 between counterfactual and post fit
    y_cf0 = b0 + b2 * 0
    y_po0 = b0 + b1 + b2 * 0
    ax.annotate("", xy=(0.28, y_po0), xytext=(0.28, y_cf0),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.4))
    sig = "***" if p1 < 0.01 else ("**" if p1 < 0.05 else ("*" if p1 < 0.1 else "n.s."))
    ax.annotate(rf"$\beta_1$={b1:,.0f} ({sig})", xy=(0.4, (y_cf0 + y_po0) / 2),
                fontsize=10, va="center", ha="left",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.7", alpha=0.9))

    # stats box (含自相关稳健 p 与 pre 诊断)
    flag = "causal ITS" if credible else "descriptive only"
    txt = (rf"$\beta_1$ (break) = {b1:,.0f}, p={p1:.3f} (HAC p={p1_hac:.3f})" + "\n"
           rf"$\beta_2$ (trend) = {b2:,.1f}, p={p2:.3f}" + "\n"
           rf"pre linear $R^2$={r2_pre:.2f}, $n_{{post}}$={n_post}  [{flag}]")
    ax.text(0.03, 0.05, txt, transform=ax.transAxes, fontsize=9.0, va="bottom",
            bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="0.8"))
    if not credible:
        ax.text(0.5, 0.97, "interpret as descriptive, not causal",
                transform=ax.transAxes, fontsize=8.5, ha="center", va="top",
                style="italic", color="#c0392b")

    ax.set_title(title, fontsize=11, pad=8)
    ax.set_xlabel("Event time  (years relative to shock, t=0)")
    # secondary x labels as calendar years
    yrs = m.year.values
    ax.set_xticks(t[::2])
    ax.set_xticklabels([f"{ry:+d}\n{yr}" for ry, yr in zip(t[::2], yrs[::2])],
                       fontsize=8)
    return res


def main():
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2), sharex=False)
    summ = []
    for ax, (tag, foc, t0, title) in zip(axes, FOCALS):
        m = load_series(tag, t0)
        res = fit_and_plot(ax, m, t0, title)
        summ.append((foc, res.params["post"], res.pvalues["post"],
                     res.params["rel_year"], res.pvalues["rel_year"]))
    axes[0].set_ylabel("Net inflow of scholars  (inflow − outflow, persons)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=len(labels),
               fontsize=9, framealpha=0.9, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Interrupted Time Series of Scholarly Net Inflow around Political Shocks "
                 "(own WoS-based data, 2008–2024)", fontsize=13, y=1.02)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(OUT, f"its_own_data_panel.{ext}"),
                    dpi=200, bbox_inches="tight")
    print("saved:", os.path.join(OUT, "its_own_data_panel.png"))
    for s in summ:
        print(f"  {s[0]}: b1={s[1]:.1f} (p={s[2]:.4f})  b2={s[3]:.1f} (p={s[4]:.4f})")


if __name__ == "__main__":
    main()
