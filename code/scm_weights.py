#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read donor weights exported by the SCM do-files.

Every ``compare*.do`` writes ``<unit>_weights_country.xlsx`` next to itself with
columns ``country_id``, ``Country`` and ``_W_Weight``. These helpers load that
file so the lollipop figures and the SI weight tables stay in sync with the
Stata output instead of repeating hard-coded literals.
"""

from pathlib import Path

import pandas as pd

WEIGHT_COL = "_W_Weight"
COUNTRY_COL = "Country"

# Countries are stored upper-case with underscores (RUSSIAN_FEDERATION,
# COSTA_RICA). These are the display forms used in the paper.
DISPLAY_NAMES = {
    "RUSSIAN_FEDERATION": "Russia",
    "UNITED_STATES": "USA",
    "UNITED_KINGDOM": "UK",
    "KOREA,_REP.": "Korea",
    "KOREA": "Korea",
    "SLOVAK_REPUBLIC": "Slovak Republic",
    "COSTA_RICA": "Costa Rica",
    "SOUTH_AFRICA": "South Africa",
    "TURKIYE": "Türkiye",
    "EU": "EU",
}


def display_name(raw: str) -> str:
    """Map a Stata country label to the form used in the paper."""
    key = str(raw).strip().upper()
    if key in DISPLAY_NAMES:
        return DISPLAY_NAMES[key]
    return key.replace("_", " ").title()


def load_weights(path, drop_zero=True, min_weight=0.0):
    """Load one weights xlsx as a DataFrame sorted by descending weight.

    ``drop_zero`` removes donors the optimiser assigned no weight; treated units
    appear with a missing weight and are always removed. ``min_weight`` filters
    donors below a threshold, useful for readable figures.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Weights file not found: {path}\n"
            "Run the corresponding compare*.do first."
        )

    frame = pd.read_excel(path)
    missing = {COUNTRY_COL, WEIGHT_COL} - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing column(s): {sorted(missing)}")

    frame = frame.dropna(subset=[WEIGHT_COL]).copy()
    frame[WEIGHT_COL] = frame[WEIGHT_COL].astype(float)

    if drop_zero:
        frame = frame[frame[WEIGHT_COL] > 0]
    if min_weight > 0:
        frame = frame[frame[WEIGHT_COL] >= min_weight]

    frame["label"] = frame[COUNTRY_COL].map(display_name)
    return frame.sort_values(WEIGHT_COL, ascending=False).reset_index(drop=True)


def top_donors(path, top_n=4, min_weight=0.0):
    """Return ``(labels, weights)`` for the ``top_n`` heaviest donors."""
    frame = load_weights(path, drop_zero=True, min_weight=min_weight)
    if frame.empty:
        raise ValueError(f"No non-zero donor weights in {path}")
    if top_n is not None:
        frame = frame.head(top_n)
    return frame["label"].tolist(), frame[WEIGHT_COL].tolist()
