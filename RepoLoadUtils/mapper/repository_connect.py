import pandas as pd
import numpy as np
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from search_and_save import read_medial_signal
#sys.path.append('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med

df_dict = {}

source = 'kpnw'
repository_path = '/home/Repositories/KPNW/kpnw_aug20/'
rep_file = os.path.join(repository_path, source+'.repository')
sigs_file = os.path.join(repository_path, source+'.signals')
default_sig = 'Hemoglobin'
rep = med.PidRepository()
rep.read_all(rep_file, [], ['Hemoglobin'])
sig_unit_map = read_medial_signal()
sig_unit_map = sig_unit_map.set_index('Name')['FinalUnit']


def get_all_signals():
    sigs = pd.read_csv(sigs_file, sep='\t', usecols=[0, 1], error_bad_lines=False, names=['type', 'signal'])
    sigs = sigs[sigs['type'] == 'SIGNAL']
    sigs.sort_values(by='signal', inplace=True)
    return sigs['signal'].values.tolist()


def get_sig_unit(signal):
    if signal in sig_unit_map.index:
        return sig_unit_map[signal]
    else:
        return None


def get_signal(signal):
    if signal in df_dict.keys():
        sig_df = df_dict[signal]
    else:
        sig_df = rep.get_sig(signal)
        first_chanel = sig_df.columns[1]
        #vals_cols = [x for x in sig_df.columns if 'val' in x]
        #if len(vals_cols) == 0:
        #    sig_df.rename(columns={first_chanel: 'val'}, inplace=True)
        if 'val' not in first_chanel:
            sig_df.rename(columns={first_chanel: 'date'}, inplace=True)  # Change the first date chanel to be called date
        df_dict[signal] = sig_df
    unit = get_sig_unit(signal)
    return sig_df, unit

