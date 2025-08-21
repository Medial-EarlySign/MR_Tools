#!/bin/bash

SIGNAL=${1-Uric_Acid}
FIN_SIG_PATH=${2-/nas1/Work/Users/Tamar/thin21_load/FinalSignals}

awk -F"\t" '{split($NF,  arr, "|") ; c[arr[1] "_" arr[2]]+=1;} END {for (i in c) {print i "\t" c[i]}}' ${FIN_SIG_PATH}/${SIGNAL}_* | sort -g -r -k2 | awk -F"\t" '{printf("%s\t%03d\n", $1,NR);}' >  /tmp/units

awk -F"\t" '{split($NF,  arr, "|") ;print arr[1] "_" arr[2] "\t" $4}' ${FIN_SIG_PATH}/${SIGNAL}_*  | awk -F"\t" '{s[$1][$2]+=1; n[$1]+=1;} END { for (unit in n) { for (i in s[unit]) {print unit "\t" i "\t" s[unit][i]}}}' | sort -g -k1 -k2 -t $'\t' | paste.py -ids2 0 -ids1 0 -f2 /tmp/units -ads 1 -s $'\t' -os $'\t' -o 2 |  awk -F"\t" '{print $NF "::" $1 "\t" $2 "\t" $3 }' | plot.py --group_col 0 --x_cols 1 --y_cols 2 > ~/1.html

echo "Wrote html into ~/1.html"