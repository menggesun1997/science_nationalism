# -*- coding: utf-8 -*-
# ITS 诊断: 量化三国 pre 期是否近似线性 + post 点数 + 自相关。
# 对每个 focal 报告:
#   - n_pre / n_post (点数, 判断自由度)
#   - pre 线性 R^2 (直线对 pre 期的解释力)
#   - pre 二次项检验 (加 rel_year^2, 若显著 -> pre 弯曲, 非线性)
#   - 全样本 ITS 的 Durbin-Watson (自相关诊断)
#   - OLS vs Newey-West(HAC) 下 beta1 的 p 值对比
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

ROOT = "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code"
FOCALS = [("uk", "GBR", 2016, "United Kingdom — Brexit (2016)"),
          ("russia", "RUS", 2022, "Russia — invasion (2022)"),
          ("ukraine", "UKR", 2022, "Ukraine — invasion (2022)")]


def load_series(tag, t0):
    d = f"{ROOT}/3ppml_migration_did_{tag}_internal_control"
    i = (pd.read_csv(f"{d}/ppml_data_in.csv")
         .groupby(["year", "rel_year"], as_index=False).paper_count.sum()
         .rename(columns={"paper_count": "inflow"}))
    o = (pd.read_csv(f"{d}/ppml_data_out.csv")
         .groupby("year", as_index=False).paper_count.sum()
         .rename(columns={"paper_count": "outflow"}))
    m = i.merge(o, on="year").sort_values("year").reset_index(drop=True)
    m["net_inflow"] = m.inflow - m.outflow
    m["post"] = (m.year >= t0).astype(int)
    m["rel_year2"] = m.rel_year ** 2
    return m


def diagnose(m, foc, title):
    pre = m[m.post == 0]
    post = m[m.post == 1]
    n_pre, n_post = len(pre), len(post)

    # pre 线性拟合
    lin = smf.ols("net_inflow ~ rel_year", data=pre).fit()
    r2_lin = lin.rsquared

    # pre 二次项检验: 若 rel_year^2 显著 -> 非线性
    quad = smf.ols("net_inflow ~ rel_year + rel_year2", data=pre).fit()
    p_quad = quad.pvalues.get("rel_year2", np.nan)
    r2_quad = quad.rsquared

    # 全样本 ITS: OLS vs Newey-West
    ols = smf.ols("net_inflow ~ post + rel_year", data=m).fit()
    dw = durbin_watson(ols.resid)
    # Newey-West HAC, lag=1
    hac = smf.ols("net_inflow ~ post + rel_year", data=m).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1})

    print("=" * 74)
    print(f"{foc}  |  {title}")
    print("-" * 74)
    print(f"  点数: n_pre={n_pre}, n_post={n_post}  "
          f"(post 点数<3 时断点自由度极低)")
    print(f"  pre 线性 R^2         = {r2_lin:5.3f}   "
          f"(越低=直线越难概括 pre)")
    print(f"  pre 加二次项 R^2      = {r2_quad:5.3f}")
    print(f"  pre 二次项 p 值       = {p_quad:5.3f}   "
          f"({'显著->pre弯曲/非线性' if p_quad < 0.1 else '不显著->线性尚可'})")
    print(f"  Durbin-Watson       = {dw:5.3f}   "
          f"(远离2=有自相关; <1.5 或 >2.5 需警惕)")
    print(f"  beta1  OLS   : {ols.params['post']:8.1f}  p={ols.pvalues['post']:.3f}")
    print(f"  beta1  Newey : {hac.params['post']:8.1f}  p={hac.pvalues['post']:.3f}"
          f"   <- 修正自相关后的 p")
    return dict(focal=foc, n_pre=n_pre, n_post=n_post, r2_lin=r2_lin,
                p_quad=p_quad, dw=dw,
                b1=ols.params["post"], p1_ols=ols.pvalues["post"],
                p1_hac=hac.pvalues["post"])


def main():
    rows = []
    for tag, foc, t0, title in FOCALS:
        m = load_series(tag, t0)
        rows.append(diagnose(m, foc, title))
    print("=" * 74)
    df = pd.DataFrame(rows)
    out = f"{ROOT}/0raw_publiations_process/raw data processing/its_own_data/its_diagnostics.csv"
    df.to_csv(out, index=False)
    print("saved:", out)


if __name__ == "__main__":
    main()
