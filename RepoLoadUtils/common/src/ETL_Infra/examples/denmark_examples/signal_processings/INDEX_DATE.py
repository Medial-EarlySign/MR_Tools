#You have dataframe called "df". Please process it to generare signal/s of class "cancer_registry"

#Signal or class of signal "cancer_registry" is not recognized. please define it in rep.signals first
#or change signal column to known one

#Source Dataframe - df.head() output(synthetic data example):
#   dup index_dato  LC date_LCdiagnosis outpatientclinic_date  Age  FEV1  height weight   BMI   Sex Smokingstatus stage  NSCLC  pathology signal  pid
#0    0  27mar1988   0              NaN             27mar1988   37   NaN     NaN    NaN  25.0  male  Formersmoker   NaN    NaN        NaN   None    1

from signal_processings.helper import *


#Index date - add copd dx and date:
df_index = df[['pid', 'outpatientclinic_date']].rename(columns={'outpatientclinic_date':'value_0'}).copy()
df_index['value_0'] = df_index['value_0'].apply(conv_date)
df_index['signal'] = 'INDEX_DATE'
df_index = df_index[['pid', 'signal', 'value_0']].sort_values(['pid', 'value_0']).reset_index(drop=True)
#Take first date for each patient!
df_index = df_index.drop_duplicates(subset=['pid']).reset_index(drop=True)

df = df_index

