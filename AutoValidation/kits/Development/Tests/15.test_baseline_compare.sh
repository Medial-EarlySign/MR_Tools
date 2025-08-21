#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH BASELINE_MODEL_PATH MODEL_PATH TEST_SAMPLES BT_COHORT BASELINE_COMPARE_TOP) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "Test 1 - Test baseline butWhy features - does the model makes sense? no missing important feature?" 

mkdir -p ${WORK_DIR}/ButWhy.baseline
mkdir -p ${WORK_DIR}/ButWhy.baseline/single_features
if [ ! -f ${WORK_DIR}/ButWhy.baseline/shapley.report ] || [ ${OVERRIDE} -gt 0 ] ; then
	Flow --shap_val_request --f_model ${BASELINE_MODEL_PATH} --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES} --max_samples 200000 --group_signals "" --bin_method "split_method=iterative_merge;binCnt=50;min_bin_count=100;min_res_value=0" --f_output ${WORK_DIR}/ButWhy.baseline/shapley.report --cohort_filter ""
fi
if [ ! -f ${WORK_DIR}/ButWhy.baseline/shapley_grouped.report ] || [ ${OVERRIDE} -gt 0 ] ; then
	Flow --shap_val_request --f_model ${BASELINE_MODEL_PATH} --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES} --max_samples 200000 --group_signals "BY_SIGNAL_CATEG" --bin_method "split_method=iterative_merge;binCnt=50;min_bin_count=100;min_res_value=0" --f_output ${WORK_DIR}/ButWhy.baseline/shapley_grouped.report --cohort_filter ""
fi

feature_importance_printer.py --report_path ${WORK_DIR}/ButWhy.baseline/shapley_grouped.report --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/ButWhy.baseline/Global.html

feature_importance_printer.py --report_path ${WORK_DIR}/ButWhy.baseline/shapley.report --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/ButWhy.baseline/Global.ungrouped.html

feature_importance_printer.py --report_path ${WORK_DIR}/ButWhy.baseline/shapley.report --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 1 --output_path ${WORK_DIR}/ButWhy.baseline/single_features

echo "Please refer to ${WORK_DIR}/ButWhy.baseline" 
#################################

echo "Test 2 - Apply baseline and get bootstrap of baseline. compare to full model"

BT_JSON_P="--json_model ${BT_JSON}"
if [ -z "${BT_JSON}" ]; then
	echo "BT_JSON is missing in enviroment - Can't have complicated cohorts"
	BT_JSON_P=""
fi

#Get preds;
if [ ! -f ${WORK_DIR}/bootstrap/test.baseline.preds ] || [ $OVERRIDE -gt 0 ]; then
	Flow --get_model_preds --rep ${REPOSITORY_PATH} --f_samples ${TEST_SAMPLES} --f_preds ${WORK_DIR}/bootstrap/test.baseline.preds --f_model ${BASELINE_MODEL_PATH}
fi

if [ ! -f ${WORK_DIR}/bootstrap/bt.baseline.pivot_txt ] || [ $OVERRIDE -gt 0 ]; then
	bootstrap_app --use_censor 0 --sample_per_pid 0 --rep ${REPOSITORY_PATH} ${BT_JSON_P} --cohorts_file ${BT_COHORT} --working_points_fpr 0.1,0.5,1,2,3,4,5,6,7,8,9,10,12,15,17,20,25,30,35,40,45,50 --working_points_sens 10,20,30,40,50,60,65,70,75,80,85,90,95,99 --working_points_pr 0.1,0.5,1,2,3,4,5,6,7,8,9,10,12,15,17,20,25,30,35,40,45,50 --input ${WORK_DIR}/bootstrap/test.baseline.preds --output ${WORK_DIR}/bootstrap/bt.baseline
fi

#Deciede on important measurements/cohort and compare performance:
bootstrap_format.py --report_path ${WORK_DIR}/bootstrap/bt.baseline.pivot_txt ${WORK_DIR}/bootstrap/bt.pivot_txt --report_name baseline MES_Full --measure_regex "AUC" --table_format c,rm --cohorts_list "." | tee ${WORK_DIR}/bootstrap/bt_baseline_compare.tsv

echo "Please refer to ${WORK_DIR}/bootstrap/bt_baseline_compare.tsv"

#################################
mkdir -p ${WORK_DIR}/compare_to_baseline
echo "Test 3 - Test correlation with full model scores" 

paste.py -f1 ${WORK_DIR}/bootstrap/test.baseline.preds -f2 ${WORK_DIR}/bootstrap/test.preds -ids1 1 2 -ids2 1 2 -ads2 6 -s $'\t' -os $'\t' | awk -F"\t" '{print $(NF-1) "\t" $NF}' | getStats --cols 0,1 --nbootstrap 100 &> ${WORK_DIR}/compare_to_baseline/correlation.txt

cat ${WORK_DIR}/compare_to_baseline/correlation.txt

###############################
echo "Test 4 - Use TestModelExternal to compare top flagged individuals of top ${BASELINE_COMPARE_TOP}% in full model VS Baseline using full model features - what is the main difference in the flagged?" 

SAMLPES_CNT=$(cat ${TEST_SAMPLES} | wc -l)
TAKE_TOP=$(echo $SAMLPES_CNT | awk -v top_f=${BASELINE_COMPARE_TOP} '{print int($1*top_f/100) }')

head -n 1 ${WORK_DIR}/bootstrap/test.baseline.preds > ${WORK_DIR}/bootstrap/test.baseline.top.preds
set +o pipefail
tail -n +2 ${WORK_DIR}/bootstrap/test.baseline.preds | sort -S40% -g -r -k7 | head -n ${TAKE_TOP} | sort -S40% -g -k2 -k3 >> ${WORK_DIR}/bootstrap/test.baseline.top.preds

head -n 1 ${WORK_DIR}/bootstrap/test.preds > ${WORK_DIR}/bootstrap/test.top.preds
tail -n +2 ${WORK_DIR}/bootstrap/test.preds | sort -S40% -g -r -k7 | head -n ${TAKE_TOP} | sort -S40% -g -k2 -k3 >> ${WORK_DIR}/bootstrap/test.top.preds

set -o pipefail

mkdir -p $WORK_DIR/compare_to_baseline

if [ ! -f /${WORK_DIR}/compare_to_baseline/rep_propensity.model ] || [ $OVERRIDE -gt 0 ]; then
	TestModelExternal --rep_test $REPOSITORY_PATH --rep_train $REPOSITORY_PATH --model_path ${MODEL_PATH}  --sub_sample_but_why 200000 --print_mat 0 --calc_shapley_mask 1 --train_ratio 0.7 --output $WORK_DIR/compare_to_baseline --samples_train ${WORK_DIR}/bootstrap/test.baseline.top.preds --samples_test ${WORK_DIR}/bootstrap/test.top.preds --name_for_test "MES_model" --name_for_train "Baseline" 
fi

if [ -f ${WORK_DIR}/compare_to_baseline/shapley_report.tsv ]; then
	feature_importance_printer.py --report_path ${WORK_DIR}/compare_to_baseline/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/compare_to_baseline/Global.html

	feature_importance_printer.py --report_path ${WORK_DIR}/compare_to_baseline/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 1 --output_path ${WORK_DIR}/compare_to_baseline/single_features

fi
###############################
echo "Test 5 - Test Intersection in top 3/5% - van diagram between models. how much of the top 3% in baseline is covered in top 3%,5%,10%,25% of the full model?" 

SAMPLES_SIZE=$(wc -l ${WORK_DIR}/bootstrap/test.baseline.preds | awk '{print $1}')
tail -n +2 ${WORK_DIR}/bootstrap/test.baseline.preds | awk -F"\t" 'BEGIN {OFS="\t"} {print $2, $3, $7}' | sort -S80% -g -r -k3 | awk -F"\t" -v smp_size=${SAMPLES_SIZE} 'BEGIN {OFS="\t"} {print $0, NR, 100*NR/smp_size}' > ${WORK_DIR}/compare_to_baseline/baseline_rank.tsv
tail -n +2 ${WORK_DIR}/bootstrap/test.preds | awk -F"\t" 'BEGIN {OFS="\t"} {print $2, $3, $7}' | sort -S80% -g -r -k3 | awk -F"\t" -v smp_size=${SAMPLES_SIZE} 'BEGIN {OFS="\t"} {print $0, NR, 100*NR/smp_size}' > ${WORK_DIR}/compare_to_baseline/mes_rank.tsv

paste.py -f1 ${WORK_DIR}/compare_to_baseline/baseline_rank.tsv -ids1 0 1 -f2 ${WORK_DIR}/compare_to_baseline/mes_rank.tsv -ids2 0 1 -ads2 2 3 4 -os $'\t' -s $'\t' > ${WORK_DIR}/compare_to_baseline/join.tsv

JOIN_CNT=$(cat ${WORK_DIR}/compare_to_baseline/join.tsv | wc -l)
BASE_CNT=$(cat ${WORK_DIR}/compare_to_baseline/baseline_rank.tsv | wc -l)
if [ $BASE_CNT -ne $JOIN_CNT ]; then
	echo "Error After join not equal count: ${JOIN_CNT}, before was ${BASE_CNT}"
	exit -2
fi

MIN_RES=0.1
sort -S80% -g -k3 -r ${WORK_DIR}/compare_to_baseline/join.tsv | awk -F"\t" -v pr_point=${BASELINE_COMPARE_TOP} '$5<=pr_point' | sort -S80 -g -r -k6 | awk -F "\t" -v pr_point=${BASELINE_COMPARE_TOP} -v min_res=${MIN_RES} '{ pr_exact=$8; pr_res=int(pr_exact/min_res+0.5)*min_res; c+=1; if (pr_res in d) { if ( sqrt((d_exact_x[pr_res]-pr_res)*(d_exact_x[pr_res]-pr_res)) > sqrt((pr_exact-pr_res)*(pr_exact-pr_res)) ) { d[pr_res]=c; d_exact_x[pr_res]=pr_exact;  } } else { d[pr_res]=c; d_exact_x[pr_res]=pr_exact;} } END {print "MES_PR_CUTOFF" "\t" "COVERAGE_OF_BASELINE_" pr_point ; for (pr in d) {print pr "\t" 100*d[pr]/c} }' | sort -S80% -g -k1 > ${WORK_DIR}/compare_to_baseline/baseline_coverage_by_mes_${BASELINE_COMPARE_TOP}.tsv

plot.py --input ${WORK_DIR}/compare_to_baseline/baseline_coverage_by_mes_${BASELINE_COMPARE_TOP}.tsv --output ${WORK_DIR}/compare_to_baseline/baseline_coverage_by_mes_${BASELINE_COMPARE_TOP}.html  --has_header 1 --x_cols 0 --y_cols 1

echo "Please open ${WORK_DIR}/compare_to_baseline/baseline_coverage_by_mes_${BASELINE_COMPARE_TOP}.html to check coverage of baseline by MES full model" 

###############################
echo "Test 6 - Compare Intersting feautres like age in the flagged population of the two models - for example Age distribution in top 3/5% in baseline Vs full model" 

if [ -z "${BT_JSON}" ]; then
	echo "Please define BT_JSON to run this part"
	exit 2
fi

if [ ! -f ${WORK_DIR}/bootstrap/test.baseline.top.matrix ]; then
	Flow --get_json_mat --rep ${REPOSITORY_PATH} --f_samples ${WORK_DIR}/bootstrap/test.baseline.top.preds --f_json ${BT_JSON} --f_matrix ${WORK_DIR}/bootstrap/test.baseline.top.matrix 
fi
if [ ! -f ${WORK_DIR}/bootstrap/test.top.matrix ]; then
	Flow --get_json_mat --rep ${REPOSITORY_PATH} --f_samples ${WORK_DIR}/bootstrap/test.top.preds --f_json ${BT_JSON} --f_matrix ${WORK_DIR}/bootstrap/test.top.matrix 
fi
#Now we can plot some features and compare dists!

#Example - let's print Age:
AGE_COL=$(head -n 1 ${WORK_DIR}/bootstrap/test.baseline.top.matrix | awk -F, '{ for (i=1;i<=NF;i++) {print $i "\t" i} }' | grep "Age" | awk -F"\t" '{print $2}' )
mkdir -p ${WORK_DIR}/tmp

awk -F, -v f_col=${AGE_COL} '{val=$(f_col); c[val]+=1; n=n+1} END { for (v in c) {print v "\t" c[v] "\t" (c[v]/n)*100 "\t" "Baseline"} }' ${WORK_DIR}/bootstrap/test.baseline.top.matrix | sort -S40% -g -k1 | awk 'BEGIN {print "Value" "\t" "Count" "\t" "Percentage" "\t" "Model"} {print $0}' > ${WORK_DIR}/tmp/feat_dist   

awk -F, -v f_col=${AGE_COL} '{val=$(f_col); c[val]+=1; n=n+1} END { for (v in c) {print v "\t" c[v] "\t" (c[v]/n)*100 "\t" "MES_Full"} }' ${WORK_DIR}/bootstrap/test.top.matrix | sort -S40% -g -k1 >> ${WORK_DIR}/tmp/feat_dist

plot.py --input ${WORK_DIR}/tmp/feat_dist --output ${WORK_DIR}/compare_to_baseline/compare_Age_top_flagged.html --has_header 1 --group_col 3 --x_cols 0 --y_cols 2 --graph_mode bar

###############################
