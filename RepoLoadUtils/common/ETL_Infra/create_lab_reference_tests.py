#!/bin/python
import med, os
import pandas as pd

from .define_signals import _read_signals_map
from .env import *

ref_rep='/home/Repositories/MHS/build_Feb2016_Mode_3/maccabi.repository'
rep=med.PidRepository()
q_diff=0.1
q_diff_end=0.01
q_list=[0.001,0.01,0.1,0.5,0.9,0.99,0.999]
q_list.append(0.5-q_diff)
q_list.append(0.99-q_diff_end)

#print(os.path.abspath( os.path.dirname(__file__)))
#exit(0)

rep.read_all(ref_rep, [], [])

#Intersect with known "labs" signals:
sig_types=_read_signals_map(FULL_SIGNALS_TYPES)
labs_sigs=list(filter(lambda x: 'labs' in x.classes, sig_types.values()))
labs_sigs=set(map(lambda x: x.name, labs_sigs))

sig_list=rep.list_signals()
remove_list=['BDATE', 'BYEAR', 'DEATH', 'GENDER', 'TRAIN']
sig_list=list(filter(lambda x: x in labs_sigs ,sig_list))

all_sigs=[]
for sig_name in sig_list:
    print(f'Fetching stats for {sig_name}', flush=True)
    sig=rep.get_sig(sig_name).rename(columns={'val':'value_0', 'val0':'value_0'})
    sig=sig[sig['value_0']>0].reset_index(drop=True)
    res=pd.DataFrame(sig['value_0'].quantile(q_list).reset_index()).rename(columns={'index':'q'})
    
    median=res[res['q']==0.5]['value_0'].iloc[0]
    min_range=res[res['q']==0.5-q_diff]['value_0'].iloc[0]
    diff_res=median-min_range
    
    high_p=res[res['q']==0.99]['value_0'].iloc[0]
    min_high_p=res[res['q']==0.99-q_diff_end]['value_0'].iloc[0]
    diff_res_high=high_p-min_high_p
    #Generate config file with the signal parameter to compare with - as dataframe
    res['signal']=sig_name
    res=res[['signal', 'q', 'value_0']]
    all_sigs.append(res)
full_cfg=pd.concat(all_sigs, ignore_index=True)
#Store config file in disk:
full_file_pt=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'rep_signals', 'signals_prctile.cfg')
full_cfg.to_csv(full_file_pt, sep='\t', index=False)
print(f'Stored cfg file for signals in {full_file_pt}', flush=True)