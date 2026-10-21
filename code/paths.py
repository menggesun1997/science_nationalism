"""Central path resolution for the Science Nationalism pipeline.

Every path in this repository is derived from the location of this file, so
the code runs unchanged from any checkout directory on any operating system.

Usage from a script anywhere under ``code/``::

    from paths import CODE, RAW_PUBLICATIONS

    df = pd.read_csv(RAW_PUBLICATIONS / "countries_yearly_statistics.csv")

Because scripts live at varying depths, add the bootstrap below at the top of
a script before importing (``parents[n]`` must resolve to ``code/``; for a
script directly inside ``code/`` use ``parents[0]``, one level deeper
``parents[1]``, and so on)::

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from paths import CODE

Licensed Web of Science inputs are not distributed with this repository. Point
``SCIENCE_NATIONALISM_RAW`` at your own copy to relocate them without editing
code (see DATA.md)::

    export SCIENCE_NATIONALISM_RAW=/path/to/brexit_rawdata
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Anchors -----------------------------------------------------------------

CODE = Path(__file__).resolve().parent
REPO = CODE.parent

PAPER = REPO / "paper"
MIGRATION_DATA = REPO / "migration_data"

# --- Publication data (licensed; see DATA.md) --------------------------------

RAW_PUBLICATIONS = CODE / "00_data_processing"
RAW_PROCESSING = RAW_PUBLICATIONS / "raw data processing"

# Overridable location of the licensed Clarivate/OST article-level files. The
# default points at the in-repo directory, which in the original working copy
# holds symlinks to an external store.
RAW_DATA_STORE = Path(
    os.environ.get("SCIENCE_NATIONALISM_RAW", RAW_PUBLICATIONS)
).expanduser().resolve()

PUBLICATIONS_RAW = RAW_DATA_STORE / "publications_raw_data"
BREXIT_EXPERIMENTAL = RAW_DATA_STORE / "brexit_experimental_data"
INDICATOR_RAW = RAW_DATA_STORE / "indicator_raw data"
INDICATOR_CLEAN = RAW_DATA_STORE / "indicator_clean_data"
RAW_DATA_2026 = RAW_DATA_STORE / "raw_data_2026"

# Optional / unused by the current paper; kept so leftover scripts still import.
LEGACY_BREXIT = Path(
    os.environ.get(
        "SCIENCE_NATIONALISM_LEGACY_BREXIT",
        RAW_DATA_STORE / "legacy_brexit_cooperation",
    )
).expanduser()
MIGRATION_2026 = (
    MIGRATION_DATA
    / "Global-flows-and-rates-of-international-migration-of-scholars-2026_V2"
    / "2026_V2"
)

# --- Analysis modules (see code/README.md) -----------------------------------

EVENTS = ("eu", "russia", "uk", "ukraine")

WEST_EAST_TILT = CODE / "04_west_east_tilt"
NETWORKS_RUSSIA_UKRAINE = WEST_EAST_TILT  # backward-compatible alias
FIGURES_OUT = CODE / "figures"
SCM_BREXIT = CODE / "01_scm_brexit"
SCM_CRIMEA = CODE / "01_scm_crimea_2014"
SCM_WAR = CODE / "01_scm_war_2022"
BRIDGING = CODE / "06_bridging"


def ppml_internal(event: str) -> Path:
    """Partner-level PPML DiD with internal controls (main-text maps)."""
    _check_event(event)
    return CODE / f"02_ppml_partners_{event}"


def two_way(event: str) -> Path:
    """External-control two-way DiD (SI G)."""
    _check_event(event)
    return CODE / f"03_twoway_did_{event}"


def scm_disciplines(event: str) -> Path:
    """Discipline-level SCM. ``event`` is brexit, crimea_2014, or war_2022."""
    names = {
        "brexit": "05_scm_disciplines_brexit",
        "crimea_2014": "05_scm_disciplines_crimea_2014",
        "war_2022": "05_scm_disciplines_war_2022",
    }
    if event not in names:
        raise ValueError(f"event must be one of {tuple(names)}, got {event!r}")
    return CODE / names[event]


def _check_event(event: str) -> None:
    if event not in EVENTS:
        raise ValueError(f"event must be one of {EVENTS}, got {event!r}")


def require(path: Path, hint: str = "") -> Path:
    """Return ``path``, or raise with an actionable message if it is missing.

    Guards against the two failure modes reviewers hit most often: licensed
    inputs that were never obtained, and Dropbox placeholder files that exist
    but are zero bytes.
    """
    if not path.exists():
        msg = f"Required input not found: {path}"
        if hint:
            msg += f"\n  {hint}"
        msg += "\n  See DATA.md for how to obtain the input data."
        raise FileNotFoundError(msg)
    if path.is_file() and path.stat().st_size == 0:
        raise FileNotFoundError(
            f"Input exists but is empty (0 bytes): {path}\n"
            "  This is typically an unsynced cloud-storage placeholder.\n"
            "  See DATA.md."
        )
    return path


if __name__ == "__main__":
    print(f"REPO             {REPO}")
    print(f"CODE             {CODE}")
    print(f"PAPER            {PAPER}   exists={PAPER.exists()}")
    print(f"RAW_DATA_STORE   {RAW_DATA_STORE}")
    print(f"FIGURES_OUT      {FIGURES_OUT}")
