# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 09:59:05 2019

@author: ron-internal
"""

# run bootstrap for samples


import pandas as pd
import numpy as np
import argparse, sys

##
parser = argparse.ArgumentParser()
parser.add_argument('--preds_file_1', default = '', help = 'First prediction file. Either samples with prediction scores, or bootstrap raw file (determined by whether cohort_string exists.' )
parser.add_argument('--preds_file_2', default = '' , help = 'Second prediction file. Either samples with prediction scores, or bootstrap raw file (determined by whether cohort_string exists.')
parser.add_argument('--cohort_string', default = '',  help = 'When working on bootstrap raw file, the cohort to work on.  ')

args = parser.parse_args()
##

def rename_columns(df):
    rename_dict = {'prediction_time': 'time', 'pid' : 'id', 'label' : 'outcome', 'prediction' : 'pred_0'}
    df.rename(columns= rename_dict, inplace = True)
                
def calc_p_value(preds_file_1, preds_file_2, cohort_string):
    df_samps_1 = pd.read_csv(preds_file_1,sep = '\t')
    df_samps_2 = pd.read_csv(preds_file_2,sep = '\t')
    
    rename_columns(df_samps_1)
    rename_columns(df_samps_2)
    
    # filter by cohort:
    if not (cohort_string == ''):
        # 
        df_samps_1_filt = df_samps_1[df_samps_1.cohort_name == cohort_string].reset_index(drop = True)
        df_samps_2_filt = df_samps_2[df_samps_2.cohort_name == cohort_string].reset_index(drop = True)   
    else:
        df_samps_1_filt = df_samps_1.copy()
        df_samps_2_filt = df_samps_2.copy()
    
    
    df_samps_1_filt = df_samps_1_filt[df_samps_1_filt.id.astype('str').str.isnumeric()]
    df_samps_2_filt = df_samps_2_filt[df_samps_2_filt.id.astype('str').str.isnumeric()]
    
    df_samps_1_filt.id = df_samps_1_filt.id.astype('int64')
    df_samps_1_filt.time = df_samps_1_filt.time.astype('int64')
    df_samps_1_filt.outcome = df_samps_1_filt.outcome.astype('float')
    df_samps_1_filt.pred_0 = df_samps_1_filt.pred_0.astype('float')
    
    df_samps_2_filt.id = df_samps_2_filt.id.astype('int64')
    df_samps_2_filt.time = df_samps_2_filt.time.astype('int64')
    df_samps_2_filt.outcome = df_samps_2_filt.outcome.astype('float')
    df_samps_2_filt.pred_0 = df_samps_2_filt.pred_0.astype('float')
    
    
    df_samps_1_filt.sort_values(['id','time'], inplace = True)
    df_samps_1_filt.reset_index(inplace = True, drop = True)
    df_samps_2_filt.sort_values(['id','time'], inplace = True)
    df_samps_2_filt.reset_index(inplace = True, drop = True)
    
    if len(df_samps_1_filt.id) == len(df_samps_2_filt.id):
        if (all(df_samps_1_filt.id == df_samps_2_filt.id) and all(df_samps_1_filt.time == df_samps_2_filt.time)):
            print('preds are equal')
        else:
            print('Error: not equal preds')
    else:
        print(f'Error: different lengths {len(df_samps_1_filt.id)} {len(df_samps_2_filt.id)}')
        df_samps_1_filt = df_samps_1_filt.set_index(['id', 'time']).join(df_samps_2_filt[['id', 'time']].set_index(['id', 'time']), how='inner').reset_index()
        df_samps_2_filt = df_samps_2_filt.set_index(['id', 'time']).join(df_samps_1_filt[['id', 'time']].set_index(['id', 'time']), how='inner').reset_index()
        print(f'After intersection: {len(df_samps_1_filt.id)} {len(df_samps_2_filt.id)}')
        
    # 
    
    # keep 1 per id
    ind = np.array(df_samps_1_filt.index)
    np.random.shuffle(ind)
    df_samps_1_filt_uniq = df_samps_1_filt.iloc[ind].drop_duplicates('id').sort_values('id').reset_index(drop = True)
    df_samps_2_filt_uniq = df_samps_2_filt.iloc[ind].drop_duplicates('id').sort_values('id').reset_index(drop = True)
    
    preds_1_case = df_samps_1_filt_uniq[df_samps_1_filt_uniq.outcome == 1]['pred_0'].values
    preds_1_control = df_samps_1_filt_uniq[df_samps_1_filt_uniq.outcome == 0]['pred_0'].values
    preds_2_case = df_samps_2_filt_uniq[df_samps_2_filt_uniq.outcome == 1]['pred_0'].values
    preds_2_control = df_samps_2_filt_uniq[df_samps_2_filt_uniq.outcome == 0]['pred_0'].values
    # cases index on the row axis, and controls index on the columns
    Vmat1 = (np.vstack(preds_1_case) > preds_1_control) + 0.5*(np.vstack(preds_1_case) == preds_1_control)
    Vmat2 = (np.vstack(preds_2_case) > preds_2_control) + 0.5*(np.vstack(preds_2_case) == preds_2_control)
    
    n1 = len(preds_1_case)
    n0 = len(preds_1_control)
    
    # MES
    V11 = 1/n0* np.sum(Vmat1,axis=1)
    V10 = 1/n1* np.sum(Vmat1,axis=0)
    A1 = 1/n1*np.sum(V11)
    
    S_10 = 1/(n0 - 1)*np.sum((V10 - A1)**2)
    S_11 = 1/(n1 - 1)*np.sum((V11 - A1)**2)
    V_1 = 1/n1* S_11 +   1/n0* S_10   # Variance of predictor 1
    
    # Baseline
    V21 = 1/n0* np.sum(Vmat2,axis=1)
    V20 = 1/n1* np.sum(Vmat2,axis=0)
    A2 = 1/n1*np.sum(V21)
    
    S_20 = 1/(n0 - 1)*np.sum((V20 - A1)**2)
    S_21 = 1/(n1 - 1)*np.sum((V21 - A1)**2)
    V_2 = 1/n1* S_21 +   1/n0* S_20   # Variance of predictor 2
    
    S_1121 = 1/(n1-1)*(np.dot(V11 - A1, V21 - A2))
    S_1020 = 1/(n0-1)*(np.dot(V10 - A1, V20 - A2))
    Cov12= S_1121/n1 + S_1020/n0
    
    #
    z = (A1 - A2)/np.sqrt(V_1 + V_2 - 2*Cov12 )
    from scipy.stats import norm
    p = 1 - norm.cdf(z)
    std1 = np.sqrt(V_1)
    low_ci = A1 -1.96 * std1
    up_ci = A1 +1.96 * std1
    print(f"model 1: AUC: {A1}, Variance: {V_1}, estimated 95% CI: [{low_ci}, {up_ci}]" )
    std2 = np.sqrt(V_2)
    low_ci = A2 -1.96 * std2
    up_ci = A2 +1.96 * std2
    print(f"model 2: AUC: {A2}, Variance: {V_2}, estimated 95% CI: [{low_ci}, {up_ci}]" )
    print(f'Z - score: {z}, p-value: {p}')
    
    return z, p

if (__name__ == '__main__'): 
    calc_p_value(args.preds_file_1, args.preds_file_2, args.cohort_string)
