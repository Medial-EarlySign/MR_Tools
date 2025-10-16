#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REPOSITORY_PATH MODEL_PATH EXPLAINABLE_MODEL EXPLAIN_JSON TEST_SAMPLES)
DEPENDS=() # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh
CURR_PT=${2}

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

COHORT=""
if [ ! -z "$EXPLAIN_COHORT" ]; then
	COHORT="--cohort $EXPLAIN_COHORT"
fi

mkdir -p ${WORK_DIR}/ButWhy
mkdir -p ${WORK_DIR}/ButWhy/explainer_examples
mkdir -p ${WORK_DIR}/tmp

if [ ! -f ${WORK_DIR}/ButWhy/bt_filter.Raw ]; then
	echo "### Creating bootstrap filter... ###"
	awk -F"\t" 'BEGIN {OFS="\t"; } {if (NR==1) {print $0, "pred_0"} else { print $0,rand()} }' $TEST_SAMPLES > ${WORK_DIR}/tmp/1
	bootstrap_app --rep ${REPOSITORY_PATH} --use_censor 0 --input ${WORK_DIR}/tmp/1 --output ${WORK_DIR}/ButWhy/bt_filter --json_model ${EXPLAIN_JSON} $COHORT --output_raw
	echo "### Done Creating bootstrap filter! ###"
fi

cat ${WORK_DIR}/ButWhy/bt_filter.Raw | awk -F"\t" 'NR>1 {print $1}' | sort -S40% | uniq > ${WORK_DIR}/tmp/cohorts

echo "Start Explainers on each cohort"

while read -r line;
do
			
	cohort_name=$(echo $line | sed -r 's|[,;:]|_|g' | sed 's|\.000||g')
	echo "$cohort_name"
	if [ ! -f "${WORK_DIR}/ButWhy/explainer_examples/cohort.${cohort_name}.preds" ]; then
		echo "### Generate sample and preds for cohort.${cohort_name}.preds ... ###"
		head -n 1 $TEST_SAMPLES > "${WORK_DIR}/ButWhy/explainer_examples/cohort.${cohort_name}.samples"
		cat ${WORK_DIR}/ButWhy/bt_filter.Raw | awk -F"\t" -v cohort="$line" 'BEGIN {OFS="\t"; } NR>1 && $1==cohort {print "SAMPLE",$4,$5,$3,$6,$7}' >> "${WORK_DIR}/ButWhy/explainer_examples/cohort.${cohort_name}.samples"

		Flow --get_model_preds --f_model ${MODEL_PATH} --f_samples "${WORK_DIR}/ButWhy/explainer_examples/cohort.${cohort_name}.samples" --f_preds "${WORK_DIR}/ButWhy/explainer_examples/cohort.${cohort_name}.preds" --rep ${REPOSITORY_PATH}
		echo "### Done Generate sample and preds for cohort.${cohort_name}.preds ! ###"
	fi

	head -n 1 $TEST_SAMPLES > "${WORK_DIR}/ButWhy/explainer_examples/top.${cohort_name}.samples"

	#CNT=$(tail -n +2 ${RUN_PATH_FULL}/ButWhy/explainer_examples/cohort.${cohort_name}.preds | awk '{print $2}' | sort -S40% | uniq | wc -l | awk '{print $1*0.03}')
	#echo "will select $CNT"
	CNT=1000

	tail -n +2 "${WORK_DIR}/ButWhy/explainer_examples/cohort.${cohort_name}.preds" | sort -S40% -r -g -k7 | awk -F"\t" -v cnt=$CNT '{ if (seen[$2]==0) {c+=1; if (c<=cnt) {print $0}}  seen[$2]=1; }' | sort -S40% -g -k2 -k3 | awk -F"\t" 'BEGIN {OFS="\t"; } {print $1,$2,$3,$4,$5,$6}' >> "${WORK_DIR}/ButWhy/explainer_examples/top.${cohort_name}.samples"

	TEST_SAMPLES_C="${WORK_DIR}/ButWhy/explainer_examples/top.${cohort_name}.samples"

	if [ ! -f "${WORK_DIR}/ButWhy/explainer_examples/test_report.${cohort_name}.tsv" ]; then
		echo "### Generate report for ${TEST_SAMPLES_C} ... ###"
		CreateExplainReport --rep ${REPOSITORY_PATH} --samples_path "${TEST_SAMPLES_C}" --model_path ${EXPLAINABLE_MODEL} --take_max 10 --expend_dict_names 1 --expend_feature_names 1 --rep_settings "min_count=2;sum_ratio=0.5" --output_path "${WORK_DIR}/ButWhy/explainer_examples/test_report.${cohort_name}.tsv" --viewer_url_base '=HYPERLINK("http://node-04:8196/pid,%d,%d,prediction_time,Smoking_Status&Smoking_Duration&P_White&P_Red&Platelets&P_Diabetes&P_Cholesterol&P_Liver&P_Renal&ICD9_Diagnosis&Race&Lung_Cancer_Location","Open Viewer")'
		echo "### Done Generate report for ${TEST_SAMPLES_C} ! ###"
	fi

	echo "Final report is in: ${WORK_DIR}/ButWhy/explainer_examples/test_report.${cohort_name}.tsv" 
done < ${WORK_DIR}/tmp/cohorts

#how much to show for each group
MAX_GRP=3
MAX_FEAT=3
MAX_F=3

while read -r line;
do
	cohort_name=$(echo $line | sed -r 's|[,;:]|_|g' | sed 's|\.000||g')
	TEST_SAMPLES_C="${WORK_DIR}/ButWhy/explainer_examples/top.${cohort_name}.samples"
	REPORT_PATH=${WORK_DIR}/ButWhy/explainer_examples/test_report.${cohort_name}.tsv
	
	${CURR_PT}/resources/lib/reformat.sh ${REPORT_PATH} ${MAX_GRP} ${MAX_FEAT} | awk -F"\t" -v max_grp=${MAX_GRP} -v max_feat=${MAX_FEAT} 'NR>1 && NF>1 { for (i=1;i<=max_grp;i++) { for (j=1;j<=max_feat;j++) { grp_idx=3+2*(i-1)*(max_feat+1); f_idx=3+2*(max_feat+1)*(i-1) +2*j+1; group_name=$(grp_idx); if (index(group_name,"(")>0) {group_name=substr(group_name,0,index(group_name,"(")-1);} feat_name=$(f_idx); feat_name= substr(feat_name,0, index(feat_name, "(")-1); print group_name "\t" feat_name "\t" NR  }  } }' | awk -F"\t" '{if (prev!=$NF || prev_g!=$1 || $2!="") {print $0} prev=$NF; prev_g=$1; }' > ${WORK_DIR}/tmp/grp_to_feat

	R_CNT=$(cat ${TEST_SAMPLES_C} | wc -l | awk '{print $1-1}')
	echo "Report is based on ${R_CNT} examples"
	${CURR_PT}/resources/lib/reformat.sh ${REPORT_PATH} ${MAX_GRP} 0 | awk -F"\t" -v max_grp=${MAX_GRP} -v r_cnt=${R_CNT} 'NR>1 { for (i=1;i<=max_grp;i++) { grp_idx=3+(i-1)*2; group_name=$(grp_idx); if (index(group_name,"(")>0) {group_name=substr(group_name,0,index(group_name,"(")-1);} if (length($(grp_idx))>0) {c[group_name]+=1; n+=1; }} } END {for (g in c) print g "\t" c[g] "\t" 100*c[g]/r_cnt }' > ${WORK_DIR}/tmp/grp_hist

	awk -F"\t" '{print $2}' ${WORK_DIR}/tmp/grp_to_feat | sort -S80% | uniq > ${WORK_DIR}/tmp/feats
	Flow --get_feature_group --group_signals BY_SIGNAL_CATEG --select_features file:${WORK_DIR}/tmp/feats | awk '{print $1 "\t" $3}' > ${WORK_DIR}/tmp/map_feat_to_sig
	#text_file_processor --input ${WORK_DIR}/tmp/grp_to_feat --output ${WORK_DIR}/tmp/grp_to_sig --has_header 0 --config_parse "0;file:${WORK_DIR}/tmp/map_feat_to_sig#0#1#1;2"

	cat ${WORK_DIR}/tmp/grp_to_feat | sort -S80% | uniq | awk '{print $1 "\t" $2}' | sort -S80% | uniq -c | awk '{print $2 "\t" $3 "\t" $1}' | sort -S80% -k1,1 -k3,3gr > ${WORK_DIR}/tmp/group_to_sig_counts

	text_file_processor --input ${WORK_DIR}/tmp/group_to_sig_counts --output ${WORK_DIR}/tmp/grp_info --has_header 0 --config_parse "0;file:${WORK_DIR}/tmp/grp_hist#0#0#1,2;1;2"

	cat ${WORK_DIR}/tmp/grp_info | awk -F"\t" -v max_f=${MAX_F} 'BEGIN {last_g=""; c=0;} { if (last_g==$1) {c+=1;} else {printf("\n%s\t%d\t%2.1f",$1,$2,$3); last_g=$1; c=1;} if (c<=max_f) {printf("\t%s\t%d", $4,$5);  }   }' | sort -S80% -r -g -k2 | awk -F"\t" -v max_f=${MAX_F} 'BEGIN { printf("Group\tFrequency\tPercentage"); for (i=1;i<=max_f;i++) {printf("\tleading_feature_%d\tfeature_frequency_%d", i,i);} printf("\n");  } {print $0}' > ${WORK_DIR}/ButWhy/explainer_examples/group_stats_final.${cohort_name}.tsv

	echo "file done in ${WORK_DIR}/ButWhy/explainer_examples/group_stats_final.${cohort_name}.tsv"
done < ${WORK_DIR}/tmp/cohorts
