import sys, os, re, time
import pandas as pd
import numpy as np
from Configuration import Configuration
from const_and_utils import fixOS


cfg = Configuration()
out_folder = fixOS(cfg.work_path)

prev_id2inr = fixOS(cfg.prev_id2ind)
curr_id2inr = os.path.join(out_folder, 'ID2NR')
old_train = os.path.join(out_folder, 'TRAIN18')
print(old_train)
tr_df = pd.read_csv(old_train, sep='\t', usecols=[0,2], names=['pid', 'val'], dtype={'pid': int, 'val': int})
old_ids = tr_df['pid'].unique()

#old_id2nr = pd.read_csv(prev_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
#old_ids = old_id2nr['medialid'].unique()
#del old_id2nr

cur_id2nr = pd.read_csv(curr_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
cur_ids = cur_id2nr['medialid'].unique()
del cur_id2nr

not_in_cur = list(set(old_ids) - set(cur_ids))
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
tr_df['signal'] = 'TRAIN'
tr_df.sort_values(by='pid', inplace=True) 
tr_df[['pid', 'signal', 'val']].to_csv(os.path.join(out_folder, 'FinalSignals', 'TRAIN'), sep='\t', index=False, header=headers, mode='a', line_terminator='\n')