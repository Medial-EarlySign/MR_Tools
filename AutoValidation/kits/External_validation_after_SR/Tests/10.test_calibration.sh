#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR FIRST_WORK_DIR BT_COHORT_CALIBRATION BT_JSON_CALIBRATION) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

REPOSITORY_PATH=${WORK_DIR}/rep/test.repository	
INPUT_PREDS=${FIRST_WORK_DIR}/compare/3.test_cohort.preds
if [ -f ${FIRST_WORK_DIR}/predictions/all.preds ]; then
	INPUT_PREDS=${FIRST_WORK_DIR}/predictions/all.preds
fi
TEST_SAMPLES=$WORK_DIR/Samples/relabeled.samples
SMP_SIZE=$(cat ${TEST_SAMPLES} | wc -l)
if [ ! -f ${WORK_DIR}/bootstrap/all.preds ] || [ ${INPUT_PREDS} -nt ${WORK_DIR}/bootstrap/all.preds ] || [ ${TEST_SAMPLES} -nt ${WORK_DIR}/bootstrap/all.preds ] || [ $OVERRIDE -gt 0 ]; then
		paste.py -f1 ${TEST_SAMPLES} -ids1 1 2 -f2 ${INPUT_PREDS} -ids2 1 2 -ads2 6 -os $'\t' > ${WORK_DIR}/bootstrap/all.preds	
fi
PRED_SIZE=$(cat ${WORK_DIR}/bootstrap/all.preds | wc -l)

if [ $PRED_SIZE -ne $SMP_SIZE ]; then
	echo "Requested to join input samples with ${SMP_SIZE} and ended up with ${PRED_SIZE} samples"
fi

if [ ! -f ${WORK_DIR}/bootstrap/eligible_only.preds ] || [ ${WORK_DIR}/bootstrap/all.preds -nt ${WORK_DIR}/bootstrap/eligible_only.preds ] || [ $OVERRIDE -gt 0 ]; then
	cat ${WORK_DIR}/bootstrap/all.preds | awk -F"\t" 'BEGIN {OFS="\t"} NR==1 || $7=="" || NF==7 {if (NF==7) {print $0} else { print $1,$2,$3,$4,$5,$6,$8}}' > ${WORK_DIR}/bootstrap/eligible_only.preds
fi

TEST_SAMPLES_CALIBRATION=${WORK_DIR}/bootstrap/eligible_only.preds

set +e +o pipefail
HAS_YEAR_COHORT=$(cat ${BT_COHORT_CALIBRATION} | grep "Year" | wc -l)
set -e -o pipefail
if [ $HAS_YEAR_COHORT -lt 1 ]; then
	echo "WARNING BT_COHORT_CALIBRATION = ${BT_COHORT_CALIBRATION} doesn't contains performance by year analysis"
	#exit 1
fi

mkdir -p ${WORK_DIR}/calibration
mkdir -p ${WORK_DIR}/calibration/graphs

mkdir -p ${WORK_DIR}/tmp
if [ ! -f ${WORK_DIR}/calibration/test_calibration ] || [ $OVERRIDE -gt 0 ]; then
	echo "${TEST_SAMPLES_CALIBRATION}" > ${WORK_DIR}/tmp/tests
	TestCalibration --tests_file ${WORK_DIR}/tmp/tests --output ${WORK_DIR}/calibration/test_calibration --rep ${REPOSITORY_PATH} --json_model ${BT_JSON_CALIBRATION}  --cohorts_file ${BT_COHORT_CALIBRATION} --bootstrap_graphs ${WORK_DIR}/calibration/graphs --pred_binning_arg "split_method=iterative_merge;binCnt=100;min_bin_count=100;min_res_value=0.001" --bt_params "loopCnt=500;sample_per_pid=0"

	awk -F"\t" '{print $7, $(NF-1), $(NF-2), $4}' ${TEST_SAMPLES_CALIBRATION}  | sort -S40% -r -g -k1 | awk '{s+=$1; c+=$4; n+=1} END {print "mean_score", "mean_outcome/incidence", "total_count";print s/n, c/n, n}'
fi

echo "Please refer to ${WORK_DIR}/calibration/bt.pivot_txt"

echo "please verify it has Years, Monthly, Different time windows, different groups, membership period"