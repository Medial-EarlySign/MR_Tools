#!/bin/bash
cat /server/Work/Users/Tamar/thin21_load/FinalSignals/PTT_thinlabs_1 /server/Work/Users/Tamar/thin21_load/FinalSignals/APTT_thinlabs_1 | awk -F"\t" '{split($NF, arr, "|"); split($3,b,"-"); print int($1) "\t" "SIGNAL_NAME" "\t" b[1] b[2] b[3] "\t" $4 "\t" arr[2] "\t" $6 }' | awk -F"\t" '{bin=5; val=int($4/bin)*bin; c[$(NF-1)][$NF][val]+=1; tot[$(NF-1)][$NF]+=1; } END { for (code in c) { for (unit in c[code]) { if (tot[code][unit]>1000) {for (v in c[code][unit]) { print code "\t" unit "\t" v "\t" c[code][unit][v] }} } } }' | sort -k1,2 -k3,3g | grep -v "42j9.00" > /tmp/a


echo "please refer to  /tmp/a to decide on mapping"

#Creation of all togehter
#cat /server/Work/Users/Tamar/thin21_load/FinalSignals/PTT_thinlabs_1 /server/Work/Users/Tamar/thin21_load/FinalSignals/APTT_thinlabs_1 | awk -F"\t" '{split($NF, arr, "|"); split($3,b,"-"); print int($1) "\t" "SIGNAL_NAME" "\t" b[1] b[2] b[3] "\t" $4 "\t" arr[2] "\t" $6 }' | paste.py -ids1 4 5 -f2 ../thin21_etl/PTT_APPT_map_with_units.tsv -ids2 0 1 -ads2 2 -s $'\t' -os $'\t' | awk -F"\t" 'BEGIN {OFS="\t"} {print $1, $NF,$3,$4,$5,$6}' | sort -S80% -k1,1g -k3,3g > /server/Work/Users/Tamar/thin21_load/FinalSignals/PTT_APPT_APTT_r_thinlabs.all_together