#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['WORK_DIR', 'CONFIG_DIR']
DEPENDS=[5, 6] # Dependency test
# End edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import traceback
import pandas as pd
import numpy as np

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

print(f'Please refer to {WORK_DIR} for coverage test')

input_cutoff=[1,3,5,10] #In positive rate (percentage)
code_exec = os.path.join(CONFIG_DIR, 'coverage_groups.py')
if not(os.path.exists(code_exec)):
  raise NameError('Please generate code file in %s - that fills dictionary "cohort_f" with filters on "df" -dataframe object. You can use "getcol" function to retrieve columns'%(code_exec))

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
print('tot size test %d'%(tot_df_sz))
print('tot size in reference %d'%(ref_tot_sz))

df=df.set_index(['id', 'outcome']).join(df_ids.set_index(['id', 'outcome']), how='inner').reset_index()
ref_df=ref_df.set_index(['id', 'outcome']).join(df_ids.set_index(['id', 'outcome']), how='inner').reset_index()

if len(df)!=tot_df_sz:
  raise NameError('miss')
df=df.set_index(['str_attr_original_id', 'time']).join(scores.set_index(['str_attr_original_id', 'time']), how='inner').reset_index()
ref_df=ref_df.set_index(['str_attr_original_id', 'time']).join(ref_scores.set_index(['str_attr_original_id', 'time']), how='inner').reset_index()
if len(df)!=tot_df_sz:
  raise NameError('miss2')

cutoffs= np.array(input_cutoff)
score_cutoff=df['pred_0'].quantile(q=1-(cutoffs/100))
score_cutoff=pd.DataFrame({'prc': score_cutoff.index, 'score': score_cutoff.values})

cohort_f=dict()

#Execute code from 
of = open(code_exec, 'r')
code_txt=of.read()
of.close()
try:
  print('Defining groups from %s'%(code_exec))
  exec(code_txt, globals(), locals())
except:
  print('Error in excution of code, please fix')
  print(traceback.format_exc())
  sys.exit(-1)
  
#store also conditions on ref_df:
cohort_f_ref=dict()
code_txt_ref=code_txt.replace('cohort_f', 'cohort_f_ref').replace('df.', 'ref_df.').replace('df[', 'ref_df[')
try:
  exec(code_txt_ref, globals(), locals())
except:
  print('Error in excution of code for ref, please fix')
  print(traceback.format_exc())

print('#########################################################################')
for cohort_name, filter_cond in cohort_f.items():
  cohort=df[filter_cond].reset_index(drop=True)
  sz=len(cohort)
  ref_cohort=None
  ref_sz=None
  if cohort_name in cohort_f_ref:
    ref_filter_cond=cohort_f_ref[cohort_name]
    ref_cohort=ref_df[ref_filter_cond].reset_index(drop=True)
    ref_sz=len(ref_cohort)
  
  if ref_cohort is None:
    print('Cohort %s :: Has %d patient in cohort out of %d (%2.1f%%)'%(cohort_name, sz, len(df), sz/len(df)*100))
  else:
    print('Cohort|reference %s :: Has %d|%d patient in cohort out of %d|%d (%2.1f%%|%2.1f%%)'%( \
        cohort_name, sz, ref_sz, len(df), len(ref_df), sz/len(df)*100, 100*ref_sz/len(ref_df) ) )
  
  #Analyze in different cutoff
  for i in range(len(score_cutoff)):
    covered=len(cohort[cohort['pred_0']>= score_cutoff.iloc[i]['score']])
    total_mark=len(df[df['pred_0']>= score_cutoff.iloc[i]['score']])
    if sz == 0:
        continue #Empty cohort
    if ref_cohort is None or ref_sz == 0:
      print('Analyze cutoff %2.1f%% with score %2.5f => covered %d (%2.1f%%), total_flag %d (%2.1f%%), %2.1f%% has condition in flagged. Lift=%2.1f'%( 100-score_cutoff.iloc[i]['prc']*100, score_cutoff.iloc[i]['score'],
      covered, 100*covered/sz,total_mark, 100*total_mark/tot_df_sz, 100*covered/total_mark, covered/sz/(total_mark/tot_df_sz) ))
    else:
      ref_cov=len(ref_cohort[ref_cohort['pred_0']>= score_cutoff.iloc[i]['score']])
      ref_tot_mark=len(ref_df[ref_df['pred_0']>= score_cutoff.iloc[i]['score']])
      print('Analyze cutoff %2.1f%% with score %2.5f => covered %d (%2.1f%%|%2.1f%%), total_flag %d (%2.1f%%|%2.1f%%), %2.1f%%|%2.1f%% has condition in flagged. Lift=%2.1f|%2.1f'%( 100-score_cutoff.iloc[i]['prc']*100, score_cutoff.iloc[i]['score'],
      covered, 100*covered/sz, 100*ref_cov/ref_sz,total_mark , 100*total_mark/tot_df_sz, 100*ref_tot_mark/ref_tot_sz, \
       100*covered/total_mark, 100*ref_cov/ref_tot_mark , covered/sz/(total_mark/tot_df_sz) , ref_cov/ref_sz/(ref_tot_mark/ref_tot_sz) ))
  print('#########################################################################')
