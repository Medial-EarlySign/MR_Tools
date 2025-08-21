#!/bin/bash
set -e -o pipefail

CURR_PT=${2}
source ${CURR_PT}/configs/env.sh
TEST_NAME_=${0##*/}
TEST_NAME=${TEST_NAME_%.*}

#EXIT CODE 0 When all OK
#EXIT CODE 1 when missing parameter
#EXIT CODE 2 when failed internal test
#EXIT CODE 3 when other error/crash

OVERRIDE=${1-0}

#Example test for parameters
REQ_PARAMS=(WORK_DIR MODEL_PATH)
for PARAM in ${REQ_PARAMS[@]}; do
	if [ -z "${!PARAM}" ]; then
		echo "${PARAM} is missing in environment - skipping test ${TEST_NAME}"
		exit 1
	fi
done

OUT_MODEL_PATH=${MODEL_PATH}.transformed

adjust_model --preProcessors ${CURR_PT}/configs/add_empty.json --skip_model_apply 1 --learn_rep_proc 0 --inModel ${MODEL_PATH} --out ${OUT_MODEL_PATH} 

echo "Created transformed model in ${OUT_MODEL_PATH} Please change the path of MODEL_PATH under ${CURR_PT}/configs/env.sh" | tee ${WORK_DIR}/${TEST_NAME}.log