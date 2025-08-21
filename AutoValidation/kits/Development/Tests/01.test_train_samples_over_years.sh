#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR TRAIN_SAMPLES_BEFORE_MATCHING) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

samples_by_year.sh ${TRAIN_SAMPLES_BEFORE_MATCHING}

#Check by month also
 echo -e "\nMonth\tControls\tcases\tperecntage"
 tail -n +2 ${TRAIN_SAMPLES_BEFORE_MATCHING} | awk '{ d[int($3/100)%100][$4 >0]+=1; } END { for (i in d) { print i "\t" d[i][0] "\t" d[i][1] "\t" int(10000*d[i][1]/(d[i][1] + d[i][0]))/100 "%" } }' | sort -g -k1
 
 #Check cases/controls distribution to outcomeTime-time. how many pateints are boths cases/controls. 
 
 python ${CURR_PT}/resources/lib/samples_stats.py ${TRAIN_SAMPLES_BEFORE_MATCHING} ${WORK_DIR}/samples_stats.train