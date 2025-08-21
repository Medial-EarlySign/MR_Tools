#!/bin/bash

#Input parameters
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA4PQ5O74ILBL4FSGZ
AWS_SECRET_ACCESS_KEY=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

AWS_INPUT_PATH=s3://mes-sftp-us-east-1/roche-tricore/Complete_data_set_Roche_LGI_flag.txt
AWS_OUTPUT_PATH=GENERATE
#AWS_INFO_PATH=s3://yex1aqz448do6dnb/lgi-flag/input/IDandDate2ClientType.csv
#REPOSITORY_PATH=/nas1/Work/Users/coby/LGI/Japan/outputs/Repository/japan.repository
#output
WORK_DIR=/earlysign/workspace2/silentrun_tricore

#################################################################### DONT TOUCH BELOW #####################################

#Environement params - NO NEED to change
COMPARE_COHORT=Age:40,75

SCRIPT_PATH=${BASH_SOURCE[0]}
BT_JSON=${SCRIPT_PATH%/*}/bootstrap/bootstrap.json
BT_COHORT=${SCRIPT_PATH%/*}/bootstrap/bt.params

MODEL_PATH=/earlysign/AlgoMarkers/LGI/LGI-Flag-3.1.explainer.model
REFERENCE_MATRIX=/earlysign/AlgoMarkers/LGI/features.matrix
CMP_FEATURE_RES="Age:1,Gender:1,FTR_000074.MCH.slope.win_0_1000:0.5,MCH.min.win_0_180:0.5,Platelets.Estimate.360:1,Platelets.win_delta.win_0_180_730_10000:5,MPV.min.win_0_10000:0.1,Hemoglobin.last.win_0_10000:0.2,Hemoglobin.slope.win_0_730:0.1,Hematocrit.Estimate.360:0.2,Neutrophils%.std.win_0_10000:0.2"
SCORE_MIN_RANGE=0.1
SCORE_MAX_RANGE=0.2
FILTER_LAST_DATE=0
TOP_EXPLAIN_PERCENTAGE=3
TOP_EXPLAIN_GROUP_COUNT=3
CALIBRATED_MODEL_PATH=/earlysign/AlgoMarkers/LGI/LGI-Flag-3.1.calibrated.model
OTHER_DIAG_PREFIX=ICD10
DIAG_PREFIX=ICD9

#Created
SILENCE_RUN_INPUT_FILES_PATH=$WORK_DIR/data/input
if [ "$AWS_OUTPUT_PATH" != "GENERATE" ]; then
	SILENCE_RUN_OUTPUT_FILES_PATH=$WORK_DIR/data/output.tsv
else
	SILENCE_RUN_OUTPUT_FILES_PATH="GENERATE"
fi
