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
#Take only relevant data for GENDER - NOT NEEDED. Will be done by ETL infa
#df=df[df['signal']=='GENDER'].reset_index(drop=True)[['pid', 'signal', 'value_0']]

before_nana=len(df)
df=df[df['value_0'].notnull()].reset_index(drop=True)
threshold_missings=10
df['signal']='GENDER'

if len(df)!=before_nana:
    print(f'Removed empty GENDER. size was {before_nana}, now {len(df)}. Excluded {before_nana-len(df)}')

    rr=100-len(df)/before_nana*100
    if rr>threshold_missings:
        raise NameError(f'Dropped more than {threshold_missings}% in GENDER')

df=df[['pid', 'signal', 'value_0']]