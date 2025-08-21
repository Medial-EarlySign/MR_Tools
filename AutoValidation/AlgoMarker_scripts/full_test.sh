#!/bin/bash
set -e
source ${0%/*}/env.sh

OVERRIDE=${1-0}

CURR_DIR=${0%/*}
AM_DIR=$(realpath ${CURR_DIR}/..)
AM_CONFIG=$(ls -1 ${AM_DIR}/*.amconfig)
LIB_PATH=${AM_DIR}/lib/libdyn_AlgoMarker.so
MODEL_PATH=$(awk -F"\t" -v base_dir="${AM_DIR}" '$1=="MODEL" {print base_dir "/" $2}' ${AM_CONFIG})

EXP_DIR=${AM_DIR}/examples

mkdir -p ${EXP_DIR}

if [ ! -f ${EXP_DIR}/req.json ]; then
	REQ_PATH=${CURR_DIR}/configs/jreq_defs.json
	if [ -f ${CURR_DIR}/configs/jreq_defs.butwhy.json ]; then
		REQ_PATH=${CURR_DIR}/configs/jreq_defs.butwhy.json
	fi

	${APP_PATH} --rep $TEST_REP --samples ${TEST_SAMPLES} --model  $MODEL_PATH --amconfig $AM_CONFIG --create_jreq --single --jreq_out ${EXP_DIR}/req.json --jreq_defs ${REQ_PATH}
fi

if [ ! -f ${EXP_DIR}/data.json ]; then
#Create data json single must be turnned on
	SIG_RENAME=""
	if [ -f ${CURR_DIR}/configs/signal_rename.tsv ]; then
		SIG_RENAME="--rename_signal ${CURR_DIR}/configs/signal_rename.tsv"
	fi
	
	SIG_REGEX_FILTER=""
	if [ -f ${CURR_DIR}/configs/signal_regex_filter.tsv ]; then
		SIG_REGEX_FILTER="--signal_categ_regex ${CURR_DIR}/configs/signal_regex_filter.tsv"
	fi
	${APP_PATH} --rep $TEST_REP --samples ${TEST_SAMPLES} --model  $MODEL_PATH --amconfig $AM_CONFIG --out_jsons ${EXP_DIR}/data.json --single --calculator "LungFlag" --allow_rep_adjustment 1 ${SIG_REGEX_FILTER} ${SIG_RENAME}
	
	#--ignore_sig to ignore signal
fi

if [ ! -f ${EXP_DIR}/resp.json ] || [ $OVERRIDE -gt 0 ]; then
#Test from input jsons and store output: --json_req_test --in_jsons PATH_TO_DATA_JSON(if REQ_JSON_HAS_NO_DATA, NOT CREATED WITH --add_data_to_jreq) --jreq PATH_TO_REQUEST_JSON --jresp PATH_TO_OUTPUT_RESPONSE
	${APP_PATH} --amlib $LIB_PATH --amconfig $AM_CONFIG --json_req_test --in_jsons ${EXP_DIR}/data.json --jreq ${EXP_DIR}/req.json --jresp ${EXP_DIR}/resp.json --single --print_msgs --discovery ${AM_DIR}/discovery.json
fi

echo "Please run this to start server:"
echo "python $MR_ROOT/Tools/test_algomarker/show_explainer_output.py ${EXP_DIR}/resp.json"