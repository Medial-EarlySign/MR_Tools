#!/bin/bash
echo -e "SECTION\tDIAGNOSIS" > /server/Work/Users/Alon/NWP/dicts/dict.DIAGNOSIS

tail -n +2 /server/Work/Users/Alon/NWP/Data/medial_flu_diagnosis.tsv | awk -F"\t" 'BEGIN {OFS="\t";} {gsub(/[, ]/,"_", $NF); gsub(/,/,".",$9); gsub(/ /,"_",$9); gsub(/[, ]/,"_", $10); d[$10 ":" $9][$NF] = 1;} END { cnt=0; for (i in d)  {cnt = cnt +1; print "DEF", 100 + cnt, i; for (j in d[i]) {print "DEF", 100 + cnt, j;} }}' >> /server/Work/Users/Alon/NWP/dicts/dict.before.DIAGNOSIS
