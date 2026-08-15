import excel "/Users/sunmengge/Dropbox/Brexit/Data/experimental_data/stata_results/crimes/original_completed.xlsx", sheet("Sheet1") firstrow clear

gen treated = (Country == "RUSSIAN FEDERATION" & Year > 2022)
// RUSSIAN FEDERATION

gen log_pub_total = log(pub_total + 1)
gen log_gdp_per_capita = log(gdp_per_capita + 1)
gen log_rp = log(ResearchersinRD + 1)

sdid log_pub_total Country Year treated, vce(placebo) covariates(log_gdp_per_capita RD log_rp) graph g2_opt()
