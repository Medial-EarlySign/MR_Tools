#!/bin/bash
set -e
source ${0%/*}/env.sh

CURR_DIR=${0%/*}
AM_DIR=$(realpath ${CURR_DIR}/..)
AM_CONFIG=$(ls -1 ${AM_DIR}/*.amconfig)
LIB_PATH=${AM_DIR}/lib/libdyn_AlgoMarker.so

EXP_DIR=${AM_DIR}/examples

mkdir -p ${EXP_DIR}

${APP_PATH} --amlib $LIB_PATH --amconfig $AM_CONFIG --json_req_test --in_jsons ${EXP_DIR}/data.single.json --jreq ${EXP_DIR}/req.single.json --jresp ${EXP_DIR}/resp.single.json --single --print_msgs --discovery ${AM_DIR}/discovery.json

echo "result in ${EXP_DIR}/resp.single.json"