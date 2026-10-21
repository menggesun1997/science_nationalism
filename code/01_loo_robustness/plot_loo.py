"""Plot leave-one-out (drop-one-donor) robustness bands for the aggregate SCMs.

For each event (Brexit / 2014 Crimea / 2022 war) a 2x2 grid is drawn: rows are
the two outcomes (total publications, international-collaboration ratio) and
columns are the two treated units. Each panel overlays the observed series on
the mean synthetic control across all leave-one-out refits, with a shaded
+/- 1.96 SD band showing how sensitive the counterfactual is to any single
donor. A tight band that stays clear of the observed post-treatment path means
no individual donor drives the estimated effect.

Reads results/<analysis>/loo_<unit>_band.xlsx and writes to figures/.
Colours follow the shared palette (config.do): UK red, Russia blue-violet,
Ukraine golden. (EU is no longer treated as a unit.)
"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

COL = {"uk": "#BE2738", "russia": "#4B5C9C", "ukraine": "#E2C341"}
NAME = {"uk": "UK", "russia": "Russia", "ukraine": "Ukraine"}
LINE = "#444444"
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

# event -> (results-folder stem, treatment year, x cap or None, unit order)
EVENTS = {
    "brexit": ("brexit", 2016, None, ["uk"]),
    "crimea": ("crimea", 2014, 2021, ["russia", "ukraine"]),
    "war":    ("war", 2022, None, ["russia", "ukraine"]),
}
OUTCOMES = [("total", "Total publications"),
            ("ratio", "International collaboration ratio")]


def integer_axis(ax):
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))


def panel(ax, df, unit, tyear, xcap, ylab):
    if xcap is not None:
        df = df[df["Year"] <= xcap]
    c = COL[unit]
    ax.fill_between(df["Year"], df["ci_lower"], df["ci_upper"],
                    color=c, alpha=0.18, lw=0,
                    label="Leave-one-out 95% band")
    ax.plot(df["Year"], df["mean_synth"], color=c, lw=1.6,
            ls=(0, (5, 3)), label="Mean synthetic")
    ax.plot(df["Year"], df["actual"], color=c, lw=1.9, marker="o",
            ms=4, mfc=c, mec=c, label="Observed")
    ax.axvline(tyear, color=LINE, lw=1.3, ls=(0, (2, 2)))
    ax.set_title(NAME[unit], fontsize=11, fontweight="bold", pad=5)
    ax.set_xlabel("Year", fontsize=9)
    if ylab:
        ax.set_ylabel(ylab, fontsize=9)
    integer_axis(ax)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)


def make_event(event):
    stem, tyear, xcap, units = EVENTS[event]

    if len(units) == 1:
        # Single treated unit (Brexit = UK): place the two outcomes side by
        # side in one row rather than stacking them vertically.
        unit = units[0]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), squeeze=False)
        for cc, (suffix, ylab) in enumerate(OUTCOMES):
            ax = axes[0][cc]
            fp = os.path.join(RESULTS, f"{stem}_{suffix}",
                              f"loo_{unit}_band.xlsx")
            if not os.path.exists(fp):
                ax.set_visible(False)
                continue
            df = pd.read_excel(fp).sort_values("Year")
            panel(ax, df, unit, tyear, xcap, ylab)
            ax.set_title(ylab, fontsize=11, fontweight="bold", pad=5)
        first_ax = axes[0][0]
        handles, labels = first_ax.get_legend_handles_labels()
        fig.legend(handles, labels, frameon=False, fontsize=9.5,
                   loc="lower center", ncol=len(labels),
                   bbox_to_anchor=(0.5, -0.02))
        fig.tight_layout(rect=(0, 0.07, 1, 1))
        for ext in ("pdf", "png"):
            fig.savefig(os.path.join(OUT, f"loo_{event}.{ext}"), dpi=300,
                        bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"saved loo_{event}.pdf / .png")
        return

    ncol = len(units)
    fig, axes = plt.subplots(2, ncol, figsize=(5.3 * ncol, 7.4),
                             squeeze=False)
    for r, (suffix, ylab) in enumerate(OUTCOMES):
        for cc, unit in enumerate(units):
            ax = axes[r][cc]
            fp = os.path.join(RESULTS, f"{stem}_{suffix}",
                              f"loo_{unit}_band.xlsx")
            if not os.path.exists(fp):
                ax.set_visible(False)
                continue
            df = pd.read_excel(fp).sort_values("Year")
            panel(ax, df, unit, tyear, xcap,
                  ylab if cc == 0 else "")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=9.5,
               loc="lower center", ncol=len(labels),
               bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"loo_{event}.{ext}"), dpi=300,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved loo_{event}.pdf / .png")


if __name__ == "__main__":
    for ev in EVENTS:
        make_event(ev)
