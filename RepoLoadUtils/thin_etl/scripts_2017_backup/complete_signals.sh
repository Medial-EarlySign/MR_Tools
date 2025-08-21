#!/bin/bash

ROOT=/server/UsersData/ido/MR
base_folder=${0%/*}/..
base_code=${MR_ROOT}/Tools/RepoLoadUtils/thin_etl

mkdir -p ${base_folder}/Completions

$ROOT/Tools/RepoLoadUtils/Linux/Release/PanelCompleter --repository_file=${base_folder}/repository_data/thin.repository --out_folder=${base_folder}/Completions --codes_to_signals_file=${base_folder}/repository_data/codes_to_signals --instructions_file=${base_code}/config_2017/Instructions.txt
