#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR CMP_FEATURE_RES) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "Please refer to ${WORK_DIR}/signals_cnt to see signals counts" 

#Test perofmrance on unlabeled samples with prop model to labeled samples:

mkdir -p ${WORK_DIR}
mkdir -p ${WORK_DIR}/signals_cnt

REP_PATH=${WORK_DIR}/rep/test.repository

echo ${CMP_FEATURE_RES} | sed 's|ICD9_CODE:|ICD9_CODE_|g' | sed 's|ICD10_CODE:|ICD10_CODE_|g' | sed 's|ATC_CODE:|ATC_CODE_|g' | awk -F, '{ for (i=1;i<=NF;i++) {  split($i, arr, ":"); split(arr[1], arr2, "."); print arr2[1] } }' | egrep -v "^FTR_" | grep -v "Age" | sed 's|ICD9_CODE_|ICD9_CODE:|g' | sed 's|ICD10_CODE_|ICD10_CODE:|g' | sed 's|ATC_CODE_|ATC_CODE:|g' | egrep -v "category_|Smoking" | awk 'BEGIN{print "DIAGNOSIS"; print "Smoking_Status"} {print $0}' | while read -r signal
do
	signal_clean=${signal%*_log}
    echo "Doing signal ${signal_clean}"
	
	HAS_SIG=$(cat ${WORK_DIR}/rep/test.signals | { egrep "${signal_clean}\s" || true; } | wc -l)
    if [ $HAS_SIG -lt 1 ]; then
        echo "WARN nop signal ${signal_clean} - skip" 
        continue
    fi
	
	Flow --rep ${REP_PATH} --pids_sigs --sigs "${signal_clean}" | awk -F"\t" -v sig="$signal_clean" 'BEGIN {prev_id=-1; prev_date=-1;} NR>1 { if ($1!=prev_id) { prev_id=$1; prev_date=-1; } if (prev_date!=$4) { cnt[$1]+=1;  prev_date=$4; } } END { for (pid in cnt) { cc[cnt[pid]]+=1 } for (counter in cc) {print sig "\t" counter "\t" cc[counter]} }' | sort -S40% -g -k2 > ${WORK_DIR}/signals_cnt/${signal_clean}.tsv
done 


echo "Report can be found in ${WORK_DIR}/signals_cnt"

