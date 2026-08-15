"""Rewrite hard-coded absolute paths in mainline pipeline scripts.

The repository accumulated four mutually incompatible root directories as it
was renamed and passed between machines. All four denote today's ``code/``
directory:

    /Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES     (old repo name)
    /Users/sunmengge/Dropbox/GitHub/sicence nationism/code   (current)
    C:/Users/91916/Dropbox/GitHub/sicence nationism/code     (co-author, Windows)
    /Users/sunmengge/Dropbox/GitHub/Brexit/exps/...           (predecessor project)

Python files are rewritten to derive paths from ``code/paths.py``; do-files to
use the ``$CODE`` global defined in ``code/config.do``.

Run from the repository root:

    python tools/rewrite_paths.py --check      # report only, no writes
    python tools/rewrite_paths.py --apply      # rewrite in place
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CODE = REPO / "code"

# Historical root directories, all of which map onto today's code/ tree.
# The repository was renamed several times and moved between machines, and
# each analysis originally lived in its own standalone folder before being
# consolidated here. None of these paths exist any more, so scripts holding
# them cannot run at all.
#
# Ordered longest-first so the more specific pattern wins.
ROOTS = [
    # Current locations
    "/Users/sunmengge/Dropbox/GitHub/sicence nationism/code",
    "C:/Users/91916/Dropbox/GitHub/sicence nationism/code",
    "C:\\Users\\91916\\Dropbox\\GitHub\\sicence nationism\\code",

    # Previous repository name
    "/Users/sunmengge/Dropbox/RUSSIA_UKRAIN_WAR_ALL_CODES",

    # Standalone folders, before consolidation. Mapped to their present
    # location under code/ (verified file-by-file).
    #
    # stata_results/ held one subdirectory per analysis, and those names
    # survive unchanged under code/ — except Brexit-stata_external, which
    # was renamed Brexit-stata_external_try. Order matters: the rename must
    # be matched before the generic prefix.
    "/Users/sunmengge/Dropbox/Brexit/Data/experimental_data/stata_results/"
    "Brexit-stata_external:Brexit-stata_external_try",
    "/Users/sunmengge/Dropbox/Brexit/Data/experimental_data/stata_results:.",
    "/Users/sunmengge/Dropbox/Brexit/Data/experimental_data:.",
    "/Users/sunmengge/Desktop/SCM_STATA/Brexit:Brexit-stata_external_try",
    "/Users/sunmengge/Desktop/SCM_STATA/crimes:crimes",
    "/Users/sunmengge/Dropbox/Brexit-stata:Brexit-stata_external_try",
    "/Users/sunmengge/Dropbox/crimes_2022:crimes_2022",
    "/Users/sunmengge/Dropbox/crimes:crimes",
    "/Users/sunmengge/Dropbox/disciplines_crimes_2014:disciplines_crimes_2014",
    "/Users/sunmengge/Dropbox/disciplines_crimes:disciplines_crimes",
    "/Users/sunmengge/Dropbox/disciplines_brexit:disciplines_brexit",
]


def split_mapping(entry: str) -> tuple[str, str]:
    """Split "oldroot:subdir" into (oldroot, subdir under code/).

    A bare entry maps directly onto code/. Windows drive letters contain a
    colon, so only split on the last one and require the tail to be a
    relative path.
    """
    if ":" in entry:
        head, _, tail = entry.rpartition(":")
        # Reject a Windows drive letter ("C:/Users/..."): its tail starts
        # with a separator and its head is a single character.
        if head and len(head) > 1 and not tail.startswith(("/", "\\")):
            return head, "" if tail == "." else tail
    return entry, ""

# Roots that denote the repository root rather than code/.
REPO_ROOTS = [
    "/Users/sunmengge/Dropbox/GitHub/sicence nationism",
    "C:/Users/91916/Dropbox/GitHub/sicence nationism",
]

LEGACY_BREXIT_ROOTS = [
    # Longest first.
    "/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related/"
    "experimental_data/Data/experimental_data/cooperation_related",
    "/Users/sunmengge/Dropbox/GitHub/Brexit/exps/cooperation related",
]

RAW_STORE = "/Users/sunmengge/Dropbox/brexit_rawdata"

PY_BOOTSTRAP_MARKER = "from paths import"


def depth_to_code(path: Path) -> int:
    """Number of ``parents`` hops from ``path`` up to ``code/``."""
    return len(path.relative_to(CODE).parts) - 1


def python_bootstrap(path: Path) -> str:
    """The sys.path bootstrap needed for ``path`` to import ``paths``."""
    n = depth_to_code(path)
    parents = f"parents[{n}]" if n else "parent"
    return (
        "import sys\n"
        "from pathlib import Path\n\n"
        "# Resolve repository paths without hard-coding any absolute directory.\n"
        f"sys.path.insert(0, str(Path(__file__).resolve().{parents}))\n"
        "from paths import CODE, REPO, RAW_DATA_STORE, LEGACY_BREXIT  # noqa: E402\n"
    )


# A path literal split across lines by implicit string concatenation, e.g.
#     "/Users/me/proj/"
#     "sub/file.png"
# Substituting str(CODE / ...) for the first part would break the implicit
# join, so fold such runs into one literal before substituting.
IMPLICIT_JOIN_RE = re.compile(
    r"""(?P<q1>['"])(?P<a>(?:/Users/|[A-Za-z]:[/\\])[^'"\n]*)(?P=q1)"""
    r"""(?P<gap>\s*\n\s*)(?P<f>f?)(?P<q2>['"])(?P<b>[^'"\n]*)(?P=q2)"""
)


def fold_implicit_joins(text: str) -> str:
    """Merge multi-line implicit string concatenations into single literals."""
    for _ in range(5):  # runs can be longer than two parts
        new = IMPLICIT_JOIN_RE.sub(
            lambda m: f'{m.group("f")}{m.group("q1")}{m.group("a")}{m.group("b")}{m.group("q1")}',
            text,
        )
        if new == text:
            break
        text = new
    return text


def rewrite_python(text: str, path: Path) -> tuple[str, int]:
    n = 0
    text = fold_implicit_joins(text)

    def sub_root(m: re.Match) -> str:
        nonlocal n
        n += 1
        tail = m.group("tail")
        return f'CODE / f"{tail.lstrip("/")}"' if tail else "CODE"

    # Replace quoted string literals that begin with a known root.
    for entry in ROOTS:
        root, subdir = split_mapping(entry)
        pattern = re.compile(
            r"""(?P<q>['"])""" + re.escape(root) + r"""(?P<tail>[^'"]*)(?P=q)"""
        )

        def repl(m: re.Match, subdir: str = subdir) -> str:
            nonlocal n
            n += 1
            tail = m.group("tail").lstrip("/").lstrip("\\").replace("\\", "/")
            joined = f"{subdir}/{tail}" if subdir and tail else (subdir or tail)
            if not joined:
                return "str(CODE)"
            return f'str(CODE / "{joined}")'

        text = pattern.sub(repl, text)

    for root in REPO_ROOTS:
        pattern = re.compile(
            r"""(?P<q>['"])""" + re.escape(root) + r"""(?P<tail>[^'"]*)(?P=q)"""
        )

        def repl_repo(m: re.Match) -> str:
            nonlocal n
            n += 1
            tail = m.group("tail").lstrip("/").lstrip("\\")
            if not tail:
                return "str(REPO)"
            return f'str(REPO / "{tail}")'

        text = pattern.sub(repl_repo, text)

    for legacy in LEGACY_BREXIT_ROOTS:
        pattern = re.compile(
            r"""(?P<q>['"])""" + re.escape(legacy) + r"""(?P<tail>[^'"]*)(?P=q)"""
        )

        def repl_legacy(m: re.Match) -> str:
            nonlocal n
            n += 1
            tail = m.group("tail").lstrip("/")
            if not tail:
                return "str(LEGACY_BREXIT)"
            return f'str(LEGACY_BREXIT / "{tail}")'

        text = pattern.sub(repl_legacy, text)

    pattern = re.compile(
        r"""(?P<q>['"])""" + re.escape(RAW_STORE) + r"""(?P<tail>[^'"]*)(?P=q)"""
    )

    def repl_raw(m: re.Match) -> str:
        nonlocal n
        n += 1
        tail = m.group("tail").lstrip("/")
        if not tail:
            return "str(RAW_DATA_STORE)"
        return f'str(RAW_DATA_STORE / "{tail}")'

    text = pattern.sub(repl_raw, text)

    if n and PY_BOOTSTRAP_MARKER not in text:
        text = insert_bootstrap(text, python_bootstrap(path))

    return text, n


def insert_bootstrap(text: str, bootstrap: str) -> str:
    """Insert the bootstrap after the module docstring / leading comments."""
    lines = text.splitlines(keepends=True)
    i = 0

    # Shebang and encoding declaration stay first.
    while i < len(lines) and (
        lines[i].startswith("#!") or "coding" in lines[i][:30] and lines[i].startswith("#")
    ):
        i += 1

    # Skip a leading comment block.
    while i < len(lines) and lines[i].lstrip().startswith("#"):
        i += 1

    # Skip a module docstring.
    j = i
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j < len(lines):
        stripped = lines[j].lstrip()
        for quote in ('"""', "'''"):
            if stripped.startswith(quote):
                if stripped.count(quote) >= 2 and len(stripped) > 3:
                    i = j + 1
                else:
                    k = j + 1
                    while k < len(lines) and quote not in lines[k]:
                        k += 1
                    i = k + 1
                break

    return "".join(lines[:i]) + "\n" + bootstrap + "\n" + "".join(lines[i:])


def rewrite_do(text: str, path: Path) -> tuple[str, int]:
    n = 0
    rel_to_code = path.relative_to(CODE).parent
    hops = len(rel_to_code.parts)
    config_rel = "/".join([".."] * hops + ["config.do"]) if hops else "config.do"

    for entry in ROOTS:
        root, subdir = split_mapping(entry)
        n += text.count(root)
        text = text.replace(root, f"$CODE/{subdir}" if subdir else "$CODE")

    for root in REPO_ROOTS:
        before = text
        text = text.replace(root, "$ROOT")
        n += before.count(root)

    before = text
    text = text.replace(RAW_STORE, "$RAWSTORE")
    n += before.count(RAW_STORE)

    if n and "config.do" not in text:
        header = (
            "* Resolve $ROOT / $CODE without hard-coding an absolute path.\n"
            f'do "`c(pwd)\'/{config_rel}"\n'
        )
        text = insert_do_header(text, header, config_rel)

    return text, n


DO_HEADER = """
* ── Path resolution ──────────────────────────────────────────────────────
* Sets $ROOT, $CODE, $PAPER and the shared colour palette via code/config.do,
* so no absolute path appears below. Resolution order:
*   1. $CODE already set by a calling master do-file
*   2. $SCIENCE_NATIONALISM_ROOT environment variable
*   3. walk up from the working directory looking for code/config.do
* If none succeed, set it manually once per session:
*   global ROOT "/path/to/sicence nationism"
*   do "$ROOT/code/config.do"
capture confirm file "$CODE/config.do"
if _rc {
    local _cfg ""
    local _env : environment SCIENCE_NATIONALISM_ROOT
    if "`_env'" != "" {
        capture confirm file "`_env'/code/config.do"
        if !_rc local _cfg "`_env'/code/config.do"
    }
    if "`_cfg'" == "" {
        local _d "`c(pwd)'"
        forvalues _i = 1/12 {
            capture confirm file "`_d'/code/config.do"
            if !_rc {
                local _cfg "`_d'/code/config.do"
                continue, break
            }
            local _d = regexr("`_d'", "/[^/]+$", "")
            if "`_d'" == "" continue, break
        }
    }
    if "`_cfg'" == "" {
        di as error "Cannot locate code/config.do. Set SCIENCE_NATIONALISM_ROOT"
        di as error "or define global ROOT before running this file. See README.md."
        exit 601
    }
    do "`_cfg'"
}

"""


def insert_do_header(text: str, header: str, config_rel: str) -> str:
    """Insert the config.do include after `clear all` / `set more off`."""
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        s = lines[i].strip().lower()
        if s.startswith(("clear", "set more", "set ", "*", "//")) or not s:
            i += 1
            continue
        break

    return "".join(lines[:i]) + DO_HEADER + "".join(lines[i:])


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="report only")
    g.add_argument("--apply", action="store_true", help="rewrite in place")
    ap.add_argument(
        "--list",
        type=Path,
        help="file listing target scripts, one path relative to code/ per line",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="target every .py and .do under code/",
    )
    args = ap.parse_args()

    if args.all:
        paths = sorted(
            list(CODE.rglob("*.py")) + list(CODE.rglob("*.do")),
            key=lambda p: str(p),
        )
        skip = {"paths.py", "config.do"}
        targets = [
            str(p.relative_to(CODE))
            for p in paths
            if p.name not in skip
            # Directories excluded from the release
            and "crimes_2022" not in p.parts
            and not any(part.endswith("_new") for part in p.parts)
        ]
    elif args.list:
        targets = [
            line.strip()
            for line in args.list.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    else:
        ap.error("pass either --all or --list FILE")

    total_files = 0
    total_subs = 0
    for rel in targets:
        path = CODE / rel
        if not path.is_file():
            print(f"  SKIP (missing)  {rel}")
            continue

        original = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            new, n = rewrite_python(original, path)
        elif path.suffix == ".do":
            new, n = rewrite_do(original, path)
        else:
            continue

        if n:
            total_files += 1
            total_subs += n
            print(f"  {n:3d} paths  {rel}")
            if args.apply:
                path.write_text(new, encoding="utf-8")

    verb = "rewrote" if args.apply else "would rewrite"
    print(f"\n{verb} {total_subs} paths across {total_files} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
