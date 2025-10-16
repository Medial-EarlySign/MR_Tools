#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

HAS_DIAG=$(cat ${WORK_DIR}/rep/test.signals | { grep DIAGNOSIS || true; } | wc -l)
if [ $HAS_DIAG -lt 1 ]; then
        echo "No Diagnosis skipping..."
        exit 0
fi

REP_PATH=${WORK_DIR}/rep/test.repository

TEST_SAMPLES=${WORK_DIR}/predictions/all.preds

if [ -z "${DIAG_PREFIX}" ]; then
        echo "DIAG_PREFIX s missing in enviroment - skipping test ${TEST_NAME}"
        exit 1
fi


OUT_PATH=${WORK_DIR}/unmapped_diagnosis
mkdir -p ${OUT_PATH}

find_unmapped_codes --rep $REP_PATH --sig DIAGNOSIS --regex_target ${DIAG_PREFIX} --output_path ${OUT_PATH}/missing_from_dictionaries.csv

if [ -z "$OTHER_DIAG_PREFIX" ]; then
	python ${CURR_PT}/resources/lib/explore_diag.py --rep $REP_PATH --samples $TEST_SAMPLES --mydic ${OUT_PATH}/missing_from_dictionaries.csv --output ${OUT_PATH}/missing.ALL.txt
else
	prefix=$(echo $OTHER_DIAG_PREFIX | tr "," "\n")
	for pre in $prefix
	do
		python ${CURR_PT}/resources/lib/explore_diag.py --rep $REP_PATH --samples $TEST_SAMPLES --mydic ${OUT_PATH}/missing_from_dictionaries.csv --prefix $pre --output ${OUT_PATH}/missing.${pre}.txt
	done
fi

