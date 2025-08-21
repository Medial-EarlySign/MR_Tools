#!/bin/bash
TimeRangeMerger --output /nas1/Temp/NWP/res/MERGE --has_header 0 --date_app 20190501 20200401 20200801 20201101 --input /nas1/Temp/NWP/FILE_1 /nas1/Temp/NWP/FILE_2 /nas1/Temp/NWP/FILE_3 /nas1/Temp/NWP/FILE_4 --close_buffer_backward 30 --close_buffer_foreward 30

#Fetch last flag of active/non active status of members
awk '{if (FILENAME!="/nas1/Temp/NWP/FILE_4") {d[$1]=0;} else { if (d[$1] < $NF) {d[$1]=$NF;}}} END {for (p in d) {print int(p) "\t" int(d[p])}}' /nas1/Temp/NWP/FILE_1 /nas1/Temp/NWP/FILE_2 /nas1/Temp/NWP/FILE_3 /nas1/Temp/NWP/FILE_4 | sort -S80% -g -k1 > /tmp/last.pids

#Convert to loading format
text_file_processor --has_header 0 --input /nas1/Temp/NWP/res/MERGE --config_parse '0;1;2;file:/tmp/last.pids#0#0#1' --output - | sort -S80% -g -k1 -k2 | awk 'BEGIN {OFS="\t"} {print $1, "MEMBERSHIP", $2, $3, $4}' > /nas1/Temp/NWP/res/sorted_Membership

echo "Your file is in here: /nas1/Temp/NWP/res/sorted_Membership"