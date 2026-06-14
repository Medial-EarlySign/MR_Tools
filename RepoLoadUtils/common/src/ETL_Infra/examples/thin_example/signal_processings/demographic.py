#You have dataframe called "df". Please process it to generare signal/s of class "demographic"

#Example signal from this class might be GENDER

#The target dataframe should have those columns:
#    pid
#    signal
#    value_0 - numeric (rep channel type f)

#Source Dataframe - df.head() output (synthetic data):
#  patflag       yob famenum sex   regdate regstat signal  pid
#0       A  19450000  002633   1  20061019      02   None    1
#1       A  19610000  004589   2  20120228      02   None    2
#2       A  19880000  004769   1  20160813      02   None    3
#3       A  19691000  002973   2  19990607      02   None    4
#4       A  19240000  002973   1  19990412      02   None    5

from signal_processings.process_helper import *

removecnt = len(df[~df['patflag'].isin(['A', 'C', 'D'])])
print(f'Exclude {removecnt} patients due to bad patflag')
data = df[df['patflag'].isin(['A', 'C', 'D'])].reset_index(drop=True)
data.rename(columns={'yob':'BDATE', 'sex':'GENDER', 'dod':'DEATH'}, inplace=True)

# fix/check BDATE
data = check_and_fix_date(data, col='BDATE')
data_death=data[['pid', 'DEATH']].copy()
data_death = check_and_fix_date(data_death, col='DEATH')
data = data.drop(columns=['DEATH'])

data=data.set_index('pid').join( data_death.set_index('pid'), how='left' ).reset_index()
data.loc[data['DEATH'].isnull(), 'DEATH'] = -1
# arrange in the right format        
data = (
      data[['pid', 'GENDER', 'BDATE', 'DEATH']]
      .set_index('pid')
      .stack()
      .reset_index()
      .rename(columns={'level_1':'signal', 0:'value_0'})
       )


# remove patients with DEATH out of repo range or no death
before = len(data)
to_drop = (data.signal=='DEATH') & (~data.value_0.astype(int).between(MIN_REPO_DATE, MAX_REPO_DATE))
if to_drop.sum() > 0:
    print('Drop ' + str(to_drop.sum()) + ' out of ' + str(len(data.drop_duplicates(subset='pid'))) + ' patients death date is out of repo range')
    data = data[~to_drop].reset_index(drop=True)

# remove BDATE before 1900 or after 2021
to_drop = (data.signal=='BDATE') & (~data.value_0.astype(int).between(MIN_REPO_DATE, MAX_REPO_DATE))
if to_drop.sum() > 0:
    print('Drop ' + str(to_drop.sum()) + ' out of ' + str(len(data.drop_duplicates(subset='pid'))) + ' patients with BDATE before 1901 or after 2021 or not a date as BDATE')
    data = data[~to_drop].reset_index()

# remove signal GENDER with value not in [1,2]
to_drop = (data.signal=='GENDER') & (~data.value_0.isin(['1', '2']))
if to_drop.sum() > 0:
    print('Drop ' + str(to_drop.sum()) + ' out of ' + str(len(data.drop_duplicates(subset='pid'))) + ' patients with GENDER other than MALE or FEMALE')
    data = data[~to_drop]

df = data