# -*- coding: utf-8 -*-
# Academic-style ITS visualization using the MPIDR SMD 2.0 data
# (built into the *_mpidr folders as net_inflow_timeseries_<prov>.csv).
# Same layout/logic as 10plot_its_own_data.py, one figure per provider.
# Output: its_mpidr_data/its_mpidr_panel_<prov>.{png,pdf}

import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code"
OUT = os.path.join(ROOT, "0raw_publiations_process", "raw data processing", "its_mpidr_data")
os.makedirs(OUT, exist_ok=True)

# panel order: UK, Russia, Ukraine (matches own-data figure)
FOCALS = [("uk", "GBR", 2016, "United Kingdom — Brexit referendum (2016)"),
          ("russia", "RUS", 2022, "Russia — full-scale invasion (2022)"),
          ("ukraine", "UKR", 2022, "Ukraine — full-scale invasion (2022)")]
PROVIDERS = ["openalex", "scopus"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
})

C_PRE, C_POST, C_CF, C_EVT = "#2c6fbb", "#c0392b", "#7f8c8d", "#c0392b"


def load_series(tag, prov):
    d = f"{ROOT}/3ppml_migration_did_{tag}_internal_control_mpidr"
    return pd.read_csv(f"{d}/ppml_net_{prov}.csv").sort_values("year")


def fit_and_plot(ax, m, title):
    res = smf.ols("net_inflow ~ post + rel_year", data=m).fit()
    b0, b1, b2 = res.params["Intercept"], res.params["post"], res.params["rel_year"]
    p1, p2 = res.pvalues["post"], res.pvalues["rel_year"]

    t = m.rel_year.values
    pre = m[m.post == 0]
    post = m[m.post == 1]
    ax.scatter(pre.rel_year, pre.net_inflow, s=34, color=C_PRE, zorder=5,
               label="Observed (pre)")
    ax.scatter(post.rel_year, post.net_inflow, s=34, color=C_POST, zorder=5,
               label="Observed (post)")

    tt_pre = np.linspace(t.min(), -0.001, 50)
    ax.plot(tt_pre, b0 + b2 * tt_pre, color=C_PRE, lw=2, zorder=4,
            label="Fitted trend (pre)")
    tt_post = np.linspace(0, t.max(), 50)
    ax.plot(tt_post, b0 + b1 + b2 * tt_post, color=C_POST, lw=2, zorder=4,
            label="Fitted trend (post)")
    ax.plot(tt_post, b0 + b2 * tt_post, color=C_CF, lw=1.8, ls="--", zorder=3,
            label="Counterfactual (no event)")

    ax.axvline(0, color=C_EVT, lw=1.1, ls=":", alpha=0.7)
    ax.axhline(0, color="black", lw=0.6, alpha=0.4)

    y_cf0 = b0
    y_po0 = b0 + b1
    ax.annotate("", xy=(0.28, y_po0), xytext=(0.28, y_cf0),
                arrowprops=dict(arrowstyle="<->", color="black", lw=1.4))
    sig = "***" if p1 < 0.01 else ("**" if p1 < 0.05 else ("*" if p1 < 0.1 else "n.s."))
    ax.annotate(rf"$\beta_1$={b1:,.0f} ({sig})", xy=(0.4, (y_cf0 + y_po0) / 2),
                fontsize=10, va="center", ha="left",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.7", alpha=0.9))

    txt = (rf"$\beta_1$ (break) = {b1:,.0f}, p={p1:.3f}" + "\n"
           rf"$\beta_2$ (trend) = {b2:,.1f}, p={p2:.3f}")
    ax.text(0.03, 0.05, txt, transform=ax.transAxes, fontsize=9.5, va="bottom",
            bbox=dict(boxstyle="round,pad=0.35", fc="#f7f7f7", ec="0.8"))

    ax.set_title(title, fontsize=11, pad=8)
    ax.set_xlabel("Event time  (years relative to shock, t=0)")
    yrs = m.year.values
    ax.set_xticks(t[::2])
    ax.set_xticklabels([f"{ry:+d}\n{yr}" for ry, yr in zip(t[::2], yrs[::2])],
                       fontsize=8)
    return res


def main():
    for prov in PROVIDERS:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
        summ = []
        for ax, (tag, foc, t0, title) in zip(axes, FOCALS):
            m = load_series(tag, prov)
            res = fit_and_plot(ax, m, title)
            summ.append((foc, res.params["post"], res.pvalues["post"],
                         res.params["rel_year"], res.pvalues["rel_year"]))
        axes[0].set_ylabel("Net inflow of scholars  (inflow − outflow, persons)")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=len(labels),
                   fontsize=9, framealpha=0.9, bbox_to_anchor=(0.5, -0.02))
        fig.suptitle(f"Interrupted Time Series of Scholarly Net Inflow around Political "
                     f"Shocks (MPIDR SMD 2.0 — {prov}, 2008–2024)", fontsize=13, y=1.02)
        fig.tight_layout(rect=[0, 0.04, 1, 1])
        for ext in ["png", "pdf"]:
            fig.savefig(os.path.join(OUT, f"its_mpidr_panel_{prov}.{ext}"),
                        dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"saved its_mpidr_panel_{prov}.png")
        for s in summ:
            print(f"  {s[0]}: b1={s[1]:.1f} (p={s[2]:.4f})  b2={s[3]:.1f} (p={s[4]:.4f})")


if __name__ == "__main__":
    main()
