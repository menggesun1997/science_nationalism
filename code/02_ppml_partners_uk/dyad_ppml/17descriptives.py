#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯描述性统计：EU-27 对外合作的构成与份额演变。

不涉及任何回归，只看原始计数和占比，用来判断 mu_it 这个参照基准是由
哪些伙伴构成的。

口径说明
  计数为 **dyad-year 加总**：一篇德法英合著论文在 GERMANY-FRANCE、
  GERMANY-UK、FRANCE-UK 三个 dyad 里各计一次。看份额趋势时分子分母
  同口径，不影响结论；但绝对数大于实际论文数。

分组
  EU-internal  伙伴是其他 EU-27 成员
  UK           伙伴是英国
  CHINA+US     伙伴是中国或美国
  other        其余第三国

输出 desc_eu_portfolio.csv        逐年构成与份额
     desc_eu_portfolio_by_country.csv  各 EU 国家的 UK 依赖度
     desc_eu_portfolio.pdf/.png   堆叠面积图 + 份额折线
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator

HERE = Path(__file__).resolve().parent
PANEL = HERE / "dyad_panel.csv"

UK = "UNITED KINGDOM"
CN_US = {"CHINA", "UNITED STATES"}

EU27 = {
    "AUSTRIA", "BELGIUM", "BULGARIA", "CROATIA", "CYPRUS", "CZECHIA",
    "DENMARK", "ESTONIA", "FINLAND", "FRANCE", "GERMANY", "GREECE",
    "HUNGARY", "IRELAND", "ITALY", "LATVIA", "LITHUANIA", "LUXEMBOURG",
    "MALTA", "NETHERLANDS", "POLAND", "PORTUGAL", "ROMANIA",
    "SLOVAK REPUBLIC", "SLOVENIA", "SPAIN", "SWEDEN",
}

GROUPS = ["EU-internal", "UK", "CHINA+US", "other"]
COLOURS = {"EU-internal": "#214194", "UK": "#BE2738",
           "CHINA+US": "#D7B754", "other": "#A8B4C8"}


def classify(p: str) -> str:
    if p == UK:
        return "UK"
    if p in EU27:
        return "EU-internal"
    if p in CN_US:
        return "CHINA+US"
    return "other"


def load() -> pd.DataFrame:
    d = pd.read_csv(PANEL)
    d["group"] = d["partner_country"].map(classify)
    return d


def yearly_pooled(d: pd.DataFrame) -> pd.DataFrame:
    """口径一：把 EU-27 合并成一个实体再算份额（按合作量加权）。

    等价于对各国份额按其合作总量加权平均，因此由德法意西等大国主导。
    """
    t = (d.pivot_table(index="year", columns="group", values="paper_count",
                       aggfunc="sum", fill_value=0)
         .reindex(columns=GROUPS, fill_value=0))
    t["total"] = t.sum(axis=1)
    for g in GROUPS:
        t[f"sh_{g}"] = 100 * t[g] / t["total"]
    return t


def yearly_unweighted(d: pd.DataFrame) -> pd.DataFrame:
    """口径二：先算每个 EU 国家各自的份额，再对 27 国取未加权平均。

    每国等权，反映"典型成员国"的组合构成，不被大国主导。
    同时返回跨国标准差与分位数，便于看成员国之间的离散程度。
    """
    # 每个 (focal, year) 的分组份额
    per = (d.pivot_table(index=["focal_country", "year"], columns="group",
                         values="paper_count", aggfunc="sum", fill_value=0)
           .reindex(columns=GROUPS, fill_value=0))
    tot = per.sum(axis=1)
    sh = per.div(tot, axis=0) * 100
    sh = sh.reset_index()

    out = sh.groupby("year")[GROUPS].mean()
    out.columns = [f"sh_{g}" for g in GROUPS]
    for g in GROUPS:
        gr = sh.groupby("year")[g]
        out[f"sd_{g}"] = gr.std()
        out[f"p25_{g}"] = gr.quantile(0.25)
        out[f"p50_{g}"] = gr.median()
        out[f"p75_{g}"] = gr.quantile(0.75)
    return out, sh


def by_country_table(d: pd.DataFrame) -> pd.DataFrame:
    """各 EU 国家：EU 内部 vs UK 的份额，pre/post 对比。"""
    d = d.copy()
    d["period"] = d["year"].apply(lambda y: "pre" if y <= 2016 else "post")
    rows = []
    for focal, g in d.groupby("focal_country"):
        rec = {"focal_country": focal}
        for per in ("pre", "post"):
            s = g[g["period"] == per]
            tot = s["paper_count"].sum()
            for grp in ("EU-internal", "UK"):
                v = s.loc[s["group"] == grp, "paper_count"].sum()
                rec[f"sh_{grp}_{per}"] = 100 * v / tot if tot else float("nan")
        rec["d_UK"] = rec["sh_UK_post"] - rec["sh_UK_pre"]
        rec["d_EU"] = rec["sh_EU-internal_post"] - rec["sh_EU-internal_pre"]
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("sh_UK_pre", ascending=False)


def integer_xaxis(ax) -> None:
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(round(v))}"))


def plot(tp: pd.DataFrame, tu: pd.DataFrame, sh: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
    ax1, ax2, ax3 = axes
    yrs = tu.index.to_numpy()

    # 左：未加权均值的份额堆叠
    ax1.stackplot(yrs, *[tu[f"sh_{g}"].to_numpy() for g in GROUPS],
                  labels=GROUPS, colors=[COLOURS[g] for g in GROUPS],
                  alpha=0.9)
    ax1.set_ylim(0, 100)
    ax1.set_xlim(yrs.min(), yrs.max())
    ax1.set_ylabel("Mean share across EU-27 members (%)")
    ax1.set_xlabel("Year")
    ax1.set_title("Portfolio composition\n(unweighted country mean)",
                  fontsize=11)

    # 中：UK 份额，两种口径对比 + 跨国四分位带
    ax2.fill_between(yrs, tu["p25_UK"], tu["p75_UK"], color=COLOURS["UK"],
                     alpha=0.15, lw=0, label="IQR across members")
    ax2.plot(yrs, tu["sh_UK"], marker="o", ms=4, color=COLOURS["UK"],
             lw=1.8, label="unweighted mean")
    ax2.plot(yrs, tp["sh_UK"], marker="s", ms=3.5, color="#444444",
             lw=1.4, ls="--", label="EU-27 pooled")
    ax2.axvline(2016.5, color="#888888", ls=":", lw=1.2)
    ax2.set_ylabel("UK share (%)")
    ax2.set_xlabel("Year")
    ax2.set_title("UK share of each member's portfolio", fontsize=11)
    ax2.grid(alpha=0.25, ls=":")
    ax2.legend(frameon=False, fontsize=8.5, loc="upper right")

    # 右：中美份额，同样两种口径
    ax3.fill_between(yrs, tu["p25_CHINA+US"], tu["p75_CHINA+US"],
                     color=COLOURS["CHINA+US"], alpha=0.2, lw=0,
                     label="IQR across members")
    ax3.plot(yrs, tu["sh_CHINA+US"], marker="o", ms=4,
             color=COLOURS["CHINA+US"], lw=1.8, label="unweighted mean")
    ax3.plot(yrs, tp["sh_CHINA+US"], marker="s", ms=3.5, color="#444444",
             lw=1.4, ls="--", label="EU-27 pooled")
    ax3.axvline(2016.5, color="#888888", ls=":", lw=1.2)
    ax3.set_ylabel("China + US share (%)")
    ax3.set_xlabel("Year")
    ax3.set_title("China + US share", fontsize=11)
    ax3.grid(alpha=0.25, ls=":")
    ax3.legend(frameon=False, fontsize=8.5, loc="upper right")

    for ax in axes:
        integer_xaxis(ax)

    h1, l1 = ax1.get_legend_handles_labels()
    fig.legend(h1, l1, frameon=False, loc="lower center", ncol=len(l1),
               bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    for ext in ("pdf", "png"):
        fig.savefig(HERE / f"desc_eu_portfolio.{ext}", dpi=300,
                    bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    d = load()
    tp = yearly_pooled(d)
    tu, sh = yearly_unweighted(d)

    pd.set_option("display.width", 220)

    print("=" * 78)
    print("Shares (%): unweighted mean across the 27 member states")
    print("  (each country's own share computed first, then averaged)")
    print("=" * 78)
    u = tu[[f"sh_{g}" for g in GROUPS]].copy()
    u.columns = GROUPS
    print(u.to_string(float_format="%.2f"))

    print("\n" + "=" * 78)
    print("Same, pooled (EU-27 treated as one entity, volume-weighted)")
    print("=" * 78)
    p = tp[[f"sh_{g}" for g in GROUPS]].copy()
    p.columns = GROUPS
    print(p.to_string(float_format="%.2f"))

    print("\n" + "=" * 78)
    print("Change 2005 -> 2024 (percentage points)")
    print("=" * 78)
    print(f"  {'group':<14} {'unweighted':>22}   {'pooled':>22}")
    for g in GROUPS:
        ua, ub = u[g].iloc[0], u[g].iloc[-1]
        pa, pb = p[g].iloc[0], p[g].iloc[-1]
        print(f"  {g:<14} {ua:>6.2f} -> {ub:>6.2f} ({ub-ua:+6.2f}pp)"
              f"   {pa:>6.2f} -> {pb:>6.2f} ({pb-pa:+6.2f}pp)")

    print("\n  pre (2005-2016) vs post (2017-2024), unweighted mean:")
    pre = sh[sh["year"] <= 2016]
    post = sh[sh["year"] >= 2017]
    for g in GROUPS:
        a, b = pre[g].mean(), post[g].mean()
        print(f"  {g:<14} {a:>6.2f}  ->  {b:>6.2f}   {b - a:+6.2f} pp")

    print("\n" + "=" * 78)
    print("Dispersion across members (unweighted), UK share")
    print("=" * 78)
    print(tu[["sh_UK", "sd_UK", "p25_UK", "p50_UK", "p75_UK"]].to_string(
        float_format="%.2f"))

    bc = by_country_table(d)
    print("\n" + "=" * 78)
    print("By EU country: EU-internal and UK shares, pre vs post (%)")
    print("=" * 78)
    show = bc.rename(columns={
        "sh_EU-internal_pre": "EUint_pre", "sh_EU-internal_post": "EUint_post",
        "sh_UK_pre": "UK_pre", "sh_UK_post": "UK_post"})
    print(show[["focal_country", "EUint_pre", "EUint_post", "d_EU",
                "UK_pre", "UK_post", "d_UK"]].to_string(
                    index=False, float_format="%.2f"))

    tu.to_csv(HERE / "desc_eu_portfolio.csv")
    tp.to_csv(HERE / "desc_eu_portfolio_pooled.csv")
    sh.to_csv(HERE / "desc_shares_country_year.csv", index=False)
    bc.to_csv(HERE / "desc_eu_portfolio_by_country.csv", index=False)
    plot(tp, tu, sh)
    print("\nsaved desc_eu_portfolio.csv (unweighted, main)")
    print("      desc_eu_portfolio_pooled.csv")
    print("      desc_shares_country_year.csv  (country x year shares)")
    print("      desc_eu_portfolio_by_country.csv")
    print("      desc_eu_portfolio.pdf / .png")


if __name__ == "__main__":
    main()
