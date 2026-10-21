"""Plot Ukraine domestic vs international SCM decomposition around 2014.

Two panels (domestic, international); each shows observed vs synthetic counts.
The window is capped at 2021 to match the Crimean-crisis analysis, with a light
extension to 2024 drawn for context. Domestic output falls far below its
counterfactual while internationally co-authored output falls only modestly,
so the rising collaboration ratio is a compositional effect of a shrinking
domestic base rather than genuine widening of international reach.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

UA = "#E2C341"     # Ukraine golden; observed and synthetic share the colour
                   # and are distinguished by line style (solid vs dashed).
HERE = "code/01_scm_crimea_2014/dom_intl_decomposition"

df = pd.read_excel(f"{HERE}/ukraine_dom_intl_merged.xlsx").sort_values("Year")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
panels = [
    ("dom_actual_real", "dom_synthetic_real", "(a) Domestic publications"),
    ("intl_actual_real", "intl_synthetic_real", "(b) International publications"),
]
for ax, (a, s, title) in zip(axes, panels):
    ax.plot(df["Year"], df[a], color=UA, lw=1.8, marker="o", ms=4,
            mfc=UA, mec=UA, label="Observed")
    ax.plot(df["Year"], df[s], color=UA, lw=1.6, ls=(0, (5, 3)), marker="o",
            ms=4, mfc=UA, mec=UA, label="Synthetic")
    ax.axvline(2014, color="0.35", lw=1.4, ls=(0, (2, 2)))
    ax.set_title(title, fontsize=11, fontweight="bold", pad=6)
    ax.set_xlabel("Year", fontsize=10)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
axes[0].set_ylabel("Publications", fontsize=10)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=10, loc="lower center",
           ncol=2, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.05, 1, 1))
for ext in ("pdf", "png"):
    fig.savefig(f"{HERE}/ukraine_dom_intl_scm.{ext}", dpi=300,
                bbox_inches="tight", facecolor="white")
print("saved ukraine_dom_intl_scm.pdf / .png")
