#!/bin/bash
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH BASELINE_COMPARE_TOP) # Required parameters
DEPENDS=(6) # Specify dependent tests to run
# END.
CURR_PT=${2}
. ${CURR_PT}/resources/lib/init_infra.sh
CURR_PT=${2}

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
mkdir -p ${WORK_DIR}/false_positive_analysis
PR_SELECT=$(echo ${BASELINE_COMPARE_TOP} | awk '{print $1/100}')

python ${CURR_PT}/resources/lib/flaggedDiagnosisAnalysis.py --rep "${REPOSITORY_PATH}" --f_preds "${WORK_DIR}/bootstrap/test.preds" --pr ${PR_SELECT} --pMax 0.05 --minAge 0 --maxAge 120 --startTime 0 --endTime 1095 --diagnosisSignal DIAGNOSIS --f_output ${WORK_DIR}/false_positive_analysis/time_window_0_1095.tsv
#--includeCases
#--firstDiagnosis