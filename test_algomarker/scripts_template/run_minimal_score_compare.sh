#!/bin/bash
set -e

#BASE_SAMPLES=/server/Work/Users/Alon/LungCancer/outputs/models/model_55.3y_matched_history.train_and_test.optimize_on_all/Samples/all.samples
TEST_REP=/nas1/Work/CancerData/Repositories/KP/kp.repository
OVERRIDE=${1-0}

ORIG_MODEL=/nas1/Work/Users/eitan/Lung/outputs/models2023/EX3/model_63/config_params/calibrated.medmdl

CURR_DIR=${0%/*}
AM_DIR=$(realpath ${CURR_DIR}/..)
AM_CONFIG=$(ls -1 ${AM_DIR}/*.amconfig)
LIB_PATH=${AM_DIR}/lib/libdyn_AlgoMarker.so
MODEL_PATH=$(awk -F"\t" -v base_dir="${AM_DIR}" '$1=="MODEL" {print base_dir "/" $2}' ${AM_CONFIG})
EXP_DIR=${AM_DIR}/minimal_score_compare

mkdir -p ${EXP_DIR}

# Generate test.samples from req.json
if [ ! -f ${EXP_DIR}/test.samples ] && [ -f ${EXP_DIR}/req.json ]; then
	python -c '
import json
import pandas as pd
with open("'${EXP_DIR}'/req.json", "r") as reader:
    js_content = reader.read()
js = json.loads(js_content)
req_list = js["requests"]
req_df=pd.DataFrame(req_list).rename(columns={"patient_id":"id"})
req_df["EVENT_FIELDS"]="SAMPLE"
req_df["outcome"]=0
req_df["outcomeTime"]=20300101
req_df["split"]=-1
req_df = req_df[["EVENT_FIELDS", "id", "time", "outcome", "outcomeTime", "split"]]
req_df.to_csv("'${EXP_DIR}'/test.samples", index=False, sep="\t")
'
fi

if [ ! -f ${EXP_DIR}/test.samples ] || [ $OVERRIDE -gt 0 ]; then
	python -c '
import pandas as pd
df = pd.read_csv("'${BASE_SAMPLES}'", sep="\t") 
df = df.drop_duplicates(subset=["id"]).sample(frac=1).reset_index(drop=True).iloc[:10000]
df = df.sort_values(["id", "time"]).reset_index(drop=True)
df.to_csv("'${EXP_DIR}'/test.samples", sep="\t", index=False)
	'
fi


#Create basic request
if [ ! -f ${EXP_DIR}/req.json ] || [ $OVERRIDE -gt 0 ]; then
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --rep $TEST_REP --samples ${EXP_DIR}/test.samples --model  $MODEL_PATH --amconfig $AM_CONFIG --create_jreq --single --jreq_out ${EXP_DIR}/req.json --jreq_defs ${CURR_DIR}/jreq_defs.json
fi

if [ ! -f ${EXP_DIR}/data.json ] || [ $OVERRIDE -gt 0 ]; then
#Create data json single must be turnned on
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --rep $TEST_REP --samples ${EXP_DIR}/test.samples --model  $MODEL_PATH --amconfig $AM_CONFIG --out_jsons ${EXP_DIR}/data.json --single --calculator "LungFlag" --allow_rep_adjustment 1 --signal_categ_regex ${CURR_DIR}/signal_regex_filter.tsv --rename_signal ${CURR_DIR}/signal_rename.tsv
	
	#--ignore_sig to ignore signal
fi

if [ ! -f ${EXP_DIR}/resp.json ] || [ $OVERRIDE -gt 0 ]; then
#Test from input jsons and store output: --json_req_test --in_jsons PATH_TO_DATA_JSON(if REQ_JSON_HAS_NO_DATA, NOT CREATED WITH --add_data_to_jreq) --jreq PATH_TO_REQUEST_JSON --jresp PATH_TO_OUTPUT_RESPONSE
	$MR_ROOT/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester --amlib $LIB_PATH --amconfig $AM_CONFIG --json_req_test --in_jsons ${EXP_DIR}/data.json --jreq ${EXP_DIR}/req.json --jresp ${EXP_DIR}/resp.json --single --print_msgs --discovery ${AM_DIR}/discovery.json
fi

if [ ! -f ${EXP_DIR}/flow_code.preds ] || [ $OVERRIDE -gt 0 ]; then
if [ -z "${ORIG_MODEL}" ]; then
	ORIG_MODEL=$MODEL_PATH
fi
	Flow --rep $TEST_REP --get_model_preds --f_samples ${EXP_DIR}/test.samples --f_preds ${EXP_DIR}/flow_code.preds --f_model ${ORIG_MODEL} --change_model_init "object_type_name=TreeExplainer;change_command=DELETE;verbose_level=2"
fi

#compare ${EXP_DIR}/flow_code.preds to ${EXP_DIR}/resp.json
# Some difference might be from Flow, since data is not exactly the same
python $MR_ROOT/Tools/test_algomarker/am_tester.py --json_resp_path ${EXP_DIR}/resp.json --preds_path ${EXP_DIR}/flow_code.preds | tee ${EXP_DIR}/compare_algomarker_flow.log

#compare resp.json to resp_old.json
python -c '
import json
import pandas as pd
with open("'${EXP_DIR}'/resp.json", "r") as reader:
    js_content = reader.read()
js=json.loads(js_content)
current_res = pd.DataFrame(js["responses"])
with open("'${EXP_DIR}'/resp_old.json", "r") as reader:
    js_content = reader.read()
js=json.loads(js_content)
old_res = pd.DataFrame(js["responses"])
print(current_res["flag_result"].value_counts(dropna=False))
comp_df = old_res.merge(current_res, on=["patient_id", "time"], suffixes=["_old", "_new"])
assert(len(old_res) == len(comp_df))
assert(len(current_res) == len(comp_df))

assert(len(comp_df[comp_df["prediction_old"]!=comp_df["prediction_new"]])==0) # Score compare
print("Different messages")
print(comp_df[(comp_df["messages_old"]!=comp_df["messages_new"]) & ((comp_df["messages_old"].notna()) | (comp_df["messages_new"].notna()))])
'
