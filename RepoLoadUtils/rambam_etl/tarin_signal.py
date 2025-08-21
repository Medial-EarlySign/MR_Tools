import os
import pandas as pd
import numpy as np
import traceback
import time
from Configuration import Configuration
from utils import write_tsv, fixOS
from generate_id2nr import get_id2nr_map
from rambam_utils import hier_field_to_dict, get_dict_item
cfg = Configuration()
out_folder = fixOS(cfg.work_path)
prev_id2inr = fixOS(cfg.prev_id2ind)
curr_id2inr = os.path.join(out_folder, 'ID2NR')
old_train = os.path.join(out_folder, 'outputs', 'TRAIN_OLD')

old_id2nr = pd.read_csv(prev_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
old_ids = old_id2nr['medialid'].unique()

cur_id2nr = pd.read_csv(curr_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
cur_ids = cur_id2nr['medialid'].unique()

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

print(old_train)
tr_df = pd.read_csv(old_train, sep='\t', names=['pid', 'val'], dtype={'pid': int, 'val': int}, header=None)
tr_df = tr_df[tr_df['pid'].isin(in_both)]

tr_df = pd.concat([tr_df, new_df])
tr_df['signal'] = 'TRAIN'
tr_df.sort_values(by='pid', inplace=True)
write_tsv(tr_df[['pid', 'signal', 'val']], os.path.join(out_folder, 'FinalSignals'), 'TRAIN')
