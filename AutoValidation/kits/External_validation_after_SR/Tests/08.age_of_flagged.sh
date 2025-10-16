#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR FIRST_WORK_DIR COHORTS) # Required parameters
DEPENDS=() # Specify dependent tests to run: silent_run 4
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

if [ -z "$ALT_PREDS_PATH" ]; then
	echo "No ALT_PREDS_PATH in env - skipping comparsing of flagged ages to comparator"
fi

REP_PATH=${FIRST_WORK_DIR}/rep/test.repository
BT_JSON=${FIRST_WORK_DIR}/json/bootstrap/bt_features.json
SAMPELS=${WORK_DIR}/bootstrap/eligible_only.preds

# filter samples
#################

cohorts=$(echo $COHORTS | tr "|" "\n")
for cohort in $cohorts
do
	c=$(echo $cohort | tr "=" "\n")
	cohort_name=$(echo $c | awk '{print $1}')
	cohort_features=$(echo $c | awk '{print $2}')
	if [ ! -f ${WORK_DIR}/bootstrap/${cohort_name}.preds ]; then
		FilterSamples --rep ${REP_PATH} --filter_train 0 --samples $SAMPELS --output ${WORK_DIR}/bootstrap/${cohort_name}.preds --filter_by_bt_cohort "$cohort_features" --json_mat $BT_JSON
		echo Done filter Samples for $cohort
	fi
done

# age script python graphs for cases and controls

mkdir -p ${WORK_DIR}/age_of_flagged

for cohort in $cohorts
do
	c=$(echo $cohort | tr "=" "\n")
	cohort_name=$(echo $c | awk '{print $1}')
	python ${2}/resources/lib/age_of_flagged.py "${1}" "${2}" ${OVERRIDE} $cohort_name
done
