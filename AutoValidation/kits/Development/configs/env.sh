#!/bin/bash
SCRIPT_PATH=${BASH_SOURCE[0]}
#INPUTS
REPOSITORY_PATH=/home/Repositories/THIN/thin_2021/thin.repository

#To Be used inside this file only
HELPER_BASE_PATH=/server/Work/Users/Alon/CKD/Undiagnosed/outputs

TRAIN_SAMPLES_BEFORE_MATCHING=${HELPER_BASE_PATH}/Samples.CKD_3_Years/Stage_1/ckd_train.samples
TEST_SAMPLES=${HELPER_BASE_PATH}/models/Undiagnosed_confirmed.optimizer_model/bootstrap/ckd_test.preds
#PREDS_CV= #If given will use those instead of applying model on TEST_SAMPLES. when we have small dataset with cross validation

MODEL_PATH=${HELPER_BASE_PATH}/models/Undiagnosed_confirmed.optimizer_model/config_params/exported_full_model.medmdl
CALIBRATED_MODEL=${MODEL_PATH}
EXPLAINABLE_MODEL=${MODEL_PATH}
TEST_SAMPLES_CALIBRATION=${TEST_SAMPLES}

BT_JSON=${SCRIPT_PATH%/*}/bootstrap/bootstrap.json
BT_COHORT=${SCRIPT_PATH%/*}/bootstrap/bt.params
NOISER_JSON=${SCRIPT_PATH%/*}/noiser_base.json

TIME_NOISES="3,30,90,180,360,720,1440,9999"
VAL_NOISES="1,2,4,6,8,10"
DROP_NOISES="1,2,4,6,8,9"

BT_JSON_CALIBRATION=${BT_JSON}
BT_COHORT_CALIBRATION=${BT_COHORT}

#EXPLAINABLE_MODEL=
EXPLAIN_JSON=${BT_JSON}
#EXPLAIN_COHORT=

#File path to fairness groups to compare in each line from bootstap (in configs/fairness_groups.cfg). Tab to seperate bootstrap from naming. For example: Gender:1,1|Gender:2,2  [TAB] Males|Females

BT_JSON_FAIRNESS=${BT_JSON}
FAIRNESS_BT_PREFIX="category_set_CKD_Diagnosis:0,0;Age:40,80;Time-Window:30,180;DM_Registry_Diabetic:1,999;CKD_Screening.last_time:365,2000"
FAIRNESS_MATCHING_PARAMS="priceRatio=15;verbose=1;strata=age,10"

#BASELINE_PARAMS:
BASELINE_MODEL_PATH=/nas1/Work/Users/Alon/CKD/Undiagnosed/outputs/models/Undiagnosed_confirmed.baseline3/config_params/exported_full_model.medmdl
BASELINE_COMPARE_TOP=5

#OUTPUTS: Location for writing output files ${WORK_DIR}/outputs
WORK_DIR=/server/Work/Users/Alon/CKD/Undiagnosed/outputs/models/Undiagnosed_confirmed.optimizer_model/Test_Kit

#TODO: 
	# Compare to baseline
	# Sensitivity analysis to values, time shifts, missing values