# 02_ppml_partners_*

Partner-level Poisson PML difference-in-differences with *internal*
controls: within a focal country, collaboration with partner *k* is
compared with the rest of that country's partner portfolio.

This is the specification behind the main-text choropleth maps.

| Folder | Paper figure |
|---|---|
| `02_ppml_partners_uk` | `uk_cooperation_changes_geopandas` |
| `02_ppml_partners_russia` | `russia_cooperation_changes_geopandas` |
| `02_ppml_partners_ukraine` | `ukraine_cooperation_changes_geopandas` |
| `02_ppml_partners_eu` | SI G.4 (EU-27 parallel) |

Run order: `1generate_ppml_data.py` → `2ppml_analysis.do` →
`3extract_partner_coefficients.do` → `4visualize_partner_changes_geopandas.py`.
