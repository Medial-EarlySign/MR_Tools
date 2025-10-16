#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH MODEL_PATH TEST_SAMPLES BT_JSON_FAIRNESS FAIRNESS_BT_PREFIX) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "starting fairness test"

if [ ! -f ${1}/fairness_groups.cfg ]; then
	echo "Please provide fairness groups in ${1}/fairness_groups.cfg" 
	echo "File format is new line for each fair ness compare with 2 tokens - tab delimeted" 
	echo "first token is bootstrap filters for defeining the groups, seperated with '|', second token is the names to give each group seperated by '|'"
	exit 2
fi

mkdir -p ${WORK_DIR}/fairness
mkdir -p ${WORK_DIR}/fairness/bootstrap_graphs

#Get preds;
if [ -z "${PREDS_CV}" ]; then
	if [ ! -f ${WORK_DIR}/bootstrap/test.preds ] || [ $OVERRIDE -gt 0 ]; then
		Flow --get_model_preds --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES} --f_preds ${WORK_DIR}/bootstrap/test.preds --f_model ${MODEL_PATH}
		PREDS_CV=${WORK_DIR}/bootstrap/test.preds
	fi
else
	if [ ! -f ${WORK_DIR}/bootstrap/test.preds ]; then
		ln -s ${PREDS_CV} ${WORK_DIR}/bootstrap/test.preds
	fi
fi

mkdir -p ${WORK_DIR}/tmp
#Generate cohorts file:
FAIRNESS_BT_PREFIX_COHORT=$(python ${CURR_PT}/resources/lib/reformat_bt_filter.py ${FAIRNESS_BT_PREFIX})	
echo -e "${FAIRNESS_BT_PREFIX_COHORT}\t${FAIRNESS_BT_PREFIX}"  > ${WORK_DIR}/tmp/bt_cohorts

awk -F"\t" -v base_cohort="${FAIRNESS_BT_PREFIX}" '{ split($1, arr, "|"); for (i=1;i<= length(arr); i++) { print base_cohort ";" arr[i] } }' ${1}/fairness_groups.cfg | while read -r COHORT_F
do
	COHORT_NAME=$(python ${CURR_PT}/resources/lib/reformat_bt_filter.py ${COHORT_F})
	echo -e "${COHORT_NAME}\t${COHORT_F}" >> ${WORK_DIR}/tmp/bt_cohorts
done

#First, lets measure the fairness diff:
if [ ! -f ${WORK_DIR}/fairness/bt.fairness.pivot_txt ]; then
	bootstrap_app --use_censor 0 --sample_per_pid 1 --input ${WORK_DIR}/bootstrap/test.preds --rep $REPOSITORY_PATH  --force_score_working_points 1 --score_resolution 0.005 --json_model $BT_JSON_FAIRNESS --output ${WORK_DIR}/fairness/bt.fairness --cohorts_file ${WORK_DIR}/tmp/bt_cohorts --print_graphs_path ${WORK_DIR}/fairness/bootstrap_graphs
fi
if [ ! -f ${WORK_DIR}/fairness/bt.fairness.by_pr.pivot_txt ]; then
	bootstrap_app --use_censor 0 --sample_per_pid 1 --input ${WORK_DIR}/bootstrap/test.preds --rep $REPOSITORY_PATH  --json_model $BT_JSON_FAIRNESS --output ${WORK_DIR}/fairness/bt.fairness.by_pr --cohorts_file ${WORK_DIR}/tmp/bt_cohorts --working_points_fpr 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99 --working_points_pr 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99
fi

#Let's extract information in certain thresholds based on "main" threshold analysis:
#${CURR_PT}/resources/lib/fairness_stats.sh "${WORK_DIR}" "${FAIRNESS_BT_PREFIX}" "${WORK_DIR}/fairness/bt.fairness.by_pr.pivot_txt" "${WORK_DIR}/fairness/bt.fairness.pivot_txt"
fairness_extraction.py --bt_report ${WORK_DIR}/fairness/bt.fairness.by_pr.pivot_txt --output ${WORK_DIR}/fairness --bt_cohort "${FAIRNESS_BT_PREFIX}" --cutoffs_pr 3 5


#Plot graphs of different groups Sens @ Score cutoffs
PY3=$(python --version | egrep "Python 3" | wc -l)
if [ $PY3 -eq 0 ]; then
	echo "Failed, please set python to Python3 before using python_env or something, python cmd should refer to python3"
fi

python ${CURR_PT}/resources/lib/fairness_analysis.py ${WORK_DIR}/fairness/bt.fairness.pivot_txt ${WORK_DIR}/fairness/Graphs_fairness ${1}/fairness_groups.cfg "${FAIRNESS_BT_PREFIX}" 

#Let's repeat with Age matching - other criteria for matching and plot graphs again!
if [ ! -z "${FAIRNESS_MATCHING_PARAMS}" ]; then
	python ${CURR_PT}/resources/lib/fairness_matching.py ${1} ${2} ${OVERRIDE}
	#TODO - print bootstrap summary on match + statistical test
	
else
	echo "To test after matching please define FAIRNESS_MATCHING_PARAMS in env.sh" 
fi
