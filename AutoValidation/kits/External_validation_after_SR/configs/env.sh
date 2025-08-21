#!/bin/bash
#Load all variables from PreOutcome step
SCRIPT_PATH=${BASH_SOURCE[0]}
source ${SCRIPT_PATH%/*}/../../PreOutcome/configs/env.sh
SCRIPT_PATH=${BASH_SOURCE[0]}
FIRST_WORK_DIR=$WORK_DIR
#Optional to limit memory (if not defined in PreOutcome):
#MEMORY_LIMIT=500000000

#Parameters for settings
OUTCOME_INPUT_FILES_PATH=/nas1/Temp/data/data_outcome
ALT_PREDS_PATH=/nas1/Temp/data/plco.preds
#end params

COMPARE_COHORT="${COMPARE_COHORT};Time-Window:90,365"

WORK_DIR=/nas1/Work/Users/Eitan/ValidationKit/second_phase_validation

CODE_DIR=${SCRIPT_PATH%/*}/LGI_codes/
CODE_LIST_FILE=all.list
SUB_CODES=CRC,gastric,upper,esophagus
COHORTS="Age_50-75=Age:50,75"