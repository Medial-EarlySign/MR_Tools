#!/bin/bash

base_folder=${0%/*}/../..

mkdir -p ${base_folder}/repository_data_final

cp ${base_folder}/dicts/dict.* ${base_folder}/repository_data_final
cp ${base_folder}/rep_configs/thin.signals ${base_folder}/repository_data_final
cp ${base_folder}/rep_configs/codes_to_signals ${base_folder}/repository_data_final

$MR_ROOT/Tools/Flow/Linux/Release/Flow --rep_create --convert_conf ${base_folder}/missing_pids_from_2016/rep_configs/thin.fix_specific2.convert_config 2>&1 | tee ${base_folder}/missing_pids_from_2016/outputs/thin.fix_specific2.convert_config.log

has_err=`egrep -i "error|failed" ${base_folder}/missing_pids_from_2016/outputs/thin.fix_specific2.convert_config.log | wc -l`

if [ $has_err -eq 0 ]; then
        echo "repository created successfully :)"
        $MR_ROOT/Tools/Flow/Linux/Release/Flow --rep_create_pids --rep=${base_folder}/repository_data_final/thin.repository
else
	echo "Error in creating repo"
fi


echo "All Done"
