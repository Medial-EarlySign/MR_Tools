#!/bin/bash
CURR_PT=${0%/*}
for i in {1..5}
do
   if [ -f "${CURR_PT}/env.sh" ] ;  then
        source ${CURR_PT}/env.sh
        echo "Load env from ${CURR_PT}"
        break
   else
        CURR_PT=$(realpath ${CURR_PT}/..)
   fi
done

set -e

#DEFINE REPO_PATH, WORK_DIR
REF_YEAR=2015
REPO_PATH=/mnt/work/Repositories/IBM/ibm.repository
WORK_DIR=/mnt/work/LGI/loading_files/outputs/demo_stats
EVENT_CD_LIST=/mnt/work/LGI/etl/configs/crc.list

mkdir -p ${WORK_DIR}

if [ ! -f ${WORK_DIR}/all_pids.samples ]; then
	Flow --rep ${REPO_PATH} --pids_sigs --sigs BYEAR | awk -F"\t" 'BEGIN {OFS="\t"; print "EVENT_FIELDS", "id", "time", "outcome", "outcomeTime", "split"} NR>1 {print "SAMPLE", $1, 20220101,0, 20220101,-1}' > ${WORK_DIR}/all_pids.samples
fi

if [ ! -f ${WORK_DIR}/all_event_patients.tsv ]; then
	search_codes --rep ${REPO_PATH} --signal DIAGNOSIS --code_list_is_file 1 --code_list ${EVENT_CD_LIST} --time_win_from 0 --time_win_to 36500 --pid_time_file  ${WORK_DIR}/all_pids.samples --output_file  ${WORK_DIR}/all_event_patients.tsv
fi

if [ ! -f ${WORK_DIR}/all_event_patients.filtered.tsv ]; then
	awk -F"\t" '$4!="MISSING"' ${WORK_DIR}/all_event_patients.tsv | awk -F"\t" '{if (min_t[$1]==0 || min_t[$1]>$3) {min_t[$1]=$3; p_diag[$1]=$4} } END { for (pid in min_t) {print pid "\t" min_t[pid] "\t" p_diag[pid]}  }' | sort -S50% -g -k1 > ${WORK_DIR}/all_event_patients.filtered.tsv
fi

if [ ! -f ${WORK_DIR}/pid_sexes ]; then
	Flow --rep ${REPO_PATH} --pids_sigs --sigs GENDER | awk 'NR>1 { split( $NF, arr, "|"); print $1 "\t" arr[2]}' > ${WORK_DIR}/pid_sexes
fi
if [ ! -f ${WORK_DIR}/pid_byear ]; then
        Flow --rep ${REPO_PATH} --pids_sigs --sigs BYEAR | awk 'NR>1 {print $1 "\t" $NF}' > ${WORK_DIR}/pid_byear
fi


#General stats

#Sex:
if [ ! -f ${WORK_DIR}/all_gender.hist ] ; then
	Flow --rep ${REPO_PATH} --pids_sigs --sigs GENDER | awk -F"\t" 'NR>1 { split( $NF, arr, "|"); c[arr[2]]+=1;n+=1;} END { for (g in c) {print g "\t" c[g] "\t" 100*c[g]/n} }' | tee ${WORK_DIR}/all_gender.hist
fi
#plot.py --input ${WORK_DIR}/outputs/all_gender.hist --output  ${WORK_DIR}/outputs/gender_hist.html --has_header 0 --x_cols 0 --y_cols 1
#sed -i 's|scatter|bar|g' ${WORK_DIR}/outputs/gender_hist.html
#Age at 2015:
if [ ! -f ${WORK_DIR}/all_ages.hist ] ; then
	cat ${WORK_DIR}/pid_byear | awk -F"\t" -v ref_year=$REF_YEAR '{age=ref_year-$2; if (age>90) {age=90} age=5*int(age/5); c[age]+=1; n+=1;} END { for (g in c) {print g "\t" c[g] "\t" 100*c[g]/n}}' | sort -g -k1 | tee ${WORK_DIR}/all_ages.hist
fi
#plot.py --input ${WORK_DIR}/outputs/all_ages.hist --output  ${WORK_DIR}/outputs/age_hist.html --has_header 0 --x_cols 0 0 --y_cols 1 2
#sed -i 's|scatter|bar|g' ${WORK_DIR}/outputs/age_hist.html

#Event stats

echo "Event by years"
awk -F"\t" 'BEGIN {print "Year\tcount\tPercentage%"} NR>1 {v=int($2/10000); c[v]+=1; n+=1;} END { for (v in c) {print v "\t" c[v] "\t" 100*c[v]/n} }' ${WORK_DIR}/all_event_patients.filtered.tsv | sort -g -k1 | plot.py --has_header 1 --x_cols 0 --y_cols 1 --output ${WORK_DIR}/event_by_years.html

echo "Event by seasons"
awk -F"\t" 'BEGIN {print "Month\tcount\tPercentage%"} NR>1 {v=int(($2%10000)/100); c[v]+=1; n+=1;} END { for (v in c) {print v "\t" c[v] "\t" 100*c[v]/n} }' ${WORK_DIR}/all_event_patients.filtered.tsv | sort -g -k1 | plot.py --has_header 1 --x_cols 0 --y_cols 1 --output ${WORK_DIR}/event_by_seasons.html
sed -i 's|scatter|bar|g'  ${WORK_DIR}/event_by_seasons.html

#Sex:
paste.pl ${WORK_DIR}/all_event_patients.filtered.tsv 0 ${WORK_DIR}/pid_sexes 0 1 -t | awk -F"\t" '{c[$NF]+=1; n+=1;} END { for (g in c) {print g "\t" c[g] "\t" 100*c[g]/n} }' | tee ${WORK_DIR}/event_gender.hist

#plot.py --input ${WORK_DIR}/outputs/event_gender.hist --output  ${WORK_DIR}/outputs/event_gender_hist.html --has_header 0 --x_cols 0 --y_cols 1
#sed -i 's|scatter|bar|g' ${WORK_DIR}/outputs/event_gender_hist.html
paste.pl ${WORK_DIR}/all_gender.hist 0 ${WORK_DIR}/event_gender.hist 0 1 2 -t | awk -F"\t" 'BEGIN {OFS="\t"; print "Sex", "All", "All","Event","Event"} {print $1, $3, $2,$5,$4}' | transpose.pl - -t  | awk -F"\t" '{if (NR>1) { if (c[$1]==0) {m1[$1]=$2; m2[$1]=$3; printf("%s\t%s\t%s",$1,$2,$3); c[$1]=1} else { printf("\t%s\t%s\n", $2 "(" m1[$1] "%)", $3 "(" m2[$1] "%)"); }  } else {print $0} }' | plot.py --output ${WORK_DIR}/gender_hist.html --x_cols 0 0 --has_header 1 --y_cols 1 2 --txt_cols 3 4 --graph_mode bar --layout_str "barmode:'stack'"

#Age:
paste.pl ${WORK_DIR}/all_event_patients.filtered.tsv 0 ${WORK_DIR}/pid_byear 0 1 -t | awk -F"\t" '{ref_year=int($2/10000); age=ref_year-$4; if (age>90) {age=90} age=5*int(age/5); c[age]+=1 ; n+=1;} END { for (g in c) {print g "\t" c[g] "\t" 100*c[g]/n} }' | sort -g -k1 | tee ${WORK_DIR}/event_ages.hist

paste.pl ${WORK_DIR}/all_ages.hist 0 ${WORK_DIR}/event_ages.hist 0 1 2 -t | awk -F"\t" 'BEGIN {OFS="\t"; print "Age", "All", "All","Event","Event"} {print $1, $3, $2,$5,$4}' | plot.py --output  ${WORK_DIR}/age_hist.html --has_header 1 --x_cols 0 0 --y_cols 1 3 --txt_cols 2 4 --graph_mode bar

#plot.py --input ${WORK_DIR}/outputs/event_ages.hist --output  ${WORK_DIR}/outputs/event_ages_hist.html --has_header 0 --x_cols 0 0 --y_cols 1 2
#sed  -i 's|scatter|bar|g' ${WORK_DIR}/outputs/event_ages_hist.html

