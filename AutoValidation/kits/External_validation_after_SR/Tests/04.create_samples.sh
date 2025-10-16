#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR FIRST_WORK_DIR BT_JSON COMPARE_COHORT CODE_LIST_FILE CODE_DIR SUB_CODES) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...ers

BT_JSON=${FIRST_WORK_DIR}/json/bootstrap/bt_features.json
REP_PATH=${WORK_DIR}/rep/test.repository
INPUT=${FIRST_WORK_DIR}/Samples/1.all_potential.samples

mkdir -p ${WORK_DIR}/Samples
OUTPUT=${WORK_DIR}/Samples/relabeled.samples

echo "Relabeling samples..."

if [ ! -f ${WORK_DIR}/Samples/outcome.reg ] || [ $OVERRIDE -gt 0 ]; then 
	python ${CURR_PT}/resources/lib/create_registry.py --rep $REP_PATH --signal DIAGNOSIS --output ${WORK_DIR}/Samples/outcome.reg --end_of_data 20230101 --codes_dir ${CODE_DIR} --codes_list ${CODE_LIST_FILE} --sub_codes ${SUB_CODES}
fi

if [ ! -f ${OUTPUT} ] || [ $OVERRIDE -gt 0 ]; then 
	python ${CURR_PT}/resources/lib/relabel.py --registry ${WORK_DIR}/Samples/outcome.reg --samples ${FIRST_WORK_DIR}/Samples/3.test_cohort.samples --output ${OUTPUT} --output_dropout ${WORK_DIR}/Samples/dropped.samples --follow_up_controls 730 --time_window_case_maximal_before 730 --time_window_case_minimal_before 0 --future_cases_as_control 0 --sub_codes ${SUB_CODES}
fi

# membership_time_frame should be 0 when using MEMBERSHIP signal
# otherwise, use the same time_frame parameter used in creating the membership registery 

echo "Distribution by year:" 
samples_by_year.sh $OUTPUT  

echo "Distribution by Month:" 
echo -e "\nMonth\tControls\tcases\tperecntage"
tail -n +2 $OUTPUT | awk '{ d[int($3/100)%100][$4 >0]+=1; } END { for (i in d) { print i "\t" d[i][0] "\t" d[i][1] "\t" int(10000*d[i][1]/(d[i][1] + d[i][0]))/100 "%" } }' | sort -g -k1
 
python ${CURR_PT}/resources/lib/samples_stats.py ${OUTPUT} ${WORK_DIR}/samples_stats


if [ ! -f ${WORK_DIR}/Samples/3.test_cohort.samples ] || [ $OVERRIDE -gt 0 ]; then
	awk -F"\t" 'BEGIN{OFS="\t"} {print $1,$2,$3,$4,$5,$6}' ${OUTPUT} > $WORK_DIR/Samples/clean.samples
	FilterSamples --rep ${REP_PATH} --filter_train 0 --samples $WORK_DIR/Samples/clean.samples --output ${WORK_DIR}/Samples/3.test_cohort.samples --filter_by_bt_cohort "${COMPARE_COHORT}" --json_mat ${BT_JSON}
fi

samples_by_year.sh $WORK_DIR/Samples/3.test_cohort.samples