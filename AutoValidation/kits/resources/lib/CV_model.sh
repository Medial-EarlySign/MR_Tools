#!/bin/bash
set -e -o pipefail
REP=$1
MODELS_PATH=$2
TEST_SAMPLES=$3
WORK_PATH=$4
OUTPUT_PATH=$5

OVERRIDE=${6-0}

mkdir -p ${WORK_PATH}/tmp

 ls -1 ${MODELS_PATH}/CV_MODEL_*.medmdl | egrep "medmdl$" | while read -r model
do
	SPLIT_NUM=$(echo ${model} | awk -F"/" '{print $NF}' | awk -F"." '{split( $1,arr,"_"); print arr[3]}')
	if [ ! -f ${WORK_PATH}/tmp/${SPLIT_NUM}.preds ]; then
		echo "Predict of ${model}"
		#Prepare samples and exclude train ids:
		cat ${model}.train_samples | awk 'NR>1 {print $2}' | sort -S40% | uniq > ${WORK_PATH}/tmp/exclude_ids
		subtract.pl ${TEST_SAMPLES} 1 ${WORK_PATH}/tmp/exclude_ids 0 > ${WORK_PATH}/tmp/test_samples

		Flow --rep ${REP} --get_model_preds --f_model $model --f_samples ${WORK_PATH}/tmp/test_samples --f_preds ${WORK_PATH}/tmp/${SPLIT_NUM}.preds	
	fi
done

#Combine
head -n 1 ${TEST_SAMPLES} > ${OUTPUT_PATH}
awk 'FNR>1' ${WORK_PATH}/tmp/*.preds | sort -S80% -g -k2 -k3 -u >> ${OUTPUT_PATH}