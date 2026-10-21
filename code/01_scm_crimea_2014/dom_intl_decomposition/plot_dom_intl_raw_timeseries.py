"""Plot observed domestic vs international publication counts over time.

Uses the *raw* data (original_completed.xlsx), not the SCM synthetic series.
Domestic = pub_total - pub_intl; International = pub_intl (co-authored).
Two panels: Russia and Ukraine. A dashed vertical line marks 2014 (Crimea).
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FuncFormatter

HERE = "code/01_scm_crimea_2014/dom_intl_decomposition"
SRC = "code/01_scm_crimea_2014/original_completed.xlsx"

C_TOTAL = "#333333"   # total
C_DOM = "#4C5C9C"     # domestic (blue)
C_INTL = "#C0504D"    # international (red)

df = pd.read_excel(SRC, sheet_name="Sheet1")
df["pub_dom"] = df["pub_total"] - df["pub_intl"]

countries = [
    ("RUSSIAN_FEDERATION", "(a) Russia"),
    ("UKRAINE", "(b) Ukraine"),
]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, (code, title) in zip(axes, countries):
    d = df[df["Country"] == code].sort_values("Year")
    ax.plot(d["Year"], d["pub_total"], color=C_TOTAL, lw=1.8, marker="o",
            ms=4, label="Total")
    ax.plot(d["Year"], d["pub_dom"], color=C_DOM, lw=1.8, marker="s",
            ms=4, label="Domestic (total - intl.)")
    ax.plot(d["Year"], d["pub_intl"], color=C_INTL, lw=1.8, marker="^",
            ms=4, label="International (co-authored)")
    ax.axvline(2014, color="0.35", lw=1.4, ls=(0, (2, 2)))
    ax.set_title(title, fontsize=11, fontweight="bold", pad=6)
    ax.set_xlabel("Year", fontsize=10)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
axes[0].set_ylabel("Publications", fontsize=10)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, frameon=False, fontsize=10, loc="lower center",
           ncol=len(labels), bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.06, 1, 1))
for ext in ("pdf", "png"):
    fig.savefig(f"{HERE}/dom_intl_raw_timeseries.{ext}", dpi=300,
                bbox_inches="tight", facecolor="white")
print("saved dom_intl_raw_timeseries.pdf / .png")
