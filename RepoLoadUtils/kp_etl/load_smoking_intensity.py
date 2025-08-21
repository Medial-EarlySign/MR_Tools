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

# smoking_intnsity = smoking_intnsity[['pid','sig_name','date','value']]
# smoking_intnsity.to_csv(fileOutIntensity, sep = '\t', index = False, header = False)

df_all = pd.concat([df_cases, df_controls])
df_all['measure_date_int'] = df_all.measure_date.apply(lambda x: x.split('/')[2] + x.split('/')[0] + x.split('/')[1])
df_all.sort_values(['id','measure_date_int'], inplace = True)
df_all.reset_index(inplace = True, drop = True)


df_all_out = df_all[~df_all.tobacco_pak_per_dy.isnull()]
df_out = pd.DataFrame()
df_out['pid'] = df_all_out.id
df_out['sig_name'] = 'Smoking_Intensity'
df_out['date'] = df_all_out.measure_date_int
df_out['value'] = df_all_out.tobacco_pak_per_dy*20
fileOutIntensity = '/server/Work/Users/Ron/KP_3/Smoking_Intensity.txt'
df_out.to_csv(fileOutIntensity, sep = '\t', index = False, header = False)

df_all_out = df_all[~df_all.tobacco_used_years.isnull()]
df_out = pd.DataFrame()
df_out['pid'] = df_all_out.id
df_out['sig_name'] = 'Smoking_Duration'
df_out['date'] = df_all_out.measure_date_int
df_out['value'] = df_all_out.tobacco_used_years
fileOutIntensity = '/server/Work/Users/Ron/KP_3/Smoking_Duration.txt'
df_out.to_csv(fileOutIntensity, sep = '\t', index = False, header = False)



