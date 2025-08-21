#You have dataframe called "df". Please process it to generare signal/s of class "labs"

#Example signal from this class might be BP

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    value_0 - numeric (rep channel type s)
#    value_1 - numeric (rep channel type s)

#Source Dataframe - df.head() output:
#     pid  Date    Signal  Value   Unit
#0  82437       BDATE   19820101    
#1  82437       GENDER  F   
#2  82437   2017-08-01 Basophils#    0.1 10^9/l
#3  82437   2017-08-01 Eosinophils#    0.1 10^9/l

#This will be called only if needed - if there are problems in the data. Here we can write code to fix the data.
from signal_processings.process_helper import *
#Take relevent signals => labs by :sig_types - NOT NEEDED. Will be done by ETL infa
#all_labs= list(filter(lambda sig_name: 'labs' in sig_types[sig_name].classes ,sig_types.keys()))
#df=df[df['signal'].isin(all_labs)].reset_index(drop=True)

#Test date
df=test_numeric(df, 'time_0')
df['time_0']=df['time_0'].astype(int)

df=test_numeric(df, 'value_0', False)

df=df[['pid', 'signal', 'time_0', 'value_0', 'unit']]

generate_labs_mapping_and_units_config(df, 5)
#Please see the file "configs/map_units_stats.cfg" to get stats on labs+units. No need to edit file to fix units.

#df=map_and_fix_units(df) #no need to fix units - client passes in the right units