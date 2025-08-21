#!/bin/bash
text_file_processor --input /server/Work/Users/Alon/NWP/Data/medial_flu_vaccination.tsv --output - --treat_missings original --config_parse "1;Vaccination;4;file:/server/Work/Users/Alon/NWP/Data/CVX_IMMUNZTN_NAME.tsv#1#2#0" | awk -F"\t" 'BEGIN {OFS="\t"} {print $1,$2,substr($3,1,10), "CVX_CODE:" int($4)}' | sort -S"80%" -g -k1 -k3 > /server/Work/Users/Alon/NWP/Load/vaccination.tsv

tail -n +2 /server/Work/Users/Alon/NWP/Data/medial_flu_or_vaccination.tsv | awk -F"\t" 'BEGIN {OFS="\t"} {print $2, "Vaccination", $5, "CVX_CODE:" int($3)}' | sort -S"80%" -g -k1 -k3 > /server/Work/Users/Alon/NWP/Load/vaccination_or.tsv 

tail -n +2 /server/Work/Users/Alon/NWP/Data/medial_flu_wa_vaccination.tsv | awk -F"\t" 'BEGIN {OFS="\t"} {print $2, "Vaccination", $3, "CVX_CODE:" int($4)}' | sort -S"80%" -g -k1 -k3 > /server/Work/Users/Alon/NWP/Load/vaccination_wa.tsv

#create Dict:
echo -e "SECTION\tVaccination" > /server/Work/Users/Alon/NWP/dicts/dict.Vaccination
tail -n +2 /server/Work/Users/Alon/NWP/Data/CVX_IMMUNZTN_NAME.tsv | awk -F"\t" 'BEGIN {OFS ="\t"} {gsub(/[, ]/,"_",$2); d[int($1)][$2]=1; } END {cnt = 0; for (i in d) { cnt = cnt + 1; print "DEF", 1000+cnt, "CVX_CODE:" i; for ( j in d[i] ) { print "DEF", 1000+cnt, j }} }' >> /server/Work/Users/Alon/NWP/dicts/dict.Vaccination
#add from WA  codes:
text_file_processor --input /server/Work/Users/Alon/NWP/Load/vaccination_or.tsv --output - --treat_missings original --config_parse "file:/server/Work/Users/Alon/NWP/dicts/dict.Vaccination#2#3#1" | grep "CVX_CODE:" | sort | uniq | awk 'BEGIN {OFS ="\t"} {print "DEF", 2000+NR, $1}' >> /server/Work/Users/Alon/NWP/dicts/dict.Vaccination

text_file_processor --input /server/Work/Users/Alon/NWP/Load/vaccination_wa.tsv --output - --treat_missings original --config_parse "file:/server/Work/Users/Alon/NWP/dicts/dict.Vaccination#2#3#1" | grep "CVX_CODE:" | sort | uniq | awk 'BEGIN {OFS ="\t"} {print "DEF", 3000+NR, $1}' >> /server/Work/Users/Alon/NWP/dicts/dict.Vaccination
