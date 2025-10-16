#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR MODEL_PATH TOP_EXPLAIN_PERCENTAGE TOP_EXPLAIN_GROUP_COUNT) # Required parameters
DEPENDS=(6) # Specify dependent tests to run
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

MODEL_PATH=${WORK_DIR}/model/model.medmdl
EXPLAINABLE_MODEL_PATH=${WORK_DIR}/model/model.with_explainability.medmdl
REPOSITORY_PATH=${WORK_DIR}/rep/test.repository
TEST_SAMPLES=${WORK_DIR}/compare/3.test_cohort.preds
TEST_SAMPLES_C="${WORK_DIR}/ButWhy/explainer_examples/top.samples"


mkdir -p ${WORK_DIR}/ButWhy
mkdir -p ${WORK_DIR}/ButWhy/explainer_examples

echo "Start Explainers report"
		
head -n 1 ${TEST_SAMPLES} > ${TEST_SAMPLES_C}

CNT=$(tail -n +2 ${TEST_SAMPLES} | wc -l | awk -v top_freq=${TOP_EXPLAIN_PERCENTAGE} '{print int($1*top_freq/100)}')
echo "will select $CNT samples" 

tail -n +2 ${TEST_SAMPLES} | sort -S40% -r -g -k7 | awk -F"\t" -v cnt=$CNT '{ if (seen[$2]==0) {c+=1; if (c<=cnt) {print $0}}  seen[$2]=1; }' | sort -S40% -g -k2 -k3 | awk -F"\t" 'BEGIN {OFS="\t"; } {print $1,$2,$3,$4,$5,$6,$7}' >> ${TEST_SAMPLES_C}

if [ ! -f "${WORK_DIR}/ButWhy/explainer_examples/test_report.tsv" ]; then
	CreateExplainReport --rep ${REPOSITORY_PATH} --samples_path "${TEST_SAMPLES_C}" --model_path ${EXPLAINABLE_MODEL_PATH} --take_max 10 --expend_dict_names 1 --expend_feature_names 1 --rep_settings "min_count=2;sum_ratio=0.5" --output_path "${WORK_DIR}/ButWhy/explainer_examples/test_report.tsv" --viewer_url_base '' 2>&1 | tee -a ${WORK_DIR}/${TEST_NAME}.log
fi
echo "Final report is in: ${WORK_DIR}/ButWhy/explainer_examples/test_report.tsv" 

#how much to show for each group
MAX_GRP=${TOP_EXPLAIN_GROUP_COUNT}
MAX_FEAT=3
MAX_F=3

REPORT_PATH=${WORK_DIR}/ButWhy/explainer_examples/test_report.tsv
CURR_PT=$2

${CURR_PT}/resources/lib/reformat.sh ${REPORT_PATH} ${MAX_GRP} ${MAX_FEAT} | awk -F"\t" -v max_grp=${MAX_GRP} -v max_feat=${MAX_FEAT} 'NR>1 && NF>1 { for (i=1;i<=max_grp;i++) { for (j=1;j<=max_feat;j++) { grp_idx=3+2*(i-1)*(max_feat+1); f_idx=3+2*(max_feat+1)*(i-1) +2*j+1; group_name=$(grp_idx); if (index(group_name,"(")>0) {group_name=substr(group_name,0,index(group_name,"(")-1);} feat_name=$(f_idx); feat_name= substr(feat_name,0, index(feat_name, "(")-1); print group_name "\t" feat_name "\t" NR  }  } }' | awk -F"\t" '{if (prev!=$NF || prev_g!=$1 || $2!="") {print $0} prev=$NF; prev_g=$1; }' > ${WORK_DIR}/tmp/grp_to_feat

R_CNT=$CNT
echo "Report is based on ${R_CNT} examples"
${CURR_PT}/resources/lib/reformat.sh ${REPORT_PATH} ${MAX_GRP} 0 | awk -F"\t" -v max_grp=${MAX_GRP} -v r_cnt=${R_CNT} 'NR>1 { for (i=1;i<=max_grp;i++) { grp_idx=3+(i-1)*2; group_name=$(grp_idx); if (index(group_name,"(")>0) {group_name=substr(group_name,0,index(group_name,"(")-1);} if (length($(grp_idx))>0) {c[group_name]+=1; n+=1; }} } END {for (g in c) print g "\t" c[g] "\t" 100*c[g]/r_cnt }' > ${WORK_DIR}/tmp/grp_hist

awk -F"\t" '{print $2}' ${WORK_DIR}/tmp/grp_to_feat | sort -S80% | uniq > ${WORK_DIR}/tmp/feats
Flow --get_feature_group --group_signals BY_SIGNAL_CATEG --select_features file:${WORK_DIR}/tmp/feats | awk '{print $1 "\t" $3}' > ${WORK_DIR}/tmp/map_feat_to_sig
#text_file_processor --input ${WORK_DIR}/tmp/grp_to_feat --output ${WORK_DIR}/tmp/grp_to_sig --has_header 0 --config_parse "0;file:${WORK_DIR}/tmp/map_feat_to_sig#0#1#1;2"

cat ${WORK_DIR}/tmp/grp_to_feat | sort -S80% | uniq | awk '{print $1 "\t" $2}' | sort -S80% | uniq -c | awk '{print $2 "\t" $3 "\t" $1}' | sort -S80% -k1,1 -k3,3gr > ${WORK_DIR}/tmp/group_to_sig_counts

text_file_processor --input ${WORK_DIR}/tmp/group_to_sig_counts --output ${WORK_DIR}/tmp/grp_info --has_header 0 --config_parse "0;file:${WORK_DIR}/tmp/grp_hist#0#0#1,2;1;2"

cat ${WORK_DIR}/tmp/grp_info | awk -F"\t" -v max_f=${MAX_F} 'BEGIN {last_g=""; c=0;} { if (last_g==$1) {c+=1;} else {printf("\n%s\t%d\t%2.1f",$1,$2,$3); last_g=$1; c=1;} if (c<=max_f) {printf("\t%s\t%d", $4,$5);  }   }' | sort -S80% -r -g -k2 | awk -F"\t" -v max_f=${MAX_F} 'BEGIN { printf("Group\tFrequency\tPercentage"); for (i=1;i<=max_f;i++) {printf("\tleading_feature_%d\tfeature_frequency_%d", i,i);} printf("\n");  } {print $0}' > ${WORK_DIR}/ButWhy/explainer_examples/group_stats_final.tsv

echo "file done in ${WORK_DIR}/ButWhy/explainer_examples/group_stats_final.tsv"
