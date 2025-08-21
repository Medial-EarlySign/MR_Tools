import sys, os, re, time
import pandas as pd
import numpy as np
from Configuration import Configuration

ratio=[0.7,0.2]

cfg = Configuration()
out_folder = cfg.work_dir

prev_train = cfg.prev_train if 'prev_train' in Configuration.__dict__.values() else None
tr_df=pd.DataFrame({'pid':[], 'val':[]}, dtype=int)
old_ids=[]
if prev_train is not None:
    print('Using old training file %s'%(prev_train))
    tr_df=pd.read_csv(prev_train, sep='\t', usecols=[0,2], names=['pid', 'val'], dtype={'pid': int, 'val': int})
    old_ids = tr_df['pid'].unique()
else:
    print('Creating TRAIN from zero. please define prev_train in Configuration to use old training')

#Get ids from BYEAR:
byear_df=pd.read_csv(os.path.join(cfg.work_dir, 'FinalSignals', 'BYEAR'), sep='\t', usecols=[0], names=['pid'], dtype={'pid': int})
#print(byear_df.head())

cur_ids = byear_df['pid'].unique()

to_divide_list = list(set(cur_ids) - set(old_ids))
in_both = list(set(cur_ids) & set(old_ids))
num_of_pids=len(cur_ids)

for i,r in enumerate( ratio):
    grp_cnt= len(tr_df[(tr_df['pid'].isin(in_both)) & (tr_df['val']==(i+1))]) 
    goal_cnts= int(num_of_pids*r) 
    missing_cnt=goal_cnts-grp_cnt
    if missing_cnt < 0:
        raise NameError('In group %d, have already too many values in this category'%(i))
    if missing_cnt > 0:
        choosed_ids=np.random.choice(to_divide_list, missing_cnt, replace=False)
        grp_df=pd.DataFrame({'pid':choosed_ids}, dtype=int)
        grp_df['val']=i+1
        tr_df=tr_df.append(grp_df, ignore_index=True)
        to_divide_list=list(set(to_divide_list) - set(choosed_ids))
        print('Added %d pids to group %d (%2.3f%%), had %d before'%(len(choosed_ids), i+1, float(len(choosed_ids)*100.0)/num_of_pids , grp_cnt), flush=True)

#Add last group:
if (len(to_divide_list) > 0):
    grp_df=pd.DataFrame({'pid':to_divide_list})
    grp_df['val']=len(ratio)+1
    tr_df=tr_df.append(grp_df, ignore_index=True)
    print('Added %d pids to group %d (%2.3f%%)'%(len(to_divide_list), len(ratio)+1, float(len(to_divide_list)*100.0)/num_of_pids), flush=True)


tr_df['signal'] = 'TRAIN'
tr_df=tr_df[['pid', 'signal', 'val']]
tr_df.sort_values(by='pid', inplace=True)
tr_df.to_csv(os.path.join(out_folder, 'FinalSignals', 'TRAIN'), sep='\t', index=False, header=False)
