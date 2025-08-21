#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR MODEL_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run: 2, 3
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

REPOSITORY_PATH=${WORK_DIR}/rep/test.repository
TEST_SAMPLES=${WORK_DIR}/Samples/3.test_cohort.samples
MODEL_PATH=${WORK_DIR}/model/model.medmdl

mkdir -p ${WORK_DIR}/ButWhy
mkdir -p ${WORK_DIR}/ButWhy/single_features

if [ ! -f ${WORK_DIR}/ButWhy/shapley.report ] || [ ${OVERRIDE} -gt 0 ] ; then
	Flow --shap_val_request --f_model ${MODEL_PATH} --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES} --max_samples 200000 --group_signals "" --bin_method "split_method=iterative_merge;binCnt=50;min_bin_count=100;min_res_value=0" --f_output ${WORK_DIR}/ButWhy/shapley.report --cohort_filter ""
fi
if [ ! -f ${WORK_DIR}/ButWhy/shapley_grouped.report ] || [ ${OVERRIDE} -gt 0 ] ; then
	Flow --shap_val_request --f_model ${MODEL_PATH} --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES} --max_samples 200000 --group_signals "BY_SIGNAL_CATEG" --bin_method "split_method=iterative_merge;binCnt=50;min_bin_count=100;min_res_value=0" --f_output ${WORK_DIR}/ButWhy/shapley_grouped.report --cohort_filter ""
fi

feature_importance_printer.py --report_path ${WORK_DIR}/ButWhy/shapley_grouped.report --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/ButWhy/Global.html

feature_importance_printer.py --report_path ${WORK_DIR}/ButWhy/shapley.report --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/ButWhy/Global.ungrouped.html

feature_importance_printer.py --report_path ${WORK_DIR}/ButWhy/shapley.report --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 1 --output_path ${WORK_DIR}/ButWhy/single_features


#Fix plotly.js paths:
sed -i 's|<script src="[^"]*"|<script src="../js/plotly.js"|g' ${WORK_DIR}/ButWhy/*.html

echo "Please refer to ${WORK_DIR}/ButWhy folder"
