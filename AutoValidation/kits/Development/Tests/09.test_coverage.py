#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['WORK_DIR', 'REPOSITORY_PATH', 'MODEL_PATH', 'TEST_SAMPLES']
DEPENDS=[] # Dependency tests
# End Edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import numpy as np
import pandas as pd
import traceback

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

input_cutoff=[1,3,5,10] #In positive rate (percentage)
code_exec = os.path.join(CONFIG_DIR, 'coverage_groups.py')
if not(os.path.exists(code_exec)):
  raise NameError('Please generate code file in %s - that fills dictionary "cohort_f" with filters on "df" -dataframe object. You can use "getcol" function to retrieve columns'%(code_exec))

BS=os.path.join(WORK_DIR, 'outputs')
os.makedirs(BS, exist_ok=True)
#feat_matrix=os.path.join(BS,'features.matrix')
df = get_matrix(REPOSITORY_PATH, MODEL_PATH, TEST_SAMPLES)
#if not(os.path.exists(feat_matrix)):
#    df = get_matrix(REPOSITORY_PATH, MODEL_PATH, TEST_SAMPLES)
    #matrix.write_as_csv_mat(feat_matrix)
#    df.to_csv(feat_matrix)
#else:
#    df=pd.read_csv(feat_matrix)

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
  traceback.print_exc()
  sys.exit(-1)

tot_df_sz=len(df)
print('#########################################################################')
for cohort_name, filter_cond in cohort_f.items():
  cohort=df[filter_cond].reset_index(drop=True)
  sz=len(cohort)
  print('Cohort %s :: Has %d patient in cohort out of %d (%2.1f%%)'%(cohort_name, sz, len(df), sz/len(df)*100))
  #Analyze in different cutoff
  for i in range(len(score_cutoff)):
    covered=len(cohort[cohort['pred_0']>= score_cutoff.iloc[i]['score']])
    total_mark=len(df[df['pred_0']>= score_cutoff.iloc[i]['score']])
    if sz ==0:
        continue
    print('Analyze cutoff %2.1f%% with score %2.5f => covered %d (%2.1f%%), total_flag %d (%2.1f%%), %2.1f%% has condition in flagged. Lift=%2.1f'%( 100-score_cutoff.iloc[i]['prc']*100, score_cutoff.iloc[i]['score'],
    covered, 100*covered/sz,total_mark, 100*total_mark/tot_df_sz, 100*covered/total_mark, covered/sz/(total_mark/tot_df_sz) ))
  print('#########################################################################')

