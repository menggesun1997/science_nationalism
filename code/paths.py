"""Central path resolution for the Science Nationalism pipeline.

Every path in this repository is derived from the location of this file, so
the code runs unchanged from any checkout directory on any operating system.

Usage from a script anywhere under ``code/``::

    from paths import CODE, RAW_PUBLICATIONS, MIGRATION_2026

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

RAW_PUBLICATIONS = CODE / "0raw_publiations_process"
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

# Stage 1b (1networks_sdid_brexit) originally read from a separate Brexit
# project tree that predates this repository. Those inputs are not part of the
# release; the scripts are kept for provenance. Override the location with:
#     export SCIENCE_NATIONALISM_LEGACY_BREXIT=/path/to/cooperation_related
LEGACY_BREXIT = Path(
    os.environ.get(
        "SCIENCE_NATIONALISM_LEGACY_BREXIT",
        RAW_DATA_STORE / "legacy_brexit_cooperation",
    )
).expanduser()

# --- MPIDR Scholarly Migration Database (public; see DATA.md) ----------------

MIGRATION_2026 = (
    MIGRATION_DATA
    / "Global-flows-and-rates-of-international-migration-of-scholars-2026_V2"
    / "2026_V2"
)
MIGRATION_WOS = MIGRATION_DATA / "wos_data"

# --- Analysis stages ---------------------------------------------------------

EVENTS = ("eu", "russia", "uk", "ukraine")

NETWORKS_RUSSIA_UKRAINE = CODE / "1netoworks_did_russia_ukraine"
NETWORKS_BREXIT = CODE / "1networks_sdid_brexit"
FIGURES_OUT = CODE / "picutres"


def ppml_internal(event: str) -> Path:
    """Stage 2 directory for the internal-control PPML DiD of ``event``."""
    _check_event(event)
    return CODE / f"2ppml_did_{event}_internal_control"


def two_way(event: str) -> Path:
    """Stage 3 directory for the external-control two-way DiD of ``event``."""
    _check_event(event)
    return CODE / f"2two_way_did_{event}"


def migration_ppml(event: str, mpidr: bool = False) -> Path:
    """Stage 4 migration-flow directory. ``mpidr=True`` selects the MPIDR
    replication that uses the Scholarly Migration Database instead of WoS."""
    suffix = "_mpidr" if mpidr else ""
    return CODE / f"3ppml_migration_did_{event}_internal_control{suffix}"


def scm(event: str, source: str = "openalex") -> Path:
    """Stage 5 synthetic-control directory. ``source`` is ``openalex`` or ``wos``."""
    if source not in ("openalex", "wos"):
        raise ValueError(f"source must be 'openalex' or 'wos', got {source!r}")
    return CODE / f"4scm_{event}_{source}"


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
    print(f"MIGRATION_2026   {MIGRATION_2026}   exists={MIGRATION_2026.exists()}")
