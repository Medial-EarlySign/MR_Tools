#!/bin/bash
$MR_ROOT/Tools/Flow/Linux/Release/Flow --rep repository_data_final/thin.repository --sig_print --sig RC --output csv --normalize 0 --binCnt 0 --age_min 0 --age_max 120 2>&1 > outputs/ReadCodes_Histogram.txt2
tail -n +2 outputs/ReadCodes_Histogram.txt2 | awk -F"," '{print int($1)"\t"int($2)}' > outputs/ReadCodes_Histogram.txt
grep DEF dicts/dict.read_codes  | paste.pl outputs/ReadCodes_Histogram.txt 0 - 1 2 > outputs/ReadCodes_Histogram.txt2
awk '{print $1"\t"$3"\t"$2}' outputs/ReadCodes_Histogram.txt2 > outputs/ReadCodes_Histogram.txt
cp outputs/ReadCodes_Histogram.txt repository_data_final
