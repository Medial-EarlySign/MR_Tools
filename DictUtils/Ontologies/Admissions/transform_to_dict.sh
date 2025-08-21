#!/bin/bash

STORE_PATH=$1

if [ -z "$STORE_PATH" ]; then
	echo "please provide target path to save dict"
	exit -1
fi

tail -n +2 ${0%/*}/KPNW_ADMISSIONS.tsv | awk -F"\t" 'BEGIN {OFS="\t"} {if (NR==1) {print "SECTION\tADMISSION,VISIT"}; if($2!="") {k="ADM_TYPE::" $2; d[k]+=1; if (d[k]==1) { print "DEF", 8000+NR ,k}  ; print "SET", k, $1;} if ($3!="") {k= "ADM_DEP::" $4; d[k]+=1; if (d[k]==1) { print "DEF", 8000+NR ,k; } print "SET", k, $1;} if ($4!="") {k="ADM_CATEG::" $4; d[k]+=1; if (d[k]==1) { print "DEF", 8000+NR ,k;} print "SET", k, $1} }' > $STORE_PATH
