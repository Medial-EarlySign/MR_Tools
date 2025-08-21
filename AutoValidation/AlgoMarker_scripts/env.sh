#!/bin/bash

#DllAPITester - Path
APP_PATH=/server/UsersData/alon/MR/Libs/Internal/AlgoMarker/Linux/Release/DllAPITester

#Repository to create test data 
TEST_REP=/home/Repositories/KP/kp.repository
#Samples to create test data:
TEST_SAMPLES=/nas1/Work/Users/Alon/LungCancer/outputs/models/model_55.3y_matched_history.train_and_test.optimize_on_all/Test_Kit/ButWhy/explainer_examples/top.Age_50_80_Time-Window_90_365_Ex_or_Current_Smoker_1_999_Suspected_0_0.samples
#Samples to create full score compare
BASE_SAMPLES=/server/Work/Users/Alon/LungCancer/outputs/models/model_55.3y_matched_history.train_and_test.optimize_on_all/Samples/all.samples

#If different model needs to be applied on TEST_REP for score compare, please define ORIG_MODEL
ORIG_MODEL=/nas1/Work/Users/Eitan/Lung/outputs/models2023/EX3/model_63/config_params/calibrated.medmdl

#configs:
	# jreq_defs.json - requires for score compare 
	#If contains: signal_rename.tsv - will use to rename signals in repository to model {name in repository [TAB] for model}
	# if contains signal_regex_filter.tsv - will use to filter categorical values {signal [TAB] regex}
	# if contains jreq_defs.butwhy.json - will use this in full test instead of jreq_defs.json