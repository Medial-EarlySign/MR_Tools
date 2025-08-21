import pandas as pd
import os
import sys
import time

import numpy as np

#prepare data frame for mayo as loading
fname='/server/Data/Mayo_AS/AS_data_sharing.xlsx'
rawData=pd.DataFrame(columns=['id','signal','date','value','unit'])
print("### working on demographics and echo")
inData=pd.read_excel(io=fname,sheet_name='Demographic + Echo data')
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
print("### working on lab data ")
inData=pd.read_excel(io=fname,sheet_name='Lab data')
inData.rename(columns={'Lab_Date':'date','TestDesc':'signal','Resultn':'value','Units':'unit'},inplace=True)
rawData=pd.concat([rawData,inData],axis=0)
rawData.drop('Lab_Time',axis=1,inplace=True)


print("### working on diagnosis data ")
inData=pd.read_excel(io=fname,sheet_name='DX codes')
inData.Dx_Type=inData.Dx_Type.str.replace("-CM","")
inData['value']=inData.Dx_Type+':'+inData.Dx_Code
inData.rename(columns={'Dx_Date':'date'},inplace=True)
inData['signal']='Diagnosis'
rawData=pd.concat([rawData,inData],axis=0)
rawData.drop(['Dx_Code','Dx_Type'],axis=1,inplace=True)


print("### working on ECG ")
inData=pd.read_excel(io=fname,sheet_name='ECG data')
idCol=inData.id
dateCol=inData.ECG_Date
signals=inData.columns
signals=signals.drop(['id','ECG_Date','ECG_Desc','ECG_Time'])
for s in signals:
	tempDf=pd.DataFrame(columns=['id','signal','date','value','unit'])
	tempDf.id=idCol
	tempDf.signal=s
	tempDf.date=dateCol
	
	tempDf['value']=inData[s]
	
	rawData=pd.concat([rawData,tempDf],axis=0)

	
rawData.to_pickle('/server/Work/Users/Coby/MayoAS/raw.pkl')
rawData.to_excel('/server/Work/Users/Coby/MayoAS/raw.xlsx')