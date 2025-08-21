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



def get_tscore(new_vals, old_sig_vals):
    pop_mean = old_sig_vals.mean()

    sam_mean = new_vals.mean()
    sam_std = new_vals.std()
    sam_count = new_vals.shape[0]
    if sam_std > 0:
        tscore = ((sam_mean - pop_mean) / (sam_std / sqrt(sam_count)))
    else:
        tscore = np.nan
    pop_d = old_sig_vals.quantile(0.02)
    pop_u = old_sig_vals.quantile(0.98)
    print('pop quantile 2 = ' + str(pop_d))
    print('pop quantile 98 = ' + str(pop_u))
    pop_fixed_mean = old_sig_vals[(old_sig_vals > pop_d) & (old_sig_vals < pop_u)].mean()
    print('Mean=' + str(pop_mean) + ' fixed mean ' + str(pop_fixed_mean))

    sam_d = new_vals.quantile(0.02)
    sam_u = new_vals.quantile(0.98)
    print('sam quantile 2 = ' + str(sam_d))
    print('sam quantile 98 = ' + str(sam_u))

    sam_df = new_vals[(new_vals > sam_d) & (new_vals < sam_u)]
    sam_mean_fixed = sam_df.mean()
    sam_std_fixed = sam_df.std()
    sam_count_fixed = sam_df.shape[0]
    print('SAMP Mean=' + str(sam_mean) + ' fixed mean ' + str(sam_mean_fixed))
    print('SAMP std=' + str(sam_std) + ' fixed std ' + str(sam_std_fixed))
    print('SAMP count=' + str(sam_count) + ' fixed count ' + str(sam_count_fixed))
    if sam_std_fixed > 0:
        tscore_flag = abs(((sam_mean_fixed - pop_fixed_mean) / sam_std_fixed))
    else:
        tscore_flag = np.nan
    print('tscode = ' + str(tscore))
    print('tscore_flag = ' + str(tscore_flag))
    return tscore, tscore_flag


def describe_and_histogram_dict(df, field, signal, population):
    desc_dict = dict(df[field].describe())
    desc_dict['signal'] = signal
    desc_dict['population'] = population
    # if df.shape[0] > 0:
    #     #hist = df[(df[field] >= desc_dict['25%']) & (df[field] <= desc_dict['75%'])][field].value_counts(normalize=True,
    #     #                                                                                             bins=10)
    #     hist = df[field].value_counts(normalize=True, bins=20)
    #     hist_dict_str = ''
    #     for k, val in hist.iteritems():
    #         hist_dict_str += str(k) + ': ' + str(val * 100) + ','
    #     desc_dict['hist'] = hist_dict_str
    return desc_dict


def numeric_new_dates_compare(out_file, new_dates_start, byear_start, byear_end):
    common_pids, common_sigs = common_pids_sigs('numeric')
    common_sigs = ['CHADS2_VASC']
    new_pids = get_new_patients()
    print('# of new pids ' + str(len(new_pids)))
    ages_pids = get_pids_in_years(byear_start, byear_end)

    print('#PiDs from byear ' + str(byear_start) + ' to ' + str(byear_end) + ': ' + str(len(ages_pids)))
    new_pids_ages = list(set(new_pids) & set(ages_pids))
    print('New pids in ages ' + str(len(new_pids_ages)))
    rep_new, rep_old = read_repositories(ages_pids, common_sigs)
    report_list = []

    for sig in common_sigs:
        time1 = time.time()
        print('===== ' + sig + ' =======')
        val_field_n = 'val'
        val_field_o = 'val'
        old_sig = rep_old.get_sig(sig, pids=ages_pids)
        if 'val' not in old_sig.columns:
            val_field_o = 'val1'
        old_sig[val_field_o] = old_sig[val_field_o].astype('float64')
        new_sig = rep_new.get_sig(sig, pids=ages_pids)
        if 'val' not in new_sig.columns:
            val_field_n = 'val1'
        new_sig[val_field_n] = new_sig[val_field_n].astype('float64')
        if 'date' not in new_sig.columns:
            print('skipping signal with no date ' + sig)
            continue
        new_data_new_sig = new_sig[new_sig['date'] >= new_dates_start]
        old_data_new_sig = new_sig[new_sig['date'] < new_dates_start]

        new_pids_sig = new_sig[new_sig['pid'].isin(new_pids)]
        print('# of new PIDs from byear ' + str(byear_start) + ' to ' + str(byear_end) + ': ' + str(len(new_pids_sig)))

        new_dates_dict = describe_and_histogram_dict(new_data_new_sig, val_field_n, sig, 'new repository new dates')
        old_dates_dict = describe_and_histogram_dict(old_data_new_sig, val_field_n, sig, 'new repository old dates')
        new_pids_dict = describe_and_histogram_dict(new_pids_sig, val_field_n, sig, 'new repository new pids')
        old_rep_data = describe_and_histogram_dict(old_sig, val_field_o, sig, 'old repository')
        new_dates_dict['t score'],  new_dates_dict['t score flag'] = get_tscore(new_data_new_sig[val_field_n], old_sig[val_field_o])
        old_dates_dict['t score'], old_dates_dict['t score flag'] = get_tscore(old_data_new_sig[val_field_n], old_sig[val_field_o])
        new_pids_dict['t score'], new_pids_dict['t score flag'] = get_tscore(new_pids_sig[val_field_n], old_sig[val_field_o])

        report_list.append(new_dates_dict)
        report_list.append(old_dates_dict)
        report_list.append(new_pids_dict)
        report_list.append(old_rep_data)

        print('   process signal in ' + str(time.time() - time1))
    report_df = pd.DataFrame(report_list)
    print(report_df)
    cols = ['signal', 'population', 'count', 'mean', 'std',  '25%', '50%', '75%', 'max', 'min','t score', 't score flag']
    report_df[cols].to_csv(out_file, index=False)


def value_count_and_per(df, field, signal, population):
    vc = df[field].value_counts()
    vc_df = pd.DataFrame(vc)
    vc_df[population+'%'] = round((vc_df[field] / df.shape[0]) * 100, 2)
    vc_df.rename(columns={field: population}, inplace=True)
    return vc_df


def categoric_new_dates_compare(out_file, new_dates_start, byear_start, byear_end):
    common_pids, common_sigs = common_pids_sigs('string')
    common_sigs = ['Drug']
    new_pids = get_new_patients()
    print('# of new pids ' + str(len(new_pids)))
    ages_pids = get_pids_in_years(byear_start, byear_end)
    print('#PiDs from byear ' + str(byear_start) + ' to ' + str(byear_end) + ': ' + str(len(ages_pids)))
    new_pids_ages = list(set(new_pids) & set(ages_pids))
    print('New pids in ages ' + str(len(new_pids_ages)))
    rep_new, rep_old = read_repositories(ages_pids, common_sigs)
    vc_df = pd.DataFrame()
    for sig in common_sigs:
        time1 = time.time()
        val_field_n = 'val'
        val_field_o = 'val'
        print('===== ' + sig + ' =======')
        old_sig = rep_old.get_sig(sig, pids=ages_pids)
        if 'val' not in old_sig.columns:
            val_field_o = 'val1'
        old_sig[val_field_o] = old_sig[val_field_o].apply(lambda x: x if x == 'EMPTY_THIN_FIELD' else x.split('|')[0])
        new_sig = rep_new.get_sig(sig, pids=ages_pids)
        if 'val' not in new_sig.columns:
            val_field_n = 'val1'
        new_sig[val_field_n] = new_sig[val_field_n].apply(lambda x: x if x == 'EMPTY_THIN_FIELD' else x.split('|')[0])
        new_sig[val_field_n] = new_sig[val_field_n].apply(
            lambda x: x if (x == 'EMPTY_THIN_FIELD' or ':' not in x) else x.split(':')[1])
        if 'date' not in new_sig.columns:
            print('skipping signal with no date ' + sig)
            continue
        new_data_new_sig = new_sig[new_sig['date'] >= new_dates_start]
        old_data_new_sig = new_sig[new_sig['date'] < new_dates_start]

        new_pids_sig = new_sig[new_sig['pid'].isin(new_pids)]
        print('# of new PIDs from byear ' + str(byear_start) + ' to ' + str(byear_end) + ': ' + str(len(new_pids_sig)))

        new_dates_vc = value_count_and_per(new_data_new_sig, val_field_n, sig, 'new repository new dates')
        old_dates_vc = value_count_and_per(old_data_new_sig, val_field_n, sig, 'new repository old dates')
        new_pids_vc = value_count_and_per(new_pids_sig, val_field_n, sig, 'new repository new pids')
        old_rep_vc = value_count_and_per(old_sig, val_field_o, sig, 'old repository')
        sig_vc_df = old_rep_vc.merge(new_dates_vc, how='outer', left_index=True, right_index=True)
        sig_vc_df = sig_vc_df.merge(old_dates_vc, how='outer', left_index=True, right_index=True)
        sig_vc_df = sig_vc_df.merge(new_pids_vc, how='outer', left_index=True, right_index=True)
        sig_vc_df['signal'] = sig
        vc_df = vc_df.append(sig_vc_df.reset_index())
        print(vc_df)
    vc_df.to_csv(out_file)


if __name__ == '__main__':
    new_dates_start = 20170101
    byear_start = 1955
    byear_end = 1965
    #out_file = 'distribution_compare3.csv'
    #if not os.path.exists(out_file):
    #    print('File does not exist craeting it...')
    #    numeric_new_dates_compare(out_file, new_dates_start, byear_start, byear_end)
    #out_file_cat = 'distribution_compare_cat.csv'
    out_file_cat = 'distribution_compare_Drug.csv'
    if not os.path.exists(out_file_cat):
        print('Categorial out file does not exist craeting it...')
        categoric_new_dates_compare(out_file_cat, new_dates_start, byear_start, byear_end)
