#!/bin/bash
/server/Temp/Thin_2017_Loading/scripts/cmp_commonValue.py | grep SHRINK | awk 'BEGIN {FS="\t"} {if ( $6>100 ) print $1"\t"$2"\t"$4"\t"$6 }' | sort -n -k5 -r
