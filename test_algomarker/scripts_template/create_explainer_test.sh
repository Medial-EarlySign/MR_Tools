#!/bin/bash
set -e

OVERRIDE=${1-0}

CURR_DIR=${0%/*}
AM_DIR=$(realpath ${CURR_DIR}/..)
AM_CONFIG=$(ls -1 ${AM_DIR}/*.amconfig)
LIB_PATH=${AM_DIR}/lib/libdyn_AlgoMarker.so
MODEL_PATH=$(awk -F"\t" -v base_dir="${AM_DIR}" '$1=="MODEL" {print base_dir "/" $2}' ${AM_CONFIG})
EXP_DIR=${AM_DIR}/minimal_score_compare

mkdir -p ${EXP_DIR}

# Generate test.samples from req.json

if [ ! -f ${EXP_DIR}/data.json ]; then
	echo "Please run run_minimal_score_compare.sh first"
	exit -1
fi

#Create basic request
if [ ! -f ${EXP_DIR}/req.butwhy.json ] || [ $OVERRIDE -gt 0 ]; then
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --samples ${EXP_DIR}/test.samples --model  $MODEL_PATH --amconfig $AM_CONFIG --create_jreq --single --jreq_out ${EXP_DIR}/req.butwhy.json --jreq_defs ${CURR_DIR}/jreq_defs.butwhy.json
fi


if [ ! -f ${EXP_DIR}/resp.butwhy.json ] || [ $OVERRIDE -gt 0 ]; then
#Test from input jsons and store output: --json_req_test --in_jsons PATH_TO_DATA_JSON(if REQ_JSON_HAS_NO_DATA, NOT CREATED WITH --add_data_to_jreq) --jreq PATH_TO_REQUEST_JSON --jresp PATH_TO_OUTPUT_RESPONSE
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --amlib $LIB_PATH --amconfig $AM_CONFIG --json_req_test --in_jsons ${EXP_DIR}/data.json --jreq ${EXP_DIR}/req.butwhy.json --jresp ${EXP_DIR}/resp.butwhy.json --single --print_msgs --discovery ${AM_DIR}/discovery.json
fi

echo "Please run this to start server:"
echo "python $MR_ROOT/Tools/test_algomarker/show_explainer_output.py ${EXP_DIR}/resp.butwhy.json"
