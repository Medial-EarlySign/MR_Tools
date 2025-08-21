#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR SILENCE_RUN_INPUT_FILES_PATH SILENCE_RUN_OUTPUT_FILES_PATH AWS_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_INPUT_PATH AWS_OUTPUT_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

mkdir -p ${WORK_DIR%/*}
mkdir -p ${WORK_DIR}

mkdir -p ${SILENCE_RUN_INPUT_FILES_PATH}

aws s3 cp ${AWS_INPUT_PATH} ${SILENCE_RUN_INPUT_FILES_PATH}/input.tsv

if [ "${SILENCE_RUN_OUTPUT_FILES_PATH}" != "GENERATE"]; then
	mkdir -p ${SILENCE_RUN_OUTPUT_FILES_PATH%/*}
	aws s3 cp ${AWS_OUTPUT_PATH} ${SILENCE_RUN_OUTPUT_FILES_PATH}
fi
