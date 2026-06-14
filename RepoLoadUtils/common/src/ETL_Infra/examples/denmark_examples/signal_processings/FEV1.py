#You have dataframe called "df". Please process it to generare signal/s of class "FEV1"

#Signal or class of signal "FEV1" is not recognized. please define it in rep.signals first
#or change signal column to known one

#Source Dataframe - df.head() output(synthetic data example):
#   dup index_dato  LC date_LCdiagnosis outpatientclinic_date  Age  FEV1  height weight   BMI   Sex Smokingstatus stage  NSCLC  pathology signal  pid
#0    0  27mar1988   0              NaN             27mar1988   37   NaN     NaN    NaN  25.0  male  Formersmoker   NaN    NaN        NaN   None    1

from signal_processings.helper import *

df = df[['pid', 'outpatientclinic_date', 'FEV1']].rename(columns={'outpatientclinic_date':'time_0', 'FEV1':'value_0'}).copy()
df['time_0'] = df['time_0'].apply(conv_date)
df = df[df['value_0'].notna()].reset_index(drop=True)

df['value_0'] = df['value_0'].astype(str).apply(lambda x: float(x.replace(',','.')))

df['signal'] = 'Fev1'

