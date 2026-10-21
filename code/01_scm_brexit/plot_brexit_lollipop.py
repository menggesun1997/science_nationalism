#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Donor-weight lollipop chart for the Brexit aggregate SCM (UK only).

Two panels: UK total publications and UK international collaboration ratio.
(EU is no longer treated as a unit, so only the UK counterfactual is shown.)
Weights are read from the *_weights_country.xlsx exported by compare.do /
compare_intl_ratio.do so the figure stays in sync with the Stata output.

Output: code/01_scm_brexit/uk_eu_total_ratio_lollipop.pdf (filename kept for
the existing \\includegraphics reference in si.tex).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scm_weights import top_donors  # noqa: E402

HERE = Path(__file__).resolve().parent

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

TOP_N = 4


def draw_lollipop_subplot(ax, countries, values, title):
    data = sorted(zip(countries, values), key=lambda x: x[1], reverse=True)
    countries_sorted = [d[0] for d in data]
    values_sorted = [d[1] for d in data]

    n = len(countries_sorted)
    cmap = LinearSegmentedColormap.from_list('blue_yellow',
                                             ['#2196F3', '#FFD600'], N=n)
    colors = [cmap(i / (n - 1)) if n > 1 else cmap(0) for i in range(n)]

    for i, (cat, val, color) in enumerate(zip(countries_sorted, values_sorted, colors)):
        num_dots = max(int(val * 100), 10)
        x_dots = np.linspace(0, val, num_dots)
        ax.scatter(x_dots, np.full_like(x_dots, i), s=10, color=color, zorder=1)
        ax.scatter(val, i, s=700, color=color, zorder=2)
        ax.text(val + 0.01, i, f'{val * 100:.1f}%', va='center', ha='left',
                fontsize=12, fontweight='bold', color='black')

    ax.set_yticks(range(n))
    ax.set_yticklabels([c.upper() for c in countries_sorted],
                       fontsize=12, fontweight='bold')
    ax.set_ylim(-0.5, n - 0.5)
    x_max = ((max(values_sorted) * 10) // 1 + 1) / 10
    ax.set_xlim(0, x_max)
    x_ticks = np.arange(0, x_max + 0.05, 0.1)
    ax.set_xticks(x_ticks)
    ax.set_xticklabels([f'{t:.1f}' for t in x_ticks], fontweight='bold', fontsize=10)
    ax.invert_yaxis()
    ax.tick_params(left=False, bottom=False, labelsize=10, width=2)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_facecolor("white")


def main():
    uk_total_c, uk_total_v = top_donors(
        HERE / "total_publications" / "uk_weights_country.xlsx", top_n=TOP_N)
    uk_ratio_c, uk_ratio_v = top_donors(
        HERE / "intl_ratio" / "uk_weights_country.xlsx", top_n=TOP_N)

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
    draw_lollipop_subplot(axes[0], uk_total_c, uk_total_v,
                          "UK - Total publications")
    draw_lollipop_subplot(axes[1], uk_ratio_c, uk_ratio_v,
                          "UK - Ratio of international publications")
    plt.tight_layout()

    for ext in ("png", "pdf"):
        out = HERE / f"uk_eu_total_ratio_lollipop.{ext}"
        plt.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"saved {out}")
    plt.close()


if __name__ == '__main__':
    main()
