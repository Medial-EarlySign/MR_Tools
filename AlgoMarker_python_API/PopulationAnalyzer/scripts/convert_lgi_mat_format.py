#!/usr/bin/env python

#Lung: $LUNG_GIT - scripts/alon/get_reference_matrix.for_simulator.sh

import pandas as pd
SOURCE='/server/Work/Users/Alon/LGI/outputs/reference_matrix/features.matrix'
CBC_COUNT='/server/Work/Users/Alon/LGI/outputs/reference_matrix/cbc_counts.matrix'
TARGET='/nas1/Products/LGI-ColonFlag-3.0/Test_Kit/ref_for_pr_analysis.csv'

df = pd.read_csv(SOURCE, usecols=['id','time','outcome','outcome_time','split','pred_0','Age','Gender'])
df_cnt = pd.read_csv(CBC_COUNT)
df = df.rename(columns={'outcome_time':'outcometime'})
df.loc[df['outcometime']%100==0 ,'outcometime'] = df.loc[df['outcometime']%100==0 ,'outcometime'] + 1
df.loc[(df['outcometime']//100)%100==0 ,'outcometime'] = df.loc[(df['outcometime']//100)%100==0 ,'outcometime'] + 100
df.loc[df['time']%100==0 ,'time'] = df.loc[df['time']%100==0 ,'time'] + 1
df.loc[(df['time']//100)%100==0 ,'time'] = df.loc[(df['time']//100)%100==0 ,'time'] + 100

df_cnt.columns = list(map(lambda x: x if not(x.startswith('FTR_')) else x[11:] ,list(df_cnt.columns )))

#Add cols from CBC_COUNT:
df = df.merge(df_cnt.drop(columns=['serial', 'outcome', 'outcome_time', 'split']), on=['id', 'time'])

df['Time-Window'] = (pd.to_datetime( df['outcometime'], format='%Y%m%d') - pd.to_datetime( df['time'], format='%Y%m%d')).dt.days
# Filter controls with less then 730 days?
#df = df[(df['outcome']>0) | (df['Time-Window']>=730)].reset_index(drop=True)

df.loc[df['outcome']<1,'Time-Window'] = 0

df.to_csv(TARGET, index=False)
print(f'Wrote [{TARGET}]')