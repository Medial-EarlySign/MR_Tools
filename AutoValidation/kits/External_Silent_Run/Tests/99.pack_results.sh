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

ls -1 ${WORK_DIR} | { egrep -v "^tmp$" || true; } | { egrep -v "^data$" || true; } | { egrep -v "^rep$" || true; } | { egrep -v "^ref_matrix$" || true; } | { egrep -v "^Samples$" || true; } | { egrep -v "^full_report.tar.bz2$" || true; } | tar -cvjf ${WORK_DIR}/full_report.tar.bz2 -C ${WORK_DIR} --exclude *.matrix --exclude */test_propensity.preds --exclude */rep_propensity.model --exclude */rep_propensity.calibrated.model --exclude All_test.log --exclude ETL/FinalSignals --exclude ETL/rep_configs  --exclude *.medmat --exclude *.medmdl -T -


echo "Final file in ${WORK_DIR}/full_report.tar.bz2"
exit 1 #that will always rerun