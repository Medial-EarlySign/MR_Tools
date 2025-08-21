#!/bin/bash

base_dir=${0%/*}/..

awk '{print $1"_"$3"_"$4}' ${base_dir}/Fixed/RDW > ${base_dir}/outputs/rdw_new_data.txt
echo "add missing lines"
awk '{print $1"_"$3"_"$4}' ${base_dir}/missing_pids_from_2016/Fixed/RDW | subtract.pl - 0 ${base_dir}/outputs/rdw_new_data.txt 0 | awk 'BEGIN {FS="_"} {print $1"\tRDW\t"$2"\t"$3}' >> ${base_dir}/outputs/RDW_tmp
ln_cnt=`wc -l ${base_dir}/outputs/RDW_tmp | awk '{print $1}'`
echo "added ${ln_cnt} lines"
cat ${base_dir}/Fixed/RDW >> ${base_dir}/outputs/RDW_tmp

echo "sorting"
sort -S 5G -n -k1 ${base_dir}/outputs/RDW_tmp > ${base_dir}/outputs/RDW_final
rm -f ${base_dir}/outputs/RDW_tmp

cp -f ${base_dir}/outputs/RDW_final ${base_dir}/Fixed
rm ${base_dir}/outputs/RDW_final

