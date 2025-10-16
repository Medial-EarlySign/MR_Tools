#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['REPOSITORY_PATH', 'TEST_SAMPLES', 'MODEL_PATH', 'TRAIN_SAMPLES_BEFORE_MATCHING', 'WORK_DIR', 'BT_JSON', 'BT_COHORT', 'NOISER_JSON', 'TIME_NOISES', 'VAL_NOISES', 'DROP_NOISES']
DEPENDS=[6] # List of dependent tests
# End Edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources')) 
from lib.PY_Helper import *

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

import subprocess
import med
import pandas as pd

from os import path

experiment_directory = path.join(WORK_DIR, 'test_noiser')
adjusted_models_directory = path.join(experiment_directory, 'adjusted_models')
preds_directory = path.join(experiment_directory, 'preds')
results_directory = path.join(experiment_directory, 'results')

os.makedirs(experiment_directory, exist_ok=True)
os.makedirs(adjusted_models_directory, exist_ok=True)
os.makedirs(preds_directory, exist_ok=True)
os.makedirs(results_directory, exist_ok=True)

if (not path.exists(NOISER_JSON)):
    print(f"Failed, file not exists NOISER_JSON = {NOISER_JSON}", flush=True)
    sys.exit(1)
if (not path.exists(BT_JSON)):
    print(f"Failed, file not exists BT_JSON = {BT_JSON}", flush=True)
    sys.exit(1)
if (not path.exists(BT_COHORT)):
    print(f"Failed, file not exists BT_COHORT = {BT_COHORT}", flush=True)
    sys.exit(1)


### takes care of zero noise
subprocess.run('ln -s -f {} {}'.format(path.join(WORK_DIR, 'bootstrap', 'test.preds'), path.join(preds_directory, 'time_0.preds')), shell=True)
subprocess.run('ln -s -f {} {}'.format(path.join(WORK_DIR, 'bootstrap', 'test.preds'), path.join(preds_directory, 'val_00.preds')), shell=True)
subprocess.run('ln -s -f {} {}'.format(path.join(WORK_DIR, 'bootstrap', 'test.preds'), path.join(preds_directory, 'drop_00.preds')), shell=True)


###takes care of generating for the other noise values
def adjust_and_preds_generator(param, noise_list):

    if param == 'time':
        param_field = '_TIME_NOISE_::'
        non_param_fields = ('_VALUE_NOISE_::0.0', '_DROP_NOISE_::0.0')
    elif param == 'val':
        param_field = '_VALUE_NOISE_::'
        non_param_fields = ('_TIME_NOISE_::0', '_DROP_NOISE_::0.0')
    else:
        param_field = '_DROP_NOISE_::'
        non_param_fields = ('_VALUE_NOISE_::0.0', '_TIME_NOISE_::0')

    for noise_val in noise_list:
        float_noise = float(noise_val)
        if param in ['val', 'drop']:
            float_noise= float_noise/10.0
        print(f'amount of noise in {param}:{float_noise}', flush=True)
        adjusted_model_path = path.join(adjusted_models_directory, f'{param}_{noise_val}.mdmdl')
        output_preds = path.join(preds_directory, f'{param}_{noise_val}.preds')
        
        if os.path.exists(output_preds) and os.path.getmtime(output_preds) >= \
            max(os.path.getmtime(TEST_SAMPLES), os.path.getmtime(REPOSITORY_PATH), os.path.getmtime(NOISER_JSON), os.path.getmtime(MODEL_PATH)):
            print(f'Already done - skips {param}_{noise_val}', flush=True)
            continue
        subprocess.run(f'adjust_model --rep {REPOSITORY_PATH} --samples {TRAIN_SAMPLES_BEFORE_MATCHING} --inModel {MODEL_PATH} --learn_rep_proc 1 --preProcessors {NOISER_JSON} \
        --out {adjusted_model_path} --json_alt {param_field}{float_noise} --json_alt {non_param_fields[0]} --json_alt {non_param_fields[1]} --add_rep_first 1', shell=True, check=True)

        subprocess.run(f'Flow --get_model_preds --rep {REPOSITORY_PATH} --f_samples {TEST_SAMPLES} --f_model {adjusted_model_path} --f_preds {output_preds}', shell=True, check=True)


def generate_analysis(param, noise_list):
    scores = []

    for noise_val in noise_list:

        path_preds = path.join(preds_directory, f'{param}_{noise_val}.preds')
        samples = med.Samples()
        samples.read_from_file(path_preds)

        bt = med.Bootstrap()
        res = bt.bootstrap_cohort(samples, REPOSITORY_PATH, BT_JSON, BT_COHORT)
        res_df = res.to_df()

        float_noise = float(noise_val)
        if param in ['val', 'drop']:
            float_noise= float_noise/10.0

        #res_df[f'{param}_noise'] = float_noise
        res_df = res_df[(res_df['Measurement'].str.contains('AUC')) |
                         (res_df['Measurement'].str.contains('SENS@FPR_05')) | (res_df['Measurement'].str.contains('SENS@FPR_10'))].reset_index(drop=True)
        res_df = res_df[(res_df['Measurement'].str.contains('_Mean')) | (res_df['Measurement'].str.contains('_CI.Lower.95'))
                        | (res_df['Measurement'].str.contains('_CI.Upper.95'))].reset_index(drop=True)
        res_df.loc[res_df['Measurement'].str.contains('AUC'),'Value'] = res_df.loc[res_df['Measurement'].str.contains('AUC'),'Value'].apply(lambda x:round(x,3))
        res_df.loc[res_df['Measurement'].str.contains('SENS'),'Value'] = res_df.loc[res_df['Measurement'].str.contains('SENS'),'Value'].apply(lambda x:round(x,2))
        res_df_pivot = res_df[['Cohort', 'Measurement', 'Value']].pivot(index='Cohort', columns='Measurement', values='Value').reset_index()
        res_df_pivot[f'{param}_noise'] = float_noise
        res_df_pivot.columns.name=None
        scores.append(res_df_pivot)

    df_scores = pd.concat(scores, ignore_index=True)
    return df_scores


time_noises = TIME_NOISES.split(',')
val_noises = VAL_NOISES.split(',')
drop_noises = DROP_NOISES.split(',')

adjust_and_preds_generator('time', time_noises)
adjust_and_preds_generator('val', val_noises)
adjust_and_preds_generator('drop', drop_noises)

generate_analysis('time', time_noises).to_csv(path.join(results_directory, 'time_analysis.csv'), index=False)
generate_analysis('val', val_noises).to_csv(path.join(results_directory, 'value_analysis.csv'), index=False)
generate_analysis('drop', drop_noises).to_csv(path.join(results_directory, 'drop_analysis.csv'), index=False)



print(f'Please refer to {results_directory}', flush=True)