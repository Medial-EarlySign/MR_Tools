#You have dataframe called "df". Please process it to generare signal/s of class "labs"
#
#Example signal from this class might be BP
#
#The target dataframe should have those columns:
#     pid
#     signal
#     time_0 - type i
#     value_0 - numeric (rep channel type s)
#     value_1 - numeric (rep channel type s)
#
#Source Dataframe - df.head() output (synthetic data example):
#  index_date   lab_date     lab_name value_0                 lab_name_unfiltered signal      pid
#0  20DEC2026  15APR2045          NaN    2961               Proinsulin C-peptid;P   None      NaN
#1  20DEC2034  15APR2045  Neutrophils    4,73                  Neutrofilocytter;B   None  10377.0
#2  20DEC2042  15APR2045       Sodium     151                           Natrium;P   None  10377.0
#3  20DEC2058  15APR2045          NaN    0,07  Metamyelo.+Myelo.+Promyelocytter;B   None  10377.0
#4  20DEC2041  15APR2045   Leucocytes    6,67                       Leukocytter;B   None  10377.0
import pandas as pd
from signal_processings.helper import *

def fix_unit(df, signal, factor, bias = 0.0):
    df.loc[df['signal']==signal, 'value_0'] = df.loc[df['signal']==signal, 'value_0'] * factor + bias

#Adding mapping\units code blocks for you as starting point
#generate_labs_mapping_and_units_config(df, 5)
#Please edit the file "/work/MES/earlysign/workspace/ETL/configs/map_units_stats.cfg" and then comment out previous line for speedup in next run
#df=map_and_fix_units(df)
df = df[df['signal']!='IGNORE'].reset_index(drop=True)
#no units
df = df.rename(columns={'lab_date':'time_0'})
df['time_0'] = df['time_0'].apply(conv_date)
df = df[df['value_0'].notna()].reset_index(drop=True)
df['value_0'] = df['value_0'].astype(str).apply(lambda x: x.replace(',', '.'))
df['value_0_conv'] = pd.to_numeric(df['value_0'], errors='coerce')

bad_codes = df[df['value_0_conv'].isnull()].reset_index(drop=True)
if len(bad_codes)>0:
    print(f'Bad codes({len(bad_codes)} out of {len(df)}):\n{bad_codes.head()}')
df = df[df['value_0_conv'].notna()].reset_index(drop=True)
df['value_0']=df['value_0_conv']
#breakpoint()
#Unit Conversion
fix_unit(df, 'Albumin', 0.1) #mg/L to mg/dL
fix_unit(df, 'CRP', 0.1) #mg/L to mg/dL
fix_unit(df, 'Bilirubin', 1.0/17.1) #umol/L to mg/dL
fix_unit(df, 'Ca', 4.01) #mmol/L to mg/dL
fix_unit(df, 'Hemoglobin', 1.61) #mmol/L to mg/dL
fix_unit(df, 'Creatinine', 1.0/88.42) #mmol/L to mg/dL
fix_unit(df, 'Triglycerides', 88.57)  #mmol/L to mg/dL
fix_unit(df, 'Cholesterol', 38.67)  #mmol/L to mg/dL
fix_unit(df, 'LDL', 38.67)  #mmol/L to mg/dL
fix_unit(df, 'HDL', 38.67)  #mmol/L to mg/dL
fix_unit(df, 'Glucose', 18.0182) #mmol/L to mg/dL
fix_unit(df, 'Ferritin', 1/2.247) # ng/mL  =  2.247 pmol/L
fix_unit(df, 'MCH', 16.114) #fmol => pg
fix_unit(df, 'MCHC-M', 1.61) #mmol/L to mg/dL
fix_unit(df, 'HbA1C', 1.0/10.929, 2.15)# mmol/mol => %
fix_unit(df, 'Amylase', 3.6) #nkat/L => micromol/h*L
fix_unit(df, 'Follic_Acid', 0.4414) #ug/L => nmol/L
fix_unit(df, 'RBC', 10) #
fix_unit(df, 'Urea', 6.006) #mmol/L to mg/dL
fix_unit(df, 'Uric_Acid', 16.811) #mmol/L to mg/dL


df.loc[df['original_signal_source']=='Calcium::Calcium;P', 'value_0'] = df.loc[df['original_signal_source']=='Calcium::Calcium;P', 'value_0'] * 0.5
#Platlets!

#End conversion


df = df[['pid', 'signal', 'time_0', 'value_0', 'lab_name', 'lab_name_unfiltered']]
