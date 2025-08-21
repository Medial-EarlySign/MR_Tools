#You have dataframe called "df". Please process it to generare signal "BDATE"

#The target dataframe should have those columns:
#    pid
#    signal
#    value_0 - numeric (rep channel type i)

#Source Dataframe - df.head() output:
#     pid  Date    Signal  Value   Unit
#0  82437       BDATE   19820101    
#1  82437       GENDER  F   
#2  82437   2017-08-01 Basophils#    0.1 10^9/l
#3  82437   2017-08-01 Eosinophils#    0.1 10^9/l

#This will be called only if needed - if there are problems in the data. Here we can write code to fix the data.
from signal_processings.process_helper import *
#Take only relevant data for MEMBERSHIP - NOT NEEDED. Will be done by ETL infa
#df=df[df['signal']=='MEMBERSHIP'].reset_index(drop=True)[['pid', 'signal', 'time']]
df=df.rename(columns={'time_0': 'time'})

before_cnt=len(df)
df=df[df['time'].astype(str).map(lambda x: len(x.split(','))==2)].reset_index(drop=True)
if len(df)!=before_cnt:
    print(f'Dropped from {before_cnt} to {len(df)} beacuse of bad MEMBERSHIP format - no 2 tokens')
df['time_0']=df['time'].astype(str).map(lambda x: x.split(',')[0])
df['time_1']=df['time'].astype(str).map(lambda x: x.split(',')[1])

df=test_numeric(df, 'time_0')
df=test_numeric(df, 'time_1')
df['time_0']=df['time_0'].astype(int)
df['time_1']=df['time_1'].astype(int)

df=df[['pid', 'signal', 'time_0', 'time_1']]