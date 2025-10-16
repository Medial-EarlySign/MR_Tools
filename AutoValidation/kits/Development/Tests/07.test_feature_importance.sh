#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH MODEL_PATH BT_JSON_FAIRNESS FAIRNESS_BT_PREFIX) # Required parameters
DEPENDS=(6) # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

mkdir -p ${WORK_DIR}/ButWhy
mkdir -p ${WORK_DIR}/tmp

echo "start feature importance"

if [ ! -f ${WORK_DIR}/ButWhy/feature_importance.report.tsv ] || [ ${OVERRIDE} -gt 0 ] ; then
	Flow --print_model_info --f_model ${MODEL_PATH} 2>/dev/null | { grep FEATURE || true; } | awk '{print $3}' > ${WORK_DIR}/tmp/features.list

	if [ ! -f ${WORK_DIR}/ButWhy/features.groups.tsv ]; then
		#Get List of Signals:
		Flow --print_model_sig --f_model ${MODEL_PATH} 2>&1 | awk 'BEGIN {state=-1} { if (state==0 && $0 ~ /^############/) {state=1} if (state==0) {print $3} if (/model needs [0-9]+ signals \(no repository is given, so can/) {state=0} }' | sort > ${WORK_DIR}/tmp/phisical_sigs
	
		Flow --get_feature_group --group_signals BY_SIGNAL --select_features "file:${WORK_DIR}/tmp/features.list" | awk '{signal=$NF; if ($NF=="Smoking") {signal="Smoking_Duration,Smoking_Intensity,Pack_Years,Smoking_Status,Smoking_Quit_Date";} if (index($NF, "_Values")>0 || index($NF, "_Trends")>0) {signal=substr($NF, 1, length($NF)-7)} if (index($NF, ".")>0) { split($NF,arr,"."); signal=arr[1];} if ($NF=="eGFR_CKD_EPI") {signal="Creatinine";} ;print $NF "\t" signal}' | sort | uniq > ${WORK_DIR}/ButWhy/features.groups.tsv
		
		subtract.pl ${WORK_DIR}/ButWhy/features.groups.tsv 0 ${WORK_DIR}/tmp/phisical_sigs 0 | awk -F"\t" 'BEGIN {print "Age"; print "Gender"} {print $1}' | sort | uniq > ${WORK_DIR}/tmp/virtual_sigs
	fi

	#set -x
	IGNORE_LIST=$(awk '{if (NR==1) {printf("%s",$0)} else { printf(",%s",$0)}}' ${WORK_DIR}/tmp/virtual_sigs)
	model_signals_importance --rep ${REPOSITORY_PATH} --model_path ${MODEL_PATH} --samples ${WORK_DIR}/bootstrap/test.preds --output ${WORK_DIR}/ButWhy/feature_importance.report.tsv --features_groups BY_SIGNAL --time_windows "365,1095" --min_group_analyze_size 10 --bt_args "sample_per_pid=1;loopcnt=500;roc_params={working_point_fpr=1,3,5,7,10}" --bt_filter_json ${BT_JSON_FAIRNESS} --bt_filter_cohort ${FAIRNESS_BT_PREFIX} --measure_regex "AUC|SENS@FPR" --group2signal ${WORK_DIR}/ButWhy/features.groups.tsv --skip_list ${IGNORE_LIST} 
fi

head -n 1  ${WORK_DIR}/ButWhy/feature_importance.report.tsv | awk 'BEGIN{OFS="\t"} {print $1, $2,$3,$4,$5,$6}' > ${WORK_DIR}/ButWhy/feature_importance.sorted_final.tsv
cat ${WORK_DIR}/ButWhy/feature_importance.report.tsv | awk 'BEGIN{OFS="\t"} $1~/365:difference/ {print $1, $2,$3,$4,$5,$6}' | sort -g -r -k6 >> ${WORK_DIR}/ButWhy/feature_importance.sorted_final.tsv

echo "Please refer to ${WORK_DIR}/ButWhy/feature_importance.report.tsv for full details" 
echo "Please refer to ${WORK_DIR}/ButWhy/feature_importance.sorted_final.tsv for final" 
