#You have dataframe called "df". Please process it to generare signal "DIAGNOSIS"

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    value_0 - string categorical (rep channel type i)

#Source Dataframe - df.head() output(synthetic data example):
#   population index_dato    Code FIRST_DIAGNOSIS_DATE Factor Truncation signal    pid
#0           2  05mar2034   DI702            130aug2051    PVD          4   None  14754
#1           2  05mar2034  DI739C            13aug2051    PVD          5   None  14754
#2           2  05mar2034   DJ449            14jun2051   PULM          4   None  14754
#3           2  05mar2034   DZ049            31jul2051    NaN        .z_   None  14754
#4           2  05mar2034   DZ039            18mar2051    NaN        .z_   None  14754
from signal_processings.helper import *

df['signal'] = 'DIAGNOSIS'
df = df.rename(columns = {'FIRST_DIAGNOSIS_DATE': 'time_0'}).drop(columns=['population', 'index_dato', 'Truncation', 'Factor'])
sz = len(df)
df = df[df['Code'].notna()].reset_index(drop=True)
if len(df)!=sz:
    print(f'After filtering na values left with {len(df)} vs {sz}')

#Remove 4 bad dates
df = df[df['time_0'].apply(lambda x:x[:2]) !='2.' ].reset_index(drop=True)

df['time_0'] = df['time_0'].apply(conv_date)

df['value_0'] = 'ICD10_CODE:' +  df['Code'].astype(str).apply(lambda x: x[1:])