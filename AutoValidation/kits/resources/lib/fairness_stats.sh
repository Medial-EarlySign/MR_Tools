#!/bin/bash
set -e

WORK_DIR=$1
FAIRNESS_BT_PREFIX_FILTER=$2
BT_BY_PR=$3
BT_REPORT=$4
OUT_NAME=${5-}

mkdir -p ${WORK_DIR}/tmp

#FAIRNESS_BT_PREFIX=$(echo ${FAIRNESS_BT_PREFIX_FILTER} | sed 's|,|-|g' | sed 's|;|,|g')
FAIRNESS_BT_PREFIX=$(python ${0%/*}/reformat_bt_filter.py ${FAIRNESS_BT_PREFIX_FILTER})

FULL_CNT=$(cat ${BT_BY_PR} | egrep "^${FAIRNESS_BT_PREFIX}\s" | wc -l)
if [ $FULL_CNT -lt 1 ]; then
	echo "FAIRNESS_BT_PREFIX should be set to exact minimal cohort string. The fairness group will be addition in the begining or end"
	echo "BT path: ${BT_BY_PR}"
	echo "Error - can't find \"${FAIRNESS_BT_PREFIX}\""
	bootstrap_format.py --report_path ${BT_BY_PR} --show_cohorts 1
	exit 1
fi

bootstrap_format.py --report_path ${BT_BY_PR} --cohorts_list "^${FAIRNESS_BT_PREFIX}$" --measure_regex "SCORE@PR_(01|03|05|10|15)" --table_format m,rc > ${WORK_DIR}/fairness/cutoff_by_scores${OUT_NAME}.tsv

SCORE_THRESHOLD_10=$(egrep "SCORE@PR_10\s" ${WORK_DIR}/fairness/cutoff_by_scores${OUT_NAME}.tsv | awk -F"\t" '{print substr($2,0, index($2, "[")-1)}')
SCORE_THRESHOLD_5=$(egrep "SCORE@PR_5\s" ${WORK_DIR}/fairness/cutoff_by_scores${OUT_NAME}.tsv | awk -F"\t" '{print substr($2,0, index($2, "[")-1)}')

#Show performance in different working points:
echo -e "Cohort\tAUC\tCohort_Size\tCohort_fraction\tIncidence\tSENS@SCORE_TH_5\tSPEC@SCORE_TH_5\tSENS@SCORE_TH_10\tSPEC@SCORE_TH_10" > ${WORK_DIR}/fairness/fairness_report${OUT_NAME}.tsv

bootstrap_format.py --report_path ${BT_REPORT} --report_name MES --cohorts_list "${FAIRNESS_BT_PREFIX}" --measure_regex AUC --table_format rc,m --break_cols 0 | grep -v Warning | sed 's|MES\$||g' | sed -r 's/'${FAIRNESS_BT_PREFIX}',|,'${FAIRNESS_BT_PREFIX}'//g' | sed 's|'${FAIRNESS_BT_PREFIX}'|All|g' | awk -F"\t" 'NF>=2' | tail -n +2 | sort -S80% -k1 > ${WORK_DIR}/tmp/1.tsv

bootstrap_format.py --report_path ${BT_REPORT} --report_name MES --cohorts_list "${FAIRNESS_BT_PREFIX}" --measure_regex "POS|NEG" --take_obs 1 --table_format rc,m --break_cols 0 | grep -v Warning | sed 's|MES\$||g' | awk -F"\t" 'NF>2 {if (NR==1) { if (index($2,"NEG")>0) {n_idx=2; p_idx=3;} else {n_idx=3; p_idx=2;} } else {  split($n_idx,tokens_neg, "["); split($p_idx, tokens_pos, "["); print $1 "\t" tokens_neg[1] + tokens_pos[1] "\t" 100*tokens_pos[1]/(tokens_pos[1] + tokens_neg[1])  }}' > ${WORK_DIR}/tmp/_6.tsv
TOT_SIZE=$(egrep "^${FAIRNESS_BT_PREFIX}\s" ${WORK_DIR}/tmp/_6.tsv | awk -F"\t" '{print $2}')

if [ $TOT_SIZE -lt 1 ]; then
	echo "TOT_SIZE = ${TOT_SIZE}"
	exit -1
fi
#echo "TOT_SIZE = ${TOT_SIZE}"
#echo "SCORE_THRESHOLD_5 = ${SCORE_THRESHOLD_5}"

awk -F"\t" -v tot_size=$TOT_SIZE 'BEGIN {OFS="\t"} {print $1, $2, sprintf("%2.2f",100*$2/tot_size),  sprintf("%2.2f",$3)}' ${WORK_DIR}/tmp/_6.tsv | sort -S80% -k1 | awk -F"\t" 'BEGIN {OFS="\t"} {print $2,$3,$4}' > ${WORK_DIR}/tmp/6.tsv

grep SENS@SCORE ${BT_REPORT} | egrep "${FAIRNESS_BT_PREFIX}" | awk -v wp=$SCORE_THRESHOLD_10 '{cc[$1]+=1; if (cc[$1]==1) {min_diff[$1]=-1;} if (index($2, "_Mean") > 0) { w=substr($2,12); gsub( "_Mean", "", w); diff=(w-wp)*(w-wp); if (min_diff[$1]==-1 || min_diff[$1]>diff) { min_diff[$1]=diff; sel[$1]=$NF; sel_val[$1]=w+0; } } if (index($2, "_CI.Upper") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_h[$1][ws]=$NF} if (index($2, "_CI.Lower") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_l[$1][ws]=$NF}  } END { for (cohort in cc) { printf("%s\t%2.2f [%2.2f - %2.2f]\n", cohort , sel[cohort] ,dict_l[cohort][sel_val[cohort]] ,dict_h[cohort][sel_val[cohort]]  ); }}' | sort -S80% -k1 | awk -F"\t" '{print $2}' > ${WORK_DIR}/tmp/2.tsv

grep SENS@SCORE ${BT_REPORT} | egrep "${FAIRNESS_BT_PREFIX}" | awk -v wp=$SCORE_THRESHOLD_5 '{cc[$1]+=1; if (cc[$1]==1) {min_diff[$1]=-1;} if (index($2, "_Mean") > 0) { w=substr($2,12); gsub( "_Mean", "", w); diff=(w-wp)*(w-wp); if (min_diff[$1]==-1 || min_diff[$1]>diff) { min_diff[$1]=diff; sel[$1]=$NF; sel_val[$1]=w+0; } } if (index($2, "_CI.Upper") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_h[$1][ws]=$NF} if (index($2, "_CI.Lower") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_l[$1][ws]=$NF}  } END { for (cohort in cc) { printf("%s\t%2.2f [%2.2f - %2.2f]\n", cohort , sel[cohort] ,dict_l[cohort][sel_val[cohort]] ,dict_h[cohort][sel_val[cohort]]  ); }}' | sort -S80% -k1 | awk -F"\t" '{print $2}' > ${WORK_DIR}/tmp/3.tsv

grep SPEC@SCORE ${BT_REPORT} | egrep "${FAIRNESS_BT_PREFIX}" | awk -v wp=$SCORE_THRESHOLD_10 '{cc[$1]+=1; if (cc[$1]==1) {min_diff[$1]=-1;} if (index($2, "_Mean") > 0) { w=substr($2,12); gsub( "_Mean", "", w); diff=(w-wp)*(w-wp); if (min_diff[$1]==-1 || min_diff[$1]>diff) { min_diff[$1]=diff; sel[$1]=$NF; sel_val[$1]=w+0; } } if (index($2, "_CI.Upper") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_h[$1][ws]=$NF} if (index($2, "_CI.Lower") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_l[$1][ws]=$NF}  } END { for (cohort in cc) { printf("%s\t%2.2f [%2.2f - %2.2f]\n", cohort , sel[cohort] ,dict_l[cohort][sel_val[cohort]] ,dict_h[cohort][sel_val[cohort]]  ); }}' | sort -S80% -k1 | awk -F"\t" '{print $2}' > ${WORK_DIR}/tmp/4.tsv

grep SPEC@SCORE ${BT_REPORT} | egrep "${FAIRNESS_BT_PREFIX}" | awk -v wp=$SCORE_THRESHOLD_5 '{cc[$1]+=1; if (cc[$1]==1) {min_diff[$1]=-1;} if (index($2, "_Mean") > 0) { w=substr($2,12); gsub( "_Mean", "", w); diff=(w-wp)*(w-wp); if (min_diff[$1]==-1 || min_diff[$1]>diff) { min_diff[$1]=diff; sel[$1]=$NF; sel_val[$1]=w+0; } } if (index($2, "_CI.Upper") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_h[$1][ws]=$NF} if (index($2, "_CI.Lower") > 0){ w=substr($2,12); ws=substr(w,0,index(w, "_CI."))+0; dict_l[$1][ws]=$NF}  } END { for (cohort in cc) { printf("%s\t%2.2f [%2.2f - %2.2f]\n", cohort , sel[cohort] ,dict_l[cohort][sel_val[cohort]] ,dict_h[cohort][sel_val[cohort]]  ); }}' | sort -S80% -k1 | awk -F"\t" '{print $2}' > ${WORK_DIR}/tmp/5.tsv

paste ${WORK_DIR}/tmp/1.tsv ${WORK_DIR}/tmp/6.tsv ${WORK_DIR}/tmp/3.tsv ${WORK_DIR}/tmp/5.tsv ${WORK_DIR}/tmp/2.tsv ${WORK_DIR}/tmp/4.tsv  >> ${WORK_DIR}/fairness/fairness_report${OUT_NAME}.tsv

echo "please refer to ${WORK_DIR}/fairness/fairness_report${OUT_NAME}.tsv"

REPORT_FULL_NAME=${WORK_DIR}/fairness/fairness_report${OUT_NAME}
#Fix to do for each test separately
echo "#################### Significant test 5: ###################" 
tail -n +2 ${REPORT_FULL_NAME}.tsv | awk -F"\t" 'BEGIN {OFS="\t"} {if (NR==1) {print "Cohort", "False Negatives", "True Positives", "Sensitivity"} tot_cases=sprintf("%2.0f",$3*$5/100); split($6, tokens, " "); sel=sprintf("%2.0f", (tokens[1]/100)*tot_cases); non_sel=tot_cases-sel; print $1, non_sel, sel, sprintf("%2.1f",100*sel/(sel+non_sel))  }' | tee ${REPORT_FULL_NAME}.chi_table.5.tsv
cp ${REPORT_FULL_NAME}.chi_table.5.tsv ${WORK_DIR}/tmp/chi_table.tsv
tail -n +2 ${WORK_DIR}/tmp/chi_table.tsv | awk -F"\t" '$1!="All"'  | awk -F"\t" '{tot+=$2+$3; t[NR]=$3; f[NR]=$2;} END { p_t=(t[1]+t[2])/tot; p_f=(f[1]+f[2])/tot; e_t_1=p_t*(t[1]+f[1]); e_f_1=p_f*(t[1]+f[1]); e_t_2=p_t*(t[2]+f[2]); e_f_2=p_f*(t[2]+f[2]); chi_val=(t[1]-e_t_1)*(t[1]-e_t_1)/e_t_1 + (t[2]-e_t_2)*(t[2]-e_t_2)/e_t_2 + (f[1]-e_f_1)*(f[1]-e_f_1)/e_f_1 + (f[2]-e_f_2)*(f[2]-e_f_2)/e_f_2; print "Chi Square value = " chi_val } '  | tee -a ${REPORT_FULL_NAME}.chi_table.5.tsv
echo "##################### Significant test 10: ###################" 
tail -n +2 ${REPORT_FULL_NAME}.tsv | awk -F"\t" 'BEGIN {OFS="\t"} {if (NR==1) {print "Cohort", "False Negatives", "True Positives", "Sensitivity"} tot_cases=sprintf("%2.0f",$3*$5/100); split($8, tokens, " "); sel=sprintf("%2.0f", (tokens[1]/100)*tot_cases); non_sel=tot_cases-sel; print $1, non_sel, sel, sprintf("%2.1f",100*sel/(sel+non_sel))  }' | tee ${REPORT_FULL_NAME}.chi_table.10.tsv
cp ${REPORT_FULL_NAME}.chi_table.10.tsv ${WORK_DIR}/tmp/chi_table.tsv
tail -n +2 ${WORK_DIR}/tmp/chi_table.tsv | awk -F"\t" '$1!="All"' | awk -F"\t" '{tot+=$2+$3; t[NR]=$3; f[NR]=$2;} END { p_t=(t[1]+t[2])/tot; p_f=(f[1]+f[2])/tot; e_t_1=p_t*(t[1]+f[1]); e_f_1=p_f*(t[1]+f[1]); e_t_2=p_t*(t[2]+f[2]); e_f_2=p_f*(t[2]+f[2]); chi_val=(t[1]-e_t_1)*(t[1]-e_t_1)/e_t_1 + (t[2]-e_t_2)*(t[2]-e_t_2)/e_t_2 + (f[1]-e_f_1)*(f[1]-e_f_1)/e_f_1 + (f[2]-e_f_2)*(f[2]-e_f_2)/e_f_2; print "Chi Square value = " chi_val } ' | tee -a ${REPORT_FULL_NAME}.chi_table.10.tsv
echo "#############################################################"

