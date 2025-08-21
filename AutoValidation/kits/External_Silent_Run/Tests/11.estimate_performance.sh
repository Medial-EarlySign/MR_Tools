#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REFERENCE_MATRIX) # Required parameters
DEPENDS=(5) # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

echo "Please refer to ${WORK_DIR} to see estimate performance"
WORK_PATH=${WORK_DIR}/compare.no_overfitting

#Test perofmrance on unlabeled samples with prop model to labeled samples:

mkdir -p ${WORK_PATH}

PROP_MODEL=${WORK_PATH}/rep_propensity.calibrated.model

if [ -f ${WORK_DIR}/ref_matrix ]; then
	REFERENCE_MATRIX=${WORK_DIR}/ref_matrix #Override
fi

MAX_WEIGHT=100000

#get weights on original - to transform into test and estimate test results:
if [ ! -f ${WORK_PATH}/labeled_weights.preds ] || [ $OVERRIDE -gt 0 ]; then
	#Silence run to "original"
	#Original to silence run
	Flow --get_propensity_weights --f_matrix ${REFERENCE_MATRIX} --f_preds ${WORK_PATH}/labeled_weights.preds --trim_propensity_weight 0 --max_propensity_weight ${MAX_WEIGHT} --f_model ${PROP_MODEL} --do_conversion 1 --override_outcome 0
fi

echo "Running bootstrap on original reference" 
if [ ! -f ${WORK_PATH}/bt_reference.pivot_txt ] || [ $OVERRIDE -gt 0 ]; then
	bootstrap_app --sample_per_pid 0 --use_censor 0 --input ${WORK_DIR}/compare/reference.preds --output ${WORK_PATH}/bt_reference 
fi
echo "Running bootstrap estimated with weights..."
if [ ! -f ${WORK_PATH}/bt_reference.estimated.pivot_txt ] || [ ${WORK_PATH}/labeled_weights.preds -nt ${WORK_PATH}/bt_reference.estimated.pivot_txt ] || [ $OVERRIDE -gt 0 ]; then
	bootstrap_app --sample_per_pid 0 --use_censor 0 --input ${WORK_PATH}/labeled_weights.preds --weights_file "attr:weight"  --output ${WORK_PATH}/bt_reference.estimated  
fi

bootstrap_format.py --measure_regex AUC --format_number %2.3f --cohorts "." --report_path ${WORK_PATH}/bt_reference.pivot_txt  ${WORK_PATH}/bt_reference.estimated.pivot_txt  --report_name Reference  Reference_transfromed_to_test --table_format c,rm | tee ${WORK_PATH}/summary_table.estimated_performance.tsv

echo "Report can be found in ${WORK_PATH}/summary_table.estimated_performance.tsv" 

# patch to include LGI calibration
CURR_PT=${2}

if [ ! -f ${WORK_PATH}/bt_reference.estimated.calibrated.pivot_txt ] || [ ${WORK_PATH}/labeled_weights.preds -nt ${WORK_PATH}/bt_reference.estimated.pivot_txt ] || [ $OVERRIDE -gt -1 ]; then
    python ${CURR_PT}/resources/lib/calibrate4LGI.py $1
	bootstrap_app --sample_per_pid 0 --use_censor 0 --working_points_pr 1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90 --input ${WORK_PATH}/labeled_weights_calibrated.preds --weights_file "attr:weight"  --output ${WORK_PATH}/bt_reference.estimated.calibrated --output_raw 1
    #bootstrap_app --sample_per_pid 0 --use_censor 0 --working_points_pr 1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90 --input ${WORK_PATH}/labeled_weights_calibrated.45_55.preds --weights_file "attr:weight"  --output ${WORK_PATH}/bt_reference.estimated.calibrated.45_55
    #bootstrap_app --sample_per_pid 0 --use_censor 0 --working_points_pr 1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90 --input ${WORK_PATH}/labeled_weights_calibrated.55_65.preds --weights_file "attr:weight"  --output ${WORK_PATH}/bt_reference.estimated.calibrated.55_65
    #bootstrap_app --sample_per_pid 0 --use_censor 0 --working_points_pr 1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90 --input ${WORK_PATH}/labeled_weights_calibrated.65_75.preds --weights_file "attr:weight"  --output ${WORK_PATH}/bt_reference.estimated.calibrated.65_75
fi

bootstrap_format.py --measure_regex "AUC|NNEG|NPOS|OR@PR|SCORE@PR|SENS@PR|PPV@PR|LIFT@PR" --format_number %2.3f --cohorts "." --report_path ${WORK_PATH}/bt_reference.estimated.calibrated*.pivot_txt --table_format cr,m | tee ${WORK_PATH}/summary_table.estimated_performance.calibrated.tsv