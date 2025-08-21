import os
import sys
import pandas as pd
import numpy as np
from utils import write_tsv


def create_train_signal(cfg, old_train_path=None):
    sig = 'TRAIN'
    out_folder = cfg.work_path
    curr_id2inr = os.path.join(out_folder, 'BYEAR')
    tr_df = pd.DataFrame({'pid': [], 'val': []})
    if old_train_path is not None:
        for old_train_p in old_train_path:
            tr_df_tmp = pd.read_csv(old_train_p, sep='\t', usecols=[0,2], names=['pid', 'val'], dtype={'pid': int, 'val': int})
            tr_df = pd.concat([tr_df, tr_df_tmp])
    old_ids = tr_df['pid'].unique()

    cur_id2nr = pd.read_csv(curr_id2inr, sep='\t', names=['medialid', 'signal', 'byear'], usecols=['medialid'], dtype={'medialid': int})
    cur_ids = cur_id2nr['medialid'].unique()
    
    not_in_cur = list(set(old_ids) - set(cur_ids)) #not need to load - not used anymore
    only_in_new = list(set(cur_ids) - set(old_ids))
    in_both = list(set(cur_ids) & set(old_ids))

    per70 = int(len(only_in_new)*0.7)
    per20 = int(len(only_in_new)*0.2)

    list1 = np.random.choice(only_in_new, per70, replace=False)
    df1 = pd.DataFrame(list1)
    df1['val'] = 1

    remain = list(set(only_in_new) - set(list1))
    list2 = np.random.choice(remain, per20, replace=False)
    df2 = pd.DataFrame(list2)
    df2['val'] = 2

    remain2 = list(set(remain) - set(list2))
    df3 = pd.DataFrame(remain2)
    df3['val'] = 3

    new_df = pd.concat([df1, df2, df3])
    new_df.rename({0: 'pid'}, inplace=True, axis=1)
    
    tr_df = tr_df[tr_df['pid'].isin(in_both)]
    tr_df = pd.concat([tr_df, new_df])

    tr_df['signal'] = sig
    tr_df['pid'] = tr_df['pid'].astype(int)
    tr_df['val'] = tr_df['val'].astype(int)
    if os.path.exists(os.path.join(out_folder, 'FinalSignals', sig)):
        print('Override exisinting Train')
        os.remove(os.path.join(out_folder, 'FinalSignals', sig))
    tr_df = tr_df[['pid', 'signal', 'val']].sort_values(by='pid').reset_index(drop=True)
    write_tsv(tr_df, os.path.join(out_folder, 'FinalSignals'), sig)
