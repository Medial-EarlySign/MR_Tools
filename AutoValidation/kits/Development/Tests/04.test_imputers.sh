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

mkdir -p ${WORK_DIR}/outputs
#model needs %zu signals
#model has %zu virtual signals
set +e +o pipefail
Flow --print_model_info --f_model ${MODEL_PATH} 2>&1| { egrep "FeatureImputer|IterativeImputer|PredictorImputer"  || true; }  > ${WORK_DIR}/outputs/model_imputers
set -e -o pipefail
#Clean Categorical signals:
CNT1=$(cat ${WORK_DIR}/outputs/model_imputers | wc -l)

if [ $CNT1 -lt 1 ]; then
	echo "No imputers in model"
	exit 2
else
	echo "Test past - model has imputers"
fi

