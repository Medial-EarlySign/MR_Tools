#!/bin/bash

base_folder=${0%/*}/..
target_folder=$MR_ROOT/Tools/RepoLoadUtils/thin_etl/scripts_2017_backup

echo "backuping scripts folder..."
cp ${base_folder}/scripts/* ${target_folder}
echo "backuping rep_config folder..."
mkdir -p ${target_folder}/rep_configs
cp ${base_folder}/rep_configs/* ${target_folder}/rep_configs

mkdir -p ${target_folder}/missings_pids_from_2016/scripts
mkdir -p ${target_folder}/missings_pids_from_2016/rep_configs
cp ${base_folder}/missing_pids_from_2016/scripts/* ${target_folder}/missings_pids_from_2016/scripts
cp ${base_folder}/missing_pids_from_2016/rep_configs/* ${target_folder}/missings_pids_from_2016/rep_configs
#cp ${base_folder}/CommonValues ${target_folder}/outputs
#cp ${base_folder}/signal_units.stats ${target_folder}/outputs

