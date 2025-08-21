import sys
import os
import numpy as np
import pandas as pd
from utils import fixOS, read_first_line, get_dict_set_df
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from get_funcs import find_sickle_cell, get_sig_df, get_dict_map, SOURCE

if SOURCE == 'rep':
    import medpython as med


def print_vc(ser, name=''):
    print('')
    vc_cnt = ser.value_counts(dropna=False)
    vc_cnt.name = 'cnt'
    vc_per = ser.value_counts(dropna=False, normalize=True)
    vc_per.name = 'per'
    vc = pd.concat([vc_cnt, vc_per], axis=1)

    print(', '.join(vc.index.astype(str)))
    print(', '.join(vc['cnt'].astype(str)))
    print(', '.join(vc['per'].astype(str)))
    print('')
    print('===================================')
    vct = vc.T
    vct.rename(index={'cnt': name+' cnt', 'per': name}, inplace=True)
    return vct





def vc_record(name, ser):
    print('')
    vc = ser.value_counts(dropna=False)
    #dict1 = {'name': name}
    vc.name = name
    #for i, v in vc.items():
    #    dict1[v] = i

    return vc


def print_to_copy(df):
    print(' , ' + ', '.join(df.columns))
    for i in range(0, df.shape[0]):
        print(df.iloc[i].name + ', ' + ', '.join([str(x) for x in df.iloc[i].values]))


def total_counts(rep, sigs_files_path):
    mem_df = get_sig_df('MEMBERSHIP', rep, sigs_files_path)
    mem_df['date_end'] = mem_df['date_end'].replace(20991231, 20190601)
    mem_df['days_diff'] = pd.to_datetime(mem_df['date_end'], format='%Y%m%d') - pd.to_datetime(mem_df['date_start'],
                                                                                               format='%Y%m%d')
    mem_df['days_diff'] = mem_df['days_diff'].dt.days
    grp = mem_df.groupby('pid')
    sum_df = pd.concat([grp['days_diff'].sum(), grp['date_end'].max(), grp['date_start'].min()], axis=1)
    byear_df = get_sig_df('BYEAR', rep, sigs_files_path)
    sum_df = sum_df.merge(byear_df, on='pid')
    sum_df['age_start'] = (sum_df['date_start'] / 10000).astype(int) - sum_df['byear']
    sum_df['age_end'] = (sum_df['date_end'] / 10000).astype(int) - sum_df['byear']
    pop_all_df = sum_df[(sum_df['days_diff'] >= 730)]

    race_df = get_sig_df('RACE', rep, sigs_files_path)
    race_map = get_dict_map(fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/dicts'), 'RACE')
    race_df['race'] = race_df['race'].map(race_map)
    vc_df_all = pd.DataFrame()
    name = 'with 2 years membership'
    print(name + ': ' + str(pop_all_df.shape[0]))
    pop_all_df = pop_all_df.merge(race_df, on='pid')
    print(' Race distribution: ')
    vc_df = print_vc(pop_all_df['race'], name)
    vc_df_all = vc_df_all.append(vc_df)

    pop_df = pop_all_df[(pop_all_df['age_start'] < 80) & (pop_all_df['age_end'] > 40)]
    name = 'ages 40-80 with 2 years membership'
    print(name + ' : ' + str(pop_df.shape[0]))
    print(' Race distribution: ')
    print_vc(pop_df['race'])
    vc_df = print_vc(pop_df['race'], name)
    vc_df_all = vc_df_all.append(vc_df)

    print('Distribution with HbA1C tests')
    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)
    a1c_df.sort_values(by=['pid', 'hba1c'], inplace=True)
    a1c_df.drop_duplicates('pid', keep='last', inplace=True)
    with_a1c_df = pop_df.merge(a1c_df, on='pid', how='left')
    vc_df = print_vc(with_a1c_df[with_a1c_df['hba1c'].notnull()]['race'], 'with HbA1C tests')
    vc_df_all = vc_df_all.append(vc_df)

    print(' Diabetic distribution')
    pre2d_reg_file = fixOS('/server/Work/Users/Tamar/kpnw_diabetes_load/FinalSignals/DM_Registry')
    pre2d_df = pd.read_csv(pre2d_reg_file, sep='\t', names=['pid', 'sig', 'from_date', 'to_date', 'stat'])
    diab_df = pre2d_df[pre2d_df['stat'] == 2]
    pop_diab = pop_df.merge(diab_df, on='pid', how='left')
    vc_df = print_vc(pop_diab[pop_diab['stat'].notnull()]['race'], 'Diabetic')
    vc_df_all = vc_df_all.append(vc_df)

    print(' Pre Diabetic distribution')
    pre_diab_df = pre2d_df[pre2d_df['stat'] == 1]
    pop_pre_diab = pop_df.merge(pre_diab_df, on='pid', how='left')
    vc_df = print_vc(pop_pre_diab[pop_pre_diab['stat'].notnull()]['race'], 'Pre Diabetic')
    vc_df_all = vc_df_all.append(vc_df)

    print('Distribution of Sickle-cell')
    scl_df = find_sickle_cell(rep, sigs_files_path)
    pop_scl = pop_df.merge(scl_df, on='pid', how='left')
    pop_scl = pop_scl[pop_scl['scl'].notnull()]
    vc_df = print_vc(pop_scl['race'], 'with Sickle-cell ')
    vc_df_all = vc_df_all.append(vc_df)

    scl_diab = pop_diab.merge(pop_scl, on='pid', how='right')
    scl_diab = scl_diab[(scl_diab['stat'].notnull())]
    vc_df = print_vc(scl_diab['race_x'], 'with Sickle-cell & diabetic')
    vc_df_all = vc_df_all.append(vc_df)
    cols = ['White', 'Unknown_Race', 'Asian', 'Black_or_African_American', 'Declined_to_State',
            'Native_Hawaiian_and_Other_Pacific_Islander', 'Some_Other_Race', 'American_Indian_and_Alaska_Native', 'Multiracial']
    print_to_copy(vc_df_all[cols])


def counts_at_date(at_date, rep, sigs_files_path):
    mem_df = get_sig_df('MEMBERSHIP', rep, sigs_files_path)
    mem_df['date_end'] = mem_df['date_end'].replace(20991231, 20190601)
    mem_df['at_date'] = at_date
    mem_df = mem_df[(mem_df['date_end'] > at_date) & (mem_df['date_end'] > at_date)]
    mem_df['days_diff'] = pd.to_datetime(mem_df['at_date'], format='%Y%m%d') - pd.to_datetime(mem_df['date_start'], format='%Y%m%d')
    mem_df['days_diff'] = mem_df['days_diff'].dt.days
    mem_df = mem_df[mem_df['days_diff'] > 730]
    print('>2 years membership at '+str(at_date))

    race_df = get_sig_df('RACE', rep, sigs_files_path)
    race_map = get_dict_map(fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/dicts'), 'RACE')
    race_df['race'] = race_df['race'].map(race_map)
    vc_df_all = pd.DataFrame()
    pop_all_df = mem_df.merge(race_df, on='pid')
    print(' Race distribution: ')
    vc_df = print_vc(pop_all_df['race'], 'with 2 years membership')
    vc_df_all = vc_df_all.append(vc_df)

    byear_df = get_sig_df('BYEAR', rep, sigs_files_path)
    pop_df = pop_all_df.merge(byear_df, on='pid')
    pop_df['age'] = int(at_date/10000) - pop_df['byear']
    #for i, v in pop_df['age'].value_counts().items():
    #    print(i,v)
    pop_df = pop_df[(pop_df['age']>40) & (pop_df['age']<80)]
    vc_df = print_vc(pop_df['race'], 'ages 40-80 with 2 years membership')
    vc_df_all = vc_df_all.append(vc_df)

    print('Distribution with HbA1C tests')
    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)
    a1c_df = a1c_df[a1c_df['date'] <= at_date]
    a1c_df.drop_duplicates('pid', keep='last', inplace=True)
    with_a1c_df = pop_df.merge(a1c_df, on='pid', how='left')
    vc_df = print_vc(with_a1c_df[with_a1c_df['hba1c'].notnull()]['race'], 'with HbA1C tests')
    vc_df_all = vc_df_all.append(vc_df)

    print(' Diabetic distribution')
    #pre2d_reg_file = fixOS('/nas1/Work/AlgoMarkers/Pre2D/kpnw_no_adm/RegistryAndSamples/diabetes.DM_Registry')
    pre2d_reg_file = fixOS('W:\\Users\\Tamar\\kpnw_diabetes_load\\FinalSignals\\DM_Registry')
    pre2d_df = pd.read_csv(pre2d_reg_file, sep='\t', names=['pid', 'sig', 'from_date', 'to_date', 'stat'])
    diab_df = pre2d_df[(pre2d_df['stat'] == 2) & (pre2d_df['from_date'] <= at_date) & (pre2d_df['to_date'] > at_date)]
    pop_diab = pop_df.merge(diab_df, on='pid', how='left')
    pop_diab = pop_diab[pop_diab['stat'].notnull()]
    vc_df = print_vc(pop_diab['race'], 'Diabetic')
    vc_df_all = vc_df_all.append(vc_df)

    print(' Pre Diabetic distribution')
    pre_diab_df = pre2d_df[(pre2d_df['stat'] == 1) & (pre2d_df['from_date'] <= at_date) & (pre2d_df['to_date'] > at_date)]
    pop_pre_diab = pop_df.merge(pre_diab_df, on='pid', how='left')
    vc_df = print_vc(pop_pre_diab[pop_pre_diab['stat'].notnull()]['race'], 'Pre Diabetic')
    vc_df_all = vc_df_all.append(vc_df)

    print('Distribution of Sickle-cell')
    scl_df = find_sickle_cell(rep, sigs_files_path)
    pop_scl = pop_df.merge(scl_df, on='pid', how='left')
    pop_scl = pop_scl[pop_scl['scl'].notnull()]
    vc_df = print_vc(pop_scl['race'], 'with Sickle-cell')
    vc_df_all = vc_df_all.append(vc_df)

    scl_diab = pop_diab.merge(pop_scl, on='pid', how='right')
    scl_diab = scl_diab[(scl_diab['byear_x'].notnull()) & (scl_diab['stat'].notnull())]
    scl_diab = scl_diab[(scl_diab['stat'].notnull())]
    vc_df = print_vc(scl_diab['race_x'], 'with Sickle-cell & diabetic')
    vc_df_all = vc_df_all.append(vc_df)
    cols = ['White', 'Unknown_Race', 'Asian', 'Black_or_African_American', 'Declined_to_State',
            'Native_Hawaiian_and_Other_Pacific_Islander', 'Some_Other_Race', 'American_Indian_and_Alaska_Native',
            'Multiracial']
    print_to_copy(vc_df_all[cols])


def a1c_comp(sigs_files_path):
    mem_df = get_sig_df('MEMBERSHIP', rep, sigs_files_path)
    mem_df['date_end'] = mem_df['date_end'].replace(20991231, 20190601)
    mem_df['days_diff'] = pd.to_datetime(mem_df['date_end'], format='%Y%m%d') - pd.to_datetime(mem_df['date_start'],
                                                                                               format='%Y%m%d')
    mem_df['days_diff'] = mem_df['days_diff'].dt.days
    grp = mem_df.groupby('pid')
    sum_df = pd.concat([grp['days_diff'].sum(), grp['date_end'].max(), grp['date_start'].min()], axis=1)
    byear_df = get_sig_df('BYEAR', rep, sigs_files_path)
    sum_df = sum_df.merge(byear_df, on='pid')
    pop_df = sum_df[(sum_df['days_diff'] >= 730)]

    race_df = get_sig_df('RACE', rep, sigs_files_path)
    race_map = get_dict_map(fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/dicts'), 'RACE')
    race_df['race'] = race_df['race'].map(race_map)
    pop_df = pop_df.merge(race_df, on='pid', how='left')

    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)
    a1c_df = a1c_df.merge(pop_df, on='pid', how='left')
    a1c_df = a1c_df[a1c_df['byear'].notnull()]
    a1c_df['age'] = (a1c_df['date']/10000).astype(int) - a1c_df['byear']
    a1c_df = a1c_df[(a1c_df['age'] > 40) & (a1c_df['age'] < 80)]
    a1c_df['hba1c'] = a1c_df['hba1c'].round(2)

    pre2d_reg_file = fixOS('W:\\Users\\Tamar\\kpnw_diabetes_load\\FinalSignals\\DM_Registry')
    pre2d_df = pd.read_csv(pre2d_reg_file, sep='\t', names=['pid', 'sig', 'from_date', 'to_date', 'stat'])
    a1c_df = a1c_df.merge(pre2d_df, on='pid', how='left')
    a1c_df = a1c_df[(a1c_df['date'] >= a1c_df['from_date']) & (a1c_df['date'] < a1c_df['to_date'])]
    a1c_df1 = a1c_df[['pid', 'date', 'hba1c', 'age', 'stat', 'race']]
    #a1c_df1 = a1c_df[['pid', 'date', 'hba1c', 'stat', 'race']]
    #a1c_df1.to_csv(os.path.join(sigs_files_path, 'HbA1C_vec.csv'), sep=',', index=True)

    dct_list = pd.DataFrame()
    print('HbA1C dist of white people')
    white_df = a1c_df1[a1c_df1['race'] == 'White']
    dct_list['White'] = white_df['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of  Black_or_African_American people')
    black_df = a1c_df1[a1c_df1['race'] == 'Black_or_African_American']
    dct_list['Black'] = black_df['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of people with diebetis')
    with_db = a1c_df1[a1c_df1['stat'] == 2]
    dct_list['diabetic'] = with_db['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of people with pre diabetic')
    pre_db = a1c_df1[a1c_df1['stat'] == 1]
    dct_list['pre diabetic'] = pre_db['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of people with no diabetic')
    without_db = a1c_df1[a1c_df1['stat'] == 0]
    dct_list['no diabetic'] = without_db['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of white people with diabetic')
    white_diab_df = a1c_df1[(a1c_df1['race'] == 'White') & (a1c_df1['stat'] == 2)]
    dct_list['White and diabetic'] = white_diab_df['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of Black_or_African_American people with diabetic')
    black_diab_df = a1c_df1[(a1c_df1['race'] == 'Black_or_African_American') & (a1c_df1['stat'] == 2)]
    dct_list['Black and diabetic'] = black_diab_df['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of white people pre diabetic')
    white_pre_df = a1c_df1[(a1c_df1['race'] == 'White') & (a1c_df1['stat'] == 1)]
    dct_list['White and pre diabetic'] = white_pre_df['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of Black_or_African_American people with diabetic')
    black_pre_df = a1c_df1[(a1c_df1['race'] == 'Black_or_African_American') & (a1c_df1['stat'] == 1)]
    dct_list['Black and pre diabetic'] = black_pre_df['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of white people no diabetic')
    white_no_df = a1c_df1[(a1c_df1['race'] == 'White') & (a1c_df1['stat'] == 0)]
    dct_list['White no diabetic'] = white_no_df['hba1c'].value_counts(normalize=True)

    print('HbA1C dist of Black_or_African_American people no diabetic')
    black_no_df = a1c_df1[(a1c_df1['race'] == 'Black_or_African_American') & (a1c_df1['stat'] == 0)]
    dct_list['Black no diabetic'] = black_no_df['hba1c'].value_counts(normalize=True)
    print('population, mean, median')
    print('White, ' + str(white_df['hba1c'].mean()) + ', ' + str(white_df['hba1c'].median()))
    print('Black, ' + str(black_df['hba1c'].mean()) + ', ' + str(black_df['hba1c'].median()))
    print('Diabetic, ' + str(with_db['hba1c'].mean()) + ', ' + str(with_db['hba1c'].median()))
    print('Pre Diabetic, ' + str(pre_db['hba1c'].mean()) + ', ' + str(pre_db['hba1c'].median()))
    print('No Diabetic, ' + str(without_db['hba1c'].mean()) + ', ' + str(without_db['hba1c'].median()))
    print('Withe w Diabetic, ' + str(white_diab_df['hba1c'].mean()) + ', ' + str(white_diab_df['hba1c'].median()))
    print('Balck w Diabetic, ' + str(black_diab_df['hba1c'].mean()) + ', ' + str(black_diab_df['hba1c'].median()))
    print('White w pre, ' + str(white_pre_df['hba1c'].mean()) + ', ' + str(white_pre_df['hba1c'].median()))
    print('balck w pre, ' + str(black_pre_df['hba1c'].mean()) + ', ' + str(black_pre_df['hba1c'].median()))
    print('White w\o Diabetic, ' + str(white_no_df['hba1c'].mean()) + ', ' + str(white_no_df['hba1c'].median()))
    print('Black w\o Diabetic, ' + str(black_no_df['hba1c'].mean()) + ', ' + str(black_no_df['hba1c'].median()))

    scl_df = find_sickle_cell(rep, sigs_files_path)
    scl_pid = scl_df['pid'].unique()
    a1c_scl = a1c_df1[a1c_df1['pid'].isin(scl_pid)]
    dct_list['sickle cell'] = a1c_scl['hba1c'].value_counts(normalize=True)
    print('with sickle cell, ' + str(a1c_scl['hba1c'].mean()) + ', ' + str(a1c_scl['hba1c'].median()))

    #a1c_df[['pid', 'date', 'HbA1C', 'age', 'stat', 'race']].to_csv(os.path.join(sigs_files_path, 'hba1c.csv'), sep=',', index=False)
    df = pd.DataFrame(dct_list)
    df.to_csv(os.path.join(sigs_files_path, 'HbA1C_hist_norm.csv'), sep=',', index=True)
    #print(df)


def count_tests(rep, sigs_files_path):
    mem_df = get_sig_df('MEMBERSHIP', rep, sigs_files_path)
    mem_df['date_end'] = mem_df['date_end'].replace(20991231, 20190601)
    mem_df['days_diff'] = pd.to_datetime(mem_df['date_end'], format='%Y%m%d') - pd.to_datetime(mem_df['date_start'], format='%Y%m%d')
    mem_df['days_diff'] = mem_df['days_diff'].dt.days

    len_df = mem_df.groupby('pid')['days_diff'].sum().rename('mem_len')

    race_df = get_sig_df('RACE', rep, sigs_files_path)

    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)
    a1c_df = a1c_df.merge(mem_df, on='pid', how='left')
    a1c_df = a1c_df[(a1c_df['date'] >= a1c_df['date_start']) & (a1c_df['date'] <= a1c_df['date_end'])]
    a1c_df = a1c_df.merge(race_df, on='pid')
    grp_a1c = a1c_df.groupby('pid')

    glu_df = get_sig_df('Glucose', rep, sigs_files_path)
    glu_df = glu_df.merge(mem_df, on='pid', how='left')
    glu_df = glu_df[(glu_df['date'] >= glu_df['date_start']) & (glu_df['date'] <= glu_df['date_end'])]
    glu_df = glu_df.merge(race_df, on='pid')
    grp_glu = glu_df.groupby('pid')

    sum_df = pd.concat([grp_a1c['hba1c'].count().rename('hba1c_count'),
                       grp_a1c['race'].first().rename('race1'),
                       grp_glu['glucose'].count().rename('glucose_count'),
                       grp_glu['race'].first().rename('race2'), len_df], axis=1)
    sum_df['hba1c_count'] = (sum_df['hba1c_count']/sum_df['mem_len'])*365
    sum_df['hba1c_count'] = sum_df['hba1c_count'].round(1)
    sum_df['glucose_count'] = (sum_df['glucose_count'] / sum_df['mem_len']) * 365
    sum_df['glucose_count'] = sum_df['glucose_count'].round(1)
    name = 'hba1c_count'
    vc_ser = sum_df['hba1c_count']
    vc_df_all = vc_ser.value_counts(dropna=False, normalize=False).rename(name)
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=True).rename(name+'_p')], axis=1)

    name = 'hba1c_count-Black'
    vc_ser = sum_df[sum_df['race1'] == 1008]['hba1c_count']
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=False).rename(name)], axis=1)
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=True).rename(name + '_p')], axis=1)

    name = 'hba1c_count-White'
    vc_ser = sum_df[sum_df['race1'] == 1005]['hba1c_count']
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=False).rename(name)], axis=1)
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=True).rename(name + '_p')], axis=1)

    name = 'glucose_count'
    vc_ser = sum_df['glucose_count']
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=False).rename(name)], axis=1)
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=True).rename(name + '_p')], axis=1)

    name = 'glucose_count-Black'
    vc_ser = sum_df[sum_df['race2'] == 1008]['glucose_count']
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=False).rename(name)], axis=1)
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=True).rename(name + '_p')], axis=1)

    name = 'glucose_count-White'
    vc_ser = sum_df[sum_df['race2'] == 1005]['glucose_count']
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=False).rename(name)], axis=1)
    vc_df_all = pd.concat([vc_df_all, vc_ser.value_counts(dropna=False, normalize=True).rename(name + '_p')], axis=1)

    vc_df_all.to_csv(os.path.join(sigs_files_path, 'tests_counts_per_year.csv'), sep=',', index=True)
    print('DONE')


def a1c_bmi(rep, sigs_files_path):
    mem_df = get_sig_df('MEMBERSHIP', rep, sigs_files_path)
    mem_df['date_end'] = mem_df['date_end'].replace(20991231, 20190601)

    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)

    race_df = get_sig_df('RACE', rep, sigs_files_path)
    race_map = get_dict_map(fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/dicts'), 'RACE')
    race_df['race'] = race_df['race'].map(race_map)

    bmi_df = get_sig_df('BMI', rep, sigs_files_path)
    bmi_df['bmi'] = (bmi_df['bmi']/2).round(0)*2

    #pop_df = pop_df.merge(race_df, on='pid', how='left')
    a1c_df = get_sig_df('HbA1C', rep, sigs_files_path)
    a1c_df['hba1c'] = a1c_df['hba1c'].round(2)

    a1c_df = a1c_df.merge(mem_df, on='pid', how='left')
    a1c_df = a1c_df[(a1c_df['date'] >= a1c_df['date_start']) & (a1c_df['date'] <= a1c_df['date_end'])]
    a1c_df = a1c_df.merge(race_df, on='pid')

    a1c_df = a1c_df.merge(bmi_df, on='pid')
    a1c_df['days_diff'] = pd.to_datetime(a1c_df['date_x'], format='%Y%m%d') - pd.to_datetime(a1c_df['date_y'], format='%Y%m%d')
    a1c_df['days_diff'] = a1c_df['days_diff'].dt.days.abs()
    a1c_df.sort_values(by=['pid', 'date_x', 'days_diff'], inplace=True)
    a1c_df.drop_duplicates(subset=['pid', 'date_x'], keep='first', inplace=True)
    a1c_df = a1c_df[['pid', 'date_x', 'hba1c', 'race', 'bmi']]
    grb_bmi = a1c_df.groupby('bmi')

    all_df = pd.concat([grb_bmi['hba1c'].mean().rename('mean'),
                        grb_bmi['hba1c'].median().rename('median'),
                        a1c_df['bmi'].value_counts().rename('count'),
                        a1c_df['bmi'].value_counts(normalize=True).rename('count_norm')], axis=1)
    all_df.to_csv(os.path.join(sigs_files_path, 'HbA1C_bmi_all.csv'), sep=',', index=True)

    a1c_white = a1c_df[a1c_df['race'] == 'White']
    grb_bmi = a1c_white.groupby('bmi')
    white_df = pd.concat([grb_bmi['hba1c'].mean().rename('mean'),
                          grb_bmi['hba1c'].median().rename('median'),
                          a1c_white['bmi'].value_counts().rename('count'),
                          a1c_white['bmi'].value_counts(normalize=True).rename('count_norm')], axis=1)
    white_df.to_csv(os.path.join(sigs_files_path, 'HbA1C_bmi_white.csv'), sep=',', index=True)

    a1c_black = a1c_df[a1c_df['race'] == 'Black_or_African_American']
    grb_bmi = a1c_black.groupby('bmi')
    black_df = pd.concat([grb_bmi['hba1c'].mean().rename('mean'),
                          grb_bmi['hba1c'].median().rename('median'),
                          a1c_black['bmi'].value_counts().rename('count'),
                          a1c_black['bmi'].value_counts(normalize=True).rename('count_norm')], axis=1)
    black_df.to_csv(os.path.join(sigs_files_path, 'HbA1C_bmi_black.csv'), sep=',', index=True)

    print('DONE')


if __name__ == '__main__':
    kp_rep = fixOS('/home/Repositories/KPNW/kpnw_jun19/kpnw.repository')
    kp_diab_rep = fixOS('/server/Work/CancerData/Repositories/KPNW/kpnw_diabetes/kpnw.repository')
    sigs_files_path = fixOS('W:\\Users\\Tamar\\kpnw_diabetes_load\\temp\\')

    if SOURCE == 'rep':
        rep = med.PidRepository()
        rep.read_all(kp_rep, [], [])
        print(med.cerr())
    else:
        rep = None

    #total_counts(rep, sigs_files_path)
    #counts_at_date(20180101, rep, sigs_files_path)
    #a1c_comp(sigs_files_path)
    #a1c_bmi(rep, sigs_files_path)
    count_tests(rep, sigs_files_path)

    #print(pop_df)
