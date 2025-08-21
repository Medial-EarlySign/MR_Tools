import os
import sys
import pandas as pd
import numpy as np
import traceback
import time
MR_ROOT = '/opt/medial/tools/bin/RepoLoadUtils'
sys.path.append(os.path.join(MR_ROOT, 'common'))
from Configuration import Configuration
from utils import write_tsv, fixOS
from generate_id2nr import get_id2nr_map

cfg = Configuration()
out_folder = fixOS(cfg.work_path)
curr_id2inr = os.path.join(out_folder, 'ID2NR')

cur_id2nr = pd.read_csv(curr_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
cur_ids = cur_id2nr['medialid'].unique()


per70 = int(len(cur_ids)*0.7)
per20 = int(len(cur_ids)*0.2)

list1 = np.random.choice(cur_ids, per70, replace=False)
df1 = pd.DataFrame(list1)
df1['val'] = 1

remain = list(set(cur_ids) - set(list1))
list2 = np.random.choice(remain, per20, replace=False)
df2 = pd.DataFrame(list2)
df2['val'] = 2

remain2 = list(set(remain) - set(list2))
df3 = pd.DataFrame(remain2)
df3['val'] = 3

new_df = pd.concat([df1, df2, df3])
new_df.rename({0: 'pid'}, inplace=True, axis=1)


new_df['signal'] = 'TRAIN'
new_df.sort_values(by='pid', inplace=True)
write_tsv(new_df[['pid', 'signal', 'val']], os.path.join(out_folder, 'FinalSignals'), 'TRAIN')
