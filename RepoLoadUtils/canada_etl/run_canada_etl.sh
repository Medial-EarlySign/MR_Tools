#!/usr/bin/bash

set -x
set -e 
 
canada_etl_work_folder=/server/Work/Users/Ido/canada_122017_loading
canada_etl_code_folder=$MR_ROOT/Tools/RepoLoadUtils/canada_etl
flow_code_folder=$MR_ROOT/Tools/Flow
registries_code_folder=$MR_ROOT/Tools/Registries/
diabetes_code_folder=$MR_ROOT/Projects/Shared/Diabetes

cd $canada_etl_code_folder

if alias cp 2>/dev/null; then 
  unalias cp
fi

python 100_ids_and_demographics.py --max_end_date=20171219
python 150_train_signal.py
python 200_numeric_lab_data.py
python 400_diagnosis.py
python 500_drug.py
python 600_vital.py
python 700_visit.py
python 800_textual_lab_data.py

python $registries_code_folder/Scripts/canada_etl/100_cancer_reg.py

rm -rf $canada_etl_work_folder/repo/
mkdir -p $canada_etl_work_folder/repo/dicts/
cp -f $canada_etl_code_folder/canada.signals $canada_etl_work_folder/
cp -f $registries_code_folder/Lists/canada_etl/dict.* $canada_etl_work_folder/dicts/
cp -f $canada_etl_code_folder/dict.* $canada_etl_work_folder/dicts/
rm -f $canada_etl_work_folder/panel_completer_completed.csv
touch $canada_etl_work_folder/panel_completer_completed.csv

REPO=${canada_etl_work_folder}/repo/canada.repository
#REPO=/home/Repositories/THIN/thin_jun2017/thin.repository

pushd $flow_code_folder; smake_rel; popd;
$flow_code_folder/Linux/Release/Flow --rep_create --convert_conf ${canada_etl_code_folder}/canada.basic_signals.convert_config 2>&1 | tee ${canada_etl_work_folder}/outputs/canada.basic_signals.convert_config.log

# completions

pushd $MR_ROOT/Tools/RepoLoadUtils; smake_rel; popd;
$MR_ROOT/Tools/RepoLoadUtils/Linux/Release/PanelCompleter --repository_file=$REPO --instructions_file=$canada_etl_code_folder/Instructions.txt --out_folder=${canada_etl_work_folder}/ --out_prefix=panel_completer

$flow_code_folder/Linux/Release/Flow --rep_create --convert_conf ${canada_etl_code_folder}/canada.basic_signals.convert_config 2>&1 | tee ${canada_etl_work_folder}/outputs/canada.basic_signals_with_completions.convert_config.log

python 750_compare_numeric_data_to_thin.py

# registries 

pushd $diabetes_code_folder; smake_rel; popd;
$diabetes_code_folder/Linux/Release/Diabetes --rep $REPO --reg_type diabetes --reg_params "reg_mode=2" --create_registry --drugs $registries_code_folder/Lists/canada_etl/diabetes_drug_codes.full --read_codes $registries_code_folder/Lists/canada_etl/diabetes_read_codes_registry.full --out_reg ${canada_etl_work_folder}/diabetes.reg > ${canada_etl_work_folder}/outputs/diabetes.log

$diabetes_code_folder/Linux/Release/Diabetes --rep $REPO --diabetes_reg ${canada_etl_work_folder}/diabetes.reg --out_reg ${canada_etl_work_folder}/DM_Registry --create_registry --reg_type DM_Registry

$flow_code_folder/Linux/Release/Flow --rep_create --convert_conf ${canada_etl_code_folder}/canada.DM_Registry.convert_config 2>&1 | tee ${canada_etl_work_folder}/outputs/canada.DM_Registry.convert_config.log

$diabetes_code_folder/Linux/Release/Diabetes --rep $REPO --proteinuria --out_reg ${canada_etl_work_folder}/CKD_Registry

$flow_code_folder/Linux/Release/Flow --rep_create --convert_conf ${canada_etl_code_folder}/canada.CKD_Registry.convert_config 2>&1 | tee ${canada_etl_work_folder}/outputs/canada.CKD_Registry.convert_config.log

$registries_code_folder/CreateRegistries/Linux/Release/Hypertension --readCodesFile $registries_code_folder/Lists/canada_etl/hypertension.desc --CHF_ReadCodes $registries_code_folder/Lists/canada_etl/heart_failure_events.desc --MI_ReadCodes $registries_code_folder/Lists/canada_etl/mi.desc --AF_ReadCodes $registries_code_folder/Lists/canada_etl/atrial_fibrilation.desc --config $REPO > ${canada_etl_work_folder}/HT_Registry 2> ${canada_etl_work_folder}/outputs/HT_Registry.stderr

$flow_code_folder/Linux/Release/Flow --rep_create --convert_conf ${canada_etl_code_folder}/canada.HT_Registry.convert_config 2>&1 | tee ${canada_etl_work_folder}/outputs/canada.HT_Registry.convert_config.log

pushd $registries_code_folder/CreateRegistries/; smake_rel; popd;
for cvd in CVD_MI CVD_IschemicStroke CVD_HemorhagicStroke CVD_HeartFailure; do 
 if [ $cvd == "CVD_HeartFailure" ]; then run_type="notevent" ; else run_type="event" ; fi
 echo $cvd $run_type
 $registries_code_folder/CreateRegistries/Linux/Release/CVD --config $REPO --DiseaseReadCodesFile  $registries_code_folder/Lists/canada_etl/${cvd}_present.txt --PastReadCodesFile  $registries_code_folder/Lists/canada_etl/${cvd}_past.txt --Runtype $run_type --SignalName ${cvd} --FileOut ${canada_etl_work_folder}/${cvd}
done;

$flow_code_folder/Linux/Release/Flow --rep_create --convert_conf ${canada_etl_code_folder}/canada.CVD_Registry.convert_config 2>&1 | tee ${canada_etl_work_folder}/outputs/canada.CVD_Registry.convert_config.log
