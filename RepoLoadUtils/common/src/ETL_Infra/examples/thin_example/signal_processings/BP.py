from signal_processings.process_helper import *

thin_signal_mapping = pd.read_csv('configs/thin_signal_mapping.csv', sep='\t')

df = df[df['ahdflag']=='Y'].reset_index(drop=True)

# just BP
df = df[df.ahdcode=='1005010500']

# just numeric values in data fields
df['value_1'] = pd.to_numeric(df.data1, errors='coerce')
df['value_0'] = pd.to_numeric(df.data2, errors='coerce')

to_keep = df.value_0.notna() & df.value_1.notna() & (df.value_0 > df.value_1)

if to_keep.sum() < len(df) / 100:
    breakpoint()

df = df[to_keep]
df['value_0'] = df['value_0'].astype('int')
df['value_1'] = df['value_1'].astype('int')
df['signal'] = 'BP'

df = check_and_fix_date(df, col='time_0')

df = df[['pid', 'signal', 'time_0', 'value_0', 'value_1']]
