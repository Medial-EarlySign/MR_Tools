#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH MODEL_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

mkdir -p ${WORK_DIR}/outputs
#model needs %zu signals
#model has %zu virtual signals
set +e +o pipefail
Flow --print_model_sig --f_model ${MODEL_PATH} 2>&1 | awk 'BEGIN {start=0} {if ($1=="model" && $2=="needs" && $4="signals") { start=1 } else { if ($1=="model" && $2=="has" && $4=="virtual" && $5="signals") {start=0;} if (start) {print $3} } }' | sort | uniq | awk '$0!=""' | egrep -v "^(BDATE|BYEAR|GENDER|Smoking_Quit_Date|eGFR_CKD_EPI|VLDL)$" > ${WORK_DIR}/outputs/model_used_signals
set -e -o pipefail

#Clean Categorical signals:
SIGNAME=$(grep SIGNAL ${REPOSITORY_PATH} | awk -F"\t" '{print $2}')
SIGNAL_FILE=${REPOSITORY_PATH%/*}/${SIGNAME}

CNT1=$(cat ${WORK_DIR}/outputs/model_used_signals | wc -l)
CNT2=$(paste.pl ${WORK_DIR}/outputs/model_used_signals 0 ${SIGNAL_FILE} 1 5 -t | wc -l)

if [ $CNT1 -ne $CNT2 ]; then
	echo "Not all signals exits!!!"
	exit 2
fi



#Test has cleaner for each model
set +e +o pipefail
Flow --print_model_info --f_model ${MODEL_PATH} 2>&1 | egrep "BasicOutlierCleaner" | awk '{print $6}' > ${WORK_DIR}/outputs/model_signals_with_cleaners
set -e -o pipefail

MISS_SIGNALS=$(paste.pl ${WORK_DIR}/outputs/model_used_signals 0 ${SIGNAL_FILE} 1 5 -t | awk '$2<1' | subtract.pl - 0 ${WORK_DIR}/outputs/model_signals_with_cleaners 0 | wc -l)

if [ $MISS_SIGNALS -gt 0 ]; then
	echo "Test Failed!! has $MISS_SIGNALS signals without cleaners"
	paste.pl ${WORK_DIR}/outputs/model_used_signals 0 ${SIGNAL_FILE} 1 5 -t | awk '$2<1' | subtract.pl - 0 ${WORK_DIR}/outputs/model_signals_with_cleaners 0 | awk '{print $1}'
	exit 2
else
	echo "Test past - all signals has cleaners"
fi
