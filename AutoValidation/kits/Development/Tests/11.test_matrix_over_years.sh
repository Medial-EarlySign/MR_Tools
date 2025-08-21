#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH MODEL_PATH TEST_SAMPLES) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

DIFF_YEARS=$(awk 'NR>1 {print int($3/10000)}' ${TEST_SAMPLES} | sort -S50% -g | uniq | wc -l)

set +o pipefail
if [ $DIFF_YEARS -eq 1 ]; then
	echo "All test samples are from the same year - can't run ${TEST_NAME} analysis"
	exit 2
elif [ $DIFF_YEARS -ge 4 ]; then
	MIN_YEAR=$(awk 'NR>1 {print int($3/10000)}' ${TEST_SAMPLES} | sort -S50% -g -k1 | uniq | head -n 2 | tail -n 1)
	MAX_YEAR=$(awk 'NR>1 {print int($3/10000)}' ${TEST_SAMPLES} | sort -S50% -g -k1 -r | uniq | head -n 2 | tail -n 1)
else
	MIN_YEAR=$(awk 'NR>1 {print int($3/10000)}' ${TEST_SAMPLES} | sort -S50% -g -k1 | uniq | head -n 1)
	MAX_YEAR=$(awk 'NR>1 {print int($3/10000)}' ${TEST_SAMPLES} | sort -S50% -g -k1 -r | uniq | head -n 1)
fi
set -o pipefail
echo "Filter ${MIN_YEAR} and ${MAX_YEAR}"

mkdir -p ${WORK_DIR}/tmp

awk -F"\t" -v filter_year=$MIN_YEAR 'NR==1 || int($3/10000)==filter_year' ${TEST_SAMPLES} > ${WORK_DIR}/tmp/min_year.samples
awk -F"\t" -v filter_year=$MAX_YEAR 'NR==1 || int($3/10000)==filter_year' ${TEST_SAMPLES} > ${WORK_DIR}/tmp/max_year.samples

SAMPLES_MIN=${WORK_DIR}/tmp/min_year.samples
SAMPLES_MAX=${WORK_DIR}/tmp/max_year.samples

mkdir -p $WORK_DIR/compare_years

USE_BUT_WHY_REPORT=""
if [ -f ${WORK_DIR}/ButWhy/shapley.report ]; then
	USE_BUT_WHY_REPORT="--additional_importance_to_rank ${WORK_DIR}/ButWhy/shapley.report"
fi

TestModelExternal --rep_test $REPOSITORY_PATH --rep_train $REPOSITORY_PATH --model_path ${MODEL_PATH} ${USE_BUT_WHY_REPORT} --sub_sample_but_why 200000 --print_mat 0 --calc_shapley_mask 1 --train_ratio 0.7 --output $WORK_DIR/compare_years --samples_train ${SAMPLES_MIN} --samples_test ${SAMPLES_MAX} --name_for_test "Year_$MAX_YEAR" --name_for_train "Year_$MIN_YEAR"

if [ -f ${WORK_DIR}/compare_years/shapley_report.tsv ]; then
	feature_importance_printer.py --report_path ${WORK_DIR}/compare_years/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 0 --output_path ${WORK_DIR}/compare_years/Global.html

	feature_importance_printer.py --report_path ${WORK_DIR}/compare_years/shapley_report.tsv --num_format %2.4f --feature_name "" --max_count 30 --force_many_graph 1 --print_multiple_graphs 1 --output_path ${WORK_DIR}/compare_years/single_features
fi
