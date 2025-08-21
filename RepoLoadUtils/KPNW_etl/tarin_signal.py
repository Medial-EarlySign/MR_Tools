import os
import sys
import pandas as pd
import numpy as np
from Configuration import Configuration
from utils import write_tsv, fixOS


def train_for_pids(pid_list):

    per70 = int(len(pid_list)*0.7)
    per20 = int(len(pid_list)*0.2)

    list1 = np.random.choice(pid_list, per70, replace=False)
    df1 = pd.DataFrame(list1)
    df1['val'] = 1

    remain = list(set(pid_list) - set(list1))
    list2 = np.random.choice(remain, per20, replace=False)
    df2 = pd.DataFrame(list2)
    df2['val'] = 2

    remain2 = list(set(remain) - set(list2))
    df3 = pd.DataFrame(remain2)
    df3['val'] = 3

    new_df = pd.concat([df1, df2, df3])
    new_df.rename({0: 'pid'}, inplace=True, axis=1)
    new_df['signal'] = 'TRAIN'
    return new_df


def generate_train_signal(exist_train_df=None):
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    curr_id2inr = os.path.join(out_folder, 'ID2NR')

    cur_id2nr = pd.read_csv(curr_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
    if exist_train_df is not None:
        new_id2nr = cur_id2nr[~cur_id2nr['medialid'].isin(exist_train_df['pid'].values)]['medialid'].unique()
        train_df = train_for_pids(new_id2nr)
        train_df = exist_train_df.append(train_df)
    else:
        cur_ids = cur_id2nr['medialid'].unique()
        train_df = train_for_pids(cur_ids)
    train_df.sort_values(by='pid', inplace=True)
    write_tsv(train_df[['pid', 'signal', 'val']], os.path.join(out_folder, 'FinalSignals'), 'TRAIN')


if __name__ == '__main__':
    cfg = Configuration()
    old_train = os.path.join(fixOS(cfg.work_path), 'FinalSignalsJun20', 'TRAIN')
    old_df = pd.read_csv(old_train, sep='\t', names = ['pid', 'signal', 'val'])
    generate_train_signal(old_df)
