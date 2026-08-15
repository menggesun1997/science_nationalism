# Snakefile — Science Nationalism Research Pipeline
#
# Estimates how three geopolitical shocks changed international research
# collaboration and scholar migration:
#
#   Brexit                  referendum 2016
#   Crimea annexation       2014
#   Russian invasion        2022
#
# Usage
# -----
#     snakemake -n                  # dry run: show what would execute
#     snakemake --cores 4           # run everything
#     snakemake --cores 4 figure1   # build Figure 1 only
#     snakemake --cores 4 -F stage2 # force-rerun one stage
#
# Configure the Stata executable if yours is not `stata-mp`:
#
#     snakemake --cores 4 --config stata=stata-se
#
# Prerequisites
# -------------
# Stage 1 needs the licensed Clarivate/OST article files, which are not
# distributed with this repository (see DATA.md). Stages 2 onward run from
# the aggregated .xlsx/.csv files that ARE included, so most results can be
# reproduced without them.
#
# Every rule below invokes a real script. Rules whose outputs are shipped
# with the repository are wired as checkpoints so Snakemake does not
# recompute hours of synthetic-control estimation unnecessarily; delete the
# target file to force a rebuild.

import os
from pathlib import Path

configfile: "config.yaml"


CODE = "code"
STATA = config.get("stata", "stata-mp")
PYTHON = config.get("python", "python")

# Stata's batch mode writes logs to the working directory and offers no way
# to redirect them, so every Stata rule cds into the script's directory
# first. This also makes config.do's upward search for the repository root
# succeed.
def stata(script):
    d = os.path.dirname(script)
    f = os.path.basename(script)
    return f'cd "{d}" && {STATA} -b do "{f}"'


EVENTS = ["eu", "russia", "uk", "ukraine"]

DISCIPLINES = [
    "arts", "biology", "biomedical", "chemistry", "clinical",
    "earth", "engineering", "health", "humanities",
    "mathematics", "physics", "professional", "psychology", "social_science",
]

# Migration analyses cover three of the four events; there is no EU-level
# migration specification.
MIGRATION_EVENTS = ["russia", "uk", "ukraine"]


rule all:
    input:
        "figure1.done",
        expand(f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.csv",
               event=EVENTS),
        expand(f"{CODE}/2two_way_did_{{event}}/event_study_results.csv",
               event=EVENTS),
        expand(f"{CODE}/3ppml_migration_did_{{event}}_internal_control/results/eventstudy.csv",
               event=MIGRATION_EVENTS),
        f"{CODE}/4scm_russia_openalex/scm_panel.csv",
        f"{CODE}/4scm_ukraine_openalex/scm_panel.csv",
        f"{CODE}/4scm_brexit_uk_openalex/scm_panel.csv",
        f"{CODE}/brexit_intil_ratio_effects.pdf",


# ═════════════════════════════════════════════════════════════
# Stage 1 — Raw publication processing
#
# Requires licensed Clarivate/OST inputs (see DATA.md). Produces the
# country-year collaboration aggregates every later stage consumes.
# ═════════════════════════════════════════════════════════════

rule raw_process:
    """Map Clarivate country codes to standard names; aggregate by country-year."""
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/0process.py",
    output:
        f"{CODE}/0raw_publiations_process/brexit_experimental_data/article_cntry_brexit_initial.txt",
    shell:
        f'{PYTHON} "{{input.script}}"'


rule eu_aggregates:
    """Aggregate member states into an EU-level unit."""
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/2calculate_eu_data.py",
        upstream=rules.raw_process.output,
    output:
        touch(f"{CODE}/0raw_publiations_process/.eu_data.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule eu_indicators:
    """Merge World Bank covariates (GDP per capita, R&D share, researchers)."""
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/4calculate_eu_indicators.py",
        upstream=rules.eu_aggregates.output,
    output:
        touch(f"{CODE}/0raw_publiations_process/.indicators.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule discipline_split:
    """Split the panel into 14 discipline-level workbooks."""
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/4generate_discipline_excel_files.py",
        upstream=rules.eu_indicators.output,
    output:
        touch(f"{CODE}/0raw_publiations_process/.disciplines.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule stage1:
    input:
        rules.discipline_split.output,


# ═════════════════════════════════════════════════════════════
# Stage 2 — Collaboration network indices and DiD
# ═════════════════════════════════════════════════════════════

rule networks_tile_russia_ukraine:
    """West/East collaboration tilt index for Russia and Ukraine."""
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/0cal_west_east_tile.py",
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/.tile.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule networks_did:
    """DiD on the West-minus-East collaboration ratio."""
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/2conduct_did.py",
        upstream=rules.networks_tile_russia_ukraine.output,
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/.did.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule networks_event_study:
    """Dynamic (event-study) version of the network DiD."""
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/3event_study_dynamic_did.py",
        upstream=rules.networks_did.output,
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/.event_study.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule networks_placebo:
    """In-space placebo permutations for the network DiD."""
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/4placebo_test.py",
        upstream=rules.networks_did.output,
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/.placebo.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule brexit_sdid:
    """Synthetic DiD on UK collaboration indices around the 2016 referendum."""
    input:
        script=f"{CODE}/1networks_sdid_brexit/3conduct_sym_did.py",
    output:
        f"{CODE}/1networks_sdid_brexit/simple_did_results.csv",
    shell:
        f'{PYTHON} "{{input.script}}"'


rule stage2:
    input:
        rules.networks_event_study.output,
        rules.networks_placebo.output,
        rules.brexit_sdid.output,


# ═════════════════════════════════════════════════════════════
# Stage 3 — PPML DiD with internal controls
#
# Identification: within a focal country, compare its collaboration with
# treated partners against its other partners. Poisson PMLE with high-
# dimensional fixed effects (ppmlhdfe) handles the count outcome and
# preserves zero-valued pairs.
# ═════════════════════════════════════════════════════════════

rule ppml_data:
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/1generate_ppml_data.py",
    output:
        f"{CODE}/2ppml_did_{{event}}_internal_control/ppml_data.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule ppml_estimate:
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/2ppml_analysis.do",
        data=f"{CODE}/2ppml_did_{{event}}_internal_control/ppml_data.csv",
    output:
        f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.dta",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


rule ppml_export:
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/3extract_partner_coefficients.do",
        data=f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.dta",
    output:
        f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


rule ppml_map:
    """Choropleth of per-partner collaboration changes."""
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/4visualize_partner_changes_geopandas.py",
        data=f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.csv",
    output:
        touch(f"{CODE}/2ppml_did_{{event}}_internal_control/.map.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule stage3:
    input:
        expand(f"{CODE}/2ppml_did_{{event}}_internal_control/.map.done", event=EVENTS),


# ═════════════════════════════════════════════════════════════
# Stage 4 — Two-way DiD with external control countries
#
# Alternative identification: compare the focal country against
# structurally similar countries selected by PPML pre-trend matching or
# synthetic control, rather than against its own other partners.
# ═════════════════════════════════════════════════════════════

rule twoway_control_group:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/1build_control_group_data.py",
    output:
        f"{CODE}/2two_way_did_{{event}}/control_group_cooperation_data.xlsx",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule twoway_data:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/3generate_ppml_did_data.py",
        data=f"{CODE}/2two_way_did_{{event}}/control_group_cooperation_data.xlsx",
    output:
        f"{CODE}/2two_way_did_{{event}}/ppml_did_data.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule twoway_estimate:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/4ppml_did_analysis.do",
        data=f"{CODE}/2two_way_did_{{event}}/ppml_did_data.csv",
    output:
        f"{CODE}/2two_way_did_{{event}}/partner_coefficients.dta",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


rule twoway_event_study:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/6event_study_analysis.do",
        data=f"{CODE}/2two_way_did_{{event}}/partner_coefficients.dta",
    output:
        f"{CODE}/2two_way_did_{{event}}/event_study_results.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


rule twoway_plot:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/7visualize_event_study.py",
        data=f"{CODE}/2two_way_did_{{event}}/event_study_results.csv",
    output:
        touch(f"{CODE}/2two_way_did_{{event}}/.plot.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule stage4:
    input:
        expand(f"{CODE}/2two_way_did_{{event}}/.plot.done", event=EVENTS),


# ═════════════════════════════════════════════════════════════
# Stage 5 — Scholar migration
#
# Net inflow contains negative values, so these use interrupted time
# series at the focal-country level rather than PPML.
# ═════════════════════════════════════════════════════════════

rule migration_event_study:
    input:
        script=f"{CODE}/3ppml_migration_did_{{event}}_internal_control/3event_study.do",
    output:
        f"{CODE}/3ppml_migration_did_{{event}}_internal_control/results/eventstudy.csv",
    wildcard_constraints:
        event="|".join(MIGRATION_EVENTS),
    run:
        shell(stata(input.script))


rule migration_robustness:
    input:
        script=f"{CODE}/3ppml_migration_did_{{event}}_internal_control/4robustness.do",
        data=f"{CODE}/3ppml_migration_did_{{event}}_internal_control/results/eventstudy.csv",
    output:
        f"{CODE}/3ppml_migration_did_{{event}}_internal_control/results/robustness.csv",
    wildcard_constraints:
        event="|".join(MIGRATION_EVENTS),
    run:
        shell(stata(input.script))


rule stage5:
    input:
        expand(
            f"{CODE}/3ppml_migration_did_{{event}}_internal_control/results/robustness.csv",
            event=MIGRATION_EVENTS,
        ),


# ═════════════════════════════════════════════════════════════
# Stage 6 — Synthetic control on migration flows (MPIDR data)
#
# Uses the public MPIDR Scholarly Migration Database, so this stage runs
# without the licensed Clarivate inputs. `_wos` variants replicate the
# same design on Web of Science data as a source-robustness check.
# ═════════════════════════════════════════════════════════════

rule scm_panel:
    """Build the donor-pool panel from MPIDR country-year aggregates."""
    input:
        script=f"{CODE}/4scm_{{event}}_openalex/build_scm_panel.py",
    output:
        f"{CODE}/4scm_{{event}}_openalex/scm_panel.csv",
    wildcard_constraints:
        event="russia|ukraine|brexit_uk",
    shell:
        f'{PYTHON} "{{input.script}}"'


rule stage6:
    input:
        expand(f"{CODE}/4scm_{{event}}_openalex/scm_panel.csv",
               event=["russia", "ukraine", "brexit_uk"]),


# ═════════════════════════════════════════════════════════════
# Stage 7 — Figure 1: synthetic control across all three shocks
#
# 00_master.do runs six analyses (2 outcomes x 3 events) and combines the
# 12 resulting panels. Runtime is several hours: each synth call executes
# hundreds of placebo permutations.
# ═════════════════════════════════════════════════════════════

rule figure1:
    input:
        script=f"{CODE}/00_master.do",
    output:
        touch("figure1.done"),
    run:
        shell(stata(input.script))


# ═════════════════════════════════════════════════════════════
# Stage 8 — Discipline heterogeneity
#
# 14 disciplines x 2 outcomes, one synthetic control each. Directory
# spelling differs between trees ("intil_ratio" under disciplines_brexit,
# "initil_ratio" under disciplines_crimes*); both are preserved because
# the do-files reference them literally.
# ═════════════════════════════════════════════════════════════

rule discipline_brexit:
    input:
        script=f"{CODE}/disciplines_brexit/{{disc}}/intil_ratio/compare_intl_ratio.do",
    output:
        touch(f"{CODE}/disciplines_brexit/{{disc}}/.ratio.done"),
    wildcard_constraints:
        disc="|".join(DISCIPLINES),
    run:
        shell(stata(input.script))


rule discipline_crimea:
    input:
        script=f"{CODE}/disciplines_crimes/disciplines/{{disc}}/initil_ratio/intl_ratio_compare.do",
    output:
        touch(f"{CODE}/disciplines_crimes/disciplines/{{disc}}/.ratio.done"),
    wildcard_constraints:
        disc="|".join(DISCIPLINES),
    run:
        shell(stata(input.script))


rule discipline_effects_table:
    """Collect avg_effect across disciplines into one workbook."""
    input:
        script=f"{CODE}/extract_avg_effects.py",
        deps=expand(f"{CODE}/disciplines_brexit/{{disc}}/.ratio.done",
                    disc=DISCIPLINES),
    output:
        f"{CODE}/学科avg_effect汇总.xlsx",
    shell:
        f'{PYTHON} "{{input.script}}"'


rule discipline_effects_plot:
    input:
        script=f"{CODE}/visualize_effects.py",
        data=f"{CODE}/学科avg_effect汇总.xlsx",
    output:
        f"{CODE}/brexit_intil_ratio_effects.pdf",
        f"{CODE}/crimes_intil_ratio_effects.pdf",
    shell:
        f'{PYTHON} "{{input.script}}"'


rule stage8:
    input:
        rules.discipline_effects_plot.output,


# ═════════════════════════════════════════════════════════════
# Stage 9 — Supplementary experiments (reviewer requests)
#
# experiment_3 was dropped during revision; the numbering gap is
# intentional.
# ═════════════════════════════════════════════════════════════

rule experiment_heatmap:
    """Collaborator composition heatmaps, pre vs post shock."""
    input:
        script=f"{CODE}/add_experiments/experiment_1/{{event}}/cal_heatmap.py",
    output:
        touch(f"{CODE}/add_experiments/experiment_1/{{event}}/.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule experiment_betweenness:
    """Betweenness centrality in the collaboration network."""
    input:
        script=f"{CODE}/add_experiments/experiment_2/{{event}}/cal_betweeness.py",
    output:
        touch(f"{CODE}/add_experiments/experiment_2/{{event}}/.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule experiment_clustering:
    """PCA + k-means on country collaboration vectors."""
    input:
        script=f"{CODE}/add_experiments/experiment_4/{{event}}/cal_pca.py",
    output:
        touch(f"{CODE}/add_experiments/experiment_4/{{event}}/.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule experiment_null_model:
    """Degree-preserving null model as a baseline for network changes."""
    input:
        script=f"{CODE}/add_experiments/null_model/russia/null_model_cal.py",
    output:
        touch(f"{CODE}/add_experiments/null_model/russia/.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule stage9:
    input:
        expand(f"{CODE}/add_experiments/experiment_1/{{event}}/.done", event=EVENTS),
        expand(f"{CODE}/add_experiments/experiment_2/{{event}}/.done", event=EVENTS),
        expand(f"{CODE}/add_experiments/experiment_4/{{event}}/.done", event=EVENTS),
        rules.experiment_null_model.output,


# ═════════════════════════════════════════════════════════════
# Housekeeping
# ═════════════════════════════════════════════════════════════

rule clean_markers:
    """Remove .done sentinels so the next run re-executes everything."""
    shell:
        f'find {CODE} -name ".*.done" -delete; rm -f figure1.done'
