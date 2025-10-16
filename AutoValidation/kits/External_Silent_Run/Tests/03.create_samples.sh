#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR SILENCE_RUN_OUTPUT_FILES_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

mkdir -p $WORK_DIR/Samples

TAKE_JUST_LAST=0

if [ "${SILENCE_RUN_OUTPUT_FILES_PATH}" = "GENERATE" ]; then
	echo "Generating samples not based on scores..."
	REP_NAME=$(ls -1 ${WORK_DIR}/rep | egrep "\.repository$")
	REP_PATH=${WORK_DIR}/rep/${REP_NAME}
	if [ $TAKE_JUST_LAST -gt 0]; then
		#For each patient in Repository, take last Hemoglobin
		echo "generation samples just for LAST Hemoglobin tests" 
		Flow --rep ${REP_PATH} --pids_sigs --sigs Hemoglobin | awk -F"\t" 'BEGIN {OFS="\t";print "EVENT_FIELDS", "id", "time", "outcome","outcomeTime", "split"; last_pid=-1; last_date=-1;} NR>1 { if (last_pid!=$1 && last_pid!=-1) {print "SAMPLE", last_pid, last_date,0, 20990101, -1; } last_date=$4; last_pid=$1;} END {print "SAMPLE", last_pid, last_date,0, 20990101, -1;}' > ${WORK_DIR}/Samples/3.test_cohort.samples	
	else
		#For each patient in Repository, take all Hemoglobin (unlike the above commented line that takes only last)
		echo "generation samples for ALL Hemoglobin tests"
		Flow --rep ${REP_PATH} --pids_sigs --sigs Hemoglobin | awk -F"\t" 'BEGIN {OFS="\t";print "EVENT_FIELDS", "id", "time", "outcome","outcomeTime", "split"; last_pid=-1; last_date=-1;} NR>1 {  {print "SAMPLE", $1, $4,0, 20990101, -1; } last_date=$4; last_pid=$1;} ' > ${WORK_DIR}/Samples/3.test_cohort.samples	
	fi
	cp ${WORK_DIR}/Samples/3.test_cohort.samples ${WORK_DIR}/Samples/1.all_potential.samples
else
	if [ ! -f ${WORK_DIR}/Samples/3.test_cohort.samples ] || [ $OVERRIDE -gt 0 ]; then
		awk 'FNR!=1' ${SILENCE_RUN_OUTPUT_FILES_PATH} | awk -F"\t" 'BEGIN {OFS="\t"; tr_d["JAN"] = 1; tr_d["FEB"] = 2; tr_d["MAR"] = 3; tr_d["APR"] = 4; tr_d["MAY"] = 5; tr_d["JUN"] = 6; tr_d["JUL"] = 7; tr_d["AUG"] = 8; tr_d["SEP"] = 9; tr_d["OCT"] = 10; tr_d["NOV"] = 11; tr_d["DEC"] = 12;} {split ($4, arr, "-"); print "SAMPLE", $1, arr[1]*10000+ tr_d[arr[2]]*100+ arr[3], 0, 20990101, -1}' | sort -g -k2 -k3 -S30% | awk -F"\t" 'BEGIN {OFS="\t";} $3>0 {print $0}' | sort -S50% -g -k2 -k3 | awk -F"\t" 'BEGIN {OFS="\t";print "EVENT_FIELDS", "id", "time", "outcome","outcomeTime", "split";} {print $0}' > ${WORK_DIR}/Samples/test.bf.samples
		
		#Original preds:
		awk 'FNR!=1' ${SILENCE_RUN_OUTPUT_FILES_PATH} | awk -F"\t" 'BEGIN {OFS="\t"; tr_d["JAN"] = 1; tr_d["FEB"] = 2; tr_d["MAR"] = 3; tr_d["APR"] = 4; tr_d["MAY"] = 5; tr_d["JUN"] = 6; tr_d["JUL"] = 7; tr_d["AUG"] = 8; tr_d["SEP"] = 9; tr_d["OCT"] = 10; tr_d["NOV"] = 11; tr_d["DEC"] = 12;} {split ($4, arr, "-"); print "SAMPLE", $1, arr[1]*10000+ tr_d[arr[2]]*100+ arr[3], 0, 20990101, -1, $3}' | sort -g -k2 -k3 -S30% | awk -F"\t" 'BEGIN {OFS="\t";} $3>0 {print $0}' | sort -S50% -g -k2 -k3 | awk -F"\t" 'BEGIN {OFS="\t";print "EVENT_FIELDS", "id", "time", "outcome","outcomeTime", "split";} {print $0}' > ${WORK_DIR}/Samples/test.bf.orig.preds
		if [ -f ${WORK_DIR}/ETL/FinalSignals/ID2NR ]; then
			echo "Has ID2NR"
			head -n 1 ${WORK_DIR}/Samples/test.bf.samples > ${WORK_DIR}/Samples/3.test_cohort.samples
			paste.pl ${WORK_DIR}/Samples/test.bf.samples 1 ${WORK_DIR}/ETL/FinalSignals/ID2NR 0 1 -t | awk -F"\t" 'BEGIN {OFS="\t"} {print $1,$NF,$3,$4,$5,$6}' >> ${WORK_DIR}/Samples/3.test_cohort.samples
			head -n 1 ${WORK_DIR}/Samples/test.bf.orig.preds > ${WORK_DIR}/Samples/test.orig.preds
			paste.pl ${WORK_DIR}/Samples/test.bf.orig.preds 1 ${WORK_DIR}/ETL/FinalSignals/ID2NR 0 1 -t | awk -F"\t" 'BEGIN {OFS="\t"} {print $1,$NF,$3,$4,$5,$6,$7}' >> ${WORK_DIR}/Samples/test.orig.preds
		else
			ln -s -f ${WORK_DIR}/Samples/test.bf.samples ${WORK_DIR}/Samples/3.test_cohort.samples
			ln -s -f ${WORK_DIR}/Samples/test.bf.orig.preds ${WORK_DIR}/Samples/test.orig.preds
		fi
	fi
fi

if [ $FILTER_LAST_DATE -gt 0 ]; then
	if [ ! -f ${WORK_DIR}/ref_matrix ]; then
		#filter last date, it was rerun twice, take last records
		LAST_DATE=$(tail -n 1 ${REFERENCE_MATRIX} | awk -F, '{print $3}')

		awk -F, -v last_date=$LAST_DATE 'NR==1 || ($3==last_date)' ${REFERENCE_MATRIX} > ${WORK_DIR}/ref_matrix
	fi
else
	if [ ! -f ${WORK_DIR}/ref_matrix ]; then
		ln -s ${REFERENCE_MATRIX} ${WORK_DIR}/ref_matrix
	fi
fi

samples_by_year.sh ${WORK_DIR}/Samples/3.test_cohort.samples