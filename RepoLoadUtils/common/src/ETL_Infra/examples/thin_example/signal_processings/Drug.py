from signal_processings.process_helper import *

print('total removed bad row: ' + str(len(df[df['drugflag']!='Y'])))
df = df[df['drugflag']=='Y'].reset_index(drop=True)

# time cleaning
df = check_and_fix_date(df, col='time_0')

df['value_0'] = 'dc:' + df['value_0'].astype('str')
df.signal = 'Drug'