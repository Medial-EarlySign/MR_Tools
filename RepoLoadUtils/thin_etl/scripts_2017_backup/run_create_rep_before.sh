#!/bin/bash

base_folder=${0%/*}/..

mkdir -p ${base_folder}/repository_data

cp ${base_folder}/dicts/dict.* ${base_folder}/repository_data
cp ${base_folder}/rep_configs/thin.signals ${base_folder}/repository_data
cp ${base_folder}/rep_configs/codes_to_signals ${base_folder}/repository_data

#$MR_ROOT/Tools/Flow/Linux/Release/Flow --rep_create --convert_conf ${base_folder}/rep_configs/thin.before_completions.convert_config 2>&1 | tee ${base_folder}/outputs/thin.before_completions.convert_config.log
