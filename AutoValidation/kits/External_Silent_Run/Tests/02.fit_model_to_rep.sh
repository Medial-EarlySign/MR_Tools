#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR MODEL_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

REP_NAME=$(ls -1 ${WORK_DIR}/rep | egrep "\.repository$")
REP_PATH=${WORK_DIR}/rep/${REP_NAME}

mkdir -p ${WORK_DIR}/model

echo "Creating transformed model in ${WORK_DIR}/model"
FINAL_MODEL_PATH=${WORK_DIR}/model/model.medmdl

Flow --fit_model_to_rep --rep ${REP_PATH} --f_model ${MODEL_PATH} --f_output ${FINAL_MODEL_PATH} --cleaner_verbose -1 --remove_explainability 1 --log_action_file_path ${WORK_DIR}/model/actions.log --log_missing_categories_path ${WORK_DIR}/model/missing_categ.log

Flow --fit_model_to_rep --rep ${REP_PATH} --f_model ${MODEL_PATH} --f_output ${WORK_DIR}/model/model.with_explainability.medmdl --cleaner_verbose -1 --remove_explainability 0 --log_action_file_path ${WORK_DIR}/model/actions.with_explanability.log --log_missing_categories_path ${WORK_DIR}/model/missing_categ.with_explanability.log

if [[ ! -z "${CALIBRATED_MODEL_PATH}" ]]; then
	Flow --fit_model_to_rep --rep ${REP_PATH} --f_model ${CALIBRATED_MODEL_PATH} --f_output ${WORK_DIR}/model/model.calibrated.medmdl --cleaner_verbose -1 --remove_explainability 1 --log_action_file_path ${WORK_DIR}/model/actions.calibrated.log --log_missing_categories_path ${WORK_DIR}/model/missing_categ.calibrated.log
fi

#Let's check there are no missing categories:
HAS_MISSING=$({ egrep "MISSING_CODE_VALUE" ${WORK_DIR}/model/missing_categ.log || true; } | wc -l)
if [ $HAS_MISSING -gt 0 ]; then
	echo "Failed has ${HAS_MISSING} missing categories - please refer to ${WORK_DIR}/model/missing_categ.log"
fi

#Check no errors in the model
ALL_OK=$(cat ${WORK_DIR}/${TEST_NAME}.log | { egrep "All OK - Model can be applied on repository" || true; } | wc -l)
if [ ${ALL_OK} -lt 1 ]; then
	echo "Failed has some errors/uncertain actions in model conversion - please refer to ${WORK_DIR}/model/actions.log and ${WORK_DIR}/${TEST_NAME}.log"
	exit 2
fi
