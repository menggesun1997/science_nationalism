"""Figure 2: domestic vs international publication SCM decomposition.

Eight panels in a 2x4 grid, styled to match the lower rows of Figure 1
(99_redraw_panels.do): connected observed (solid) vs synthetic (dashed) lines
with small round markers, a shaded post-treatment period, a dashed intervention
line, a boxed "Effect = X% (p=...)" annotation, left-hand row titles, and a
shared four-item legend.

Rows are events (Crimea 2014, then Russia-Ukraine war 2022). Within each row the
four columns are Russia domestic, Russia international, Ukraine domestic, Ukraine
international. Publications are shown in thousands.

The effect is the geometric average gap on the log scale,
exp(mean(log_actual - log_synthetic)) - 1, over the event's post window, matching
the log-scale SCM the models are fit on. p-values are in-space placebo p-values.

Run from the repository root:
  python code/01_scm_war_2022/dom_intl_decomposition/plot_figure2_decomposition.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MaxNLocator

ROOT = os.environ.get("SCIENCE_NATIONALISM_ROOT", os.getcwd())
CRIMEA = os.path.join(ROOT, "code", "01_scm_crimea_2014", "dom_intl_decomposition")
WAR = os.path.join(ROOT, "code", "01_scm_war_2022", "dom_intl_decomposition")
OUT = os.path.join(ROOT, "paper", "figure", "figure2")

# Palette from code/config.do (published-figure colours).
C_RU = "#4B5C9C"
C_UA = "#E2C341"
C_SHADE = "#EEEEEE"
C_LINE = "#444444"
COLORS = {"russia": C_RU, "ukraine": C_UA}

# Post-treatment effect windows (inclusive), matching the total-publication SCMs.
POST = {"crimea": (2014, 2021), "war": (2022, 2024)}
EVENT_YEAR = {"crimea": 2014, "war": 2022}
# Visualisation windows (inclusive). Crimea stops at 2021 so the 2022 war shock
# does not intrude; war starts at 2015, the clean post-Crimea fitting window.
VIS = {"crimea": (2005, 2021), "war": (2015, 2024)}
XTICKS = {"crimea": [2005, 2010, 2015, 2020], "war": [2016, 2018, 2020, 2022, 2024]}
ROW_TITLE = {"crimea": "Crimea crisis", "war": "Russia-Ukraine war"}


def load_pvalues():
    """Return {(event, country, component): p} from the placebo CSVs."""
    frames = [
        pd.read_csv(os.path.join(CRIMEA, "pvalues_russia.csv")),
        pd.read_csv(os.path.join(CRIMEA, "pvalues_ukraine.csv")),
        pd.read_csv(os.path.join(WAR, "pvalues_2022.csv")),
    ]
    p = {}
    for df in frames:
        for _, r in df.iterrows():
            ev = "crimea" if str(r["event"]).startswith("crimea") else "war"
            p[(ev, r["country"], r["component"])] = float(r["p"])
    return p


def geom_effect(df, comp, post):
    """exp(mean(log_actual - log_synthetic)) - 1 over the post window, in %."""
    m = df[(df["Year"] >= post[0]) & (df["Year"] <= post[1])]
    return (np.exp((m[f"{comp}_actual"] - m[f"{comp}_synthetic"]).mean()) - 1) * 100


def fmt_effect(eff, p):
    sign = "+" if eff >= 0 else "\u2212"
    return f"Effect = {sign}{abs(eff):.1f}% (p={p:.3f})"


def panel(ax, df, comp, country, event, pvals):
    c = COLORS[country]
    lo, hi = VIS[event]
    ev_year = EVENT_YEAR[event]
    vis = df[(df["Year"] >= lo) & (df["Year"] <= hi)].copy()
    # Publications in thousands.
    a = vis[f"{comp}_actual_real"] / 1000.0
    s = vis[f"{comp}_synthetic_real"] / 1000.0
    yr = vis["Year"]

    # Shaded post-treatment period (event year to end of visible range).
    ax.axvspan(ev_year, hi, color=C_SHADE, alpha=0.6, lw=0)
    # Synthetic (dashed) then observed (solid), both connected with round markers.
    ax.plot(yr, s, color=c, lw=1.5, ls=(0, (5, 3)), marker="o", ms=3.2,
            mfc=c, mec=c, mew=0.4)
    ax.plot(yr, a, color=c, lw=1.7, ls="-", marker="o", ms=3.2,
            mfc=c, mec=c, mew=0.4, solid_capstyle="round")
    # Dashed intervention line.
    ax.axvline(ev_year, color=C_LINE, lw=1.2, ls=(0, (4, 3)))

    eff = geom_effect(df, comp, POST[event])
    p = pvals[(event, country, comp)]
    ax.text(0.05, 0.93, fmt_effect(eff, p), transform=ax.transAxes,
            fontsize=8.5, va="top", ha="left",
            bbox=dict(boxstyle="square,pad=0.3", fc="white", ec="none", alpha=0.85))

    ax.set_xlim(lo, hi)
    ax.set_xticks(XTICKS[event])
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)


def main():
    pvals = load_pvalues()
    ru_cr = pd.read_excel(os.path.join(CRIMEA, "russia_dom_intl_merged.xlsx")).sort_values("Year")
    ua_cr = pd.read_excel(os.path.join(CRIMEA, "ukraine_dom_intl_merged.xlsx")).sort_values("Year")
    ru_wr = pd.read_excel(os.path.join(WAR, "russia_dom_intl_2022_merged.xlsx")).sort_values("Year")
    ua_wr = pd.read_excel(os.path.join(WAR, "ukraine_dom_intl_2022_merged.xlsx")).sort_values("Year")

    # Rows = events; columns = Russia dom, Russia intl, Ukraine dom, Ukraine intl.
    specs = [
        [(ru_cr, "dom", "russia", "crimea", "Russia -- Domestic publications"),
         (ru_cr, "intl", "russia", "crimea", "Russia -- Intl. publications"),
         (ua_cr, "dom", "ukraine", "crimea", "Ukraine -- Domestic publications"),
         (ua_cr, "intl", "ukraine", "crimea", "Ukraine -- Intl. publications")],
        [(ru_wr, "dom", "russia", "war", "Russia -- Domestic publications"),
         (ru_wr, "intl", "russia", "war", "Russia -- Intl. publications"),
         (ua_wr, "dom", "ukraine", "war", "Ukraine -- Domestic publications"),
         (ua_wr, "intl", "ukraine", "war", "Ukraine -- Intl. publications")],
    ]

    fig, axes = plt.subplots(2, 4, figsize=(15, 6.6))
    letters = "abcdefgh"
    events = ["crimea", "war"]
    for r in range(2):
        for col in range(4):
            df, comp, country, event, title = specs[r][col]
            ax = axes[r, col]
            panel(ax, df, comp, country, event, pvals)
            ax.set_title(title, fontsize=9.5, fontweight="bold", pad=6)
            # Panel letter, bold, upper-left outside the axes.
            ax.text(-0.18, 1.06, letters[r * 4 + col], transform=ax.transAxes,
                    fontsize=13, fontweight="bold", va="bottom", ha="left")
            if col == 0:
                ax.set_ylabel("Publications (1,000s)", fontsize=9)
        # Left-hand row title.
        axes[r, 0].annotate(ROW_TITLE[events[r]], xy=(-0.42, 0.5),
                            xycoords="axes fraction", rotation=90,
                            fontsize=12, fontweight="bold", va="center",
                            ha="center")

    # Shared four-item legend, matching Figure 1.
    handles = [
        Line2D([], [], color="0.25", lw=1.7, ls="-", marker="o", ms=3.2),
        Line2D([], [], color="0.25", lw=1.5, ls=(0, (5, 3)), marker="o", ms=3.2),
        Patch(facecolor=C_SHADE, alpha=0.6),
        Line2D([], [], color=C_LINE, lw=1.2, ls=(0, (4, 3))),
    ]
    labels = ["Actual (observed)", "Synthetic counterfactual",
              "Post-treatment period", "Intervention year"]
    fig.legend(handles, labels, frameon=False, fontsize=9.5,
               loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=(0.02, 0.05, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(f"{OUT}.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"saved {OUT}.pdf / .png")


if __name__ == "__main__":
    main()
