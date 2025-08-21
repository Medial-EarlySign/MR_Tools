#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH CALIBRATED_MODEL TEST_SAMPLES_CALIBRATION BT_COHORT_CALIBRATION) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "OVERRIDE=${OVERRIDE}"

BT_JSON_P="--json_model ${BT_JSON_CALIBRATION}"
if [ -z "${BT_JSON_CALIBRATION}" ]; then
	echo "BT_JSON_CALIBRATION is missing in enviroment - Can't have complicated cohorts"
	BT_JSON_P=""
fi

HAS_YEAR_COHORT=$(cat ${BT_COHORT} | grep "Year" | wc -l)
if [ $HAS_YEAR_COHORT -lt 1 ]; then
	echo "BT_COHORT = ${BT_COHORT} doesn't contains performance by year analysis"
	exit 1
fi

mkdir -p ${WORK_DIR}/calibration
mkdir -p ${WORK_DIR}/calibration/graphs

#Get preds;
if [ ! -f ${WORK_DIR}/calibration/test.preds ] || [ $OVERRIDE -gt 0 ]; then
	Flow --get_model_preds --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES_CALIBRATION} --f_preds ${WORK_DIR}/calibration/test.preds --f_model ${CALIBRATED_MODEL}
fi

mkdir -p ${WORK_DIR}/tmp
if [ ! -f ${WORK_DIR}/calibration/test_calibration ] || [ $OVERRIDE -gt 0 ]; then
	echo "${WORK_DIR}/calibration/test.preds" > ${WORK_DIR}/tmp/tests
	TestCalibration --tests_file ${WORK_DIR}/tmp/tests --output ${WORK_DIR}/calibration/test_calibration --rep ${REPOSITORY_PATH} ${BT_JSON_P}  --cohorts_file ${BT_COHORT_CALIBRATION} --bootstrap_graphs ${WORK_DIR}/calibration/graphs --pred_binning_arg "split_method=iterative_merge;binCnt=100;min_bin_count=100;min_res_value=0.001" --bt_params "loopCnt=500"

	awk -F"\t" '{print $7, $(NF-1), $(NF-2), $4}' ${WORK_DIR}/calibration/test.preds  | sort -S40% -r -g -k1 | awk '{s+=$1; c+=$4; n+=1} END {print s/n, c/n, n}' 
fi

echo "Please refer to ${WORK_DIR}/calibration/bt.pivot_txt"

echo "please verify it has Years, Monthly, Different time windows, different groups, membership period" 