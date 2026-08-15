# -*- coding: utf-8 -*-
"""Run leave-one-out SCM for Russia / Ukraine via Stata, then summarize."""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

STATA = Path(r"C:\Program Files\Stata18\StataMP-64.exe")
REPO_CODE = Path(__file__).resolve().parents[1]

ISO_NAME = {
    "IDN": "Indonesia", "IRN": "Iran", "AUS": "Australia",
    "GBR": "United Kingdom", "IND": "India",
    "HUN": "Hungary", "IRQ": "Iraq", "VNM": "Vietnam",
}

SPECS = {
    "russia": {
        "dir": REPO_CODE / "4scm_russia_openalex",
        "trt": "RUS",
        "outprefix": "scm_russia",
        "baseline_frame": "results/scm_russia_frame.csv",
        "drop": ["IDN", "IRN", "AUS", "GBR", "IND"],
        "title": "Russia",
    },
    "ukraine": {
        "dir": REPO_CODE / "4scm_ukraine_openalex",
        "trt": "UKR",
        "outprefix": "scm_ukraine",
        "baseline_frame": "results/scm_ukraine_frame.csv",
        "drop": ["HUN", "IRQ", "IDN", "VNM"],
        "title": "Ukraine",
    },
}

T0 = 2022


def metrics_from_frame(path: Path, trt: str) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    synth_key = next(k for k in rows[0] if k.startswith("pred"))
    gap_key = next(k for k in rows[0] if k.startswith("tr"))

    by = {}
    for r in rows:
        c = r["cid"]
        by.setdefault(c, []).append(r)
    for c in by:
        by[c].sort(key=lambda r: int(r["year"]))

    pre_mspe, post_mspe, att = {}, {}, {}
    for c, g in by.items():
        years = np.array([int(r["year"]) for r in g])
        gap = np.array([float(r[gap_key]) for r in g])
        pre_mspe[c] = float(np.mean(gap[years < T0] ** 2))
        post_mspe[c] = float(np.mean(gap[years >= T0] ** 2))
        att[c] = float(np.mean(gap[years >= T0]))
        # also yearly for treated
        if c == trt:
            yearly = {int(r["year"]): float(r[gap_key]) for r in g}

    ratio = {c: post_mspe[c] / pre_mspe[c] if pre_mspe[c] > 0 else np.nan for c in by}
    trt_ratio = ratio[trt]
    p = sum(1 for c in by if ratio[c] >= trt_ratio) / len(by)
    return {
        "att": att[trt],
        "p_mspe": p,
        "pre_rmspe": float(np.sqrt(pre_mspe[trt])),
        "ratio": trt_ratio,
        "n": len(by),
        "gap_2022": yearly.get(2022, np.nan),
        "gap_2023": yearly.get(2023, np.nan),
        "gap_2024": yearly.get(2024, np.nan),
    }


def write_driver(spec: dict, excl: str) -> Path:
    d = spec["dir"]
    loo_dir = d / "results" / "loo"
    loo_dir.mkdir(parents=True, exist_ok=True)
    driver = loo_dir / f"_run_drop_{excl}.do"
    # paths with spaces: quote carefully for Stata
    dir_posix = str(d).replace("\\", "/")
    text = f'''
clear all
set more off
global DIR "{dir_posix}"
global TRTISO "{spec["trt"]}"
global OUTPREFIX "{spec["outprefix"]}"
do "{dir_posix}/loo_one.do" "{excl}"
'''
    driver.write_text(text, encoding="utf-8")
    return driver


def run_stata(driver: Path, cwd: Path) -> None:
    log = cwd / "results" / "loo" / (driver.stem + ".log")
    cmd = [str(STATA), "/e", "do", str(driver)]
    print("RUNNING:", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=False)
    # Stata writes log next to do-file by default when using /e do
    print("finished", driver.name)


def ensure_loo_do(spec: dict) -> None:
    src = REPO_CODE / "4scm_russia_openalex" / "loo_one.do"
    dst = spec["dir"] / "loo_one.do"
    if spec["dir"].name != "4scm_russia_openalex":
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def collect(spec: dict) -> list[dict]:
    rows = []
    # baseline
    base = spec["dir"] / spec["baseline_frame"]
    m = metrics_from_frame(base, spec["trt"])
    rows.append({"case": "baseline", "dropped": "", "dropped_name": "Baseline (all donors)", **m})
    for excl in spec["drop"]:
        path = spec["dir"] / "results" / "loo" / f"{spec['outprefix']}_loo_drop_{excl}.csv"
        if not path.exists():
            print("MISSING", path)
            continue
        m = metrics_from_frame(path, spec["trt"])
        rows.append({
            "case": f"drop_{excl}",
            "dropped": excl,
            "dropped_name": f"Drop {ISO_NAME.get(excl, excl)}",
            **m,
        })
    return rows


def save_summary(spec: dict, rows: list[dict]) -> Path:
    out = spec["dir"] / "results" / "loo" / "loo_summary.csv"
    fields = ["case", "dropped", "dropped_name", "att", "p_mspe", "pre_rmspe",
              "ratio", "n", "gap_2022", "gap_2023", "gap_2024"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return out


def plot_summary(spec: dict, rows: list[dict]) -> None:
    labels = [r["dropped_name"] for r in rows]
    atts = [r["att"] for r in rows]
    ps = [r["p_mspe"] for r in rows]

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    colors = ["#2c6fbb" if r["case"] == "baseline" else "#6c757d" for r in rows]
    y = np.arange(len(rows))

    ax[0].barh(y, atts, color=colors, height=0.6)
    ax[0].axvline(0, color="black", lw=0.6)
    ax[0].set_yticks(y)
    ax[0].set_yticklabels(labels)
    ax[0].invert_yaxis()
    ax[0].set_xlabel("AVG EFFECT (persons / year)")
    ax[0].set_title(f"{spec['title']}: LOO average effect")
    for yi, v in zip(y, atts):
        ax[0].text(v - 40 if v < 0 else v + 40, yi, f"{v:,.0f}",
                   va="center", ha="right" if v < 0 else "left", fontsize=8)

    ax[1].barh(y, ps, color=colors, height=0.6)
    ax[1].axvline(0.05, color="#c0392b", ls=":", lw=1.2, label="p=0.05")
    ax[1].set_yticks(y)
    ax[1].set_yticklabels(labels)
    ax[1].invert_yaxis()
    ax[1].set_xlabel("MSPE-ratio p-value")
    ax[1].set_title(f"{spec['title']}: LOO MSPE-ratio p")
    ax[1].set_xlim(0, max(0.2, max(ps) * 1.25))
    ax[1].legend(loc="lower right", fontsize=8)
    for yi, v in zip(y, ps):
        ax[1].text(v + 0.005, yi, f"{v:.3f}", va="center", fontsize=8)

    fig.suptitle(f"Leave-one-out robustness — {spec['title']} scholar inflow SCM", y=1.02)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        p = spec["dir"] / "results" / "loo" / f"loo_summary.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print("saved", p)


def run_case(name: str, only_summarize: bool = False) -> None:
    spec = SPECS[name]
    ensure_loo_do(spec)
    (spec["dir"] / "results" / "loo").mkdir(parents=True, exist_ok=True)

    if not only_summarize:
        for excl in spec["drop"]:
            out_csv = spec["dir"] / "results" / "loo" / f"{spec['outprefix']}_loo_drop_{excl}.csv"
            if out_csv.exists():
                print("skip existing", out_csv.name)
                continue
            driver = write_driver(spec, excl)
            run_stata(driver, spec["dir"])

    rows = collect(spec)
    out = save_summary(spec, rows)
    print("summary:", out)
    for r in rows:
        print(f"  {r['dropped_name']}: ATT={r['att']:.1f}, p={r['p_mspe']:.3f}, "
              f"preRMSPE={r['pre_rmspe']:.1f}, N={r['n']}")
    plot_summary(spec, rows)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    only = "--summarize" in args
    args = [a for a in args if a != "--summarize"]
    targets = args or ["russia", "ukraine"]
    for t in targets:
        run_case(t, only_summarize=only)
