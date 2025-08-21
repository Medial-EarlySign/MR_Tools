#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR TEST_SAMPLES) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

samples_by_year.sh ${TEST_SAMPLES}

#Check by month also
 echo -e "\nMonth\tControls\tcases\tperecntage"
 tail -n +2 ${TEST_SAMPLES} | awk '{ d[int($3/100)%100][$4 >0]+=1; } END { for (i in d) { print i "\t" d[i][0] "\t" d[i][1] "\t" int(10000*d[i][1]/(d[i][1] + d[i][0]))/100 "%" } }' | sort -g -k1


 python ${CURR_PT}/resources/lib/samples_stats.py ${TEST_SAMPLES} ${WORK_DIR}/samples_stats.test