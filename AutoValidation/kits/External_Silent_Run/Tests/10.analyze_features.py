#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['WORK_DIR', 'CMP_FEATURE_RES']
DEPENDS=[5] # Dependency test
# End Edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import pandas as pd

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

print(f'Please refer to {WORK_DIR} to see feature diff for run VS silence run')

def fix_feat_names1(s):
    categs=['ICD9_CODE', 'ICD10_CODE', 'ATC_CODE']
    for c in categs:
        s=s.replace(c+':', c+'_')
    return s
def fix_feat_names2(s):
    categs=['ICD9_CODE', 'ICD10_CODE', 'ATC_CODE']
    for c in categs:
        s=s.replace(c+'_', c+':')
    return s

#obj is single dataframe with 2 columns, or dict of dataaframes with 2 cols each

df=pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity.matrix'))
df_non_norm=pd.read_csv(os.path.join(WORK_DIR, 'compare', 'rep_propensity_non_norm.matrix'))
df_non_norm=df_non_norm[df_non_norm['outcome']>0].reset_index(drop=True)

output=os.path.join(WORK_DIR, 'features_graphs')
os.makedirs(output, exist_ok=True)

feat_res=CMP_FEATURE_RES.split(',')
fw_stats=open(os.path.join(WORK_DIR, 'features_stats.tsv'), 'w')
fw_stats.write('Feature\tReference_Mean\tReference_Std\tReference_Missing_value_percent\tTestRun_Mean\tTestRun_Std\tTestRun_Missing_value_percent\tTestRun_Missing_value_before_norm\n')

features= list(map(lambda x: fix_feat_names2(fix_feat_names1(x).split(':')[0]), feat_res))
reso=list(map(lambda x: float(x.split(':')[-1]), feat_res))
full=df.copy()
for i,feat in enumerate(features):
  res=dict()
  exact_name=list(filter(lambda x: x.find(feat)>=0, df.columns))
  if len(exact_name)!=1:
    print(list(df.columns))
    raise NameError('Found %d features for %s'%(len(exact_name), feat))
  exact_name=exact_name[0]
  df=full.copy()
  #df=df[df[exact_name]>=0].reset_index(drop=True)
  missing_df=df[(df['outcome']==0) & (df[exact_name]==-65336)]
  missing_df2=df[(df['outcome']>0) & (df[exact_name]==-65336)]
  df1=df[df[exact_name]!=-65336].reset_index(drop=True).copy()
  df[exact_name]=(df[exact_name].astype(float)/reso[i]).astype(int).astype(float)*reso[i]
  tot_sz_df=len(df[df['outcome']==0])
  fw_stats.write('%s\t%2.4f\t%2.2f\t%2.2f'%(exact_name, df1[df1['outcome']==0][exact_name].mean(), df1[df1['outcome']==0][exact_name].std(), 100*len(missing_df)/tot_sz_df))
  tot_sz_df=len(df[df['outcome']>0])
  
  missing_df1=df_non_norm[df_non_norm[exact_name]==-65336]
  fw_stats.write('\t%2.4f\t%2.2f\t%2.2f\t%2.2f%%\n'%(df1[df1['outcome']>0][exact_name].mean(), df1[df1['outcome']>0][exact_name].std(), 100*len(missing_df2)/tot_sz_df, 100*len(missing_df1)/tot_sz_df))
  df=df1
  
  print('Test_Run:Males average %s %2.1f, std=%2.1f'%(feat, df[(df['Gender']==1) & (df['outcome']>0)][exact_name].mean(), df[(df['Gender']==1) & (df['outcome']>0)][exact_name].std()))
  print('Test_Run:Females average %s %2.1f, std=%2.1f'%(feat, df[(df['Gender']==2) & (df['outcome']>0)][exact_name].mean(), df[(df['Gender']==2) & (df['outcome']>0)][exact_name].std()))
  print('Reference:Males average %s %2.1f, std=%2.1f'%(feat, df[(df['Gender']==1) & (df['outcome']==0)][exact_name].mean(), df[(df['Gender']==1) & (df['outcome']==0)][exact_name].std()))
  print('Reference:Females average %s %2.1f, std=%2.1f'%(feat, df[(df['Gender']==2) & (df['outcome']==0)][exact_name].mean(), df[(df['Gender']==2) & (df['outcome']==0)][exact_name].std()))

  res['Test_Run:Males']=df[(df['outcome']>0) & (df['Gender']==1)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'})
  res['Test_Run:Females']=df[(df['outcome']>0) & (df['Gender']==2)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'})
  res['Reference:Males']=df[(df['outcome']==0) & (df['Gender']==1)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'})
  res['Reference:Females']=df[(df['outcome']==0) & (df['Gender']==2)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'})
  res['Test_Run:Males']['count']=100*res['Test_Run:Males']['count']/res['Test_Run:Males']['count'].sum()
  res['Test_Run:Females']['count']=100*res['Test_Run:Females']['count']/res['Test_Run:Females']['count'].sum()
  res['Reference:Males']['count']=100*res['Reference:Males']['count']/res['Reference:Males']['count'].sum()
  res['Reference:Females']['count']=100*res['Reference:Females']['count']/res['Reference:Females']['count'].sum()
  for nm,df_ in res.items():
      res[nm]=df_.rename(columns={'count':'percentage(%)'})
  plot_graph(res, os.path.join(output, '%s.html'%(feat)), mode='bar', plotly_js_path = os.path.join('..', 'js', 'plotly.js'))
  df1=df[(df['outcome']>0)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'}).copy()
  df1['p']=df1['count']/df1['count'].sum()
  df2=df[(df['outcome']==0)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'}).copy()
  df2['p']=df2['count']/df2['count'].sum()
  #breakpoint()
  bin_cnt,kld,kld_uniform, p_entory= calc_kld(df1 ,df2 , exact_name, 'p')
  print('%s:: KLD(%d)=%2.1f, uniform=%2.1f, entropy=%2.1f'%(feat, bin_cnt, kld, kld_uniform, p_entory))
  print('#########################################################')
fw_stats.close()