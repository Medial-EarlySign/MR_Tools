#You have dataframe called "df". Please process it to generare signal "MEMBERSHIP"

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    time_1 - type i

#Source Dataframe - df.head() output(synthetic data):
#  pracid patid patflag active  age         dob sex  regstat   startdate  ... alcoholunits alcoholdate height  heightdate weight   bmi  weightdate signal pid
#0  j6666  000A       A      Y   54  01/01/1978   F        2  01/01/2012  ...         24.0  31/01/2012  1.7  13/07/2022  98.0  35.2  13/07/2022   None   1
#1  j6666  000H       A      Y   67  01/01/1923   M        2  01/01/2014  ...          NaN  14/01/2023  1.56  24/01/2012   80.0  25.0  25/07/2012   None   2
#2  j6666  000I       A      Y   12  01/01/1954   M        2  01/01/2016  ...          0.0  07/01/1990  1.81  10/08/1999   68.3  22.1  22/01/2008   None   3
#3  j6666  000K       A      Y   45  01/01/1912   F        2  01/01/2015  ...          NaN  13/06/2016  1.67  05/02/2011  111.0  43.1  13/05/2013   None   4
#4  j6666  000L       A      Y   76  01/01/2004   M        2  01/01/2023  ...         2.0  24/08/2011  1.79  13/08/1998   78.0  28.3  30/03/1999   None   5
#

from signal_processings.process_helper import *

removecnt = len(df[~df['patflag'].isin(['A', 'C', 'D'])])
print(f'Exclude {removecnt} patients due to bad patflag')
data = df[df['patflag'].isin(['A', 'C', 'D'])].reset_index(drop=True)
data.rename(columns={'startdate':'STARTDATE', 'enddate':'ENDDATE'}, inplace=True)

data = fix_date(data, col='deathdte')
data = fix_date(data, col='STARTDATE')
data = fix_date(data, col='ENDDATE')
# cut enddate by death date and repo max date
data.loc[data.ENDDATE=='00000000', 'ENDDATE'] = str(MAX_REPO_DATE)
data['max_repo'] = str(MAX_REPO_DATE)
data.loc[data.deathdte.notnull(), 'max_repo'] = data[data.deathdte.notnull()][['deathdte', 'max_repo']].min(axis=1).astype(int).astype(str)
data['ENDDATE'] = data[['ENDDATE', 'max_repo']].min(axis=1).astype(int).astype(str)

# fix/check dates
data = check_and_fix_date(data, col='STARTDATE')
data = check_and_fix_date(data, col='ENDDATE')

bad_start_date=len(data.loc[data['STARTDATE']< MIN_REPO_DATE])
if bad_start_date>0:
    print(f'Has {bad_start_date} records with bad start date - fixing')
    data.loc[data['STARTDATE']< MIN_REPO_DATE, 'STARTDATE']=MIN_REPO_DATE

bad_end_date=len(data.loc[data['ENDDATE']< MIN_REPO_DATE])
if bad_end_date>0:
    print(f'Has {bad_end_date} records with bad end date - removing')
    data = data[data['ENDDATE']>= MIN_REPO_DATE].reset_index(drop=True)

# remove membership when start > end ...        
before = len(data)
to_drop = data.STARTDATE > data.ENDDATE
if to_drop.sum() > 0:
    print('Drop ' + str(to_drop.sum()) + ' out of ' + str(len(data)) + ' patients membership data as start > end')
    data = data[~to_drop].reset_index()

data['signal'] = 'MEMBERSHIP'
data.rename(columns={'STARTDATE':'time_0', 'ENDDATE':'time_1'}, inplace=True)
df = data[['pid', 'signal', 'time_0', 'time_1']]