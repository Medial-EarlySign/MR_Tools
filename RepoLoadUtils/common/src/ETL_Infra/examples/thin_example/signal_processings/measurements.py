from signal_processings.process_helper import *

# readcodes for Height and Weight
rc_Weight = '22A..00'
rc_all_Weight = '22A'
rc_Height = '229..00'
rc_all_Height = '229'

flt_cnt=len(df[df['ahdflag']!='Y'])
print(f'Filtered bad rows: {flt_cnt}')
df = df[df['ahdflag']=='Y'].reset_index(drop=True)

# Weight and BMI
################
df_Weight = df[df.medcode.map(lambda x: x[0:3]=='22A')].copy()
before = len(df_Weight)
df_Weight = df_Weight[df_Weight.medcode==rc_Weight]
after = len(df_Weight)
if after < before:
    print('Drop ' + str(after - before) + ' out of ' + str(before) + ' Weight input because code is not "standard Weight"')

res = {}
my_dict = {'Weight':'data1', 'BMI':'data3'}
for m in my_dict.keys():
    col = my_dict[m]
    tmp = df_Weight[['pid', 'time_0', col]].copy()
    # just numeric values > 0 in data field
    tmp[col] = pd.to_numeric(tmp[col], errors='coerce')
    tmp = tmp[tmp[col].notna()]
    tmp[tmp[col] > 0]
    tmp['signal'] = m
    tmp.rename(columns={col:'value_0'}, inplace=True)
    print(str(len(tmp)) + ' ' + m + ' valid rows')
    res[m] = tmp

# Height
########
df_Height = df[df.medcode.map(lambda x: x[0:3]=='229')].copy()
before = len(df_Height)
df_Height = df_Height[df_Height.medcode==rc_Height]
after = len(df_Height)
if after < before:
    print('Drop ' + str(after - before) + ' out of ' + str(before) + ' Weight input because code is not "standard Height"')

# just numeric values > 0 in data field
df_Height['data1'] = pd.to_numeric(df_Height['data1'], errors='coerce')
df_Height = df_Height[df_Height['data1'].notna()]
df_Height[df_Height['data1'] > 0]

# move to cm instead of meter
df_Height.loc[df_Height.data1 < 10, 'data1'] *= 100

df_Height.rename(columns={'data1':'value_0'}, inplace=True)
df_Height['signal'] = 'Height'
print(str(len(df_Height)) + ' height valid rows')

# concat
########
df = pd.concat([df_Height, res['Weight'], res['BMI']])

# remove invalid values
before = len(df)
df = df[df.value_0 > 0]
after = len(df)
if after < before:
    print('Drop ' + str(after - before) + ' out of ' + str(before) + ' Weight/Height/BMI input because value <= 0')

# check and fix time
df = check_and_fix_date(df, col='time_0')

before = len(df)
df = df[df.time_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
after = len(df)
if before > after:
    print('Drop ' + str(before-after) + ' lab records because date of signal out of repo range')
    
df = df[['pid', 'signal', 'time_0', 'value_0']]