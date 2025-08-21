#You have dataframe called "df". Please process it to generare signal "DIAGNOSIS"

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    value_0 - numeric (rep channel type i)

#Source Dataframe - df.head() output(synthetic data):
#  eventdate datatype  medcode medflag category signal  pid
#0  20000624       01  A76..00       R        3   None    1
#1  19980213       01  ZZZZZ00       R        3   None    2
#2  19990612       01  ZZZZZ00       R        3   None    2
#3  20011028       01  ZZZZZ00       R        3   None    2
#4  19961111       01  ZZZZZ00       R        3   None    2

import re
from signal_processings.process_helper import *

print('Filtered %d(%2.1f%%) bad flag rows'%( len(df[df['medflag']!='R']), 100*len(df[df['medflag']!='R'])/len(df) ))
df = df[df['medflag']=='R'].reset_index(drop=True)

data = df.copy()
print('Total medical/diagnosis rows: ' + str(len(data)) + '\n')

data.rename(columns={'eventdate':'time_0', 'medcode':'value_0'}, inplace=True)
data = check_and_fix_date(data, col='time_0')
data['signal'] = 'DIAGNOSIS'
data['value_0']= 'ReadCode:' + data['value_0']

# keep just signal inside repo time
before = len(data)
data = data[data.time_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
after = len(data)
if before > after:
    print('Drop ' + str(before-after) + ' medical records out of ' + str(before) + ' because date of signal out of repo range')
    
# remove readcodes with ilegal characters
data['MES__ILEGAL_CNT'] = data['value_0'].map(lambda x: len(re.compile('[, "\'\t;]').findall(x))!=0)
if (data['MES__ILEGAL_CNT'].sum() > 0):
    print('Drop ' + str(data['MES__ILEGAL_CNT'].sum()) + ' medical records out of ' + str(len(data)) + ' because code has illegal charcters')
    data = data[data['MES__ILEGAL_CNT']==0]
    
# To add seperate Ethnicity signal
data.loc[(data.value_0.str.startswith('ReadCode:9S')) | (data.value_0.str.startswith('ReadCode:9t')) | (data.value_0.str.startswith('ReadCode:9T')), 'signal'] = 'Ethnicity'

df = data[['pid', 'signal', 'time_0', 'value_0']]


