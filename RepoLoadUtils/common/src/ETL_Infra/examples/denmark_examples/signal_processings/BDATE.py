#You have dataframe called "df". Please process it to generare signal "BDATE"

#The target dataframe should have those columns:
#    pid
#    signal
#    value_0 - numeric (rep channel type i)

#Source Dataframe - df.head() output(synthetic data example):
#   dup index_dato  LC date_LCdiagnosis outpatientclinic_date  Age  FEV1  height weight   BMI   Sex Smokingstatus stage  NSCLC  pathology signal  pid
#0    0  27mar1988   0              NaN             27mar1988   37   NaN     NaN    NaN  25.0  male  Formersmoker   NaN    NaN        NaN   None    1


df=df[['pid', 'Age', 'outpatientclinic_date']].copy()
df['signal']='BDATE'
df['value_0']=((df['outpatientclinic_date'].apply(lambda x: int(x[-4:])).astype(int) - df['Age'].astype(int)).astype(str) + '0101').astype(int)
df=df[['pid', 'signal', 'value_0']].drop_duplicates().reset_index(drop=True)

rr=df['pid'].value_counts().reset_index()
if 'count' not in rr.columns:
    rr = rr.rename(columns={'pid':'count', 'index':'pid'})
rr=df[df.pid.isin(rr[rr['count']>1].pid)].groupby('pid')['value_0'].agg(['min', 'max']).reset_index()

print('Histogram of BDATE differences')
hist_diff=(rr['max']//10000-rr['min']//10000).value_counts()
print(hist_diff)

#since all is one year - take min ase bdate
if (rr['max']//10000-rr['min']//10000).max() < 2:
    df=df.sort_values(['pid', 'value_0']).drop_duplicates(subset=['pid'])
else:
    raise NameError('There are patient s with age diff more then 1')
