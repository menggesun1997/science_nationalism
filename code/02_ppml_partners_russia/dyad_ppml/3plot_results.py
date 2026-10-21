#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画 2estimate_dyad_ppml.py 的结果：

  russia_dyad_by_group.pdf   规格 (2) 各集团 beta_g 的 coefficient plot
  russia_dyad_event.pdf      规格 (3) 各集团逐年 beta_gk 的事件研究路径
  russia_dyad_by_partner.pdf 规格 (4) 逐伙伴 lollipop（按集团着色）
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent

POST_YEAR = 2022
REF_YEAR = 2021

GROUP_ORDER = ("EU", "NORTH_AMERICA", "ASIA", "CHINA", "OTHER")
LABEL = {
    "EU": "EU27 + UK",
    "NORTH_AMERICA": "US + Canada",
    "ASIA": "Japan, S.Korea, Singapore",
    "CHINA": "China",
    "OTHER": "Rest of world",
}
COLOR = {
    "EU": "#1f4e79",
    "NORTH_AMERICA": "#2e8b57",
    "ASIA": "#c77b00",
    "CHINA": "#b22222",
    "OTHER": "#777777",
}


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def save(fig, stem: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {stem}.pdf / .png")


def plot_by_group(tag: str) -> None:
    d = pd.read_csv(HERE / f"res_by_group{tag}.csv")
    d["group"] = pd.Categorical(d["group"], GROUP_ORDER, ordered=True)
    d = d.sort_values("group", ascending=False)

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    y = range(len(d))
    for yi, (_, r) in zip(y, d.iterrows()):
        c = COLOR[r["group"]]
        ax.plot([r["ci_lo_pct"], r["ci_hi_pct"]], [yi, yi], color=c, lw=2.2)
        ax.plot(r["pct_change"], yi, "o", color=c, ms=7, zorder=3)
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.set_yticks(list(y))
    ax.set_yticklabels([f"{LABEL[g]}  (n={n})"
                        for g, n in zip(d["group"], d["n_partners"])])
    ax.set_xlabel(r"Change in collaboration with Russia, "
                  r"$\exp(\beta_g)-1$  (%)")
    ax.set_title("Partner groups' reallocation away from Russia\n"
                 f"(Post = {POST_YEAR}+, controls = own non-Russian "
                 "focal partners)", fontsize=10)
    ax.grid(axis="x", alpha=0.3, ls=":")
    fig.tight_layout()
    save(fig, f"russia_dyad_by_group{tag}")


def plot_event(tag: str, year_min: int = 2012, stem: str = "") -> None:
    """纵坐标用 beta_gk 本身（log 尺度），战前是否平行可直接读。

    默认从 2012 起画；2005-2011 的 beta_gk 高达 +0.5 到 +1.4（控制组国家
    早期体量小、增速快的基期效应），完整窗口见 *_full 版本。
    """
    d = pd.read_csv(HERE / f"res_event{tag}.csv")
    d = d[d["year"] >= year_min]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    for g in GROUP_ORDER:
        s = d[d["group"] == g].sort_values("year")
        lo = s["coef"] - 1.96 * s["se"]
        hi = s["coef"] + 1.96 * s["se"]
        ax.plot(s["year"], s["coef"], "-o", ms=3.5, lw=1.6,
                color=COLOR[g], label=LABEL[g])
        ax.fill_between(s["year"], lo, hi, color=COLOR[g], alpha=0.10, lw=0)
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(POST_YEAR - 0.5, color="red", lw=1.2, ls=":")
    ax.annotate("Feb 2022 invasion", (POST_YEAR - 0.4, ax.get_ylim()[1]),
                fontsize=8, color="red", va="top")
    ax.set_xlabel("Year")
    ax.set_ylabel(r"$\beta_{gk}$  (log points, ref. " + str(REF_YEAR) + ")")
    ax.set_title("Collaboration with Russia relative to control focal "
                 "countries, by partner group", fontsize=10)
    ax.grid(alpha=0.3, ls=":")
    integer_xaxis(ax)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=len(l),
               bbox_to_anchor=(0.5, -0.03), fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, stem or f"russia_dyad_event{tag}")


def plot_by_partner(tag: str, top: int = 45) -> None:
    d = pd.read_csv(HERE / f"res_by_partner{tag}.csv")
    d = d.reindex(d["mean_ru_collab"].sort_values(ascending=False).index)
    d = d.head(top).sort_values("pct_change")

    fig, ax = plt.subplots(figsize=(7.4, 0.22 * len(d) + 1.6))
    for yi, (_, r) in enumerate(d.iterrows()):
        c = COLOR[r["group"]]
        a = 1.0 if r["sig_05"] else 0.35
        ax.plot([0, r["pct_change"]], [yi, yi], color=c, lw=1.4, alpha=a)
        ax.plot(r["pct_change"], yi, "o", color=c, ms=5, alpha=a)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["partner_country"], fontsize=7)
    ax.set_xlabel(r"$\exp(\beta_i)-1$  (%)")
    ax.set_title(f"Per-partner change in collaboration with Russia\n"
                 f"(top {top} partners by volume; faded = p >= 0.05)",
                 fontsize=10)
    ax.grid(axis="x", alpha=0.3, ls=":")
    handles = [plt.Line2D([], [], color=COLOR[g], marker="o", ls="",
                          label=LABEL[g]) for g in GROUP_ORDER]
    fig.legend(handles=handles, frameon=False, loc="lower center",
               ncol=len(handles), bbox_to_anchor=(0.5, -0.01), fontsize=8)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    save(fig, f"russia_dyad_by_partner{tag}")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-controls", action="store_true")
    tag = "_allctrl" if ap.parse_args().all_controls else ""
    plot_by_group(tag)
    plot_event(tag)
    plot_event(tag, year_min=2005, stem=f"russia_dyad_event{tag}_full")
    plot_by_partner(tag)


if __name__ == "__main__":
    main()
