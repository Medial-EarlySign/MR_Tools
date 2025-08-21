import pandas as pd
import numpy as np
import os
import sys
from Configuration import Configuration
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from utils import fixOS, write_tsv, read_first_line,get_dict_set_df, get_dict_set_df_new
import med

'''
def get_dict_set_df(cfg, signal):
    sig_dicts = []
    dict_path = os.path.join(fixOS(cfg.repo_folder), 'dicts')
    for f in os.listdir(dict_path):
        first_line = read_first_line(os.path.join(dict_path, f))
        if signal in first_line:
            sig_dicts.append(f)
    if len(sig_dicts) == 0:
        return pd.DataFrame()
    all_dicts = pd.DataFrame()
    for dct in sig_dicts:
        dict_df = pd.read_csv(os.path.join(dict_path, dct), sep='\t', names=['typ', 'codeid', 'desc'], header=1)
        all_dicts = all_dicts.append(dict_df, sort=False)

    def_df = all_dicts[all_dicts['typ'] == 'DEF'].copy()
    def_df_map = def_df.set_index('desc')['codeid']

    set_df = all_dicts[all_dicts['typ'] == 'SET'].copy()
    set_df.rename(columns={'codeid': 'outer', 'desc': 'inner'}, inplace=True)
    set_df.loc[:, 'inner_code'] = set_df['inner'].map(def_df_map)
    def_df = def_df.append(set_df[['outer', 'inner_code']].rename(columns={'outer': 'desc', 'inner_code': 'codeid'}),
                           ignore_index=True, sort=False)

    while not set_df.empty:
        set_df = set_df[['outer', 'inner']].merge(set_df[['outer', 'inner']], how='left', left_on='inner',
                                                  right_on='outer')
        set_df = set_df[set_df['inner_y'].notnull()]
        set_df.loc[:, 'inner_code'] = set_df['inner_y'].map(def_df_map)
        def_df = def_df.append(set_df[['outer_x', 'inner_code']].rename(columns={'outer_x': 'desc', 'inner_code': 'codeid'}),
                               ignore_index=True, sort=False)
        set_df.rename(columns={'outer_x': 'outer', 'inner_y': 'inner'}, inplace=True)

    return def_df[['codeid', 'desc']]
'''

def prep_smoking_intensity(rep, cfg):
    sig = 'Smoking_Intensity'
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')

    rep_dir = fixOS(cfg.repo)
    rep.read_all(rep_dir, [], ['Smoking_quantity'])
    smoking_quantity = rep.get_sig('Smoking_quantity')
    smoking_intnsity = smoking_quantity[smoking_quantity['val1'] != -9]
    smoking_intnsity.loc[:, 'sig_name'] = sig
    smoking_intnsity.sort_values(by=['pid', 'time0'], inplace=True)
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(smoking_intnsity[['pid', 'sig_name', 'time0', 'val1']], out_folder, sig)


def prep_smoking_status(rep, cfg):
    sig = 'Smoking_Status'
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    rep_dir = fixOS(cfg.repo)
    print(rep_dir)
    rep.read_all(rep_dir, [], ['GENDER'])
    stat_map = pd.Series({'N/E': 'Never_or_Former', 'N': 'Never', 'E': 'Former', 'S': 'Current', 'NorS': 'NorS'})
    print('1')
    smoke_file = fixOS('/server/UsersData/tamard/MR/Projects/Shared/GenSmoking/smoking_readcodes_modified.csv')
    smoke_map = pd.read_csv(smoke_file, usecols=[0, 2], names=['rc', 'smoke_stat'])
    smoke_map['smoke_stat'].fillna('NorS', inplace=True)
    dict_df = get_dict_set_df(cfg.repo_folder, 'RC')
    dict_df = dict_df.merge(smoke_map, how='left', left_on='desc', right_on='rc')
    dict_df = dict_df[dict_df['rc'].notnull()].copy()
    dict_df['codeid'] = dict_df['codeid'].astype(float)
    print('2')
    gn_df = rep.get_sig('GENDER')
    sig_qaun = rep.get_sig('Smoking_quantity')
    pids = gn_df['pid'].unique().tolist()
    chunk_size = 1000000
    rc_df_smk_all = pd.DataFrame()
    print('3')
    cols = ['pid', 'time0', 'smoke_stat']
    for i in range(0, len(pids), chunk_size):
        curr_list = pids[i:i+chunk_size]
        rc_df = rep.get_sig('RC', pids=curr_list, translate=False)
        #print(rc_df.head(10))
        #print(dict_df.head(10))
        rc_df_smk = rc_df.merge(dict_df, how='left', left_on='val0', right_on='codeid')
        print('merge size ' + str(rc_df_smk.shape[0]))
        rc_df_smk = rc_df_smk[rc_df_smk['rc'].notnull()]
        print('merge not null size ' + str(rc_df_smk.shape[0]))
        rc_df_smk['smoke_stat'] = rc_df_smk['smoke_stat'].map(stat_map)
        rc_df_smk = rc_df_smk[cols]
        un_certen = rc_df_smk[rc_df_smk['smoke_stat'] == 'NorS'].copy()
        rc_df_smk = rc_df_smk[rc_df_smk['smoke_stat'] != 'NorS']


        un_certen = pd.merge(un_certen, sig_qaun, how='left', on=['pid', 'time0'])
        un_certen = un_certen[un_certen['val1'] > 0]
        un_certen.loc[:, 'smoke_stat'] = 'Current'
        un_certen.drop_duplicates(subset=cols, inplace=True)

        rc_df_smk = pd.concat([rc_df_smk[cols], un_certen[cols]], axis=0)
        rc_df_smk_all = rc_df_smk_all.append(rc_df_smk)
        print('rc_df_smk_all size: ' + str(rc_df_smk_all.shape[0]))
    rc_df_smk_all.drop_duplicates(subset=cols, inplace=True)
    rc_df_smk_all['signal'] = sig
    print(rc_df_smk_all.shape)
    cols = ['pid', 'signal', 'time0', 'smoke_stat']
    rc_df_smk_all.sort_values(by=['pid', 'time0'], inplace=True)
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    write_tsv(rc_df_smk_all[cols], out_folder, sig)


if __name__ == "__main__":
    cfg = Configuration()
    rep = med.PidRepository()

    prep_smoking_intensity(rep, cfg)
    prep_smoking_status(rep, cfg)
