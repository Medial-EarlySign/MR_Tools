#!/usr/bin/env python
# coding: utf-8




#Translate linear data base: pkl file  of the form 'id signal time value unit' into final files ready for loading to repository
#also produce or updates signal and unit conversion table 
# addtional outputs if specified: diagnoses file signals file qc file


import sys           
sys.path.insert(0,'/nas1/UsersData/coby/MR/Libs/Internal/MedPyExport/generate_binding/Release/medial-python36')
sys.path.append('/server/UsersData/coby-internal/MR/Tools/RepoLoadUtils/common')
import os
import math
import re
import datetime
import math
import random
import time
import datetime as dt 
import numpy as np
import pandas as pd
import statistics 
import matplotlib.pyplot as plt
import sklearn
from scipy.special import rel_entr
from dicts_utils import create_dict_generic
import argparse






def fahr_to_celsius(temp_fahr):
    """Convert Fahrenheit to Celsius
    
    Return Celsius conversion of input"""
    temp_celsius = (temp_fahr - 32) * 5 / 9
    return temp_celsius


#get parameters

parser = argparse.ArgumentParser(description = "Prepare signals for load. Convert units")
parser.add_argument("--raw_pkl",required=True,help="raw pkl file 'id signal date value unit'")
parser.add_argument("--in_table",help="input conversion table",default=[])
parser.add_argument("--out_table",required=True,help="updated conversion table")
parser.add_argument("--samples_per_signal",help="number of samples presented from each signal unit combination",default=5)
parser.add_argument("--dict_path",help="path forcategory and diagnosis  dictionaries. If missing no dictionary output",default=[])	
parser.add_argument("--signals_file",help="file where signals are listed for loading",default=[])	
parser.add_argument("--final_path",help="fdirectory ready to receive the final files for all signals",default=[])	
parser.add_argument("--qc_file",help="output file that holds quality control results. if missing: no qc",default=[])	
args = parser.parse_args() 
 
fname=args.raw_pkl
fullDF=pd.read_pickle(fname)
fullDF=fullDF[fullDF.value.notna()]


freqSignal=fullDF.signal.value_counts()
freqUnit=fullDF.value_counts(subset=['signal','unit'],dropna=False)



inData=freqSignal.reset_index().rename(columns={'index':'signal','signal':'count'}).merge(freqUnit.to_frame().reset_index().rename(columns={0:'unitCount'}),on='signal',how='left').sort_values(by=['count','signal','unitCount'],ascending=False)

inFile=args.in_table
if inFile==[] :
     inTable=pd.DataFrame(columns=['signal','unit','to_signal','to_unit','multiple_by','class','value'])
else:
    inTable=pd.read_csv(inFile)
    if inTable.empty:
        inTable=pd.DataFrame(columns=['signal','unit','to_signal','to_unit','multiple_by','class','value'])
outFile=args.out_table

#merge new date with in_table toproduce_out table with frequencies of current pkl file.
inData.unit=inData.unit.astype(str)  # in case they are all nulls  and read as floats
outTable=inData[['signal','count','unit','unitCount']].merge(inTable[['signal','unit','to_signal',    'to_unit','multiple_by','class']],how='outer',on=['signal','unit'])
outTable=outTable.rename(columns={0:'unitCount'})



samples=fullDF.groupby(['signal','unit'],dropna=False).sample(n=args.samples_per_signal,replace=True)

outTableSample=outTable.merge(samples,on=['signal','unit'],how='left').drop(['id','date'],axis=1).groupby(['signal','unit'],dropna=False).aggregate(lambda tdf: tdf.tolist())
outTableSample1=outTable.merge(outTableSample['value'],on=['signal','unit'],how='left')
outTableSample1.to_csv(outFile,index=False)
print('>>>>>outTable written to '+outFile)
if   outTableSample1.to_signal.isna().all():
	print('>>>>> No signals to convert. Exiting')
	exit()
	
	



# handle class signals
classDF=outTable[(outTable['class']=='1')]
classDF=classDF.merge(fullDF,how='left')
classDF['convertedVal']=classDF.value




#isolate the lines that convert by multiplications
numConvert=outTable[outTable['class']!=1]
numConvert.multiple_by= pd.to_numeric(numConvert.multiple_by,errors='coerce')
numConvert=numConvert[numConvert.multiple_by.notna()]
nConvertDF=fullDF.merge(numConvert,on=['signal','unit'],how='inner')
nConvertDF['convertedVal']=nConvertDF.value*nConvertDF.multiple_by
nConvertDF
                             


# isolate lines with non numeric string and convert them according to given function
funConvert=outTable[outTable['class']!=1]
funConvert=funConvert[funConvert.multiple_by.notna()]
funConvert=funConvert[pd.to_numeric(funConvert.multiple_by,errors='coerce').isna()]
                   

convertDF=fullDF.merge(funConvert,on=['signal','unit'],how='inner')
if not convertDF.empty:
	convertDF['convertedVal']=convertDF.apply(lambda x: eval(x.multiple_by+'(x.value)'),axis=1)
numDF=pd.concat([convertDF,nConvertDF]) # will need them for quality control
convertDF=pd.concat([numDF,classDF])


# prepare categories dictionary
catPath=args.dict_path
classDFG=classDF[(classDF.value.notna())&(classDF.signal!="Diagnosis")]
classDFG=classDFG[['to_signal','value']].drop_duplicates().groupby('to_signal')
if catPath!=[]:
	for sig,values in classDFG:
		catFname=catPath+'/'+sig+'.categories'
		if os.path.exists(catFname):
			os.remove(catFname)

		outF = open(catFname, 'w')
		print('SECTION\t'+sig,file=outF)
		outF.close()
		v=values.sort_values(by='value')
		v['def']='DEF'
		v['code']=range(1,v.shape[0]+1)
		v[['def','code','value']].to_csv(catFname,header=False,index=False,mode='a',sep='\t')
		print('>>>>>Created '+catPath+sig+'.categories')





#Special case for diagnosis. Check which codes are missing in existing dictionaries

if catPath !=[]:
	dicts=['dict.icd9dx','dict.icd10']
	outDict=catPath+'/dict.unmatchedDiags'
	icd9=pd.read_csv(catPath+'/dict.icd9dx',sep='\t',skiprows=1,usecols=[1,2],header=0,names=['def','code'])
	icd10=pd.read_csv(catPath+'/dict.icd10',sep='\t',skiprows=1,usecols=[1,2],header=0,names=['def','code'])

	icds=pd.concat([icd9,icd10],axis=0,ignore_index=True)
	maxDef=icds['def'].max()
	maxDef
	diags=classDF[classDF.to_signal=='Diagnosis'].value.unique()
	diags=pd.Series(diags)
	unMatched=diags.to_frame().merge(icds,how='left',left_on=0,right_on='code')
	unMatched=unMatched[unMatched.code.isna()]
	unMatched['def']=range(maxDef+1,maxDef+1+unMatched.shape[0])
	unMatched
	outF = open(outDict, 'w')
	print('SECTION\t'+'Diagnosis',file=outF)
	outF.close()
	unMatched['DEF']='DEF'
	unMatched[['DEF','def',0]].to_csv(outDict,header=False,index=False,mode='a',sep='\t')
	print('>>>>>Created '+outDict)




# make the signals file
sigName=args.signals_file
if sigName!=[]:
	sigTypes='GENERIC_SIGNAL_TYPE\tmy_SVal\tV(f)\nGENERIC_SIGNAL_TYPE\tmy_SDateVal\tT(i),V(f)\n###########\n'

	outF = open(sigName, 'w')
	print(sigTypes,file=outF)
	outF.close()
	signalDF=outTable[['to_signal','class']].drop_duplicates()
	signalDF=signalDF[signalDF.to_signal.notna()]
	signalDF.loc[signalDF['class'].isna(),'class']=0
	signalDF['code']=range(10001,10001+signalDF.shape[0])
	signalDF['label']='SIGNAL'
	signalDF['typeSig']='16:my_SDateVal'
	signalDF.loc[signalDF.to_signal.isin(['GENDER','BDATE','location','smoking_history','Race_Name','Ethnicity_Name']),'typeSig']='16:my_SVal'
	signalDF['label2']='no comment'
	signalDF[['label','to_signal','code','typeSig','label2','class']].to_csv(sigName,sep='\t',mode='a',index=False,header=False)
	print('>>>>>Created '+sigName)



# make the final files for each signal
finalDirName=args.final_path
if finalDirName!=[]:
	for sig in signalDF.to_signal:
    
    
		finalDF=convertDF[convertDF.to_signal==sig][['id','to_signal','date','convertedVal']]
		finalDF=finalDF.sort_values(by=['id','date']).rename(columns={'to_signal':'signal','convertedVal':'value'})
		typeSig=signalDF.typeSig[signalDF.to_signal==sig].squeeze()
		if typeSig=='16:my_SDateVal':
			noDate=finalDF.date.isna().sum()
			if(noDate>0):
				print ("Missing Date. Signal=",sig,'   Count=',noDate,'   out of:',finalDF.shape[0])
			finalDF=finalDF[finalDF.date.notna()]
			finalDF.date=pd.to_datetime(finalDF.date).dt.strftime('%Y%m%d')
        
        
		else:
			finalDF=finalDF.drop(columns=['date'])
   
    
    
		finalDF.to_csv( finalDirName+sig,sep='\t',index=False,header=False)
		print('>>>>>Created '+finalDirName+sig)
    



bySignal=numDF.groupby('to_signal')
bySource=numDF.groupby(['signal','unit'],dropna=False)




qcName=args.qc_file
if qcName!=[]:
	qcFile=open(qcName,'w')
	for sig in bySignal.groups:
		thisQ=pd.DataFrame()
		thisSignal=bySignal.get_group(sig).reset_index(drop=True)
		print('================',sig,'=======================',file=qcFile)
		thisSignal.loc[:,'convertedVal']+=np.random.uniform(low=-0.01,high=0.01,size=thisSignal.loc[:, 'convertedVal'].shape)
		thisQ['ALL']=thisSignal.convertedVal.quantile(np.arange(0,1.0001,0.05))

		thisHist=np.array(np.histogram(thisSignal.convertedVal,bins=thisQ.loc[:,'ALL']),dtype=object)

		thisHist=thisHist/sum(thisHist[0][range(1,19)])

		thisSignal.loc[:,'unit']=thisSignal.unit.fillna('NaN')
		bySource=thisSignal.groupby(['signal','unit'])
		for source in bySource.groups:
			thisSource=bySource.get_group(source)
			thisQ[source]=thisSource.convertedVal.quantile(np.arange(0,1.0001,0.05))
			thisHistSource=np.array(np.histogram(thisSource.convertedVal,bins=thisQ.loc[:,'ALL']),dtype=object)+1
			thisHistSource=thisHistSource/(sum(thisHistSource[0][range(1,19)]))
			klDis=sum(rel_entr(thisHist[0][range(1,19)],thisHistSource[0][range(1,19)]))
			dashes=''
			if klDis>1:
				dashes='<<<<<<<<<<<<<<<<<<<<<<<'
			print(source,'size:',thisSource.shape[0],'>>>>>>',klDis,dashes,file=qcFile)
		print (thisQ,file=qcFile)
	qcFile.close()
print('>>>>>Created '+qcName)







