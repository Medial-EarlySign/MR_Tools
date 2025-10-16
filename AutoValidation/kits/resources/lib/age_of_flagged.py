#!/usr/bin/env python
import os, sys, math
import pandas as pd
import numpy as np
from PY_Helper import *

init_env(sys.argv, locals())

#Test for parameters
REQ_PARAMETERS = ['WORK_DIR']
res = test_existence(locals(), REQ_PARAMETERS, test_name='age_of_flagged.sh')
if not(res):
    sys.exit(1)

if len(sys.argv)<=4:
    raise NameError('Missing argument for mode (=cohort name)')
mode = sys.argv[4].lower()

has_alt='ALT_PREDS_PATH' in locals()
if mode == 'all':
    has_alt='ALT_PREDS_PATH2' in locals()
    if has_alt:
        ALT_PREDS_PATH = ALT_PREDS_PATH2
if not(has_alt):
    print('No comparator predictions => no graphs for comparator for cohort', mode)
#read predictions
mes = pd.read_csv(os.path.join(WORK_DIR, 'bootstrap', mode + '.preds'), sep='\t')
if has_alt:
    plco = pd.read_csv(ALT_PREDS_PATH, sep='\t')
print('finish reading predictions')

if len(mes) == 0:
    print('empty - cohort => done here')
else:
    mes = mes.sample(frac=1).drop_duplicates(subset='id')
    if has_alt:
        plco = plco.drop(columns='outcome').merge(mes[['id', 'time', 'outcome']], on=['id', 'time'], how='inner')
        if len(mes) > len(plco):
            raise NameError(f'missing comparator predictions MES has {len(mes)}, comparator has {len(plco)}') 

    #bring age

    mat = pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity.matrix'), usecols=['outcome', 'time', 'str_attr_original_id', 'Age'])
    mat.rename(columns={'str_attr_original_id':'id'}, inplace=True)

    print('finish reading mat to bring Age')

    # split cases/controls and sort by score

    all_mes = mes.merge(mat.drop(columns=['outcome']), on=['id', 'time'], how='inner').sort_values(by='pred_0', ascending=False).reset_index(drop=True)
    ctrls_mes = all_mes[all_mes.outcome == 0].reset_index(drop=True)
    cases_mes = all_mes[all_mes.outcome == 1].reset_index(drop=True)
    if has_alt:
        all_plco = plco.merge(mat.drop(columns=['outcome']), on=['id', 'time'], how='inner').sort_values(by='pred_0', ascending=False).reset_index(drop=True)
        ctrls_plco = all_plco[all_plco.outcome == 0].reset_index(drop=True)
        cases_plco = all_plco[all_plco.outcome == 1].reset_index(drop=True)

    def get_avg_age(df):
        df = df.reset_index(drop=True).reset_index().rename(columns={'index':'TopN'})
        df['TopN'] += 1
        df['PR'] = 100 * df['TopN'] / len(df)
        df['age_sum'] = df.Age.cumsum()
        df['age_mean'] = df.age_sum / df.TopN
        # Dilute take only 1-100
        Target_PR=np.array(range(1,101))
        Target_PR = np.round(Target_PR/100*len(df))
        Target_PR[Target_PR >= len(df)] = len(df)-1
        df = df.iloc[Target_PR]
        
        return df[['PR', 'age_mean']]

    def output_res(mes_df, plco_df = None, grp='cases'):
        res = dict()
        if len(mes_df):
            res['MES'] = get_avg_age(mes_df)
            if plco_df is not None:
                res['PLCO'] = get_avg_age(plco_df)
            
            plot_graph(res, os.path.join(WORK_DIR, 'age_of_flagged', mode + f'.{grp}.html'), mode='lines+markers', plotly_js_path=os.path.join(WORK_DIR, 'js', 'plotly.js'))
            df=res['MES'].copy()
            df= df.rename(columns={'age_mean': 'MES_age_Mean'})
            df2= res['PLCO'].copy()
            df2= df2.rename(columns={'age_mean': 'PLCO_age_Mean'}).drop(columns=['PR'])
            df = pd.concat([df, df2], axis=1, ignore_index=False)
            df.to_csv( os.path.join(WORK_DIR, 'age_of_flagged', mode + f'.{grp}.tsv'), sep='\t', index=False)
    #output - cases
    output_res(cases_mes, cases_plco if has_alt else None, 'cases')
    #output - controls
    output_res(ctrls_mes, ctrls_plco if has_alt else None, 'controls')
    #All
    output_res(all_mes, all_plco if has_alt else None, 'all')
   