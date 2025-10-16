#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH MODEL_PATH TEST_SAMPLES BT_JSON BT_COHORT) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

HAS_YEAR_COHORT=$(cat ${BT_COHORT} | { grep "Year" || true; } | wc -l)
if [ $HAS_YEAR_COHORT -lt 1 ]; then
	echo "BT_COHORT = ${BT_COHORT} doesn't contains performance by year analysis"
	exit 1
fi

mkdir -p ${WORK_DIR}/bootstrap

#Get preds;
if [ -z "${PREDS_CV}" ]; then
	if [ ! -f ${WORK_DIR}/bootstrap/test.preds ] || [ ${TEST_SAMPLES} -nt ${WORK_DIR}/bootstrap/test.preds ] || [ ${MODEL_PATH} -nt ${WORK_DIR}/bootstrap/test.preds ] || [ ${REPOSITORY_PATH} -nt ${WORK_DIR}/bootstrap/test.preds ]; then
		Flow --get_model_preds --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES} --f_preds ${WORK_DIR}/bootstrap/test.preds --f_model ${MODEL_PATH}
	fi
else
	if [ ! -f ${WORK_DIR}/bootstrap/test.preds ]; then
		ln -s ${PREDS_CV} ${WORK_DIR}/bootstrap/test.preds
	fi
fi

if [ ! -f ${WORK_DIR}/bootstrap/bt.pivot_txt ] || [ ${WORK_DIR}/bootstrap/test.preds -nt ${WORK_DIR}/bootstrap/bt.pivot_txt ] || [ ${BT_COHORT} -nt ${WORK_DIR}/bootstrap/bt.pivot_txt ] || [ ${BT_JSON} -nt ${WORK_DIR}/bootstrap/bt.pivot_txt ]; then
	bootstrap_app --use_censor 0 --sample_per_pid 0 --rep ${REPOSITORY_PATH} --json_model ${BT_JSON} --cohorts_file ${BT_COHORT} --working_points_fpr 0.1,0.5,1,2,3,4,5,6,7,8,9,10,12,15,17,20,25,30,35,40,45,50 --working_points_sens 10,20,30,40,50,60,65,70,75,80,85,90,95,99 --working_points_pr 0.1,0.5,1,2,3,4,5,6,7,8,9,10,12,15,17,20,25,30,35,40,45,50 --input ${WORK_DIR}/bootstrap/test.preds --output ${WORK_DIR}/bootstrap/bt
fi

echo "Please refer to ${WORK_DIR}/bootstrap/bt.pivot_txt"

echo "please verify it has Years, Monthly, Different time windows, different groups, membership period" 