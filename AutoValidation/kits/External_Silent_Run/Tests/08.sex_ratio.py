#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['WORK_DIR', 'SCORE_MIN_RANGE', 'SCORE_MAX_RANGE']
DEPENDS=[5, 6] # Dependency test
# End edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import pandas as pd
import numpy as np

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

print(f'Please refer to {WORK_DIR} for sex ratio')

df=pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity_non_norm.matrix'))
df_ids=pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity.matrix'), usecols=['outcome', 'id', 'str_attr_original_id'])
scores=pd.read_csv(os.path.join(WORK_DIR, 'compare', '3.test_cohort.preds'), sep='\t')
ref_scores=pd.read_csv(os.path.join(WORK_DIR, 'compare', 'reference.preds'), sep='\t')

scores=scores[['id', 'time', 'pred_0']].rename(columns={'id':'str_attr_original_id'})
ref_scores=ref_scores[['id', 'time', 'pred_0']].rename(columns={'id':'str_attr_original_id'})

ref_df=df[df.outcome==0].reset_index(drop=True).copy()
df=df[df.outcome>0].reset_index(drop=True)
tot_df_sz=len(df)
ref_tot_sz=len(ref_df)
print('tot size in test %d'%(tot_df_sz))
print('tot size in reference %d'%(ref_tot_sz))
df=df.set_index(['id', 'outcome']).join(df_ids.set_index(['id', 'outcome']), how='inner').reset_index()
ref_df=ref_df.set_index(['id', 'outcome']).join(df_ids.set_index(['id', 'outcome']), how='inner').reset_index()
if len(df)!=tot_df_sz:
  raise NameError('miss')
df=df.set_index(['str_attr_original_id', 'time']).join(scores.set_index(['str_attr_original_id', 'time']), how='inner').reset_index()
ref_df=ref_df.set_index(['str_attr_original_id', 'time']).join(ref_scores.set_index(['str_attr_original_id', 'time']), how='inner').reset_index()
if len(df)!=tot_df_sz:
  raise NameError('miss2')

SCORE_SZ=100
score_cutoff=np.array([] + [i for i in range(int(float(SCORE_MIN_RANGE)*SCORE_SZ),int(float(SCORE_MAX_RANGE)*SCORE_SZ))]) /SCORE_SZ

score_cutoff=pd.DataFrame({ 'score': score_cutoff}).sort_values('score').reset_index(drop=True)

print('#########################################################################')
#Analyze in different cutoff
for i in range(len(score_cutoff)):
  flagged_males=len(df[(df['pred_0']>= score_cutoff.iloc[i]['score']) & (df['Gender']==1)])
  total_mark=len(df[df['pred_0']>= score_cutoff.iloc[i]['score']])
  ref_fl_males=len(ref_df[(ref_df['pred_0']>= score_cutoff.iloc[i]['score']) & (ref_df['Gender']==1)])
  ref_tot_marked=len(ref_df[ref_df['pred_0']>= score_cutoff.iloc[i]['score']])
  if total_mark >0:
    print('Analyze cutoff of score %2.5f (test|ref) => males ratio (%2.1f%%|%2.1f%%), total_flag %d (%2.1f%%|%2.1f%%)'%(score_cutoff.iloc[i]['score'],
     100*flagged_males/total_mark, 100*ref_fl_males/ref_tot_marked ,total_mark, 100*total_mark/tot_df_sz, 100*ref_tot_marked/ref_tot_sz  ))
print('#########################################################################')
