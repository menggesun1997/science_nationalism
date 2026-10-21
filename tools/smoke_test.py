"""Smoke-test the pipeline without running any estimation.

Checks that each mainline script could start: that its imports resolve, its
declared inputs exist and are non-empty, and that the Stata commands it calls
are installed. Reports a per-stage runnability table.

    python tools/smoke_test.py              # all checks
    python tools/smoke_test.py --no-stata   # skip the Stata probe
    python tools/smoke_test.py --json out.json

Exit status is 0 even when scripts are unrunnable: missing licensed inputs are
expected in a public checkout. A non-zero status signals a broken check.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODE = REPO / "code"

# Modules resolved from code/ rather than site-packages.
LOCAL_MODULES = {"paths"}

# sys.stdlib_module_names requires Python 3.10.
try:
    STDLIB = set(sys.stdlib_module_names)
except AttributeError:
    STDLIB = {
        "abc", "argparse", "ast", "base64", "bisect", "collections", "colorsys",
        "concurrent", "contextlib", "copy", "csv", "ctypes", "dataclasses",
        "datetime", "decimal", "difflib", "enum", "functools", "glob", "gzip",
        "hashlib", "heapq", "html", "http", "importlib", "inspect", "io",
        "itertools", "json", "logging", "math", "multiprocessing", "operator",
        "os", "pathlib", "pickle", "platform", "pprint", "queue", "random",
        "re", "shutil", "signal", "site", "socket", "sqlite3", "statistics",
        "string", "subprocess", "sys", "tempfile", "textwrap", "threading",
        "time", "timeit", "traceback", "types", "typing", "unicodedata",
        "unittest", "urllib", "uuid", "warnings", "xml", "zipfile", "zlib",
        "__future__",
    }

# Third-party import name -> pip distribution name, where they differ.
DIST_NAME = {
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "yaml": "PyYAML",
    "adjustText": "adjustText",
    "cartopy": "Cartopy",
}

STATA_COMMANDS = [
    "synth", "synth2", "ppmlhdfe", "reghdfe", "sdid",
    "estout", "parmest", "ftools",
]


@dataclass
class Result:
    script: str
    stage: str
    kind: str
    imports_ok: bool = True
    missing_imports: list[str] = field(default_factory=list)
    inputs_declared: int = 0
    inputs_missing: list[str] = field(default_factory=list)
    inputs_empty: list[str] = field(default_factory=list)
    stata_cmds: list[str] = field(default_factory=list)
    abs_paths: list[str] = field(default_factory=list)
    syntax_ok: bool = True
    note: str = ""

    @property
    def runnable(self) -> bool:
        return (
            self.syntax_ok
            and self.imports_ok
            and not self.inputs_missing
            and not self.inputs_empty
        )


STAGES = [
    ("00  data processing", ["00_data_processing"]),
    ("01  SCM aggregate", ["01_scm_brexit", "01_scm_crimea_2014",
                           "01_scm_war_2022", "00_master.do",
                           "99_combine_figure1.do"]),
    ("02  PPML partners", ["02_ppml_partners_"]),
    ("03  two-way DiD", ["03_twoway_did_"]),
    ("04  West-East tilt", ["04_west_east_tilt"]),
    ("05  SCM disciplines", ["05_scm_disciplines_"]),
    ("06  bridging", ["06_bridging"]),
    ("Utilities", ["extract_avg_effects", "visualize_effects",
                   "normalize_country_names", "visualization/",
                   "99_utilities"]),
]


def stage_of(rel: str) -> str:
    for name, prefixes in STAGES:
        if any(p in rel for p in prefixes):
            return name
    return "Other"


def module_available(name: str) -> bool:
    if name in LOCAL_MODULES or name in STDLIB:
        return True
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def check_python(path: Path) -> Result:
    rel = str(path.relative_to(CODE))
    r = Result(script=rel, stage=stage_of(rel), kind="python")
    src = path.read_text(encoding="utf-8", errors="replace")

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        r.syntax_ok = False
        r.note = f"SyntaxError line {e.lineno}: {e.msg}"
        return r

    top_level = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top_level.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                top_level.add(node.module.split(".")[0])

    for mod in sorted(top_level):
        if not module_available(mod):
            r.missing_imports.append(DIST_NAME.get(mod, mod))
    r.imports_ok = not r.missing_imports

    r.abs_paths = find_abs_paths(src)
    check_declared_inputs(src, r, path)
    return r


ABS_PATH_RE = re.compile(
    r"""['"](/Users/[^'"]+|[A-Za-z]:[/\\][^'"]+|/home/[^'"]+)['"]"""
)


# Executable locations probed as fallbacks are legitimate, unlike hard-coded
# data paths: the script tries each in turn and honours an env-var override.
EXECUTABLE_RE = re.compile(
    r"(?:Stata|stata)[^/\\]*\.(?:exe|app)|/Applications/Stata|StataMP|StataSE"
)


def find_abs_paths(src: str) -> list[str]:
    out = []
    for m in ABS_PATH_RE.finditer(src):
        p = m.group(1)
        # Shebangs and interpreter paths are not data paths.
        if p.startswith(("/usr/", "/bin/", "/opt/homebrew/bin")):
            continue
        if EXECUTABLE_RE.search(p):
            continue
        out.append(p)
    return out[:5]


# Reads whose target is a literal path we can check.
READ_RE = re.compile(
    r"""(?:read_csv|read_excel|read_parquet|read_stata|read_table|open)\s*\(\s*(?:r?)['"]([^'"]+)['"]"""
)
# Reads built from a paths.py anchor, e.g. str(CODE / "a/b.csv")
ANCHOR_RE = re.compile(
    r"""\b(CODE|REPO|RAW_DATA_STORE|MIGRATION_2026|LEGACY_BREXIT)\s*/\s*['"]([^'"]+)['"]"""
)

ANCHORS = {
    "CODE": CODE,
    "REPO": REPO,
    "RAW_DATA_STORE": Path(
        os.environ.get("SCIENCE_NATIONALISM_RAW", CODE / "00_data_processing")
    ),
    "MIGRATION_2026": REPO / "migration_data"
    / "Global-flows-and-rates-of-international-migration-of-scholars-2026_V2"
    / "2026_V2",
    "LEGACY_BREXIT": Path(
        os.environ.get(
            "SCIENCE_NATIONALISM_LEGACY_BREXIT",
            CODE / "00_data_processing" / "legacy_brexit_cooperation",
        )
    ),
}

# Extensions worth checking; skip outputs and globs.
DATA_EXT = {".csv", ".xlsx", ".xls", ".txt", ".parquet", ".dta", ".shp", ".json"}

# Assignment to a name that denotes an output, or a write call on the same line.
WRITE_HINT_RE = re.compile(
    r"(?:out(?:put)?\w*|save\w*|dest\w*|target\w*)\s*(?:_\w+)?\s*=\s*$"
    r"|to_(?:csv|excel|parquet|stata)\s*\($"
    r"|savefig\s*\($",
    re.IGNORECASE,
)


def is_write_target(src: str, pos: int) -> bool:
    """True when the path literal at ``pos`` is being written, not read."""
    line_start = src.rfind("\n", 0, pos) + 1
    prefix = src[line_start:pos]
    # Strip the wrapper that precedes the anchor, e.g. 'str(' or 'Path('.
    prefix = re.sub(r"(?:str|Path|os\.fspath)\s*\($", "", prefix.rstrip())
    return bool(WRITE_HINT_RE.search(prefix.rstrip()))


def check_declared_inputs(src: str, r: Result, path: Path) -> None:
    candidates: set[Path] = set()

    for m in ANCHOR_RE.finditer(src):
        anchor, tail = m.group(1), m.group(2)
        # "{" marks an f-string placeholder resolved at run time.
        if "*" in tail or "{" in tail:
            continue
        # Distinguish reads from writes: a path only ever written to is an
        # output, and its absence is expected before the script runs.
        if is_write_target(src, m.start()):
            continue
        p = ANCHORS[anchor] / tail
        if p.suffix.lower() in DATA_EXT:
            candidates.add(p)

    for m in READ_RE.finditer(src):
        raw = m.group(1)
        if raw.startswith(("http://", "https://")) or "*" in raw or "{" in raw:
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = path.parent / p
        if p.suffix.lower() in DATA_EXT:
            candidates.add(p)

    for p in sorted(candidates):
        r.inputs_declared += 1
        try:
            if not p.exists():
                r.inputs_missing.append(relative(p))
            elif p.is_file() and p.stat().st_size == 0:
                r.inputs_empty.append(relative(p))
        except OSError:
            r.inputs_missing.append(relative(p))


def relative(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


DO_READ_RE = re.compile(
    r"""(?:use|import\s+excel|import\s+delimited|merge\s+\d:\d\s+\w+\s+using)\s+"([^"]+)\"""",
    re.IGNORECASE,
)

# Stata local/global macros expand at run time, so a path containing one cannot
# be checked statically: `discipline' and `country' are loop variables.
STATA_MACRO_RE = re.compile(r"`|\$\{?\w")


def check_do(path: Path, installed: dict[str, bool] | None) -> Result:
    rel = str(path.relative_to(CODE))
    r = Result(script=rel, stage=stage_of(rel), kind="stata")
    src = path.read_text(encoding="utf-8", errors="replace")

    opens = src.count("{")
    closes = src.count("}")
    if opens != closes:
        r.syntax_ok = False
        r.note = f"unbalanced braces: {{={opens} }}={closes}"

    for cmd in STATA_COMMANDS:
        if re.search(rf"^\s*{cmd}\b", src, re.MULTILINE):
            r.stata_cmds.append(cmd)

    if installed is not None:
        missing = [c for c in r.stata_cmds if not installed.get(c, False)]
        if missing:
            r.imports_ok = False
            r.missing_imports = missing

    r.abs_paths = find_abs_paths(src)

    for m in DO_READ_RE.finditer(src):
        raw = m.group(1)
        expanded = raw.replace("$CODE", str(CODE)).replace("$ROOT", str(REPO))
        # Any macro left over expands only at run time; skip such paths.
        if STATA_MACRO_RE.search(expanded):
            continue
        p = Path(expanded)
        if not p.is_absolute():
            continue
        if p.suffix.lower() not in DATA_EXT:
            continue
        r.inputs_declared += 1
        if not p.exists():
            r.inputs_missing.append(relative(p))
        elif p.is_file() and p.stat().st_size == 0:
            r.inputs_empty.append(relative(p))

    return r


def probe_stata(stata: str) -> dict[str, bool] | None:
    """Return which community commands are installed, or None if Stata is absent."""
    lines = [f"capture which {c}\ndi \"ADO {c} \" _rc" for c in STATA_COMMANDS]
    with tempfile.TemporaryDirectory() as td:
        do = Path(td) / "probe.do"
        do.write_text("\n".join(lines) + "\n")
        try:
            subprocess.run(
                [stata, "-b", "do", str(do)],
                capture_output=True, timeout=120, cwd=td,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        # Batch mode writes the log next to the do-file, or in Stata's own
        # working directory when a launcher wrapper cds elsewhere.
        logs = list(Path(td).glob("*.log"))
        text = ""
        if logs:
            text = logs[0].read_text(errors="replace")
        else:
            for guess in (
                Path("/Applications/Stata 18/stata_runner.log"),
                Path("/Applications/Stata 18/probe.log"),
            ):
                if guess.exists():
                    text = guess.read_text(errors="replace")
                    break
        if not text:
            return None

        out = {}
        for m in re.finditer(r"^ADO (\w+) (\d+)", text, re.MULTILINE):
            out[m.group(1)] = m.group(2) == "0"
        return out or None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-stata", action="store_true", help="skip the Stata probe")
    ap.add_argument("--stata", default="stata-mp")
    ap.add_argument("--json", type=Path, help="also write results as JSON")
    ap.add_argument("--verbose", action="store_true",
                    help="list every unrunnable script")
    args = ap.parse_args()

    print("Probing environment ...")
    print(f"  Python {sys.version.split()[0]}  ({sys.executable})")

    installed = None
    if not args.no_stata:
        installed = probe_stata(args.stata)
        if installed is None:
            print(f"  Stata: '{args.stata}' not usable; skipping ado checks")
        else:
            ok = [c for c, v in installed.items() if v]
            bad = [c for c, v in installed.items() if not v]
            print(f"  Stata packages present: {', '.join(ok) or 'none'}")
            if bad:
                print(f"  Stata packages MISSING: {', '.join(bad)}")

    scripts = sorted(
        [p for p in CODE.rglob("*.py") if p.name not in ("paths.py",)]
        + list(CODE.rglob("*.do"))
    )
    # Exclude directories excluded from the release.
    scripts = [
        p for p in scripts
        if "crimes_2022" not in p.parts
        and not any(part.endswith("_new") for part in p.parts)
    ]

    results: list[Result] = []
    for p in scripts:
        if p.suffix == ".py":
            results.append(check_python(p))
        else:
            results.append(check_do(p, installed))

    print(f"\nChecked {len(results)} scripts "
          f"({sum(r.kind == 'python' for r in results)} Python, "
          f"{sum(r.kind == 'stata' for r in results)} Stata)\n")

    print(f"{'Stage':<34}{'scripts':>8}{'runnable':>10}{'blocked':>9}")
    print("-" * 61)
    order = [name for name, _ in STAGES] + ["Other"]
    for stage in order:
        rows = [r for r in results if r.stage == stage]
        if not rows:
            continue
        ok = sum(r.runnable for r in rows)
        print(f"{stage:<34}{len(rows):>8}{ok:>10}{len(rows) - ok:>9}")
    print("-" * 61)
    total_ok = sum(r.runnable for r in results)
    print(f"{'TOTAL':<34}{len(results):>8}{total_ok:>10}{len(results) - total_ok:>9}")

    syntax_bad = [r for r in results if not r.syntax_ok]
    if syntax_bad:
        print(f"\nSyntax problems ({len(syntax_bad)}):")
        for r in syntax_bad[:15]:
            print(f"  {r.script}: {r.note}")

    missing_mods: dict[str, int] = {}
    for r in results:
        if r.kind == "python":
            for m in r.missing_imports:
                missing_mods[m] = missing_mods.get(m, 0) + 1
    if missing_mods:
        print("\nMissing Python packages:")
        for m, c in sorted(missing_mods.items(), key=lambda kv: -kv[1]):
            print(f"  {m:<24} needed by {c} script(s)")

    abs_left = [r for r in results if r.abs_paths]
    if abs_left:
        print(f"\nScripts still holding absolute paths: {len(abs_left)}")
        print("  (expected outside the mainline; see README.md)")
        for r in abs_left[:8]:
            print(f"  {r.script}")
            print(f"      {r.abs_paths[0]}")
        if len(abs_left) > 8:
            print(f"  ... and {len(abs_left) - 8} more")

    blocked = [r for r in results if not r.runnable and r.syntax_ok]
    by_cause: dict[str, int] = {}
    for r in blocked:
        if r.inputs_empty:
            by_cause["input is an empty placeholder"] = \
                by_cause.get("input is an empty placeholder", 0) + 1
        elif r.inputs_missing:
            by_cause["input file absent"] = by_cause.get("input file absent", 0) + 1
        elif r.missing_imports:
            by_cause["dependency not installed"] = \
                by_cause.get("dependency not installed", 0) + 1
    if by_cause:
        print("\nWhy scripts are blocked:")
        for cause, n in sorted(by_cause.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>3}  {cause}")

    if args.verbose and blocked:
        print("\nBlocked scripts in detail:")
        for r in blocked:
            bits = []
            if r.inputs_missing:
                bits.append(f"missing: {', '.join(r.inputs_missing[:2])}")
            if r.inputs_empty:
                bits.append(f"empty: {', '.join(r.inputs_empty[:2])}")
            if r.missing_imports:
                bits.append(f"needs: {', '.join(r.missing_imports)}")
            print(f"  {r.script}\n      {'; '.join(bits)}")

    if args.json:
        args.json.write_text(json.dumps([asdict(r) for r in results], indent=2))
        print(f"\nWrote {args.json}")

    print("\nNote: scripts blocked on licensed Clarivate inputs are expected to")
    print("be unrunnable in a public checkout. See DATA.md.")
    return 1 if syntax_bad else 0


if __name__ == "__main__":
    sys.exit(main())
