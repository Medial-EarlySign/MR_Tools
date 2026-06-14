#You have dataframe called "df". Please process it to generare signal/s of class "demographic"

#Example signal from this class might be GENDER

#The target dataframe should have those columns:
#    pid
#    signal
#    value_0 - string categorical (rep channel type i)

#Source Dataframe - df.head() output(synthetic data example):
#   dup index_dato  LC date_LCdiagnosis outpatientclinic_date  Age  FEV1  height weight   BMI   Sex Smokingstatus stage  NSCLC  pathology signal  pid
#0    0  27mar1988   0              NaN             27mar1988   37   NaN     NaN    NaN  25.0  male  Formersmoker   NaN    NaN        NaN   None    1

df=df[['pid', 'Sex']].rename(columns={'Sex':'value_0'})
df['signal']='GENDER'
df.loc[df['value_0']=='male', 'value_0'] = 'Male'
df.loc[df['value_0']=='female', 'value_0'] = 'Female'
df=df[['pid', 'signal', 'value_0']].drop_duplicates().reset_index(drop=True)
