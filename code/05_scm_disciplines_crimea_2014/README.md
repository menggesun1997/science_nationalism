# 05_scm_disciplines_*

The same synthetic-control design as Figure 1, estimated separately for
14 NSF fields.

| Folder | Paper |
|---|---|
| `05_scm_disciplines_brexit` | SI E |
| `05_scm_disciplines_crimea_2014` | SI F.1 |
| `05_scm_disciplines_war_2022` | SI F.2 |

Inner folder spelling differs by tree (`intil_ratio` vs `initil_ratio`)
and is load-bearing. `code/extract_avg_effects.py` collects `avg_effect`
into `code/学科avg_effect汇总.xlsx`; `code/visualize_effects.py` draws
the SI bar charts.
