#!/bin/bash
if [ -z "$1" ]; then
	echo "please provide file path"
	exit 1
fi
MAX_GRP=${2-3}
MAX_LEAD_FEATURE=${3-0}

#Assume each pid is uniq

cat $1 |awk -F '\t' '$1 ~ /^[0-9]+$/ {printf("%s",$1); for (i=4;i<=NF;i++) {printf("\t%s",$i);} printf("\n");}'|awk -F"\t" -v max_groups=$MAX_GRP -v lead_f_cnt=$MAX_LEAD_FEATURE 'BEGIN {OFS="\t";  prev_id=0; c=0;} { if (prev_id==$1) {  c=c+1;} else {printf("\n%d\t%f", $1, $2); prev_id=$1; c=1;} if (c <= max_groups) { split( $3, res, ":="); printf("\t%s\t%s", res[1], res[2]); for (j=1; j<=lead_f_cnt;j++) { col=2+2*j; split($col,res_f, ":="); printf("\t%s\t%s", res_f[1], $(col+1)); } } }' | sort -S80% -g -r -k2 | awk -F"\t" -v max_groups=$MAX_GRP -v lead_f_cnt=$MAX_LEAD_FEATURE 'BEGIN {OFS="\t"; printf( "id\tscore"); for (i=1;i<=max_groups;i++) {printf("\tgroup_%d\tcontrib_%d\tgroup_description_%d",i,i,i,i); for (j=1;j<=lead_f_cnt;j++) { printf("\tlead_feature_%d\tdescription_%d", j,j);} } printf("\n");  } {print $0}'
