#!/bin/bash

base_folder=${0%/*}/..
block_proc=17798

mkdir -p ${base_folder}/repository_data_final
is_run=`ps -e | grep ${block_proc} | wc -l`
echo "Start running. blocking proces is ${is_run} running"

while [ $is_run -ne "0" ]; do
	sleep 3
	#echo "still running"
	is_run=`ps -e | grep ${block_proc} | wc -l`   
done

${base_folder}/scripts/run_create_rep_fix.sh

#echo "finished!" 
#has_err=`grep -i "error"  /server/Temp/Thin_2017_Loading/missing_pids_from_2016/outputs/thin.fix_specific.convert_config.log | wc -l`
echo "All Done."
