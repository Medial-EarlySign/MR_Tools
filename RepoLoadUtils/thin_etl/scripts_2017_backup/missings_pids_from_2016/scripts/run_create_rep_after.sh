#!/bin/bash

base_folder=${0%/*}/../..

mkdir -p ${base_folder}/repository_data_final

cp ${base_folder}/dicts/dict.* ${base_folder}/repository_data_final
cp ${base_folder}/rep_configs/thin.signals ${base_folder}/repository_data_final
cp ${base_folder}/rep_configs/codes_to_signals ${base_folder}/repository_data_final

$MR_ROOT/Tools/Flow/Linux/Release/Flow --rep_create --convert_conf ${base_folder}/rep_configs/thin.after_completions.convert_config 2>&1 | tee ${base_folder}/outputs/thin.after_completions.convert_config.log

#echo "creating op index"
#$MR_ROOT/Tools/Flow/Linux/Release/Flow --rep_create_pids --rep=${base_folder}/repository_data_final/thin.repository
