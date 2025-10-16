#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR) # Required parameters
DEPENDS=() # Specify dependent tests to run: 3
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

REPOSITORY_PATH=${WORK_DIR}/rep/test.repository
TEST_SAMPLES=${WORK_DIR}/Samples/3.test_cohort.samples
CALIBRATED_MODEL_PATH=${WORK_DIR}/model/model.medmdl

MEM_LIMIT_ADD=""
if [ ! -z "${MEMORY_LIMIT}" ] && [ ${MEMORY_LIMIT} -gt 0 ] ; then
    TMP="change_name=Limit_Memory;object_type_name=MedModel;change_command={max_data_in_mem=${MEMORY_LIMIT}}"
    MEM_LIMIT_ADD="--change_model_init ${TMP}"
fi

if [ ! -f ${WORK_DIR}/compare/test.calibrated.preds ] || [ ${OVERRIDE} -gt 0 ]; then
	Flow --rep ${REPOSITORY_PATH} --get_model_preds --f_model ${CALIBRATED_MODEL_PATH} --f_samples ${TEST_SAMPLES} --f_preds ${WORK_DIR}/compare/test.calibrated.preds ${MEM_LIMIT_ADD}
fi

mkdir -p ${WORK_DIR}/pref_from_calibration

PerformanceFromCalibration --preds ${WORK_DIR}/compare/test.calibrated.preds --output ${WORK_DIR}/pref_from_calibration/result
