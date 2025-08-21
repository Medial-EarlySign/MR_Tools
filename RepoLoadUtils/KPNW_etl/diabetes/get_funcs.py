import sys
import os
import numpy as np
import pandas as pd
from utils import fixOS, read_first_line, get_dict_set_df
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))

SOURCE = 'files'
#SOURCE = 'rep'


def get_dict_map(dict_path, signal, keep='last'):
    sig_dicts = []
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
    all_dicts.drop_duplicates(inplace=True)
    all_dicts.drop_duplicates(subset='codeid', keep=keep)
    dict_map = all_dicts.set_index('codeid')['desc']
    return dict_map


def get_sig_df(sig_name, rep, files_path):
    if SOURCE == 'rep':
        sig_df = rep.get_sig(sig_name)
    else:
        file_name = os.path.join(files_path, sig_name + '_sig.csv')
        sig_df = pd.read_csv(file_name, sep='\t')
    if 'val' in sig_df.columns:
        sig_df.rename(columns={'val': sig_name.lower()}, inplace=True)
    return sig_df


def find_sickle_cell(rep, sigs_files_path):
    scl_file = os.path.join(sigs_files_path, 'sickle_cell_sig1')
    if os.path.exists(scl_file):
        scl_df = pd.read_csv(scl_file, sep='\t',usecols=[1, 2, 3])
    else:
        diag_df = get_sig_df('DIAGNOSIS', rep, sigs_files_path)
        codes = get_dict_set_df(fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/'), 'DIAGNOSIS')
        reg_list_df = pd.DataFrame(data=['ICD10_CODE:D57', 'ICD9_CODE:282.5', 'ICD9_CODE:282.6'], columns=['desc'])
        # reg_list_df = pd.DataFrame(data=['ICD10_CODE:D550', 'ICD9_CODE:282.2'], columns=['desc'])
        relevant_codes = reg_list_df.merge(codes, how='left', on='desc')
        scl_df = diag_df[diag_df['val'].isin(relevant_codes['codeid'].values)].copy()
        scl_df.drop_duplicates('pid', inplace=True)
        scl_df.to_csv(scl_file, sep='\t', index=False)
    scl_df.rename(columns={'val': 'scl'}, inplace=True)
    return scl_df


def get_registry():
    pre2d_reg_file = fixOS('W:\\Users\\Tamar\\kpnw_diabetes_load\\FinalSignals\\DM_Registry')
    pre2d_df = pd.read_csv(pre2d_reg_file, sep='\t', names=['pid', 'sig', 'from_date', 'to_date', 'stat'])
    return pre2d_df
