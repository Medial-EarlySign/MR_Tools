#!/usr/bin/env python

# Edit parameters
REQ_PARAMETERS=['WORK_DIR', 'FIRST_WORK_DIR', 'MODEL_PATH', 'CONFIG_DIR', 'CMP_FEATURE_RES']
DEPENDS=[] #4
# END edit

import os, sys
#argv[1] is config directory, argv[2] is base script directory
sys.path.insert(0, os.path.join(sys.argv[2], 'resources'))
from lib.PY_Helper import *
import med

init_env(sys.argv, locals())
test_existence(locals(), REQ_PARAMETERS , TEST_NAME)

# EXIT CODES: 0 When all OK, 1 when missing parameter, 2 when failed internal test, 3 when other error/crash
# Write you code here below:

MODEL_PATH = os.path.join(FIRST_WORK_DIR,'model', 'model.medmdl')
rep_path= os.path.join(WORK_DIR, 'rep', 'test.repository') #Path of repositroy
samples_file = os.path.join(WORK_DIR, 'Samples', '3.test_cohort.samples') #path of samples or load samples from DataFrame using: samples.from_df(dataframe_object with the right columns)

top_features = list(map(lambda x: ':'.join(x.split(':')[:-1]) ,CMP_FEATURE_RES.split(',')))
resolution_feat = list(map(lambda x: float(x.split(':')[-1]) ,CMP_FEATURE_RES.split(',')))

rep = med.PidRepository()
rep.init(rep_path) 
  
model = med.Model()
model.read_from_file(MODEL_PATH)
model.fit_for_repository(rep)
signalNamesSet = model.get_required_signal_names() #Get list of relevant signals the model needed to fetch from repository
  
samples = med.Samples()
samples.read_from_file(samples_file)
ids = samples.get_ids() #Fetch relevant ids from samples to read from repository
  
rep.read_all(rep_path, ids, signalNamesSet) #read needed repository data
  
#Apply model:
model.apply(rep, samples, 0, med.ModelStage.APPLY_FTR_GENERATORS)
df = model.features.to_df()

output=os.path.join(WORK_DIR, 'outputs', 'graphs_with_missings')
os.makedirs(output, exist_ok=True)

fw_stats=open(os.path.join(WORK_DIR, 'outputs', 'features_stats.with_missings.tsv'), 'w')
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
  
  df=df[df[exact_name]!=-65336].reset_index(drop=True)
  #fix resolution
  df[exact_name] = (df[exact_name]/resolution_feat[i]).apply(lambda x: round(x)*resolution_feat[i])
  #
  print('Cases: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(missing_df[missing_df['outcome']>0])/tot_sz_df_cases, feat, df[(df['outcome']>0)][exact_name].mean(), df[(df['outcome']>0)][exact_name].std()))
  print('Controls: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(missing_df[missing_df['outcome']==0])/tot_sz_df_controls,feat, df[(df['outcome']==0)][exact_name].mean(), df[(df['outcome']==0)][exact_name].std()))
  print('All: missing rate %2.1f%%, average %s %2.4f, std=%2.2f'%(100*len(missing_df)/tot_sz_df, feat, df[exact_name].mean(), df[exact_name].std()))  
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
  plot_graph(res, os.path.join(output, '%s.html'%(feat)), mode='markers+lines', plotly_js_path = os.path.join('..', '..', 'js', 'plotly.js'))
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