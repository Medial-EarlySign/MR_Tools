#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR MODEL_PATH REFERENCE_MATRIX CMP_FEATURE_RES) # Required parameters
DEPENDS=() # Specify dependent tests to run: 2?
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

MODEL_PATH=${WORK_DIR}/model/model.medmdl
echo "Starting test to compare silence run matrix created matrix to reference matrix"

if [ -f ${WORK_DIR}/ref_matrix ]; then
	REFERENCE_MATRIX=${WORK_DIR}/ref_matrix #Override
fi

mkdir -p ${WORK_DIR}/compare
mkdir -p ${WORK_DIR}/compare.no_overfitting

# Create html templates - plot_with_missing but with relative link to plotly.js
mkdir -p ${WORK_DIR}/tmp
TEMPLATE_PATH=$(which plot.py)
cp ${TEMPLATE_PATH%/*}/templates/plot_with_missing.html ${WORK_DIR}/tmp
sed -i 's|<script src="[^"]*"|<script src="../../js/plotly.js"|g' ${WORK_DIR}/tmp/plot_with_missing.html
PYTHONPATH=${PYTHONPATH}:${CURR_PT}/resources/lib/ python -c 'from PY_Helper import __setup_plotly_js; __setup_plotly_js("'${WORK_DIR}'")' 
# end html templates

#compare
MAX_SIZE=500000
REP_NAME=$(ls -1 ${WORK_DIR}/rep | egrep "\.repository$")
REP_PATH=${WORK_DIR}/rep/${REP_NAME}
NEED_RERUN='[ ${WORK_DIR}/Samples/3.test_cohort.samples -nt ${WORK_DIR}/compare/compare_rep.txt ] || [ ${MODEL_PATH} -nt ${WORK_DIR}/compare/compare_rep.txt ] || [ ${REP_PATH} -nt ${WORK_DIR}/compare/compare_rep.txt ] || [ ${REFERENCE_MATRIX} -nt ${WORK_DIR}/compare/compare_rep.txt ]'
#|| [ ${OVERRIDE} -gt 0 ]
if [ ! -f ${WORK_DIR}/compare/compare_rep.txt ] || ${NEED_RERUN}; then
	TestModelExternal --model_path ${MODEL_PATH} --train_matrix_csv ${REFERENCE_MATRIX} --rep_test ${REP_PATH} --samples_test ${WORK_DIR}/Samples/3.test_cohort.samples --fix_test_res 0 --output ${WORK_DIR}/compare --sub_sample_but_why 200000 --sub_sample_test ${MAX_SIZE} --sub_sample_train ${MAX_SIZE} --feature_html_template ${WORK_DIR}/tmp/plot_with_missing.html --name_for_train Reference 
fi

mkdir -p ${WORK_DIR}/compare/ButWhy
feature_importance_printer.py --report_path ${WORK_DIR}/compare/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/compare/ButWhy/Global.html

feature_importance_printer.py --report_path ${WORK_DIR}/compare/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 1 --output_path ${WORK_DIR}/compare/ButWhy/single_features
NEED_RERUN='[ ${WORK_DIR}/Samples/3.test_cohort.samples -nt ${WORK_DIR}/compare.no_overfitting/compare_rep.txt ] || [ ${MODEL_PATH} -nt ${WORK_DIR}/compare.no_overfitting/compare_rep.txt ] || [ ${REP_PATH} -nt ${WORK_DIR}/compare.no_overfitting/compare_rep.txt ] || [ ${REFERENCE_MATRIX} -nt ${WORK_DIR}/compare.no_overfitting/compare_rep.txt ]'
#|| [ ${OVERRIDE} -gt 0 ]
if [ ! -f ${WORK_DIR}/compare.no_overfitting/compare_rep.txt ] || ${NEED_RERUN}; then
	#--smaller_model_feat_size 25 --additional_importance_to_rank ""
	#--features_subset_file
	#Flow --print_model_info --f_model ${AM_MODEL} 2>&1 | grep FEATURE | awk -F"\t" '{print $3}' | head -n 25 > ${WORK_DIR}/tmp/feat_list
	#Use CMP_FEATURE_RES:
	echo "$CMP_FEATURE_RES" | sed 's|ICD9_CODE:|ICD9_CODE_|g' | sed 's|ICD10_CODE:|ICD10_CODE_|g' | sed 's|ATC_CODE:|ATC_CODE_|g' | awk -F, '{for (i =1;i<=NF;i++) { split($i,arr,":"); print arr[1] } }' | sed 's|ICD9_CODE_|ICD9_CODE:|g' | sed 's|ICD10_CODE_|ICD10_CODE:|g' | sed 's|ATC_CODE_|ATC_CODE:|g' > ${WORK_DIR}/tmp/feat_list
	
	TestModelExternal --model_path ${MODEL_PATH} --train_matrix_csv ${REFERENCE_MATRIX}  --rep_test ${REP_PATH} --samples_test ${WORK_DIR}/Samples/3.test_cohort.samples --fix_test_res 1 --fix_train_res 1 --output ${WORK_DIR}/compare.no_overfitting --train_ratio 0.7 --features_subset_file ${WORK_DIR}/tmp/feat_list --print_mat 0 --sub_sample_but_why 200000 --sub_sample_test ${MAX_SIZE} --sub_sample_train ${MAX_SIZE} --feature_html_template ${WORK_DIR}/tmp/plot_with_missing.html --name_for_train Reference
fi

mkdir -p ${WORK_DIR}/compare.no_overfitting/ButWhy
feature_importance_printer.py --report_path ${WORK_DIR}/compare.no_overfitting/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/compare.no_overfitting/ButWhy/Global.html

feature_importance_printer.py --report_path ${WORK_DIR}/compare.no_overfitting/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 1 --output_path ${WORK_DIR}/compare.no_overfitting/ButWhy/single_features

#Fix plotly.js paths:
sed -i 's|<script src="[^"]*"|<script src="../../js/plotly.js"|g' ${WORK_DIR}/compare/ButWhy/*.html
sed -i 's|<script src="[^"]*"|<script src="../../js/plotly.js"|g' ${WORK_DIR}/compare.no_overfitting/ButWhy/*.html
sed -i 's|<script src="[^"]*"|<script src="../../../js/plotly.js"|g' ${WORK_DIR}/compare/ButWhy/single_features/*.html
sed -i 's|<script src="[^"]*"|<script src="../../../js/plotly.js"|g' ${WORK_DIR}/compare.no_overfitting/ButWhy/single_features/*.html
