#You have dataframe called "df". Please process it to generare signal/s of class "smoking"

#Example signal from this class might be Smoking_Status

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    value_0 - string categorical (rep channel type i)

#Source Dataframe - df.head() output(synthetic data example):
#   dup index_dato  LC date_LCdiagnosis outpatientclinic_date  Age  FEV1  height weight   BMI   Sex Smokingstatus stage  NSCLC  pathology signal  pid
#0    0  27mar1988   0              NaN             27mar1988   37   NaN     NaN    NaN  25.0  male  Formersmoker   NaN    NaN        NaN   None    1

from signal_processings.helper import *

df = df[['pid', 'outpatientclinic_date', 'Smokingstatus']].rename(columns={'outpatientclinic_date':'time_0', 'Smokingstatus':'value_0'}).copy()
df['time_0'] = df['time_0'].apply(conv_date)

df['signal'] = 'Smoking_Status'

map_dict = { 'Formersmoker': 'Former', 'Currentsmoker':'Current', 'Neversmoker': 'Never', 'Unknown':'Unknown' }
df = df[df['value_0'].notna()].reset_index(drop=True)
df = df.replace({'value_0': map_dict})
