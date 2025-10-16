#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR FIRST_WORK_DIR BT_COHORT BT_JSON) # Required parameters
DEPENDS=() # Specify dependent tests to run: silent-run: 4, 6
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "Running bootstrap analysis"

BT_JSON=${FIRST_WORK_DIR}/json/bootstrap/bt_features.json
BT_COHORT=${FIRST_WORK_DIR}/json/bootstrap/bt.params

HAS_YEAR_COHORT=$(cat ${BT_COHORT} | { grep "Year" || true; } | wc -l)
if [ $HAS_YEAR_COHORT -lt 1 ]; then
	echo "WARNING BT_COHORT = ${BT_COHORT} doesn't contains performance by year analysis"
fi


TEST_SAMPLES=$WORK_DIR/Samples/relabeled.samples
mkdir -p ${WORK_DIR}/bootstrap

#Get preds by joining samples with old results
SMP_SIZE=$(cat ${TEST_SAMPLES} | wc -l)
INPUT_PREDS=${FIRST_WORK_DIR}/compare/3.test_cohort.preds
if [ -f ${FIRST_WORK_DIR}/predictions/all.preds ]; then
	INPUT_PREDS=${FIRST_WORK_DIR}/predictions/all.preds
fi

if [ ! -f ${WORK_DIR}/bootstrap/all.preds ] || [ ${INPUT_PREDS} -nt ${WORK_DIR}/bootstrap/all.preds ] || [ ${TEST_SAMPLES} -nt ${WORK_DIR}/bootstrap/all.preds ] || [ $OVERRIDE -gt 0 ]; then
		paste.py -f1 ${TEST_SAMPLES} -ids1 1 2 -f2 ${INPUT_PREDS} -ids2 1 2 -ads2 6 -os $'\t' > ${WORK_DIR}/bootstrap/all.preds	
fi
PRED_SIZE=$(cat ${WORK_DIR}/bootstrap/all.preds | wc -l)

if [ $PRED_SIZE -ne $SMP_SIZE ]; then
	echo "Requested to join input samples with ${SMP_SIZE} and ended up with ${PRED_SIZE} samples"
fi

if [ ! -f ${WORK_DIR}/bootstrap/eligible_only.preds ] || [ ${WORK_DIR}/bootstrap/all.preds -nt ${WORK_DIR}/bootstrap/eligible_only.preds ] || [ $OVERRIDE -gt 0 ]; then
	cat ${WORK_DIR}/bootstrap/all.preds | awk -F"\t" 'BEGIN {OFS="\t"} NR==1 || $7=="" || NF==7 {if (NF==7) {print $0} else { print $1,$2,$3,$4,$5,$6,$8}}' > ${WORK_DIR}/bootstrap/eligible_only.preds
fi

SMP_SIZE=$PRED_SIZE
PRED_SIZE=$(cat ${WORK_DIR}/bootstrap/eligible_only.preds | wc -l)
if [ $PRED_SIZE -ne $SMP_SIZE ]; then
	echo "Requested to calculate samples with ${SMP_SIZE} and ended up with ${PRED_SIZE} samples after exclusions"
fi

SENS=10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90
FPR=0.5,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99
PR=0.5,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99
KPIS="AUC|SENS@PR|OR@PR|SCORE@PR|LIFT@PR|SPEC@PR|PR@SENS|OR@SENS|SCORE@SENS|SPEC@SENS|PPV@PR|LIFT@SENS|PPV@SENS|NPOS|NNEG"

# control weight
CONTROL_WEIGHT_ADD=""
if [ ! -z "${CONTROL_WEIGHT}" ] ; then
    CONTROL_WEIGHT_ADD="--control_weight ${CONTROL_WEIGHT}"
fi

REP_PATH=${WORK_DIR}/rep/test.repository	
if [ ! -f ${WORK_DIR}/bootstrap/mes.bt.pivot_txt ] || [ ${BT_JSON} -nt ${WORK_DIR}/bootstrap/mes.bt.pivot_txt ] || [ ${BT_COHORT} -nt ${WORK_DIR}/bootstrap/mes.bt.pivot_txt ] || [ ${WORK_DIR}/bootstrap/eligible_only.preds -nt ${WORK_DIR}/bootstrap/mes.bt.pivot_txt ] || [ $OVERRIDE -gt 0 ]; then
	bootstrap_app --use_censor 0 --sample_per_pid 0 --rep ${REP_PATH} --json_model ${BT_JSON} --cohorts_file ${BT_COHORT} --working_points_sens $SENS --working_points_pr $PR --working_points_fpr $FPR --part_auc_params 0.03,0.05,0.1 --input ${WORK_DIR}/bootstrap/eligible_only.preds --output ${WORK_DIR}/bootstrap/mes.bt $CONTROL_WEIGHT_ADD
fi

sub_codes=$(echo $SUB_CODES | tr "," "\n")
for SC in $sub_codes
do
    echo $SC
    
    python ${CURR_PT}/resources/lib/just_eligible_plus_preds.py --input ${WORK_DIR}/Samples/relabeled.samples.${SC} --eligible_with_preds ${WORK_DIR}/bootstrap/eligible_only.preds --output ${WORK_DIR}/bootstrap/${SC}.preds
    
    bootstrap_app --use_censor 0 --sample_per_pid 1 --rep ${REP_PATH} --json_model ${BT_JSON} --cohorts_file ${BT_COHORT} --working_points_sens $SENS --working_points_pr $PR --working_points_fpr $FPR --part_auc_params 0.03,0.05,0.1 --input ${WORK_DIR}/bootstrap/${SC}.preds --output ${WORK_DIR}/bootstrap/${SC}.bt $CONTROL_WEIGHT_ADD
done

bootstrap_format.py --report_path ${WORK_DIR}/bootstrap/*.pivot_txt --cohorts_list . --measure_regex $KPIS --table_format cr,m | tee ${WORK_DIR}/bootstrap/bt.just_MES.tsv

if [[ ! -z ${ALT_PREDS_PATH} ]]; then

	if [ ! -f ${WORK_DIR}/bootstrap/comperator.bt.pivot_txt ] || [ ${BT_JSON} -nt ${WORK_DIR}/bootstrap/comperator.bt.pivot_txt ] || [ ${BT_COHORT} -nt ${WORK_DIR}/bootstrap/comperator.bt.pivot_txt ] || [ ${ALT_PREDS_PATH} -nt ${WORK_DIR}/bootstrap/comperator.bt.pivot_txt ] || [ $OVERRIDE -gt 0 ]; then
	
		python ${CURR_PT}/resources/lib/fit_comperator_to_cohort.py --input $ALT_PREDS_PATH --cohort ${WORK_DIR}/bootstrap/eligible_only.preds --output ${WORK_DIR}/bootstrap/eligible_only.comperator.preds
	
		bootstrap_app --use_censor 0 --sample_per_pid 0 --rep ${REP_PATH} --json_model ${BT_JSON} --cohorts_file ${BT_COHORT} --working_points_sens $SENS --working_points_fpr $FPR --working_points_pr $PR --part_auc_params 0.03,0.05,0.1 --input ${WORK_DIR}/bootstrap/eligible_only.comperator.preds --output ${WORK_DIR}/bootstrap/comperator.bt $CONTROL_WEIGHT_ADD
	fi
	
	bootstrap_format.py --report_path ${WORK_DIR}/bootstrap/mes.bt.pivot_txt ${WORK_DIR}/bootstrap/comperator.bt.pivot_txt --report_name MES Comperator --cohorts_list . --measure_regex $KPIS --table_format cr,m | tee ${WORK_DIR}/bootstrap/bt.MES_comperator.tsv
	
	echo "Please refer to ${WORK_DIR}/bootstrap/bt.MES_comperator.pivot_txt"
else
	echo "NO comperator preds so no comperator bootstrap"
	echo "Please refer to ${WORK_DIR}/bootstrap/bt.just_MES.tsv"
fi

