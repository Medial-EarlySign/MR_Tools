#!/bin/bash
tail -n +2 /server/Work/Users/Alon/NWP/Data/medial_flu_diagnosis.tsv | awk -F"\t" 'BEGIN {OFS="\t";} { gsub(/,/,".",$9); gsub(/ /,"_",$9); gsub(/[, ]/,"_",$10) ;print $2, "DIAGNOSIS", $6, $10 ":" $9}' | sort -S"80%" -g -k1 -k3 > /server/Work/Users/Alon/NWP/Load/DIAGNOSIS.tsv
