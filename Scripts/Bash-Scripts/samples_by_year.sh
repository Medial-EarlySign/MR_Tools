#!/bin/bash
if [ -z "$1" ]; then
	echo "Please provide path to MedSampels"
	exit 1
else
	echo -e "Year\tControls\tcases\tpercentage"
	tail -n +2 $1 | awk '{ d[int($3/10000)][$4 >0]+=1; } END { for (i in d) { print i "\t" d[i][0] "\t" d[i][1] "\t" int(10000*d[i][1]/(d[i][1] + d[i][0]))/100 "%" } }' | sort -g -k1
fi

