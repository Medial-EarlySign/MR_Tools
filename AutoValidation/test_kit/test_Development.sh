#!/bin/bash
set -e
#Test we are with right python:

CURRENT_DIR=$(realpath ${0%/*})
source ${CURRENT_DIR}/env.sh
TRAIN_REPO=/nas1/Work/CancerData/Repositories/Mode3/Maccabi_feb2016/maccabi.repository
TRAIN_SAMPLES_BEFORE_MATCHING=/nas1/Work/Users/Alon/LGI/outputs.MHS/Samples.no_exclusions/train.730.1_per_control.fixed_dates.samples
TEST_SAMPLES=/nas1/Work/Users/Alon/LGI/outputs.MHS/Samples.no_exclusions/test.fixed_dates.samples
MODEL_PATH=/nas1/Work/Users/Alon/LGI/outputs.MHS//models/optimized_for_gastric.4.less_controls/config_params/exported_full_model.medmdl
FAIRNESS_BT_PREFIX="Age:45,75;Time-Window:0,365"
BASELINE_MODEL_PATH=/earlysign/AlgoMarkers/LGI/LGI-Flag-3.1.model
EXPLAINABLE_MODEL=/earlysign/AlgoMarkers/LGI/LGI-Flag-3.1.explainer.model

OVERRIDE=${1-0}
KIT_FOLDER=/nas1/Temp/test_kit_results/Development/${ALGOMARKER_NAME}
TESTKIT_CODE_FOLDER=${KIT_FOLDER}/TestKit_Code
TESTS_RESULTS_FOLDER=${KIT_FOLDER}/Kit_Results
mkdir -p ${TESTKIT_CODE_FOLDER}
mkdir -p ${TESTS_RESULTS_FOLDER}
if [ $OVERRIDE -gt 0 ]; then
	rm -fr ${TESTKIT_CODE_FOLDER}
	mkdir -p ${TESTKIT_CODE_FOLDER}
	rm -fr ${TESTS_RESULTS_FOLDER}
fi

# 1. First step, create the vanila kit:
pushd ${TESTKIT_CODE_FOLDER} > /dev/null
if [ ! -f ${TESTKIT_CODE_FOLDER}/run.sh ]; then
	${CURRENT_DIR}/../kits/generate_tests.sh <<< "Development"
fi
# 2. Now Let's configure:
#Configure WORK_DIR
sed -i 's|^WORK_DIR=.*|WORK_DIR='${TESTS_RESULTS_FOLDER}'|g' configs/env.sh
#Configure to repository
sed -i 's|^REPOSITORY_PATH=.*|REPOSITORY_PATH='${TRAIN_REPO}'|g' configs/env.sh
sed -i 's|^TRAIN_SAMPLES_BEFORE_MATCHING=.*|TRAIN_SAMPLES_BEFORE_MATCHING='${TRAIN_SAMPLES_BEFORE_MATCHING}'|g' configs/env.sh
sed -i 's|^TEST_SAMPLES=.*|TEST_SAMPLES='${TEST_SAMPLES}'|g' configs/env.sh
sed -i 's|^MODEL_PATH=.*|MODEL_PATH='${MODEL_PATH}'|g' configs/env.sh
sed -i 's|^EXPLAINABLE_MODEL=.*|EXPLAINABLE_MODEL='${EXPLAINABLE_MODEL}'|g' configs/env.sh

sed -i 's|^FAIRNESS_BT_PREFIX=.*|FAIRNESS_BT_PREFIX="'${FAIRNESS_BT_PREFIX}'"|g' configs/env.sh
sed -i 's|^BASELINE_MODEL_PATH=.*|BASELINE_MODEL_PATH='${BASELINE_MODEL_PATH}'|g' configs/env.sh

# 3. Now let's execute
./run.sh

# 4. Let's test!


#Finish
popd > /dev/null