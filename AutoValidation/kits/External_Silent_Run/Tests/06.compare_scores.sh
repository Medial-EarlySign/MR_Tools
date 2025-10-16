#!/bin/bash
set -e -o pipefail
CURR_PT=${2}
# please edit this part, BEGIN
REQ_PARAMS=(WORK_DIR REFERENCE_MATRIX MODEL_PATH) # Required parameters
DEPENDS=() # Specify dependent tests to run: 2?, 3?
# END.
. ${CURR_PT}/resources/lib/init_infra.sh

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write your code here...

MODEL_PATH=${WORK_DIR}/model/model.medmdl
echo "Comparing scores"

SAMPLES_PATH=${WORK_DIR}/Samples
BS=${WORK_DIR}/compare
mkdir -p ${BS}
mkdir -p ${BS}/score_dist_by_age

if [ -f ${WORK_DIR}/ref_matrix ]; then
	REFERENCE_MATRIX=${WORK_DIR}/ref_matrix #Override
fi

REP_NAME=$(ls -1 ${WORK_DIR}/rep | egrep "\.repository$")
REP_PATH=${WORK_DIR}/rep/${REP_NAME}

MEM_LIMIT_ADD=""
if [ ! -z "${MEMORY_LIMIT}" ] && [ ${MEMORY_LIMIT} -gt 0 ] ; then
    TMP="change_name=Limit_Memory;object_type_name=MedModel;change_command={max_data_in_mem=${MEMORY_LIMIT}}"
    MEM_LIMIT_ADD="--change_model_init ${TMP}"
fi

#get preds for all
if [ -f ${SAMPLES_PATH}/1.all_potential.samples ]; then
	mkdir -p ${WORK_DIR}/predictions
	if [ ! -f ${WORK_DIR}/predictions/all.preds ] || [ ${SAMPLES_PATH}/1.all_potential.samples -nt ${WORK_DIR}/predictions/all.preds ] || [ ${MODEL_PATH} -nt ${WORK_DIR}/predictions/all.preds ] || [ ${REP_PATH} -nt ${WORK_DIR}/predictions/all.preds ]; then
		Flow --rep ${REP_PATH} --f_samples ${SAMPLES_PATH}/1.all_potential.samples --get_model_preds --f_model  ${MODEL_PATH} --f_preds ${WORK_DIR}/predictions/all.preds ${MEM_LIMIT_ADD}
	fi
fi

#get preds 
if [ ! -f ${BS}/3.test_cohort.preds ] || [ ${SAMPLES_PATH}/3.test_cohort.samples -nt ${BS}/3.test_cohort.preds ] || [ ${MODEL_PATH} -nt ${BS}/3.test_cohort.preds ] || [ ${REP_PATH} -nt ${BS}/3.test_cohort.preds ]; then
	Flow --rep ${REP_PATH} --f_samples ${SAMPLES_PATH}/3.test_cohort.samples --get_model_preds --f_model  ${MODEL_PATH} --f_preds ${BS}/3.test_cohort.preds ${MEM_LIMIT_ADD}
fi

if [ ! -f ${BS}/reference.preds ] || [ ${REFERENCE_MATRIX} -nt ${BS}/reference.preds ]; then
	awk -F, 'BEGIN {OFS="\t"; print "EVENT_FIELDS","id","time","outcome","outcomeTime","split","pred_0"} NR>1 {print "SAMPLE", $2,$3,$4,20990101,-1,$7}' ${REFERENCE_MATRIX} > ${BS}/reference.preds
fi

echo -e "Test\tMean\tSTD" | tee ${BS}/compare_score.txt
awk -F"\t" '{n+=1; s+=$7; ss+=$7*$7} END {print "Reference\t" s/n "\t" sqrt(((ss/n)-(s/n)*(s/n)))}' ${BS}/reference.preds | tee -a ${BS}/compare_score.txt
awk -F"\t" '{n+=1; s+=$7; ss+=$7*$7} END {print "Test_Run\t" s/n "\t" sqrt(((ss/n)-(s/n)*(s/n)))}' ${BS}/3.test_cohort.preds | tee -a ${BS}/compare_score.txt
if [ -f ${WORK_DIR}/Samples/test.orig.preds ]; then
	awk -F"\t" '{n+=1; s+=$7; ss+=$7*$7} END {print "Test_Run.Original\t" s/n "\t" sqrt(((ss/n)-(s/n)*(s/n)))}' ${WORK_DIR}/Samples/test.orig.preds | tee -a ${BS}/compare_score.txt
	
	paste.pl ${WORK_DIR}/Samples/test.orig.preds 1,2 ${BS}/3.test_cohort.preds 1,2 6 | awk '{print $7 "\t" $NF}' |  getStats --stat pearson,spearman,rmse --cols 0,1 --nbootstrap 100
fi

#dist:
echo -e "Test\tscore\tPercentage" > ${BS}/score_dist.tsv
awk -F"\t"  '{n+=1; s[int($NF*200)/200]+=1;} END { for (score in s) {print "Reference" "\t" score "\t" int(s[score]/n*1000)/10} }' ${BS}/reference.preds | sort -g -k2 >> ${BS}/score_dist.tsv
awk -F"\t"  '{n+=1; s[int($NF*200)/200]+=1;} END { for (score in s) {print "Test_Run" "\t" score "\t" int(s[score]/n*1000)/10} }' ${BS}/3.test_cohort.preds | sort -g -k2 >> ${BS}/score_dist.tsv

# Create html templates - plot_with_missing but with relative link to plotly.js
mkdir -p ${WORK_DIR}/tmp
TEMPLATE_PATH=$(which plot.py)
cp ${TEMPLATE_PATH%/*}/templates/plotly_graph.html ${WORK_DIR}/tmp
sed -i 's|<script src="[^"]*"|<script src="../js/plotly.js"|g' ${WORK_DIR}/tmp/plotly_graph.html
# end html templates

plot.py --input ${BS}/score_dist.tsv --html_template ${WORK_DIR}/tmp/plotly_graph.html --output ${BS}/score_dist.html --x_cols 1 --y_cols 2 --group_col 0 --has_header 1 --graph_mode bar

python ${CURR_PT}/resources/lib/compare_scores.py ${1}

if [ -f ${BS}/bt.reference.pivot_txt ] || [ ${BS}/reference.preds -nt ${BS}/bt.reference.pivot_txt ]; then
	awk -F"\t" 'BEGIN {OFS="\t"} { if (NR>1)  { $2=NR; $4=rand()>0.5;} print $0 }' ${BS}/reference.preds > ${WORK_DIR}/tmp/1.preds
	bootstrap_app --sample_per_pid 0 --input ${WORK_DIR}/tmp/1.preds --use_censor 0 --working_points_pr 0.5,1,1.5,2,2.3,2.5,3,3.5,4,4.5,5 --output ${BS}/bt.reference
fi
if [ -f ${BS}/bt_by_score.reference.pivot_txt ] || [ ${BS}/reference.preds -nt ${BS}/bt_by_score.reference.pivot_txt ]; then
	awk -F"\t" 'BEGIN {OFS="\t"} { if (NR>1)  { $2=NR; $4=rand()>0.5;} print $0 }' ${BS}/reference.preds > ${WORK_DIR}/tmp/1.preds
	bootstrap_app --sample_per_pid 0 --input ${WORK_DIR}/tmp/1.preds --use_censor 0 --force_score_working_points 1 --output ${BS}/bt_by_score.reference
fi

if [ -f ${BS}/bt.new.pivot_txt ] || [ ${BS}/3.test_cohort.preds -nt ${BS}/bt.new.pivot_txt ]; then
	awk -F"\t" 'BEGIN {OFS="\t"} { if (NR>1)  { $4=rand()>0.5;} print $0 }' ${BS}/3.test_cohort.preds > ${WORK_DIR}/tmp/1.preds
	bootstrap_app --sample_per_pid 0 --input ${WORK_DIR}/tmp/1.preds --use_censor 0 --working_points_pr 0.5,1,1.5,2,2.3,2.5,3,3.5,4,4.5,5 --output ${BS}/bt.new 
fi
if [ -f ${BS}/bt_by_score.new.pivot_txt ] || [ ${BS}/3.test_cohort.preds -nt ${BS}/bt_by_score.new.pivot_txt ]; then
	awk -F"\t" 'BEGIN {OFS="\t"} { if (NR>1)  { $4=rand()>0.5;} print $0 }' ${BS}/3.test_cohort.preds > ${WORK_DIR}/tmp/1.preds
	bootstrap_app --sample_per_pid 0 --input ${WORK_DIR}/tmp/1.preds --use_censor 0 --force_score_working_points 1 --output ${BS}/bt_by_score.new
fi

bootstrap_format.py --report_path ${BS}/bt.reference.pivot_txt ${BS}/bt.new.pivot_txt --report_name Reference Test_Run --measure "SCORE@PR" --format_num %2.4f | tee -a $BS/compare_score.txt

