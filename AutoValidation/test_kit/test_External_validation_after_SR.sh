#!/bin/bash
set -e
#Test we are with right python:

CURRENT_DIR=$(realpath ${0%/*})
source ${CURRENT_DIR}/env.sh

OVERRIDE=${1-0}
KIT_FOLDER=/nas1/Temp/test_kit_results/External_validation_after_SR/${ALGOMARKER_NAME}
TESTKIT_CODE_FOLDER=${KIT_FOLDER}/TestKit_Code
TESTS_RESULTS_FOLDER=${KIT_FOLDER}/Kit_Results
mkdir -p ${TESTKIT_CODE_FOLDER}
mkdir -p ${TESTS_RESULTS_FOLDER}
if [ $OVERRIDE -gt 0 ]; then
	rm -fr ${TESTKIT_CODE_FOLDER}
	mkdir -p ${TESTKIT_CODE_FOLDER}
	rm -fr ${TESTS_RESULTS_FOLDER}
fi

# 1. First step, create the vanila kit:
pushd ${TESTKIT_CODE_FOLDER} > /dev/null
if [ ! -f ${TESTKIT_CODE_FOLDER}/run.sh ]; then
	${CURRENT_DIR}/../kits/generate_tests.sh <<< "External_validation_after_SR"
fi
# 2. Now Let's configure:
#fix source env:
sed -i 's|^source .*|source \${SCRIPT_PATH%/*}/../../../../External_Silent_Run/'${ALGOMARKER_NAME}'/TestKit_Code/configs/env.sh|g' configs/env.sh
#Configure WORK_DIR
sed -i 's|^WORK_DIR=.*|WORK_DIR='${TESTS_RESULTS_FOLDER}'|g' configs/env.sh
#Configure to use already loaded repository to test, configured in env.sh
sed -i 's|^REPOSITORY_PATH=.*||g' configs/env.sh
echo "REPOSITORY_PATH=${TEST_REPOSITORY_PATH}" >> configs/env.sh
cp Tests/Templates/01.load_existing_repositoty.sh Tests/
#Remove alt preds:
sed -i 's|^ALT_PREDS_PATH=|#ALT_PREDS_PATH=|g' configs/env.sh
echo "BT_COHORT_CALIBRATION=\${BT_COHORT}" >> configs/env.sh
echo "BT_JSON_CALIBRATION=\${BT_JSON}" >> configs/env.sh
#Add COHORTS
#echo "COHORTS=Age_50-75=Age:50,75" >> configs/env.sh

# 3. Now let's execute
./run.sh

# 4. Let's test!


#Finish
popd > /dev/null
