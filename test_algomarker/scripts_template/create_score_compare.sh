#!/bin/bash
set -e

BASE_SAMPLES=/server/Work/Users/Alon/LungCancer/outputs/models/model_55.3y_matched_history.train_and_test.optimize_on_all/Samples/all.samples
TEST_REP=/home/Repositories/KP/kp.repository
ORIG_MODEL=/nas1/Work/Users/Eitan/Lung/outputs/models2023/EX3/model_63/config_params/calibrated.medmdl


OVERRIDE=${1-0}

CURR_DIR=${0%/*}
AM_DIR=$(realpath ${CURR_DIR}/..)
AM_CONFIG=$(ls -1 ${AM_DIR}/*.amconfig)
LIB_PATH=${AM_DIR}/lib/libdyn_AlgoMarker.so
MODEL_PATH=$(awk -F"\t" -v base_dir="${AM_DIR}" '$1=="MODEL" {print base_dir "/" $2}' ${AM_CONFIG})
EXP_DIR=${AM_DIR}/score_compare

mkdir -p ${EXP_DIR}

if [ ! -f ${EXP_DIR}/test.samples ] || [ $OVERRIDE -gt 0 ]; then
	cat ${BASE_SAMPLES} | awk 'BEGIN {OFS="\t"} {c[$2]+=1; if (NR==1) {print $0} else { if (c[$2]==1) {print $1,$2,20180101,$4,$5,$6} }}' > ${EXP_DIR}/test.samples
fi

#Create basic request
if [ ! -f ${EXP_DIR}/req.json ] || [ $OVERRIDE -gt 0 ]; then
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --rep $TEST_REP --samples ${EXP_DIR}/test.samples --model  $MODEL_PATH --amconfig $AM_CONFIG --create_jreq --single --jreq_out ${EXP_DIR}/req.json --jreq_defs ${CURR_DIR}/jreq_defs.json
fi

if [ ! -f ${EXP_DIR}/data.json ] || [ $OVERRIDE -gt 0 ]; then
#Create data json single must be turnned on
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --rep $TEST_REP --samples ${EXP_DIR}/test.samples --model  $MODEL_PATH --amconfig $AM_CONFIG --out_jsons ${EXP_DIR}/data.json --single --calculator "LungFlag" --allow_rep_adjustment 1 --signal_categ_regex ${CURR_DIR}/signal_regex_filter.tsv --rename_signal ${CURR_DIR}/signal_rename.tsv
	
	#--ignore_sig to ignore signal
fi

if [ ! -f ${EXP_DIR}/resp.json ] || [ $OVERRIDE -gt 0 ]; then
#Test from input jsons and store output: --json_req_test --in_jsons PATH_TO_DATA_JSON(if REQ_JSON_HAS_NO_DATA, NOT CREATED WITH --add_data_to_jreq) --jreq PATH_TO_REQUEST_JSON --jresp PATH_TO_OUTPUT_RESPONSE
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --amlib $LIB_PATH --amconfig $AM_CONFIG --json_req_test --in_jsons ${EXP_DIR}/data.json --jreq ${EXP_DIR}/req.json --jresp ${EXP_DIR}/resp.json --single --print_msgs --discovery ${AM_DIR}/discovery.json
fi

if [ ! -f ${EXP_DIR}/flow_code.preds ] || [ $OVERRIDE -gt 0 ]; then
if [ -z "${ORIG_MODEL}" ]; then
	ORIG_MODEL=$MODEL_PATH
fi
	Flow --rep $TEST_REP --get_model_preds --f_samples ${EXP_DIR}/test.samples --f_preds ${EXP_DIR}/flow_code.preds --f_model ${ORIG_MODEL} --change_model_init "object_type_name=TreeExplainer;change_command=DELETE;verbose_level=2"
fi

#compare ${EXP_DIR}/flow_code.preds to ${EXP_DIR}/resp.json
python $MR_ROOT/Tools/test_algomarker/am_tester.py --json_resp_path ${EXP_DIR}/resp.json --preds_path ${EXP_DIR}/flow_code.preds | tee ${EXP_DIR}/compare_algomarker_flow.log
