"""Figure 2: domestic vs international decomposition for both events.

Layout is 2 rows (Russia, Ukraine) x 4 columns. The left two columns cover the
2014 Crimean crisis (domestic, international); the right two cover the 2022
full-scale invasion (domestic, international). Solid lines are observed counts,
dashed lines the synthetic counterfactual; a vertical dashed line marks each
event year. Observed and synthetic share a country colour and are distinguished
by line style.

The figure makes the paper's central decomposition visible at a glance: in both
countries and both events the anomaly concentrates in the domestic component,
while the international component behaves very differently across cases
(Russia's collapses only after 2022; Ukraine's stays near its counterfactual).
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

RU = "#4B5C9C"
UA = "#E2C341"
ROOT = "c:/Users/91916/Dropbox/GitHub/sicence nationism"
C14 = f"{ROOT}/code/01_scm_crimea_2014/dom_intl_decomposition"
C22 = f"{ROOT}/code/01_scm_war_2022/dom_intl_decomposition"

data = {
    ("russia", 2014): f"{C14}/russia_dom_intl_merged.xlsx",
    ("ukraine", 2014): f"{C14}/ukraine_dom_intl_merged.xlsx",
    ("russia", 2022): f"{C22}/russia_dom_intl_2022_merged.xlsx",
    ("ukraine", 2022): f"{C22}/ukraine_dom_intl_2022_merged.xlsx",
}
frames = {k: pd.read_excel(v).sort_values("Year") for k, v in data.items()}

fig, axes = plt.subplots(2, 4, figsize=(15, 7))
# column -> (event_year, component, panel-title stem)
columns = [
    (2014, "dom", "Domestic"),
    (2014, "intl", "International"),
    (2022, "dom", "Domestic"),
    (2022, "intl", "International"),
]
rows = [("russia", RU, "Russia"), ("ukraine", UA, "Ukraine")]
tags = iter("abcdefgh")

for r, (country, color, cname) in enumerate(rows):
    for c, (year, comp, comp_name) in enumerate(columns):
        ax = axes[r, c]
        df = frames[(country, year)]
        a, s = f"{comp}_actual_real", f"{comp}_synthetic_real"
        ax.plot(df["Year"], df[a], color=color, lw=1.8, marker="o", ms=3.5,
                mfc=color, mec=color)
        ax.plot(df["Year"], df[s], color=color, lw=1.6, ls=(0, (5, 3)),
                marker="o", ms=3.5, mfc="white", mec=color)
        ax.axvline(year, color="0.35", lw=1.3, ls=(0, (2, 2)))
        ax.set_title(f"({next(tags)}) {cname}: {comp_name}",
                     fontsize=10, fontweight="bold", pad=5)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8)
        if r == 1:
            ax.set_xlabel("Year", fontsize=9)
        if c == 0:
            ax.set_ylabel("Publications", fontsize=9)

# Event-group headers spanning the two columns each.
fig.text(0.30, 0.98, "2014 Crimean crisis", ha="center", fontsize=12,
         fontweight="bold")
fig.text(0.74, 0.98, "2022 full-scale invasion", ha="center", fontsize=12,
         fontweight="bold")

legend_handles = [
    Line2D([0], [0], color="0.3", lw=1.8, label="Observed"),
    Line2D([0], [0], color="0.3", lw=1.6, ls=(0, (5, 3)), label="Synthetic"),
]
fig.legend(handles=legend_handles, frameon=False, fontsize=10,
           loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.04, 1, 0.96))

for ext in ("pdf", "png"):
    fig.savefig(f"{ROOT}/paper/figure/figure2.{ext}", dpi=300,
                bbox_inches="tight", facecolor="white")
print("saved paper/figure/figure2.pdf / .png")
