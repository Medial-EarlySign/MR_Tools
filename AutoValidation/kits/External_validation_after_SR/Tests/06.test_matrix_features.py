#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['WORK_DIR', 'FIRST_WORK_DIR', 'MODEL_PATH', 'REFERENCE_MATRIX', 'CONFIG_DIR']
DEPENDS=[] # Silent run 13
# END.

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import pandas as pd

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

MODEL_PATH = os.path.join(FIRST_WORK_DIR,'model', 'model.medmdl')

shap_report=os.path.join(FIRST_WORK_DIR, 'ButWhy', 'shapley.report')
if not(os.path.exists(shap_report)):
    raise NameError('Please run ButWhy analysis before... We want to analyze most important features based on it')

resolution_file=os.path.join(CONFIG_DIR, 'feat_resolution.tsv')
resolution_df=None
if not(os.path.exists(resolution_file)):
    print('INFO :: if you want to provide limitation for features print - please create file under %s'%(resolution_file))
    print('INFO ::  file format is tab delimited with - Feature, resolution, trim_min, trim_max - some can be empty')
else:
    resolution_df=pd.read_csv(resolution_file, sep='\t')
#Read Shapley file
feat_importance=pd.read_csv(shap_report, sep='\t', usecols=['Feature', 'Importance'])
feat_importance=feat_importance[feat_importance['Importance']>0].reset_index(drop=True)
top_features=list(feat_importance.head(25)['Feature'].values)
top_features.append('pred_0')

#Get matrix
REPOSITORY_PATH=os.path.join(WORK_DIR, 'rep', 'test.repository')
df = get_matrix(REPOSITORY_PATH, MODEL_PATH, os.path.join(WORK_DIR, 'Samples', '3.test_cohort.samples'))

ref_df = pd.read_csv(REFERENCE_MATRIX)

output=os.path.join(WORK_DIR, 'outputs', 'graphs')
os.makedirs(output, exist_ok=True)

if resolution_df is not None:
    feat_idx = resolution_df.columns.get_loc('Feature')
    for i in range(len(resolution_df)):
        fname=resolution_df.iloc[i]['Feature']
        exact_name=list(filter(lambda x: x.find(fname)>=0, df.columns))
        if len(exact_name)!=1:
            print(list(df.columns))
            raise NameError('Resulotion config file: Found %d features for %s'%(len(exact_name), fname))
        fname=exact_name[0]
        resolution_df.iloc[i, feat_idx]=fname
        
fw_stats=open(os.path.join(WORK_DIR, 'outputs', 'features_stats.tsv'), 'w')
fw_stats.write('Feature\tMean\tStd\tMissing_value_percent\tCases_Mean\tCases_Std\tCases_Missing_value_percent\tControls_Mean\tControls_Std\tControls_Missing_value_percent\n')
full=df.copy()
for i,feat in enumerate(top_features):
  res=dict()
  exact_name=list(filter(lambda x: x.find(feat)>=0, df.columns))
  if len(exact_name)!=1:
    print(list(df.columns))
    raise NameError('Found %d features for %s'%(len(exact_name), feat))
  exact_name=exact_name[0]
  df=full.copy()
  tot_sz_df=len(df)
  tot_sz_df_cases=len(df[df['outcome']>0])
  tot_sz_df_controls=len(df[df['outcome']==0])
  missing_df=df[df[exact_name]==-65336]
  
  ref_data=ref_df.copy()
  ref_tot_sz_df=len(ref_data)
  ref_tot_sz_df_cases=len(ref_data[ref_data['outcome']>0])
  ref_tot_sz_df_controls=len(ref_data[ref_data['outcome']==0])
  ref_missing_df=ref_data[ref_data[exact_name]==-65336]
  
  df=df[df[exact_name]!=-65336].reset_index(drop=True)
  ref_data=ref_data[ref_data[exact_name]!=-65336].reset_index(drop=True)
  if (resolution_df is not None) and len(resolution_df[resolution_df['Feature']==exact_name])>0:
    min_trim=resolution_df[resolution_df['Feature']==exact_name]['trim_min']
    if not(min_trim is None) and len(str(min_trim))>0:
        #breakpoint()
        min_trim=float(min_trim)
        df.loc[ df[exact_name] < min_trim ,exact_name]=min_trim
        ref_data.loc[ ref_data[exact_name] < min_trim ,exact_name]=min_trim
    max_trim=resolution_df[resolution_df['Feature']==exact_name]['trim_max']
    if not(max_trim is None) and len(str(max_trim))>0:
        max_trim=float(max_trim)
        df.loc[ df[exact_name] > max_trim ,exact_name]=max_trim
        ref_data.loc[ ref_data[exact_name] > max_trim ,exact_name]=max_trim
    reso_f=resolution_df[resolution_df['Feature']==exact_name]['resolution']
    if not(reso_f is None) and len(str(reso_f))>0:
        reso_f=float(reso_f)
        df[exact_name]=(df[exact_name].astype(float)/reso_f).astype(int).astype(float)*reso_f
        ref_data[exact_name]=(ref_data[exact_name].astype(float)/reso_f).astype(int).astype(float)*reso_f
  else:
    if exact_name=='pred_0':
        reso_f=0.001 #Default
        df[exact_name]=(df[exact_name].astype(float)/reso_f).astype(int).astype(float)*reso_f
        ref_data[exact_name]=(ref_data[exact_name].astype(float)/reso_f).astype(int).astype(float)*reso_f
  
  #
  print('Cases: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(missing_df[missing_df['outcome']>0])/tot_sz_df_cases, feat, df[(df['outcome']>0)][exact_name].mean(), df[(df['outcome']>0)][exact_name].std()))
  print('Controls: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(missing_df[missing_df['outcome']==0])/tot_sz_df_controls,feat, df[(df['outcome']==0)][exact_name].mean(), df[(df['outcome']==0)][exact_name].std()))
  print('All: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(missing_df)/tot_sz_df, feat, df[exact_name].mean(), df[exact_name].std()))
  print('Reference Cases: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(ref_missing_df[ref_missing_df['outcome']>0])/ref_tot_sz_df_cases, feat, ref_data[(ref_data['outcome']>0)][exact_name].mean(), ref_data[(ref_data['outcome']>0)][exact_name].std()))
  print('Reference Controls: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(ref_missing_df[ref_missing_df['outcome']==0])/ref_tot_sz_df_controls,feat, ref_data[(ref_data['outcome']==0)][exact_name].mean(), ref_data[(ref_data['outcome']==0)][exact_name].std()))
  print('Reference All: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(ref_missing_df)/ref_tot_sz_df, feat, ref_data[exact_name].mean(), ref_data[exact_name].std()))
  fw_stats.write('%s\t%2.4f\t%2.2f\t%2.2f\t%2.4f\t%2.2f\t%2.2f\t%2.4f\t%2.2f\t%2.2f\n'%(exact_name, df[exact_name].mean(), df[exact_name].std(), 100*len(missing_df)/tot_sz_df,
                                                                                         df[(df['outcome']>0)][exact_name].mean(), df[(df['outcome']>0)][exact_name].std(), 100*len(missing_df[missing_df['outcome']>0])/tot_sz_df_cases,
                                                                                        df[(df['outcome']==0)][exact_name].mean(), df[(df['outcome']==0)][exact_name].std(), 100*len(missing_df[missing_df['outcome']==0])/tot_sz_df_controls))

  res['Cases']=df[(df['outcome']>0)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'})
  res['Controls']=df[(df['outcome']==0)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'})
  res['All']=df[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'})
  res['Cases']['count']=100*res['Cases']['count']/res['Cases']['count'].sum()
  res['Controls']['count']=100*res['Controls']['count']/res['Controls']['count'].sum()
  res['All']['count']=100*res['All']['count']/res['All']['count'].sum()
  
  for nm,df_ in res.items():
      res[nm]=df_.rename(columns={'count':'percentage(%)'})
  plot_graph(res, os.path.join(output, '%s.html'%(feat)), mode='bar', plotly_js_path = os.path.join('..','..', 'js', 'plotly.js'))
  df1=df[(df['outcome']>0)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'}).copy()
  df1['p']=df1['count']/df1['count'].sum()
  df2=df[(df['outcome']==0)].reset_index(drop=True)[[exact_name, 'id']].groupby(exact_name).count().reset_index().rename(columns={'id':'count'}).copy()
  df2['p']=df2['count']/df2['count'].sum()
  #breakpoint()
  bin_cnt,kld,kld_uniform, p_entory= calc_kld(df1 ,df2 , exact_name, 'p')
  print('%s:: KLD(%d)=%2.1f, uniform=%2.1f, entropy=%2.1f'%(feat, bin_cnt, kld, kld_uniform, p_entory))
  print('#########################################################')
fw_stats.close()

print(f'Please refer to {WORK_DIR}')
print('Additional log message')