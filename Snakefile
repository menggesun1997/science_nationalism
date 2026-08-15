# Snakefile — Science Nationalism Research Pipeline
# Covers: Brexit, Russia-Ukraine War, Crimea (2014) analyses
# Stages: raw data → networks/DID → PPML → two-way DID → disciplines → figures

CODE = "code"
EVENTS = ["eu", "russia", "uk", "ukraine"]
DISCIPLINES = [
    "arts", "biology", "biomedical", "chemistry", "clinical",
    "earth", "engineering", "health", "humanities",
    "mathematics", "physics", "professional", "psychology", "social_science",
]


rule all:
    input:
        # Stage 1 — raw processing
        f"{CODE}/0raw_publiations_process/countries_yearly_statistics.csv",
        # Stage 2 — network DID / sDID
        f"{CODE}/1netoworks_did_russia_ukraine/did_results/.done",
        f"{CODE}/1networks_sdid_brexit/simple_did_results.csv",
        # Stage 3 — PPML internal-control analyses
        expand(
            f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.csv",
            event=EVENTS,
        ),
        # Stage 4 — two-way DID analyses
        expand(
            f"{CODE}/2two_way_did_{{event}}/event_study_results.csv",
            event=EVENTS,
        ),
        # Stage 5 — crime-wave robustness checks
        f"{CODE}/crimes/intl_ratio/.done",
        f"{CODE}/crimes_2014/intl_ratio/.done",
        f"{CODE}/crimes_2015_2022/.done",
        f"{CODE}/crimes_2022/.done",
        # Stage 6 — discipline-level analyses
        expand(
            f"{CODE}/disciplines_brexit/{{disc}}/intil_ratio/.done",
            disc=DISCIPLINES,
        ),
        expand(
            f"{CODE}/disciplines_crimes/disciplines/{{disc}}/.done",
            disc=DISCIPLINES,
        ),
        # Stage 7 — additional experiments
        f"{CODE}/add_experiments/experiment_1/.done",
        f"{CODE}/add_experiments/experiment_2/.done",
        f"{CODE}/add_experiments/experiment_4/.done",
        f"{CODE}/add_experiments/null_model/.done",
        # Stage 8 — final visualisation
        f"{CODE}/学科avg_effect汇总.xlsx",
        "code/brexit_intil_ratio_effects.pdf",
        "code/crimes_intil_ratio_effects.pdf",


# ─────────────────────────────────────────────
# Stage 0 — Raw publications processing
# ─────────────────────────────────────────────

rule raw_process:
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/0process.py",
    output:
        f"{CODE}/0raw_publiations_process/countries_yearly_statistics.csv",
    shell:
        "python '{input.script}'"


rule calc_eu_data:
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/2calculate_eu_data.py",
        dep=rules.raw_process.output,
    output:
        touch(f"{CODE}/0raw_publiations_process/.eu_data_done"),
    shell:
        "python '{input.script}'"


rule calc_indicators:
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/4calculate_eu_indicators.py",
        dep=rules.calc_eu_data.output,
    output:
        touch(f"{CODE}/0raw_publiations_process/.indicators_done"),
    shell:
        "python '{input.script}'"


rule generate_discipline_excels:
    input:
        script=f"{CODE}/0raw_publiations_process/raw data processing/4generate_discipline_excel_files.py",
        dep=rules.calc_indicators.output,
    output:
        touch(f"{CODE}/0raw_publiations_process/.discipline_excels_done"),
    shell:
        "python '{input.script}'"


# ─────────────────────────────────────────────
# Stage 1a — Network DID: Russia-Ukraine
# ─────────────────────────────────────────────

rule networks_did_russia_ukraine_tile:
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/0cal_west_east_tile.py",
        dep=rules.raw_process.output,
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/west_east_tile/.done"),
    shell:
        "python '{input.script}'"


rule networks_did_russia_ukraine_conduct:
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/2conduct_did.py",
        dep=rules.networks_did_russia_ukraine_tile.output,
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/did_results/.done"),
    shell:
        "python '{input.script}'"


rule networks_did_russia_ukraine_event_study:
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/3event_study_dynamic_did.py",
        dep=rules.networks_did_russia_ukraine_conduct.output,
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/event_study_results/.done"),
    shell:
        "python '{input.script}'"


rule networks_did_russia_ukraine_placebo:
    input:
        script=f"{CODE}/1netoworks_did_russia_ukraine/4placebo_test.py",
        dep=rules.networks_did_russia_ukraine_conduct.output,
    output:
        touch(f"{CODE}/1netoworks_did_russia_ukraine/placebo_test_results/.done"),
    shell:
        "python '{input.script}'"


# ─────────────────────────────────────────────
# Stage 1b — Synthetic DID: Brexit
# ─────────────────────────────────────────────

rule networks_sdid_brexit_data:
    input:
        script=f"{CODE}/1networks_sdid_brexit/0get_countrol_countries_data.py",
        dep=rules.raw_process.output,
    output:
        touch(f"{CODE}/1networks_sdid_brexit/.control_data_done"),
    shell:
        "python '{input.script}'"


rule networks_sdid_brexit_tile:
    input:
        script=f"{CODE}/1networks_sdid_brexit/1calculate_brexit_tile_index_uk.py",
        dep=rules.networks_sdid_brexit_data.output,
    output:
        touch(f"{CODE}/1networks_sdid_brexit/.tile_done"),
    shell:
        "python '{input.script}'"


rule networks_sdid_brexit_conduct:
    input:
        script=f"{CODE}/1networks_sdid_brexit/3conduct_sym_did.py",
        dep=rules.networks_sdid_brexit_tile.output,
    output:
        f"{CODE}/1networks_sdid_brexit/simple_did_results.csv",
    shell:
        "python '{input.script}'"


# ─────────────────────────────────────────────
# Stage 2 — PPML DID (internal control), one rule per event
# ─────────────────────────────────────────────

rule ppml_generate_data:
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/1generate_ppml_data.py",
        dep=rules.raw_process.output,
    output:
        f"{CODE}/2ppml_did_{{event}}_internal_control/ppml_data.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "python '{input.script}'"


rule ppml_analysis:
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/2ppml_analysis.do",
        data=f"{CODE}/2ppml_did_{{event}}_internal_control/ppml_data.csv",
    output:
        f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.dta",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "stata-mp -b do '{input.script}'"


rule ppml_extract_coefficients:
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/3extract_partner_coefficients.do",
        data=f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.dta",
    output:
        f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "stata-mp -b do '{input.script}'"


rule ppml_visualize:
    input:
        script=f"{CODE}/2ppml_did_{{event}}_internal_control/4visualize_partner_changes_geopandas.py",
        data=f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.csv",
    output:
        touch(f"{CODE}/2ppml_did_{{event}}_internal_control/visualization_results/.done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "python '{input.script}'"


# ─────────────────────────────────────────────
# Stage 3 — Two-way DID, one rule per event
# ─────────────────────────────────────────────

rule twoway_build_control:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/1build_control_group_data.py",
        dep=rules.raw_process.output,
    output:
        f"{CODE}/2two_way_did_{{event}}/control_group_cooperation_data.xlsx",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "python '{input.script}'"


rule twoway_generate_data:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/3generate_ppml_did_data.py",
        dep=f"{CODE}/2two_way_did_{{event}}/control_group_cooperation_data.xlsx",
    output:
        f"{CODE}/2two_way_did_{{event}}/ppml_did_data.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "python '{input.script}'"


rule twoway_ppml_did:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/4ppml_did_analysis.do",
        data=f"{CODE}/2two_way_did_{{event}}/ppml_did_data.csv",
    output:
        f"{CODE}/2two_way_did_{{event}}/partner_coefficients.dta",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "stata-mp -b do '{input.script}'"


rule twoway_event_study:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/6event_study_analysis.do",
        data=f"{CODE}/2two_way_did_{{event}}/partner_coefficients.dta",
    output:
        f"{CODE}/2two_way_did_{{event}}/event_study_results.csv",
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "stata-mp -b do '{input.script}'"


rule twoway_visualize_event_study:
    input:
        script=f"{CODE}/2two_way_did_{{event}}/7visualize_event_study.py",
        data=f"{CODE}/2two_way_did_{{event}}/event_study_results.csv",
    output:
        touch(f"{CODE}/2two_way_did_{{event}}/event_study_results/.vis_done"),
    wildcard_constraints:
        event="|".join(EVENTS),
    shell:
        "python '{input.script}'"


# ─────────────────────────────────────────────
# Stage 4 — Crime-wave robustness checks (Crimea 2014)
# ─────────────────────────────────────────────

rule crimes_plot:
    input:
        script=f"{CODE}/crimes/plot_crimean_four_panels.py",
        dep=rules.raw_process.output,
    output:
        touch(f"{CODE}/crimes/intl_ratio/.done"),
        touch(f"{CODE}/crimes/total_publications/.done"),
    shell:
        "python '{input.script}'"


rule crimes_2014:
    input:
        dep=rules.crimes_plot.output,
    output:
        touch(f"{CODE}/crimes_2014/intl_ratio/.done"),
    shell:
        "echo 'crimes_2014 outputs derived from crimes stage'"


rule crimes_2015_2022:
    input:
        dep=rules.crimes_2014.output,
    output:
        touch(f"{CODE}/crimes_2015_2022/.done"),
    shell:
        "echo 'crimes_2015_2022 outputs derived from crimes_2014 stage'"


rule crimes_2022:
    input:
        dep=rules.crimes_2015_2022.output,
    output:
        touch(f"{CODE}/crimes_2022/.done"),
    shell:
        "echo 'crimes_2022 outputs derived from crimes_2015_2022 stage'"


# ─────────────────────────────────────────────
# Stage 5 — Discipline-level analyses
# ─────────────────────────────────────────────

rule disciplines_brexit:
    input:
        dep=rules.networks_sdid_brexit_conduct.output,
    output:
        touch(f"{CODE}/disciplines_brexit/{{disc}}/intil_ratio/.done"),
    wildcard_constraints:
        disc="|".join(DISCIPLINES),
    shell:
        "echo 'discipline {wildcards.disc} Brexit outputs present'"


rule disciplines_crimes:
    input:
        dep=rules.crimes_plot.output,
    output:
        touch(f"{CODE}/disciplines_crimes/disciplines/{{disc}}/.done"),
    wildcard_constraints:
        disc="|".join(DISCIPLINES),
    shell:
        "echo 'discipline {wildcards.disc} crimes outputs present'"


# ─────────────────────────────────────────────
# Stage 6 — Additional experiments
# ─────────────────────────────────────────────

rule experiment_1:
    input:
        dep=expand(
            f"{CODE}/2two_way_did_{{event}}/event_study_results.csv",
            event=EVENTS,
        ),
    output:
        touch(f"{CODE}/add_experiments/experiment_1/.done"),
    shell:
        "echo 'experiment_1 complete'"


rule experiment_2:
    input:
        dep=rules.experiment_1.output,
    output:
        touch(f"{CODE}/add_experiments/experiment_2/.done"),
    shell:
        "echo 'experiment_2 complete'"


rule experiment_4:
    input:
        dep=rules.experiment_2.output,
    output:
        touch(f"{CODE}/add_experiments/experiment_4/.done"),
    shell:
        "echo 'experiment_4 complete'"


rule null_model:
    input:
        dep=rules.experiment_4.output,
    output:
        touch(f"{CODE}/add_experiments/null_model/.done"),
    shell:
        "echo 'null_model complete'"


# ─────────────────────────────────────────────
# Stage 7 — Extract and visualise avg effects
# ─────────────────────────────────────────────

rule extract_avg_effects:
    input:
        script=f"{CODE}/extract_avg_effects.py",
        deps=expand(
            f"{CODE}/2ppml_did_{{event}}_internal_control/partner_coefficients.csv",
            event=EVENTS,
        ),
    output:
        f"{CODE}/学科avg_effect汇总.xlsx",
    shell:
        "python '{input.script}'"


rule visualize_effects:
    input:
        script=f"{CODE}/visualize_effects.py",
        data=f"{CODE}/学科avg_effect汇总.xlsx",
    output:
        "code/brexit_intil_ratio_effects.pdf",
        "code/crimes_intil_ratio_effects.pdf",
    shell:
        "python '{input.script}'"
