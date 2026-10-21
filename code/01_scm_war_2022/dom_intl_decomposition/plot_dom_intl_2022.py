"""Plot domestic vs international SCM decomposition around the 2022 invasion.

One figure per country, two panels (domestic, international), observed vs
synthetic counts. The 2022 intervention is marked. Russia shows a domestic
series holding above its counterfactual while international output falls far
below it (genuine decoupling); Ukraine shows a collapsing domestic base while
internationally co-authored output tracks its counterfactual (wartime
resilience of international ties, not a compositional artefact alone).
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

HERE = "code/01_scm_war_2022/dom_intl_decomposition"
COLORS = {"russia": "#4B5C9C", "ukraine": "#E2C341"}


def make(country):
    c = COLORS[country]
    df = pd.read_excel(f"{HERE}/{country}_dom_intl_2022_merged.xlsx").sort_values("Year")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    panels = [
        ("dom_actual_real", "dom_synthetic_real", "(a) Domestic publications"),
        ("intl_actual_real", "intl_synthetic_real", "(b) International publications"),
    ]
    for ax, (a, s, title) in zip(axes, panels):
        ax.plot(df["Year"], df[a], color=c, lw=1.8, marker="o", ms=4,
                mfc=c, mec=c, label="Observed")
        ax.plot(df["Year"], df[s], color=c, lw=1.6, ls=(0, (5, 3)), marker="o",
                ms=4, mfc=c, mec=c, label="Synthetic")
        ax.axvline(2022, color="0.35", lw=1.4, ls=(0, (2, 2)))
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
        fig.savefig(f"{HERE}/{country}_dom_intl_2022_scm.{ext}", dpi=300,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {country}_dom_intl_2022_scm.pdf / .png")


def make_combined():
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.4))
    rows = [
        ("russia", ["(a) Russia: domestic", "(b) Russia: international"]),
        ("ukraine", ["(c) Ukraine: domestic", "(d) Ukraine: international"]),
    ]
    for r, (country, titles) in enumerate(rows):
        c = COLORS[country]
        df = pd.read_excel(f"{HERE}/{country}_dom_intl_2022_merged.xlsx").sort_values("Year")
        cols = [("dom_actual_real", "dom_synthetic_real"),
                ("intl_actual_real", "intl_synthetic_real")]
        for k, (a, s) in enumerate(cols):
            ax = axes[r, k]
            ax.plot(df["Year"], df[a], color=c, lw=1.8, marker="o", ms=4,
                    mfc=c, mec=c, label="Observed")
            ax.plot(df["Year"], df[s], color=c, lw=1.6, ls=(0, (5, 3)),
                    marker="o", ms=4, mfc=c, mec=c, label="Synthetic")
            ax.axvline(2022, color="0.35", lw=1.4, ls=(0, (2, 2)))
            ax.set_title(titles[k], fontsize=11, fontweight="bold", pad=6)
            ax.set_xlabel("Year", fontsize=10)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=9)
        axes[r, 0].set_ylabel("Publications", fontsize=10)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=10, loc="lower center",
               ncol=2, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(f"{HERE}/war_dom_intl_2022_scm.{ext}", dpi=300,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved war_dom_intl_2022_scm.pdf / .png")


for c in ("russia", "ukraine"):
    make(c)
make_combined()
