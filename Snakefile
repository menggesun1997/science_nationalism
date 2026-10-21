# Snakefile — The Scientific Cost of Geopolitical Conflict
#
#   Brexit                  referendum 2016
#   Crimea annexation       2014
#   Full-scale invasion     2022 (nested on the post-2014 baseline)
#
#     snakemake -n
#     snakemake --cores 4 figure1
#     snakemake --cores 4 --config stata=stata-se
#
# Stage 00 needs licensed Clarivate/OST article files (see DATA.md).
# Later modules run from the aggregated .xlsx/.csv files that ARE shipped.

import os

configfile: "config.yaml"

CODE = "code"
STATA = config.get("stata", "stata-mp")
PYTHON = config.get("python", "python")


def stata(script):
    d = os.path.dirname(script)
    f = os.path.basename(script)
    return f'cd "{d}" && {STATA} -b do "{f}"'


EVENTS = ["eu", "russia", "uk", "ukraine"]
MAP_EVENTS = ["uk", "russia", "ukraine"]  # main-text maps
DISCIPLINES = [
    "arts", "biology", "biomedical", "chemistry", "clinical",
    "earth", "engineering", "health", "humanities",
    "mathematics", "physics", "professional", "psychology", "social_science",
]


rule all:
    input:
        "figure1.done",
        expand(f"{CODE}/02_ppml_partners_{{event}}/partner_coefficients.csv",
               event=MAP_EVENTS),
        expand(f"{CODE}/03_twoway_did_{{event}}/event_study_results.csv",
               event=EVENTS),
        f"{CODE}/04_west_east_tilt/.did.done",
        f"{CODE}/brexit_intil_ratio_effects.pdf",
        f"{CODE}/08_eu_donor_robustness/figures/eu_donor_brexit.pdf",


# ── 00  publication processing ──────────────────────────────────────────

rule raw_process:
    input:
        script=f"{CODE}/00_data_processing/raw data processing/0process.py",
    output:
        f"{CODE}/00_data_processing/brexit_experimental_data/article_cntry_brexit_initial.txt",
    shell:
        f'{PYTHON} "{{input.script}}"'


rule eu_aggregates:
    input:
        script=f"{CODE}/00_data_processing/raw data processing/2calculate_eu_data.py",
        upstream=rules.raw_process.output,
    output:
        touch(f"{CODE}/00_data_processing/.eu_data.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule eu_indicators:
    input:
        script=f"{CODE}/00_data_processing/raw data processing/4calculate_eu_indicators.py",
        upstream=rules.eu_aggregates.output,
    output:
        touch(f"{CODE}/00_data_processing/.indicators.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule discipline_split:
    input:
        script=f"{CODE}/00_data_processing/raw data processing/4generate_discipline_excel_files.py",
        upstream=rules.eu_indicators.output,
    output:
        touch(f"{CODE}/00_data_processing/.disciplines.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


# ── 01  aggregate SCM (Figure 1) ────────────────────────────────────────

rule figure1:
    input:
        script=f"{CODE}/00_master.do",
    output:
        touch("figure1.done"),
    run:
        shell(stata(input.script))


# ── 02  partner PPML DiD (main-text maps) ───────────────────────────────

rule ppml_data:
    input:
        script=f"{CODE}/02_ppml_partners_{{event}}/1generate_ppml_data.py",
    output:
        f"{CODE}/02_ppml_partners_{{event}}/ppml_data.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule ppml_estimate:
    input:
        script=f"{CODE}/02_ppml_partners_{{event}}/2ppml_analysis.do",
        data=f"{CODE}/02_ppml_partners_{{event}}/ppml_data.csv",
    output:
        f"{CODE}/02_ppml_partners_{{event}}/partner_coefficients.dta",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


rule ppml_export:
    input:
        script=f"{CODE}/02_ppml_partners_{{event}}/3extract_partner_coefficients.do",
        data=f"{CODE}/02_ppml_partners_{{event}}/partner_coefficients.dta",
    output:
        f"{CODE}/02_ppml_partners_{{event}}/partner_coefficients.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


rule ppml_map:
    input:
        script=f"{CODE}/02_ppml_partners_{{event}}/4visualize_partner_changes_geopandas.py",
        data=f"{CODE}/02_ppml_partners_{{event}}/partner_coefficients.csv",
    output:
        touch(f"{CODE}/02_ppml_partners_{{event}}/.map.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


# ── 03  external-control two-way DiD (SI G) ─────────────────────────────

rule twoway_control_group:
    input:
        script=f"{CODE}/03_twoway_did_{{event}}/1build_control_group_data.py",
    output:
        f"{CODE}/03_twoway_did_{{event}}/control_group_cooperation_data.xlsx",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule twoway_data:
    input:
        script=f"{CODE}/03_twoway_did_{{event}}/3generate_ppml_did_data.py",
        data=f"{CODE}/03_twoway_did_{{event}}/control_group_cooperation_data.xlsx",
    output:
        f"{CODE}/03_twoway_did_{{event}}/ppml_did_data.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule twoway_estimate:
    input:
        script=f"{CODE}/03_twoway_did_{{event}}/4ppml_did_analysis.do",
        data=f"{CODE}/03_twoway_did_{{event}}/ppml_did_data.csv",
    output:
        f"{CODE}/03_twoway_did_{{event}}/partner_coefficients.dta",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


rule twoway_event_study:
    input:
        script=f"{CODE}/03_twoway_did_{{event}}/6event_study_analysis.do",
        data=f"{CODE}/03_twoway_did_{{event}}/partner_coefficients.dta",
    output:
        f"{CODE}/03_twoway_did_{{event}}/event_study_results.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    run:
        shell(stata(input.script))


# ── 04  West–East tilt (SI H) ───────────────────────────────────────────

rule west_east_tile:
    input:
        script=f"{CODE}/04_west_east_tilt/0cal_west_east_tile.py",
    output:
        touch(f"{CODE}/04_west_east_tilt/.tile.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


rule west_east_did:
    input:
        script=f"{CODE}/04_west_east_tilt/2conduct_did.py",
        upstream=rules.west_east_tile.output,
    output:
        touch(f"{CODE}/04_west_east_tilt/.did.done"),
    shell:
        f'{PYTHON} "{{input.script}}"'


# ── 05  discipline SCM (SI E, F) ────────────────────────────────────────

rule discipline_brexit:
    input:
        script=f"{CODE}/05_scm_disciplines_brexit/{{disc}}/intil_ratio/compare_intl_ratio.do",
    output:
        touch(f"{CODE}/05_scm_disciplines_brexit/{{disc}}/.ratio.done"),
    wildcard_constraints:
        disc="|".join(DISCIPLINES),
    run:
        shell(stata(input.script))


rule discipline_effects_table:
    input:
        script=f"{CODE}/extract_avg_effects.py",
        deps=expand(f"{CODE}/05_scm_disciplines_brexit/{{disc}}/.ratio.done",
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
    shell:
        f'{PYTHON} "{{input.script}}"'


# ── 06  bridging (SI I) ─────────────────────────────────────────────────

rule bridging:
    input:
        script=f"{CODE}/06_bridging/{{event}}/cal_heatmap.py",
    output:
        touch(f"{CODE}/06_bridging/{{event}}/.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        f'{PYTHON} "{{input.script}}"'


# ── 08  EU-donor robustness for Brexit (SI B.5) ─────────────────────────

rule eu_donor_scm:
    input:
        script=f"{CODE}/08_eu_donor_robustness/eu_donor_brexit.do",
        data=f"{CODE}/01_scm_crimea_2014/original_completed.xlsx",
    output:
        f"{CODE}/08_eu_donor_robustness/results/eu_donor_brexit_total.xlsx",
        f"{CODE}/08_eu_donor_robustness/results/eu_donor_brexit_ratio.xlsx",
    run:
        shell(stata(input.script))


rule eu_donor_plot:
    input:
        script=f"{CODE}/08_eu_donor_robustness/plot_eu_donor.py",
        total=f"{CODE}/08_eu_donor_robustness/results/eu_donor_brexit_total.xlsx",
        ratio=f"{CODE}/08_eu_donor_robustness/results/eu_donor_brexit_ratio.xlsx",
    output:
        f"{CODE}/08_eu_donor_robustness/figures/eu_donor_brexit.pdf",
    shell:
        f'{PYTHON} "{{input.script}}"'
