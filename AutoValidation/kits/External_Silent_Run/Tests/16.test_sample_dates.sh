#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR) # Required parameters
DEPENDS=() # Specify dependent tests to run: 3
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

TEST_SAMPLES=${WORK_DIR}/Samples/3.test_cohort.samples

mkdir -p ${WORK_DIR}/samples_stats

cat ${TEST_SAMPLES} | awk -F"\t" 'NR>1 {print int($3/100)}' | sort -S80% -g | uniq -c | awk 'BEGIN {print "Date\tCount"} {print $2 "\t" $1}' | tee ${WORK_DIR}/samples_stats/by_date.tsv
plot.py --input ${WORK_DIR}/samples_stats/by_date.tsv --html_template ${WORK_DIR}/tmp/plotly_graph.html --output  ${WORK_DIR}/samples_stats/by_date.html --has_header 1

echo "Please refer to ${WORK_DIR}/samples_stats folder"
