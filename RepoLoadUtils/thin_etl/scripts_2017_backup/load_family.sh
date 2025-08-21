#!/bin/bash
awk '{print substr(FILENAME,length(FILENAME)-4,10) substr($0,1,4)"\t""Family_Number""\t"substr($0,14,6)}' /server/Data/THIN1701/THINDB1701/patient.* | paste.pl - 0 ID2NR 0 1 > /server/Temp/Thin_2017_Loading/demo/Family_Number.temp
awk '{print substr(FILENAME,length(FILENAME)-4,10) substr($0,1,4)"\t""Family_Number""\t"substr($0,14,6)}' missing_pids_from_2016/data/patient.* | paste.pl - 0 ID2NR 0 1 >> /server/Temp/Thin_2017_Loading/demo/Family_Number.temp
awk '{print $4"\t"$2"\t"$3}' /server/Temp/Thin_2017_Loading/demo/Family_Number.temp > /server/Temp/Thin_2017_Loading/demo/Family_Number
#paste.pl demo/Family_Number 0 ID2NR 0 1 >  /server/Temp/Thin_2017_Loading/demo/Family_Number2
awk '{d[$3]+=1} END {for (i in d) print i,d[i]}' demo/Family_Number > demo/Family_Number.hist
