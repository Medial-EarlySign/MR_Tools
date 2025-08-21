#You have dataframe called "df". Please process it to generare signal "DIAGNOSIS"

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    value_0 - string categorical (rep channel type i)

#Source Dataframe - df.head() output:
#     pid  Date    Signal  Value   Unit
#0  82437       BDATE   19820101    
#1  82437       GENDER  F   
#2  82437   2017-08-01 Basophils#    0.1 10^9/l
#3  82437   2017-08-01 Eosinophils#    0.1 10^9/l

#This will be called only if needed - if there are problems in the data. Here we can write code to fix the data.
from signal_processings.process_helper import *
#Take only Diagnosis - NOT NEEDED. Will be done by ETL infa
#df=df[df['signal']=='DIAGNOSIS'].reset_index(drop=True)[['pid', 'signal', 'value_0']]

df=test_numeric(df, 'time_0')
df['time_0']=df['time_0'].astype(int)

df['value_0'] = df['value_0'].astype(str).map(lambda x: x.replace('.', ''))
before_nana=len(df)
df=df[df['value_0'].notnull()].reset_index(drop=True)
if len(df)!=before_nana:
    print(f'Removed empty diagnosis. size was {before_nana}, now {len(df)}. Excluded {before_nana-len(df)}')

df=df[['pid', 'signal', 'time_0', 'value_0']]