*==============================================================*
* config.do — central path resolution for all Stata do-files
*
* Defines these globals, used by every analysis do-file so that no
* absolute path is hard-coded anywhere:
*
*   $ROOT     repository root
*   $CODE     $ROOT/code
*   $PAPER    $ROOT/paper
*   $MIGDATA  $ROOT/migration_data
*   $FIGDIR   $CODE/figures        (Figure 1 panels and .gph sources)
*   $RAWPUB   $CODE/00_data_processing
*
* Include it at the top of any do-file. Stata has no equivalent of Python's
* __file__, so pass the including file's directory when you know it:
*
*     do "../config.do"
*
* Resolution order:
*   1. $ROOT already set (a master do-file set it) — reused
*   2. SCIENCE_NATIONALISM_ROOT environment variable
*   3. walk up from the current working directory looking for code/paths.py
*
* If all three fail, set it manually once per session:
*
*     global ROOT "/path/to/sicence nationism"
*     do "$ROOT/code/config.do"
*==============================================================*

* ── Step 1: keep an already-resolved root ──────────────────────────────
capture confirm file "$ROOT/code/paths.py"
if _rc {
    global ROOT ""
}

* ── Step 2: environment variable ───────────────────────────────────────
if "$ROOT" == "" {
    local envroot : environment SCIENCE_NATIONALISM_ROOT
    if "`envroot'" != "" {
        capture confirm file "`envroot'/code/paths.py"
        if !_rc {
            global ROOT "`envroot'"
        }
        else {
            di as error "SCIENCE_NATIONALISM_ROOT is set to `envroot'"
            di as error "but `envroot'/code/paths.py does not exist."
        }
    }
}

* ── Step 3: walk up from the working directory ─────────────────────────
* Marker file is code/paths.py, which exists only at the repository root.
if "$ROOT" == "" {
    local candidate "`c(pwd)'"
    forvalues up = 1/12 {
        capture confirm file "`candidate'/code/paths.py"
        if !_rc {
            global ROOT "`candidate'"
            continue, break
        }
        * Strip the final path component. regexr handles directory names
        * containing spaces, which tokenising on "/" does not.
        local candidate = regexr("`candidate'", "/[^/]+$", "")
        if "`candidate'" == "" {
            continue, break
        }
    }
}

* ── Fail loudly rather than silently writing to the wrong place ─────────
if "$ROOT" == "" {
    di as error "{hline 70}"
    di as error "config.do could not locate the repository root."
    di as error ""
    di as error "Fix by either setting the environment variable before"
    di as error "launching Stata:"
    di as error "    export SCIENCE_NATIONALISM_ROOT=/path/to/sicence nationism"
    di as error ""
    di as error "or by setting the global once per session:"
    di as error `"    global ROOT "/path/to/sicence nationism""'
    di as error `"    do "$ROOT/code/config.do""'
    di as error "{hline 70}"
    exit 601
}

* ── Derived paths ──────────────────────────────────────────────────────
global CODE    "$ROOT/code"
global PAPER   "$ROOT/paper"
global MIGDATA "$ROOT/migration_data"
global FIGDIR  "$CODE/figures"
global RAWPUB  "$CODE/00_data_processing"

* ── Shared colour palette ──────────────────────────────────────────────
* These are the colours of the published figures (paper/figure/a-f.pdf,
* ru-crimean.pdf, ru-war.pdf), sampled from the final PDFs so that a rerun
* reproduces them instead of drifting to a different scheme. Keep them in
* sync with 99_redraw_panels.do, which plots the Figure 1 panels.
global C_EU    "33 65 148"      // #214194  deep blue  — EU
global C_UK    "190 39 56"      // #BE2738  red        — UK
global C_RU    "75 92 156"      // #4B5C9C  blue-violet — Russia
global C_UA    "226 195 65"     // #E2C341  golden     — Ukraine
global C_GOLD  "215 183 84"     // #D7B754  gold accent (Figure 1)
global C_SLATE "81 98 153"      // #516299  slate blue accent (Figure 1)
global C_SHADE "238 238 238"    // #EEEEEE  post-treatment shading
global C_LINE  "68 68 68"       // #444444  intervention line
global C_GREY  "85 85 85"       // #555555  secondary text/lines

* In-space placebo plots: treated unit red, donor placebos light pink.
global C_TREATED "201 6 43"     // #C9062B  treated-unit gap
global C_PLACEBO "233 155 170"  // #E99BAA  donor placebo gaps

* ── Required community-contributed commands ────────────────────────────
* ppmlhdfe/reghdfe/ftools install from SSC; synth2 and sdid are hosted
* on GitHub and need the `github` package.
foreach pkg in ppmlhdfe reghdfe ftools estout parmest synth {
    capture which `pkg'
    if _rc {
        di as txt "Installing `pkg' from SSC ..."
        capture noisily ssc install `pkg', replace
    }
}

foreach pkg in synth2 sdid {
    capture which `pkg'
    if _rc {
        di as error "Missing required command: `pkg'"
        di as error "  ssc install github"
        di as error "  github install <repo>   // see README.md"
    }
}

di as result "config.do: ROOT = $ROOT"
