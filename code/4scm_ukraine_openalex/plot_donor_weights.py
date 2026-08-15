# -*- coding: utf-8 -*-
# Bar chart of positive SCM donor weights (Ukraine nested main estimate).
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = "C:/Users/91916/Dropbox/GitHub/sicence nationism/code/4scm_ukraine_openalex"

# Nested main estimate weights from scm_ukraine.log
weights = [
    ("Hungary", 0.378),
    ("Iraq", 0.214),
    ("Indonesia", 0.209),
    ("Vietnam", 0.200),
]
names = [w[0] for w in weights]
vals = [w[1] for w in weights]

fig, ax = plt.subplots(figsize=(8.2, 4.8))
bars = ax.bar(names, vals, color="#2c6fbb", width=0.65, edgecolor="none")
ax.set_ylabel("Donor weight")
ax.set_xlabel("")
ax.set_ylim(0, max(vals) * 1.18)
ax.yaxis.grid(True, alpha=0.3)
ax.set_axisbelow(True)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

for bar, v in zip(bars, vals):
    ax.text(bar.get_x() + bar.get_width() / 2, v + 0.012, f"{v:.3f}",
            ha="center", va="bottom", fontsize=10)

ax.set_title("Synthetic Ukraine: donor country weights")
fig.tight_layout()
for ext in ("png", "pdf"):
    out = f"{DIR}/results/scm_donor_weights.{ext}"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("saved:", out)
