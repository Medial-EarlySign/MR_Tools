#!/usr/bin/env python
# coding: utf-8


import pandas as pd
import os
import sys
import time

import numpy as np

#prepare data frame for mayo as loading
fname='/server/Data/Mayo_AS/07-05-2023/AS_echo_May2023.xlsx'
rawData=pd.DataFrame(columns=['id','signal','date','value','unit'])
print("### working on demographics and As_echo")
inData=pd.read_excel(io=fname,sheet_name='AS_echo_May2023')
idCol=inData.id
dateCol=inData.procedure_date
signals=inData.columns
signals=signals.drop(['id','procedure_date'])
for s in signals:
	tempDf=pd.DataFrame(columns=['id','signal','date','value','unit'])
	tempDf.id=idCol
	tempDf.signal=s
	tempDf.date=dateCol
	
	tempDf['value']=inData[s]
	
	rawData=pd.concat([rawData,tempDf],axis=0)

print('#working on BDATE')
ageDF=rawData[rawData.signal=='age_at_echo'].copy()
ageDF.loc[:,'value']=(ageDF.date.dt.year-ageDF.value)*10000+101



print('>>>>>>>>>>Max difference between birth years of same patient:')
print(ageDF.groupby('id').value.agg(np.ptp).abs().max())
mostFreq=ageDF.groupby('id').value.agg(pd.Series.mode).to_frame().reset_index()
# break ties in mode
mostFreq.loc[:,'value']=mostFreq.value.apply(lambda x:  x if type(x)==int  else x[0] )
mostFreq['signal']="BDATE"
rawData=pd.concat([rawData,mostFreq],axis=0)

# gender check for multiples
gender=rawData[rawData.signal=='Gender']
gender=gender[['id','value']].drop_duplicates()
maxGendersPerId=gender.id.value_counts().max()
print('>>>>>>Max genders per person:', maxGendersPerId)
rawData.loc[rawData.signal=='Gender']=rawData.loc[rawData.signal=='Gender'].drop_duplicates(subset=['id','value'])
rawData=rawData[rawData.signal.notna()]# the line above leaves nul rows

# Race_Name check for multiples
Race_Name=rawData[rawData.signal=='Race_Name']
Race_Name=Race_Name[['id','value']].drop_duplicates()
maxRace_NamePerId=Race_Name.id.value_counts().max()
print('>>>>>>Max Race_Name per person:', maxRace_NamePerId)
rawData.loc[rawData.signal=='Race_Name']=rawData.loc[rawData.signal=='Race_Name'].drop_duplicates(subset=['id','value'])
rawData=rawData[rawData.signal.notna()]# the line above leaves nul rows

# Ethnicity_Name check for multiples
Ethnicity_Name=rawData[rawData.signal=='Ethnicity_Name']
Ethnicity_Name=Ethnicity_Name[['id','value']].drop_duplicates()
maxEthnicity_NamePerId=Ethnicity_Name.id.value_counts().max()
print('>>>>>>Max Ethnicity_Name per person:', maxEthnicity_NamePerId)
rawData.loc[rawData.signal=='Ethnicity_Name']=rawData.loc[rawData.signal=='Ethnicity_Name'].drop_duplicates(subset=['id','value'])
rawData=rawData[rawData.signal.notna()]# the line above leaves nul rows
print("### working on lab data ")
fname='/server/Data/Mayo_AS/AS_labs.csv'
inData=pd.read_csv(fname,parse_dates=[['Lab_Date','Lab_Time']])
inData.rename(columns={'Lab_Date_Lab_Time':'date','TestDesc':'signal','Resultn':'value','Units':'unit'},inplace=True)
inData.date=pd.to_datetime(inData.date,errors='coerce',infer_datetime_format=True)# get NA to missing dates

rawData=pd.concat([rawData,inData],axis=0)


print("### working on diagnosis data ")
fname='/server/Data/Mayo_AS/AS_dxs.csv'
inData=pd.read_csv(fname,parse_dates =['Dx_Date'])

inData['splitted']=inData.Dx_Code.str.split(', ') # when they give more than one code in a line
inData=inData.explode('splitted')
inData.Dx_Code=inData.splitted
inData=inData.drop(columns='splitted')
inData.Dx_Type=inData.Dx_Type.str.replace("-CM","")
inData.Dx_Type=inData.Dx_Type.str.replace("-","")
inData['value']=inData.Dx_Type+'_CODE:'+inData.Dx_Code.str.replace(".","",regex=False)
inData.rename(columns={'Dx_Date':'date'},inplace=True)
inData['signal']='Diagnosis'
rawData=pd.concat([rawData,inData],axis=0)
rawData.drop(['Dx_Code','Dx_Type'],axis=1,inplace=True)


print("### working on ECG ")
fname='/server/Data/Mayo_AS/AS_ECG.csv'
inData=pd.read_csv(fname,parse_dates=[['ECG_Date','ECG_Time']])
idCol=inData.id
dateCol=inData.ECG_Date_ECG_Time
signals=inData.columns
signals=signals.drop(['id','ECG_Date_ECG_Time','ECG_Desc'])
for s in signals:
	tempDf=pd.DataFrame(columns=['id','signal','date','value','unit'])
	tempDf.id=idCol
	tempDf.signal=s
	tempDf.date=dateCol
	
	tempDf['value']=inData[s]
	# avoid multiplying single test with different codes
	tempDf=tempDf.drop_duplicates()
	
	rawData=pd.concat([rawData,tempDf],axis=0)

print("### working on smoking and location ")
fname='/server/Data/Mayo_AS/AS_loc_smoke_Mar2023.xlsx'
inData=pd.read_excel(io=fname,sheet_name='data')
idCol=inData.id

signals=inData.columns
signals=signals.drop('id')
for s in signals:
	tempDf=pd.DataFrame(columns=['id','signal','date','value','unit'])
	tempDf.id=idCol
	tempDf.signal=s

	
	tempDf['value']=inData[s]
	
	
	rawData=pd.concat([rawData,tempDf],axis=0)	
	
	
	
print("### working on outcomes ")
fname='/server/Data/Mayo_AS/AS_outcomes.xlsx'
inData=pd.read_excel(io=fname,sheet_name='AS_outcomes_Jan2023')
idCol=inData.id
signals=inData.columns
signals=signals.drop(['id'])
for s in signals:
	tempDf=pd.DataFrame(columns=['id','signal','date','value','unit'])
	tempDf.id=idCol
	tempDf.signal=s
	tempDf.date=inData[s]
	
	
	
	rawData=pd.concat([rawData,tempDf],axis=0)

print("### saving output")

rawData.to_pickle('/server/Work/Users/Coby/MayoAS/raw.pkl')
rawData.to_csv('/server/Work/Users/Coby/MayoAS/raw.csv',index=False)