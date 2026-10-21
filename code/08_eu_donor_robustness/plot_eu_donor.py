"""Plot the EU-donor robustness check for Brexit (treated unit: UK).

The main Brexit SCM excludes the 27 EU member states from the donor pool. This
figure shows that admitting them as controls barely moves the synthetic UK: for
each outcome (total publications, international-collaboration ratio) the observed
UK series is overlaid with two synthetic counterfactuals - one built from the
17 non-EU donors used in the main text, one built from all 44 donors including
the 27 EU members. Overlapping synthetic lines and a stable post-2016 gap mean
the estimated Brexit effect is not an artefact of donor-country selection.

Reads results/eu_donor_brexit_{total,ratio}.xlsx, writes figures/eu_donor_brexit.{pdf,png}.
Colours follow the shared palette (config.do): UK red for the observed series.
"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator

C_UK = "#BE2738"      # observed UK
C_BASE = "#4B5C9C"    # synthetic, non-EU donor pool (main text)
C_EU = "#E2A100"      # synthetic, EU-inclusive donor pool
LINE = "#444444"
TREAT_YEAR = 2016

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

OUTCOMES = [
    ("total", "Total publications", lambda s: s / 1000.0,
     "Total publications (thousands)"),
    ("ratio", "International collaboration ratio", lambda s: s,
     "International collaboration ratio"),
]


def integer_xaxis(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def panel(ax, df, scale, ylab):
    yr = df["Year"]
    ax.plot(yr, scale(df["actual"]), color=C_UK, lw=1.9, marker="o",
            ms=4, mfc=C_UK, mec=C_UK, label="Observed UK", zorder=5)
    ax.plot(yr, scale(df["synth_base"]), color=C_BASE, lw=1.7,
            ls=(0, (5, 3)), label="Synthetic UK (non-EU donor pool)")
    ax.plot(yr, scale(df["synth_eu"]), color=C_EU, lw=1.7,
            ls=(0, (1, 1.3)), label="Synthetic UK (EU-inclusive donor pool)")
    ax.axvline(TREAT_YEAR, color=LINE, lw=1.2, ls=(0, (2, 2)))
    ax.set_title(ylab, fontsize=11, fontweight="bold", pad=6)
    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel(ylab, fontsize=9)
    integer_xaxis(ax)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)


def main():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), squeeze=False)
    for cc, (suffix, _title, scale, ylab) in enumerate(OUTCOMES):
        ax = axes[0][cc]
        fp = os.path.join(RESULTS, f"eu_donor_brexit_{suffix}.xlsx")
        if not os.path.exists(fp):
            ax.set_visible(False)
            continue
        df = pd.read_excel(fp).sort_values("Year")
        panel(ax, df, scale, ylab)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9.5,
               loc="lower center", ncol=len(labels),
               bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"eu_donor_brexit.{ext}"), dpi=300,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved eu_donor_brexit.pdf / .png")


if __name__ == "__main__":
    main()
