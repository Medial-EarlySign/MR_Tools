#You have dataframe called "df". Please process it to generare signal/s of class "smoking"

#Example signal from this class might be Smoking_Quit_Date

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    value_0 - string categorical (rep channel type f)

#Source Dataframe - df.head() output(synthetic data):
#     time_0     ahdcode ahdflag      data1   data2      data3 data4 data5 data6  medcode signal  pid
#0  19931126  1009060000       Y             INP001                N           Y  4K22.00   None    1
#1  19970804  2007040200       Y  76.000000          12.600000                    22A..00   None    3
#2  19970531  1005060000       Y          Y       3                               136..00   None    3
#3  19960109  3002080000       Y          N       0                               137L.00   None    4
#4  19971216  4006400092       Y                                                  537..00   None    4


from signal_processings.process_helper import * 
from configs.smoking_config import *

flt_cnt=len(df[df['ahdflag']!='Y'])
print(f'Filtered bad rows: {flt_cnt}')
df = df[df['ahdflag']=='Y'].reset_index(drop=True)
df = df[df.medcode.str.startswith('137')]

# remove irrelevant codes
to_ignore = df.medcode.isin(ignore) 
print('Ignore rows: ' + str(to_ignore.sum()) + '\n')
df = df[~to_ignore].reset_index()

# status not given
to_drop = ~df.data1.isin(['Y', 'D', 'N'])
if to_drop.sum() > 0:
    print('Missing status: ' + str(to_drop.sum()) + '\n')
    df = df[~to_drop].reset_index()

# check for unknown codes
no_code = ~df.medcode.isin(ex_smoker + smoker + ever_smoker + never_smoker + non_smoker + generic_smoker) 
if no_code.sum() > 0:
    print('Unknown codes: ' + str(no_code.sum()) + '\n')
    print(df[no_code].medcode.value_counts())
    df = df[~no_code].reset_index()

# update D to N when necessary, and remove in-consistent rows 

before = len(df)

data = N2D(df, MAX_INTENSITY) 
data = data[(~data.medcode.isin(ex_smoker)) | (data.data1=='D')]
data = data[(~data.medcode.isin(smoker)) | (data.data1=='Y')]
data = data[(~data.medcode.isin(ever_smoker)) | (data.data1.isin(['Y','D']))]
data = data[(~data.medcode.isin(never_smoker)) | (data.data1=='N')] # note that we drop here original N that we changed to D as they are 'never' (not just non) with intesity info
data = data[(~data.medcode.isin(non_smoker)) | (data.data1.isin(['N','D']))]

after = len(data)
print('In-consistent rows: ' + str(before-after) + ' equal to ' + str(round(100*(before-after)/before,1)) + '%\n')
           
# Smoking_Status signal

dict = pd.DataFrame(data={('N', 'Never'), ('D', 'Former'), ('Y', 'Current')}, columns=['data1', 'value_0'])
smoking_status = data[['pid', 'time_0', 'data1' ]].merge(dict, on='data1', how='left')
smoking_status['signal'] = 'Smoking_Status'
smoking_status.drop(columns='data1', inplace=True)

# Smoking_Quit_Date signal

quit_date = data[(data.data1=='D') & (data.data6 != '')][['pid', 'time_0', 'data6']].copy()
quit_date['signal'] = 'Smoking_Quit_Date'
quit_date.rename(columns={'data6':'value_0'}, inplace=True)
quit_date = check_and_fix_date(quit_date, col='value_0')
quit_date = quit_date[quit_date.value_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]

# Smoking_Intensity

intensity = data[(data.data1!='N') & (data.data2!='')][['pid', 'time_0', 'data2']].copy()
intensity['signal'] = 'Smoking_Intensity'
intensity.rename(columns={'data2':'value_0'}, inplace=True)
intensity = intensity[intensity.value_0.str.isnumeric()]
intensity = intensity[intensity.value_0.astype(int).between(1,MAX_INTENSITY)]

# Pack_Years: Ignore, almost no information
# Smoking_Duration: Ignore, almost no information about start date

return_df = pd.concat([smoking_status, quit_date, intensity])
return_df = return_df.sort_values(by=['pid', 'time_0'])
return_df = check_and_fix_date(return_df, col='time_0')

before = len(return_df)
return_df = return_df[return_df.time_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
after = len(return_df)
if before > after:
    print('Drop ' + str(before-after) + ' smoking features because date of signal out of repo date range')
df=return_df

