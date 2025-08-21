# -*- coding: utf-8 -*-
"""
Created on Sun Sep  1 14:36:54 2019

@author: ron-internal
"""

import pandas as pd
df_cases = pd.read_csv('/server/Data/kpsc/15-08-2019/cases_smoking_new.txt',sep = '\t')
df_controls = pd.read_csv('/server/Data/kpsc/15-08-2019/controls_smoking_new.txt',sep = '\t')
df_cases_old = pd.read_csv('/server/Data/kpsc/03-05-2018/cases_smoking.txt',sep = '\t')
df_controls_old = pd.read_csv('/server/Data/kpsc/03-05-2018/controls_smoking.txt',sep = '\t')
df_demo_cases = pd.read_csv('/server/Data/kpsc/03-05-2018/cases_demo.txt',sep = '\t')
df_demo_controls = pd.read_csv('/server/Data/kpsc/03-05-2018/controls_demo.txt',sep = '\t')


df_all = pd.concat([df_cases, df_controls])

df_cases_old['type'] = 'old'
df_cases['type'] = 'new'

# cases
df_cases_comb = pd.concat([df_cases_old,df_cases[df_cases_old.columns]])
df_cases_comb.loc[:,'measure_date_new'] = df_cases_comb.measure_date.apply(lambda x: x.split('/')[2] + x.split('/')[0] + x.split('/')[1])
df_cases_comb.sort_values(['id','measure_date_new'], inplace = True)
df_cases_comb.drop_duplicates(['id','measure_date_new','pkyr'], inplace = True, keep = False)
is_eq = df_cases.pkyr == df_cases.tobacco_pak_per_dy * df_cases.tobacco_used_years
df_cases[((df_cases.pkyr < df_cases.tobacco_pak_per_dy * df_cases.tobacco_used_years - 1) | (df_cases.pkyr > df_cases.tobacco_pak_per_dy * df_cases.tobacco_used_years + 1) )& ~df_cases.pkyr.isnull()]


# controls
df_controls_comb = pd.concat([df_controls_old,df_controls[df_controls_old.columns]])
df_controls_comb.loc[:,'measure_date_new'] = df_controls_comb.measure_date.apply(lambda x: x.split('/')[2] + x.split('/')[0] + x.split('/')[1])
df_controls_comb.sort_values(['id','measure_date_new'], inplace = True)
df_controls_comb.drop_duplicates(['id','measure_date_new','pkyr'], inplace = True, keep = False)
is_eq = df_controls.pkyr == df_controls.tobacco_pak_per_dy * df_controls.tobacco_used_years
df_controls[((df_controls.pkyr < df_controls.tobacco_pak_per_dy * df_controls.tobacco_used_years - 1) | (df_controls.pkyr > df_controls.tobacco_pak_per_dy * df_controls.tobacco_used_years + 1) )& ~df_controls.pkyr.isnull()]

# check values:

import datetime

def calcAge(df):
    df['measure_date_dt'] = df['measure_date'].apply(lambda x : datetime.datetime(int(x.split('/')[2]), int(x.split('/')[0]), int(x.split('/')[1])))
    df['dob_dt'] = df['dob'].apply(lambda x : datetime.datetime(int(x.split('/')[2]), int(x.split('/')[0]), int(x.split('/')[1])))
    df['dob_age'] = df['measure_date_dt']  - df['dob_dt'] 
    df['age'] = df['dob_age'].apply(lambda x : x.days/365)

    

df_demo_all = pd.concat([df_demo_cases,df_demo_controls])
df_all.tobacco_pak_per_dy.max()
df_all[df_all.tobacco_used_years == df_all.tobacco_used_years.max()]
df_demo_cases[df_demo_cases.id == 198823]
tt = pd.merge(df_all,df_demo_all, on = 'id',how = 'left')
calcAge(tt)

df_all.loc[:,'dob'] = tt.dob
df_all.loc[:,'age'] = tt.age
df_all[(df_all.age < df_all.tobacco_used_years) & ~df_all.tobacco_used_years.isnull()].id.nunique()
