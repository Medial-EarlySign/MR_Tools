import os
import sys
import pandas as pd
sys.path.append('/mnt/project/python_lib/')
import medpython as med
from Configuration import Configuration


groups = [0, 10,20,30,40,50,60,70,80,90,100]
age_group_map = {}
for j in range(1, len(groups)):
        for i in range(groups[j-1], groups[j]):
            age_group_map[i] = str(groups[j-1])+'-'+str(groups[j])
age_group_map = pd.Series(age_group_map)
age_group_map.replace({'90-100': '90+'}, inplace=True)


def by_group(df1, grpby, outfile):
    age_df = df1.groupby(grpby)['pid'].count()
    sum1 = age_df.sum()
    age_df = age_df.to_frame()
    age_df['precent'] = age_df['pid'] / sum1
    age_df.loc['total'] = age_df.sum(numeric_only=True)
    age_df.to_csv(outfile, sep='\t')


def to_csvc(df2, outdir, file_pref):
    by_group(df2, 'age_group', os.path.join(outdir, file_pref+'by_age.csv'))
    by_group(df2, 'gender', os.path.join(outdir, file_pref+'_by_gender.csv'))
    by_group(df2, ['gender', 'age_group'], os.path.join(outdir, file_pref+'_by_age_gender.csv'))


def save_sample_file(control_df, cases_df, cdate, pref=''):
    outfile = '/home/LinuxDswUser/work/Pre2D/RegistryAndSamples/pre2d_20170101'+pref+'.sample'
    control_df.loc[:, 'outcome'] = 0
    control_df.loc[:, 'outcomeTime'] = control_df['enddate'] - 1

    cases_df.loc[:, 'outcome'] = 1
    cases_df.loc[:, 'outcomeTime'] = cases_df['start_y']
    cols = ['pid', 'outcome', 'outcomeTime']
    samp_df = pd.concat([control_df[cols], cases_df[cols]])
    samp_df.sort_values(['pid', 'outcome'], inplace=True)
    samp_df.drop_duplicates(['pid'], keep='last', inplace=True)
    samp_df['EVENT_FIELDS'] = 'SAMPLE'
    samp_df['time'] = cdate
    samp_df.rename(columns={'pid': 'id'}, inplace=True)
    samp_df['split'] = -1
    cols = ['EVENT_FIELDS', 'id', 'time', 'outcome', 'outcomeTime', 'split']
    samp_df[cols].to_csv(outfile, sep='\t', index=False)

    print('DOME')


def get_cases_by_tests(cases_df, a1c_df, glu_df, curr_date):
    high_test = pd.concat([a1c_df[a1c_df['val0'] > 6.5], glu_df[glu_df['val0'] > 125]])
    high_test = high_test[high_test['time0'] > curr_date]
    high_test.sort_values(['pid', 'time0'], inplace=True)
    high_test.drop_duplicates('pid', inplace=True)
    new_cases = high_test.merge(cases_df, on='pid', how='left')
    new_cases = new_cases[new_cases['start_x'].notnull()]
    return new_cases



def diab_reports(rep, demo_df, reg_df, curr_date):
    last_year = curr_date - 10000
    diab_in_date = reg_df[(reg_df['stat'] == 2) & (reg_df['start'] < curr_date)]
    diab_after_date = reg_df[(reg_df['stat'] == 2) & (reg_df['start'] > curr_date)]
    pre_in_date = reg_df[(reg_df['stat'] == 1) & (reg_df['start'] < curr_date) &
                         (~reg_df['pid'].isin(diab_in_date['pid']))]
    print(' Diabetics in date ' + str(curr_date) + ': ' + str(diab_in_date.shape[0]))
    print(' Diabetics after date ' + str(curr_date) + ': ' + str(diab_after_date.shape[0]))
    print(' Pre Diabetics in date ' + str(curr_date) + ': ' + str(pre_in_date.shape[0]))

    pre_diab_df = pre_in_date.merge(demo_df, on='pid', how='left')
    pre_diab_df = pre_diab_df[pre_diab_df['age'] >= 18]
    print(' Pre Diabetics in date 18+ ' + str(curr_date) + ': ' + str(pre_diab_df.shape[0]))

    glu_df = rep.get_sig('Glucose')
    glu_df = glu_df[glu_df['pid'].isin(pre_diab_df['pid'])]
    #glu_df.rename(columns={'val0': 'glu', 'time0': 'glu_time'})

    # find the last test before curr_date
    a1c_df = rep.get_sig('HbA1C')
    a1c_df = a1c_df[a1c_df['pid'].isin(pre_diab_df['pid'])]
    #a1c_df.rename(columns={'val0': 'a1c', 'time0': 'a1c_time'})
    test_df = pd.concat([glu_df, a1c_df])
    test_df.sort_values(['pid', 'time0'])

    test_test_prev = test_df[test_df['time0'] < curr_date]
    test_test_prev = test_test_prev.drop_duplicates(['pid'], keep='last')
    test_test_prev = test_test_prev[test_test_prev['time0'] > last_year]
    pre_diab_df = pre_diab_df[pre_diab_df['pid'].isin(test_test_prev['pid'])]
    print(' Prediabtic with test in the last year: '+ str(pre_diab_df.shape[0]))

    test_test_after = test_df[test_df['time0'] > curr_date]
    pre_diab_df_with_tests = pre_diab_df[pre_diab_df['pid'].isin(test_test_after['pid'])]
    print(' Prediabtic with test in the last year and test after: ' + str(pre_diab_df_with_tests.shape[0]))

    cases_df = pre_diab_df[pre_diab_df['pid'].isin(diab_after_date['pid'])]
    control_df = pre_diab_df[~pre_diab_df['pid'].isin(diab_after_date['pid'])]
    control_with_tests_df = control_df[~control_df['pid'].isin(pre_diab_df_with_tests['pid'])]

    print(' Cases: ' + str(cases_df.shape[0]))
    print(' Controls: ' + str(control_df.shape[0]))
    print(' Controls with tests: ' + str(control_with_tests_df.shape[0]))
    # to_csvc(pre_diab_df, outdir, 'cohort')
    # to_csvc(cases_df, outdir, 'cases')
    # to_csvc(control_df, outdir, 'control')
    cases_df = cases_df.merge(diab_after_date, on='pid', how='left')
    cases_by_tests = get_cases_by_tests(cases_df, a1c_df, glu_df, curr_date)
    save_sample_file(control_df, cases_df, curr_date)
    save_sample_file(control_with_tests_df, cases_df, curr_date, 'only_with_res')
    save_sample_file(control_df, cases_by_tests, curr_date, 'cases_by_tests')


if __name__ == '__main__':
    cfg = Configuration()
    rep = med.PidRepository()
    rep.read_all(cfg.repo, [], ['GENDER'])
    print(med.cerr())
    outdir = os.path.join(cfg.work_path, 'reports')
    reg_file = '/home/LinuxDswUser/work/Pre2D/RegistryAndSamples/diabetes.DM_Registry'
    reg_df = pd.read_csv(reg_file, sep='\t', names=['pid', 'start', 'end', 'stat'], usecols=[0, 2, 3, 4])

    curr_date = 20170101
    curr_yaer = int(curr_date/10000)

    gender_df = rep.get_sig('GENDER')
    gender_df.rename(columns={'val0': 'gender'}, inplace=True)
    gender_df['gender'] = gender_df['gender'].astype(str)

    byear_df = rep.get_sig('BYEAR')
    byear_df.rename(columns={'val0': 'byear'}, inplace=True)

    demo_df = gender_df.merge(byear_df, on='pid')
    demo_df['age'] = 2017 - demo_df['byear']
    demo_df['age_group'] = demo_df['age'].map(age_group_map)

    start = rep.get_sig('STARTDATE')
    start.rename(columns={'val0': 'startdate'}, inplace=True)
    end = rep.get_sig('ENDDATE')
    end.rename(columns={'val0': 'enddate'}, inplace=True)

    demo_df = demo_df.merge(start, on='pid')
    demo_df = demo_df.merge(end, on='pid')

    print('Total patients: ' + str(demo_df.shape[0]))
    demo_df = demo_df[(demo_df['enddate'] > curr_date) & (demo_df['startdate'] < curr_date)]
    print('members in date  ' + str(curr_date) + ': ' + str(demo_df.shape[0]))
    #by_group(demo_df, 'age_group', os.path.join(outdir, 'all_by_age.csv'))
    #by_group(demo_df, 'gender', os.path.join(outdir, 'all_by_gender.csv'))
    #by_group(demo_df, ['gender', 'age_group'], os.path.join(outdir, 'all_by_age_gender.csv'))

    diab_reports(rep, demo_df, reg_df, curr_date)