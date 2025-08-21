#!/bin/bash
set -e

CURR_DIR=${0%/*}
AM_DIR=$(realpath ${CURR_DIR}/..)
AM_CONFIG=$(ls -1 ${AM_DIR}/*.amconfig)
LIB_PATH=${AM_DIR}/lib/libdyn_AlgoMarker.so

EXP_DIR=${AM_DIR}/examples

mkdir -p ${EXP_DIR}

$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --amlib $LIB_PATH --amconfig $AM_CONFIG --json_req_test --in_jsons ${EXP_DIR}/data.single.json --jreq ${EXP_DIR}/req.single.json --jresp ${EXP_DIR}/resp.single.json --single --print_msgs --discovery ${AM_DIR}/discovery.json

#/server/UsersData/alon/MR/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --amlib $LIB_PATH --amconfig $AM_CONFIG --json_req_test --in_jsons ${EXP_DIR}/eldan/add_data.json --jreq ${EXP_DIR}/eldan/req.json --jresp ${EXP_DIR}/eldan/resp.json --single --print_msgs
#echo "result in ${EXP_DIR}/eldan/resp.json"

echo "result in ${EXP_DIR}/resp.single.json"