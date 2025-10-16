#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR FIRST_WORK_DIR OUTCOME_INPUT_FILES_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh
CURR_PT=$2

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "Loading Repository"

#First - let's load Repository if not loaded yet:
mkdir -p ${WORK_DIR}
mkdir -p ${WORK_DIR}/ETL
mkdir -p ${WORK_DIR}/rep
mkdir -p ${WORK_DIR}/rep/data
mkdir -p ${WORK_DIR}/tmp

cp -R ${FIRST_WORK_DIR}/ETL/* ${WORK_DIR}/ETL

#To call general ETL:
python ${CURR_PT}/resources/lib/ETL/load_outcomes.py "${1}" "${2}"

if [ ! -f ${WORK_DIR}/rep/loading_done ] || [ $OVERRIDE -gt 0 ]; then
	chmod +x ${WORK_DIR}/ETL/rep_configs/load_with_flow.sh
	${WORK_DIR}/ETL/rep_configs/load_with_flow.sh

	echo "Loaded done" > ${WORK_DIR}/rep/loading_done
fi


