#You have dataframe called "df". Please process it to generare signal/s of class "measurements"

#Example signal from this class might be BMI

#The target dataframe should have those columns:
#    pid
#    signal
#    time_0 - type i
#    value_0 - numeric (rep channel type f)

#Source Dataframe - df.head() output(synthetic data example):
#   dup index_dato  LC date_LCdiagnosis outpatientclinic_date  Age  FEV1  height weight   BMI   Sex Smokingstatus stage  NSCLC  pathology signal  pid
#0    0  27mar1988   0              NaN             27mar1988   37   NaN     NaN    NaN  25.0  male  Formersmoker   NaN    NaN        NaN   None    1

from signal_processings.helper import *

def fetch_value(df, field_value, signal_name):
    df_i = df[['pid', 'time_0', field_value]].rename(columns={field_value: 'value_0'}).copy()
    df_i = df_i[df_i['value_0'].notna()].reset_index(drop=True)
    df_i['value_0'] = df_i['value_0'].astype(str).apply(lambda x: x.replace(',', '.')).astype(float)
    df_i['signal'] = signal_name
    df_i = df_i[['pid', 'signal', 'time_0', 'value_0']]
    return df_i

df = df[['pid', 'height', 'weight', 'BMI', 'outpatientclinic_date']].rename(columns={'outpatientclinic_date':'time_0'}).copy()
df['time_0'] = df['time_0'].apply(conv_date)

df_h = fetch_value(df, 'height', 'Height')
df_w = fetch_value(df, 'weight', 'Weight')
df_bmi = fetch_value(df, 'BMI', 'BMI')

#union all
df = pd.concat([df_h, df_w, df_bmi], ignore_index=True)

