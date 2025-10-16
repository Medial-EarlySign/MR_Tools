#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR BT_JSON BT_COHORT) # Required parameters
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

mkdir -p ${WORK_DIR}/json
mkdir -p ${WORK_DIR}/tmp
mkdir -p ${WORK_DIR}/json/bootstrap

if [ ! -f ${WORK_DIR}/json/bootstrap/bt_features.json ] || [ $OVERRIDE -gt 0 ]; then
	#copy all config files in bootstrap folder
	if [ -d "${1}/bootstrap" ]; then
		cp -r ${1}/bootstrap/* ${WORK_DIR}/json/bootstrap
	fi

	cp ${BT_JSON} ${WORK_DIR}/json/bootstrap/bt_features.json
	cp ${BT_COHORT} ${WORK_DIR}/json/bootstrap/bt.params
	dos2unix ${WORK_DIR}/json/bootstrap/bt_features.json
	dos2unix ${WORK_DIR}/json/bootstrap/bt.params

	BT_JSON=${WORK_DIR}/json/bootstrap/bt_features.json
	BT_COHORT=${WORK_DIR}/json/bootstrap/bt.params

	#edit BT_JSON, BT_COHORT

	#Check if race exists:
	HAS_RACE=$( { grep "Race" ${WORK_DIR}/rep/test.signals || true; } | wc -l)
	if [ ${HAS_RACE} -lt 1 ]; then
		echo "Repository has no Race information - removing from analysis..." | tee -a ${WORK_DIR}/${TEST_NAME}.log
		sed -i 's|"json:race.json"|//"json:race.json"|g' ${BT_JSON}
		awk -F"\t" '!/White:/ {print}' ${BT_COHORT} > ${WORK_DIR}/tmp/1
		mv ${WORK_DIR}/tmp/1 ${BT_COHORT}
	fi
	#Check if has Lung_Cancer_Type:
	HAS_CANCER_TYPE=$( { grep "Lung_Cancer_Type" ${WORK_DIR}/rep/test.signals || true; } | wc -l)
	if [ ${HAS_CANCER_TYPE} -lt 1 ]; then
		echo "Repository has no Lung_Cancer_Type information - removing from analysis..." | tee -a ${WORK_DIR}/${TEST_NAME}.log
		sed -i 's|"json:cancer_type.json"|//"json:cancer_type.json"|g' ${BT_JSON}
		sed -i 's|"json:cancer_type.fp.json"|//"json:cancer_type.fp.json"|g' ${BT_JSON}
		awk -F"\t" '!/Histology_Squamous:/ {print}' ${BT_COHORT} > ${WORK_DIR}/tmp/1
		mv ${WORK_DIR}/tmp/1 ${BT_COHORT}
	fi
	HAS_CANCER_STAGE=$( { grep "Lung_Cancer_Stage" ${WORK_DIR}/rep/test.signals || true; } | wc -l)
	if [ ${HAS_CANCER_STAGE} -lt 1 ]; then
		echo "Repository has no Lung_Cancer_Stage information - removing from analysis..." | tee -a ${WORK_DIR}/${TEST_NAME}.log
		sed -i 's|"json:cancer_stage.json"|//"json:cancer_stage.json"|g' ${BT_JSON}
		sed -i 's|"json:cancer_stage.fp.json"|//"json:cancer_stage.fp.json"|g' ${BT_JSON}
		if [ ${HAS_CANCER_TYPE} -lt 1 ]; then
			#This is last so we need to remove last comma:
			sed -i -r -z 's|,\n\s*//"json:cancer_type.fp.json"|\n\t//"json:cancer_type.fp.json"|g' ${BT_JSON}
		fi
		awk -F"\t" '!/Cancer_Stage/ {print}' ${BT_COHORT} > ${WORK_DIR}/tmp/1
		mv ${WORK_DIR}/tmp/1 ${BT_COHORT}
	fi
fi
