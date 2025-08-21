import pandas as pd
import numpy as np
import sys
import os
import time
from math import sqrt
MR_ROOT = '/nas1/UsersData/' + os.environ['USER'] +'/MR'
sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'thin1801'))
sys.path.append(os.path.join(MR_ROOT, 'Tools', 'RepoLoadUtils', 'thin1801', 'test_and_compare'))
from gets_and_filters import get_signals_from_sig_file, get_common_patients, read_repositories, common_pids_sigs, get_pids_in_years, get_new_patients
from const_and_utils import fixOS
from Configuration import Configuration


def value_count_df(df, field, population):
    vc = df[field].value_counts()
    vc_df = pd.DataFrame(vc)
    #vc_df[population+'%'] = round((vc_df[field] / df.shape[0]) * 100, 2)
    vc_df.rename(columns={field: population}, inplace=True)
    return vc_df


if __name__ == '__main__':
    new_dates_start = 20170101
    byear_start = 1955
    byear_end = 1956
    sig = 'Drug'
    print('===== ' + sig + ' =======')

    cfg = Configuration()
    new_rep = fixOS(cfg.curr_repo)
    old_rep = fixOS(cfg.prev_repo)
    drug_dict_old = pd.read_csv(os.path.join(old_rep, 'dict.drugs_defs'), sep='\t',  header=1, names=['medid', 'code'],
                                encoding='latin-1', usecols=[1, 2], dtype={'medid': int, 'code': str})
    drug_dict_new = pd.read_csv(os.path.join(new_rep, 'dict.drugs_defs'), sep='\t', header=1, names=['medid', 'code'],
                                usecols=[1, 2], dtype={'medid': int, 'code': str})

    drug_dict_old['code'] = drug_dict_old['code'].str.replace('dc: ', '')
    drug_dict_old['code'] = drug_dict_old['code'].str.replace('dc', '')
    drug_dict_old['code'] = drug_dict_old['code'].str.replace('_#1', '')
    drug_dict_new['code'] = drug_dict_new['code'].str.replace('dc:', '')

    merged_dict = drug_dict_old.merge(drug_dict_new, how='left', on='code', suffixes=['_old', '_new'])
    merged_dict = merged_dict.drop_duplicates(subset=['medid_old'])[['medid_new', 'medid_old']]
    #merged_dict = merged_dict[merged_dict['medid_new'].notnull()]
    dict_map = merged_dict.set_index('medid_old')['medid_new']

    list_map_new = drug_dict_new[['medid', 'code']].groupby('medid').agg(lambda x: list(set(x.tolist())))['code']

    new_pids = get_new_patients()
    #vc_df = pd.DataFrame()
    #ages_pids = get_pids_in_years(byear_start, byear_end)

    rep_new, rep_old = read_repositories([], [sig, 'BYEAR'])

    byers = rep_new.get_sig('BYEAR')
    start = int(byers['val'].min())
    end = int(byers['val'].max())
    print(byers['val'].min(), byers['val'].max())
    new_dates_vc_sum = pd.DataFrame(columns=['new repository new dates'])
    old_dates_vc_sum = pd.DataFrame(columns=['new repository old dates'])
    new_pids_vc_sum = pd.DataFrame(columns=['new repository new pids'])
    old_rep_vc_sum = pd.DataFrame(columns=['old repository'])

    sig_dict = {'new values in new years': 0, 'new values': 0, 'missing values': 0, 'changed values': 0}
    for x in range(start, end, 10):
        years_pids = byers[(byers['val'] >= x) & (byers['val'] < x+10)]['pid']
        print(len(years_pids))
        if years_pids.shape[0] == 0:
            continue

        time1 = time.time()
        old_sig = rep_old.get_sig(sig, pids=years_pids, translate=False)
        new_sig = rep_new.get_sig(sig, pids=years_pids, translate=False)

        old_sig['val1'] = old_sig['val1'].map(dict_map)
        old_sig['val2'] = old_sig['val2'].map(dict_map)

        sig_dict['new values in new years'] += new_sig[new_sig['date'] >= new_dates_start].shape[0]
        new_data_new_sig = new_sig[new_sig['date'] >= new_dates_start]
        old_data_new_sig = new_sig[(new_sig['date'] < new_dates_start) & (~new_sig['pid'].isin(new_pids))]

        new_sig = new_sig[new_sig['date'] < new_dates_start]
        new_pids_sig = new_sig[new_sig['pid'].isin(new_pids)]

        time2 = time.time()
        print('  Reading and filtering sigs and  ' + str(time2 - time1))
        cols = new_sig.columns
        old_sig['source'] = 'old'
        new_sig['source'] = 'new'
        diff_df_sig = pd.concat([old_sig, new_sig], sort=False).drop_duplicates(subset=cols, keep=False)
        cnts = diff_df_sig.groupby(['pid', 'source']).count().reset_index()[['pid', 'source']].groupby('pid').count()
        diff_df_sig = diff_df_sig.merge(pd.DataFrame(cnts), how='left', left_on='pid', right_index=True)

        sig_dict['new values'] += diff_df_sig[(diff_df_sig['source_x'] == 'new') & (diff_df_sig['source_y'] == 1) & (diff_df_sig['val1'] != 0)].shape[0]
        sig_dict['missing values'] += diff_df_sig[(diff_df_sig['source_x'] == 'old') & (diff_df_sig['source_y'] == 1)].shape[0]
        chd_diff = diff_df_sig[diff_df_sig['source_y'] > 1]
        chd_diff = chd_diff[chd_diff.duplicated(subset=['pid', 'date'], keep=False)]
        sig_dict['changed values'] += len(chd_diff['pid'].unique())
        print(sig_dict)
        print('   process signal in pid byears start in '+str(x) + ' - ' + str(time.time() - time2))

        new_data_new_sig = new_sig[new_sig['date'] >= new_dates_start]
        old_data_new_sig = new_sig[new_sig['date'] < new_dates_start]

        new_pids_sig = new_sig[new_sig['pid'].isin(new_pids)]
        print('# of new PIDs from byear ' + str(x) + ' to ' + str(x+10) + ': ' + str(len(new_pids_sig)))

        new_dates_vc = value_count_df(new_data_new_sig, 'val1', 'new repository new dates')
        new_dates_vc_sum = new_dates_vc_sum.add(new_dates_vc, fill_value=0)

        old_dates_vc = value_count_df(old_data_new_sig, 'val1', 'new repository old dates')
        old_dates_vc_sum = old_dates_vc_sum.add(old_dates_vc, fill_value=0)

        new_pids_vc = value_count_df(new_pids_sig, 'val1', 'new repository new pids')
        new_pids_vc_sum = new_pids_vc_sum.add(new_pids_vc, fill_value=0)

        old_rep_vc = value_count_df(old_sig, 'val1', 'old repository')
        old_rep_vc_sum = old_rep_vc_sum.add(old_rep_vc, fill_value=0)
        del new_sig
        del old_sig

    sig_vc_df = old_rep_vc_sum.merge(new_dates_vc_sum, how='outer', left_index=True, right_index=True)
    sig_vc_df = sig_vc_df.merge(old_dates_vc_sum, how='outer', left_index=True, right_index=True)
    sig_vc_df = sig_vc_df.merge(new_pids_vc_sum, how='outer', left_index=True, right_index=True)
    sig_vc_df['signal'] = sig
    #vc_df = vc_df.append(sig_vc_df.reset_index())
    print(sig_vc_df)
    report = pd.DataFrame.from_dict(sig_dict, orient='index')
    print(report)
    report.to_csv('diff_drugs_counts.csv')

    sig_vc_df.to_csv('dist_diff_drugs.csv')




