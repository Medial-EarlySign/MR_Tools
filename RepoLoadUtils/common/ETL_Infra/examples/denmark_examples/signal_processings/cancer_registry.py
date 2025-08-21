#You have dataframe called "df". Please process it to generare signal/s of class "cancer_registry"

#Signal or class of signal "cancer_registry" is not recognized. please define it in rep.signals first
#or change signal column to known one

#Source Dataframe - df.head() output(synthetic data example):
#   dup index_dato  LC date_LCdiagnosis outpatientclinic_date  Age  FEV1  height weight   BMI   Sex Smokingstatus stage  NSCLC  pathology signal  pid
#0    0  27mar1988   0              NaN             27mar1988   37   NaN     NaN    NaN  25.0  male  Formersmoker   NaN    NaN        NaN   None    1

from signal_processings.helper import *

#Add COPD for all patients:
df_copd = df[['pid', 'outpatientclinic_date']].rename(columns={'outpatientclinic_date':'time_0'}).copy()
df_copd['time_0'] = df_copd['time_0'].apply(conv_date)
df_copd['signal'] = 'DIAGNOSIS'
df_copd['value_0'] = 'ICD9_CODE:496' 
df_copd = df_copd[['pid', 'signal', 'time_0', 'value_0']]

#Index date - add copd dx and date:
df_index = df[['pid', 'index_dato']].rename(columns={'index_dato':'time_0'}).copy()
df_index['time_0'] = df_index['time_0'].apply(conv_date)
df_index['signal'] = 'DIAGNOSIS'
df_index['value_0'] = 'ICD9_CODE:496' 
df_index = df_index[['pid', 'signal', 'time_0', 'value_0']]

df = df[['pid', 'date_LCdiagnosis', 'stage', 'NSCLC', 'pathology']].rename(columns={'date_LCdiagnosis':'time_0'}).copy()
df = df[df['time_0'].notna()].reset_index(drop=True)
df['time_0'] = df['time_0'].apply(conv_date)

#Stage
df_stage=df.rename(columns={'stage': 'value_0'}).copy()
df_stage['signal']='Cancer_Stage'
df_stage = df_stage[df_stage['value_0'].notna()].reset_index(drop=True)
df_stage = df_stage[['pid', 'signal', 'time_0', 'value_0']]
#NSLCS:
df_tp = df.rename(columns={'NSCLC': 'value_0'}).copy()
df_tp['signal'] = 'Cancer_Type'
df_tp = df_tp[df_tp['value_0'].notna()].reset_index(drop=True)
df_tp['value_0'] = df_tp['value_0'].astype(int)
df_tp = df_tp[['pid', 'signal', 'time_0', 'value_0']]

#pathology:
df_pat = df.rename(columns={'pathology': 'value_0'}).copy()
df_pat['signal'] = 'Cancer_Pathology'
df_pat = df_pat[df_pat['value_0'].notna()].reset_index(drop=True)
df_pat['value_0'] = df_pat['value_0'].astype(int)
df_pat = df_pat[['pid', 'signal', 'time_0', 'value_0']]

#DIAGNOSIS:
df_diag = df.copy()
df_diag['value_0'] = 'ICD10_CODE:C34'
df_diag['signal'] = 'DIAGNOSIS'
df_diag = df_diag[['pid', 'signal', 'time_0', 'value_0']]

#Index date:

df = pd.concat([df_stage, df_tp, df_pat, df_diag, df_copd, df_index], ignore_index=True)
