#!/bin/bash

SIG=${1-Hemoglobin}

mkdir -p /mnt/work/LGI/loading_files/outputs/lab_plots

echo "Creating plot for ${SIG}"

awk -F"\t" '{bin=0.1; v=bin*int($4/bin); n+=1; c[$6 ":" $5][v]+=1; cc[$6 ":" $5]+=1} END { for (unit in c) { for (v in c[unit]) { print unit "(" cc[unit] ")" "\t" v "\t" c[unit][v] "\t" c[unit][v]/cc[unit]*100 "\t" cc[unit] } }   }' /mnt/work/LGI/loading_files/FinalSignals/BeforeFilter/${SIG} > /tmp/before_sort

cat /tmp/before_sort | sort -S80% -k5,5gr -k1,1 -k2,2g  | awk -F"\t" 'BEGIN {print "UNIT\tValue\tCount\tPercentage%\tGROUP_SIZE"} {print $0}' | plot.py --has_header 1 --group_col 0 --x_cols 1 --y_cols 3 --output /mnt/work/LGI/loading_files/outputs/lab_plots/${SIG}.html
