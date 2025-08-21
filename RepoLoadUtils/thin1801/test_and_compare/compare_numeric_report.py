import pandas as pd
import sys
import os
import time
MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'thin1801'))
sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'thin1801', 'test_and_compare'))
from gets_and_filters import get_signals_from_sig_file, get_common_patients, read_repositories, common_pids_sigs

import numpy as np
sys.path.insert(0,'/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med


def prepare_diff_table(out_file, new_dates_start):
    common_pids, common_sigs = common_pids_sigs('numeric')
    rep_new, rep_old = read_repositories(common_pids, common_sigs)
    common_sigs = ['Smoking_quantity', 'Alcohol_quantity']
    diffs1 = {}
    diffs2 = {}
    diffs3 = {}
    #common_sigs = ['Basophils#']
    for sig in common_sigs:
        time1 = time.time()
        print('===== ' + sig + ' =======')
        old_sig = rep_old.get_sig(sig)
        new_sig = rep_new.get_sig(sig)
        diff_df = pd.concat([old_sig, new_sig], sort=False).drop_duplicates(keep=False)
        if 'val' not in diff_df.columns:
            diff_df.rename(columns={'val1': 'val'}, inplace=True)
        diff_df['roundval'] = diff_df['val'].round()
        diff_df.reset_index(inplace=True, drop=True)
        allpids = list(diff_df['pid'].unique())
        print('#PIDs with diffs = ' + str(len(allpids)))
        if 'date' in diff_df.columns:
            diff_no_new_df = diff_df[diff_df['date'] < new_dates_start]
            no_new_pids = list(diff_no_new_df['pid'].unique())
            only_new_pids = list(set(allpids) - set(no_new_pids))
            print('#PIDs with diff no new dates= ' + str(len(no_new_pids)))
            diffs1[sig] = {x: 1 for x in only_new_pids}
            prob_df = diff_no_new_df.drop_duplicates(subset=['pid', 'date', 'roundval'], keep=False)
            prod_pids = list(prob_df['pid'].unique())
            round_pids = list(set(no_new_pids) - set(prod_pids))
        else:
            prob_df = diff_df.drop_duplicates(subset=['pid', 'roundval'], keep=False)
            prod_pids = list(prob_df['pid'].unique())
            round_pids = list(set(allpids) - set(prod_pids))
        if len(round_pids) > 0:
            diffs2[sig] = {x: 2 for x in round_pids}
        print('#PIDs with diff no round= ' + str(len(prod_pids)))
        diffs3[sig] = {x: 3 for x in prod_pids}
        print('   process signal in ' + str(time.time() - time1))
    print('1')
    report1 = pd.DataFrame(diffs1)
    print('2')
    report2 = pd.DataFrame(diffs2)
    print('3')
    report3 = pd.DataFrame(diffs3)
    # report = pd.DataFrame.from_dict(diffs, orient='columns')
    print('4')
    report1.to_csv('1' + out_file)
    report2.to_csv('2' + out_file)
    report3.to_csv('3' + out_file)
    print('DONE')


def diff_problems(diff_df, new_dates_start):
    sigs = list(diff_df.columns)
    sigs.remove('pid')
    pids = list(diff_df['pid'])
    print('Number of sigs: ' + str(len(sigs)))
    print('Number of pids: ' + str(len(pids)))
    rep_new, rep_old = read_repositories(pids, sigs)
    all_sig_dict = {}
    for sig in sigs:
        sig_dict = {}
        #sig_dict = {'new values': 0, 'missing values': 0, 'changed values': 0, 'new 0 values': 0}
        time1 = time.time()
        print('===== ' + sig + ' =======')
        diff_pids = list(diff_df[diff_df[sig] == 3]['pid'])
        print('pids with diffs: ' + str(len(diff_pids)))
        old_sig = rep_old.get_sig(sig, pids=diff_pids)
        new_sig = rep_new.get_sig(sig, pids=diff_pids)
        if 'date' in new_sig.columns:
            new_sig = new_sig[new_sig['date'] < new_dates_start]

        cols = new_sig.columns
        old_sig['source'] = 'old'
        new_sig['source'] = 'new'
        diff_df_sig = pd.concat([old_sig, new_sig], sort=False).drop_duplicates(subset=cols, keep=False)
        if 'val' not in diff_df_sig.columns:
            diff_df_sig.rename(columns={'val1': 'val'}, inplace=True)
        cnts = diff_df_sig.groupby(['pid', 'source']).count().reset_index()[['pid', 'source']].groupby('pid').count()
        diff_df_sig = diff_df_sig.merge(pd.DataFrame(cnts), how='left', left_on='pid', right_index=True)

        sig_dict['new values'] = diff_df_sig[(diff_df_sig['source_x'] == 'new') & (diff_df_sig['source_y'] == 1) & (diff_df_sig['val'] != 0)].shape[0]
        sig_dict['new 0 values'] = diff_df_sig[(diff_df_sig['source_x'] == 'new') & (diff_df_sig['source_y'] == 1) & (diff_df_sig['val'] == 0)].shape[0]
        sig_dict['missing values'] = diff_df_sig[(diff_df_sig['source_x'] == 'old') & (diff_df_sig['source_y'] == 1)].shape[0]

        chd_diff = diff_df_sig[diff_df_sig['source_y'] > 1]
        if 'date' in diff_df_sig.columns:
            chd_diff = chd_diff[chd_diff.duplicated(subset=['pid', 'date'], keep=False)]
        sig_dict['changed values'] = len(chd_diff['pid'].unique())
        print(sig_dict)
        print('   process signal in ' + str(time.time() - time1))
        all_sig_dict[sig] = sig_dict

    #report = pd.DataFrame(all_sig_dict)
    report = pd.DataFrame.from_dict(all_sig_dict, orient='index')
    print(report)
    #report.to_csv('diff_reason_count.csv')


if __name__ == '__main__':
    new_dates_start = 20170101
    out_file = 'numeric_compare_quntaty.csv'
    diff3_file = '3' + out_file
    if not os.path.exists(diff3_file):
        prepare_diff_table(out_file, new_dates_start)

    diff3_df = pd.read_csv(diff3_file)  # , usecols=[0, 1, 2, 3])
    diff3_df.rename(columns={diff3_df.columns[0]: 'pid'}, inplace=True)
    #temp_sigs = ['pid', 'Alcohol_quantity']
    #diff3_df = diff3_df[temp_sigs]
    diff_problems(diff3_df, new_dates_start)
