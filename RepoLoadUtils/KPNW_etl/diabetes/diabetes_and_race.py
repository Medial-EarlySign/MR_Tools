import sys
import os
import numpy as np
import pandas as pd
from utils import fixOS, read_first_line, get_dict_set_df
# sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from get_funcs import get_sig_df, get_registry


SOURCE = 'files'
#SOURCE = 'rep'

if SOURCE == 'rep':
    import medpython as med


def get_cohort_at(at_date, rep, sigs_files_path):
    yr_before = 2
    mem_df = get_sig_df('MEMBERSHIP', rep, sigs_files_path)
    mem_df['date_end'] = mem_df['date_end'].replace(20991231, 20190601)
    mem_df['at_date'] = at_date
    mem_df = mem_df[(mem_df['date_end'] > at_date) & (mem_df['date_start'] < at_date)]
    mem_df['before_days_diff'] = pd.to_datetime(mem_df['at_date'], format='%Y%m%d') - pd.to_datetime(mem_df['date_start'],
                                                                                              format='%Y%m%d')
    #mem_df['after_days_diff'] = pd.to_datetime(mem_df['date_end'], format='%Y%m%d') - pd.to_datetime(mem_df['at_date'],
    #                                                                                          format='%Y%m%d')
    mem_df['before_days_diff'] = mem_df['before_days_diff'].dt.days
    #mem_df['after_days_diff'] = mem_df['after_days_diff'].dt.days
    mem_df = mem_df[mem_df['before_days_diff'] >= 730]
    #print('>2 years membership at ' + str(at_date))

    reg = get_registry()
    ch_df = mem_df.merge(reg, on='pid', how='left')
    # take all pre diabetic patients with at least 1 year membership before and after the at date
    #ch_df = ch_df[(ch_df['after_days_diff'] > 365) & (ch_df['before_days_diff'] > yr_before*365) & (ch_df['stat'] == 1)]
    ch_df = ch_df[(ch_df['stat'] == 1)]

    # check if having Glucose or A1C 1 year before date
    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)
    glu_df = get_sig_df('Glucose', rep, sigs_files_path)
    test_df = pd.concat([a1c_df[['pid', 'date']], glu_df[['pid', 'date']]])

    # all tests at years befor the date
    test_df = test_df[(test_df['date'] >= at_date - yr_before*10000) & (test_df['date'] <= at_date)]
    ch_df = ch_df[ch_df['pid'].isin(test_df['pid'].unique())]
    return ch_df[['pid', 'at_date', 'from_date', 'date_end']]


def build_sample_file(cohort_df, out_dir, win_days):
    reg = get_registry()
    diab_df = reg[reg['stat'] == 2]
    cohort1 = cohort_df.merge(diab_df, on='pid', how='left')
    cases = cohort1[(cohort1['from_date_y'] > cohort1['from_date_x']) & (cohort1['stat'] == 2)]
    cases['outcome'] = 1
    cases['outcomeTime'] = cases['from_date_y']
    controls = cohort1[((cohort1['from_date_y'] > cohort1['at_date']) | (cohort1['from_date_y'].isnull())) & (cohort1['stat'] != 2)]
    controls['outcome'] = 0
    controls['outcomeTime'] = controls['date_end']
    samp_df = pd.concat([controls[['pid', 'at_date', 'outcome', 'outcomeTime']],  cases[['pid', 'at_date', 'outcome', 'outcomeTime']]])
    samp_df['EVENT_FIELDS'] = 'SAMPLE'
    samp_df['split'] = -1
    samp_df.rename(columns={'pid': 'id', 'at_date': 'time'}, inplace=True)
    samp_df['diff'] = pd.to_datetime(samp_df['outcomeTime'], format='%Y%m%d') - pd.to_datetime(samp_df['time'], format='%Y%m%d')
    print('Censored: ' + str(samp_df[samp_df['diff'].dt.days < win_days].shape))
    samp_df = samp_df[samp_df['diff'].dt.days >= win_days]
    print('Controls: ' + str(samp_df[samp_df['outcome'] == 0].shape))
    print('Cases: ' + str(samp_df[samp_df['outcome'] == 1].shape))
    cols = ['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split']
    atdate = samp_df.iloc[0]['time']
    samp_df[cols].to_csv(os.path.join(out_dir, 'pre2d_ondate' + str(atdate) + '.sample'), sep='\t', index=False)
    return samp_df[cols]


def read_cohort(pred_dir, pred_file, rep, sigs_files_path):
    pred_df = pd.read_csv(os.path.join(pred_dir, pred_file), sep='\t', usecols=[1, 2, 3, 4, 5, 6])
    race_df = get_sig_df('RACE', rep, sigs_files_path)
    pred_df = pred_df.merge(race_df, right_on='pid', left_on='id', how='left')
    print(pred_df)


if __name__ == '__main__':
    out_dir = 'W:\\AlgoMarkers\\Pre2D\\kp_races'
    kp_rep = fixOS('/home/Repositories/KPNW/kpnw_jun19/kpnw.repository')
    kp_diab_rep = fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/kpnw.repository')
    sigs_files_path = fixOS('W:\\Users\\Tamar\\kpnw_diabetes_load\\temp\\')

    if SOURCE == 'rep':
        rep = med.PidRepository()
        rep.read_all(kp_rep, [], [])
        print(med.cerr())
    else:
        rep = None
    yr = 20180101
    cohort = get_cohort_at(yr, rep, sigs_files_path)
    samp_df = build_sample_file(cohort, out_dir, 364)

    read_cohort(out_dir, 'pre2d_ondate20180101.preds', rep, sigs_files_path)



