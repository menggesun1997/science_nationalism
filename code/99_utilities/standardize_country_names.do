cd "$CODE"
replace Country = upper(strtrim(Country))
replace Country = subinstr(Country, ".", "", .)
replace Country = subinstr(Country, ",", "", .)
replace Country = stritrim(Country)
replace Country = "KOREA" if Country == "KOREA REP"
replace Country = subinstr(Country, " ", "_", .)
