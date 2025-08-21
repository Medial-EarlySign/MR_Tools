#!/bin/bash

pushd ${0%/*} > /dev/null 
WORK_DIR=$(python -c 'from Configuration import Configuration;cfg=Configuration();print(cfg.work_dir)')
popd > /dev/null

set -e

echo "Work Dir=${WORK_DIR}"

Flow --rep_create --convert_conf ${WORK_DIR}/rep_configs/ibm.convert_config --load_err_file ${WORK_DIR}/outputs/flow_loading_err.log --load_args "check_for_error_pid_cnt=500000;allowed_missing_pids_from_forced_ratio=0.03;max_bad_line_ratio=0.05;allowed_unknown_catgory_cnt=50" 2>&1 | tee ${WORK_DIR}/outputs/flow_loading.log

pushd ${0%/*} > /dev/null
REPO_DIR=$(python -c 'from Configuration import Configuration;cfg=Configuration();print(cfg.repo_folder)')
popd > /dev/null
REP_NAME=$(awk '$1=="CONFIG" {print $2}' ${WORK_DIR}/rep_configs/ibm.convert_config)
REP=$REPO_DIR/$REP_NAME

Flow --rep_create_pids --rep $REP
