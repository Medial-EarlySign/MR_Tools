#!/usr/bin/bash

set -x
set -e 

rambam_etl_work_folder=/server/Work/Users/Ido/rambam_load/
rambam_etl_code_folder=$MR_ROOT/Tools/InPatientLoaders/Rambam
rambam_repo_folder=/server/Work/CancerData/Repositories/Rambam/rambam_aug2018/

flow_code_folder=$MR_ROOT/Tools/Flow

cd $rambam_etl_code_folder

if alias cp 2>/dev/null; then 
  unalias cp
fi
smake_rel() {
    pushd CMakeBuild/Linux/Release && make -j 8; popd
}
head_it() {
 cat
 #head -$1
} 

python generate_id2nr.py --work_folder $rambam_etl_work_folder

pushd RambamParser; smake_rel; popd;
RambamParser/Linux/Release/RambamParser --id2nr $rambam_etl_work_folder/id2nr --in_list <(cat $rambam_etl_work_folder/id2nr | head_it) --create_tables "demographic,lab,transfers,diagnosis,procedures,dict,hist" --out_dir $rambam_etl_work_folder/raw_tables_extracted_from_xmls/

python extract_repo_load_files_from_tables.py --work_folder $rambam_etl_work_folder #--limit_records 10000

cat ${rambam_etl_work_folder}/repo_load_files/rambam_microbiology |awk -F '\t' '{print $5;print $6}'|sort|uniq > ${rambam_etl_work_folder}/raw_tables_extracted_from_xmls/microbiology.dict

python extract_repo_dicts_from_raw_dicts.py --work_folder $rambam_etl_work_folder 

python extract_drugs.py --work_folder $rambam_etl_work_folder 

mkdir -p ${rambam_etl_work_folder}/repo/dicts/

python extract_microbiology_labs_measurements.py --work_folder $rambam_etl_work_folder --do_condor_flag 1

python generate_signals_file.py --work_folder $rambam_etl_work_folder 

pushd $flow_code_folder; smake_rel; popd;
$flow_code_folder/Linux/Release/Flow --rep_create --convert_conf ${rambam_etl_work_folder}/repo_load_files/rambam.convert_config 2>&1

$flow_code_folder/Linux/Release/Flow --rep ${rambam_repo_folder}/rambam.repository --printall --pid 101000000 > ${rambam_etl_work_folder}/101000000.txt

$flow_code_folder/Linux/Release/Flow --rep ${rambam_repo_folder}/rambam.repository --generate_features --f_outcome=rambam_example.samples --model_init_fname=rambam_example.json --f_matrix=${rambam_etl_work_folder}/rambam_example.csv --hospital_rep

cat ${rambam_etl_work_folder}/rambam_example.csv

bash ${rambam_repo_folder}/../../rsync_rambam_to_home_folders.sh

