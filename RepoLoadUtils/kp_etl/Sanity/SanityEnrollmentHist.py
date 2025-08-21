# -*- coding: utf-8 -*-
"""
Created on Tue Apr 17 15:28:26 2018

@author: Ron
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import copyFig

fileControlDemo = r'\controls_demo.txt'
fileControlDxList =[r'\controls_dx1.txt',r'\controls_dx2.txt',r'\controls_dx3.txt'] 
fileCaseTumor =  r'\cases_tumor.txt'
fileCaseDemo = r'\cases_demo.txt'
fileCaseDx = r'\cases_dx.txt'

sourceDir = r'D:\Databases\kpsc'
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
dfCaseTumor =  pd.read_csv(sourceDir + fileCaseTumor, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 

###############################################################################
# Distibution of year of enrollwment:
###############################################################################

dfControlDemoExt = dfControlDemo
dfCaseDemoExt = dfCaseDemo
# First, not currently active:
# Case:
dateMax = 20180101  #dfQuitMembers['mem_stop_for_sort'].max()
dfControlDemoExt['index_for_sort'] = dfControlDemo.apply(lambda row: int(row.index_date[6:] + row.index_date[0:2] + row.index_date[3:5]),axis = 1)
dfControlDemoExt['mem_start_for_sort'] = dfControlDemo.apply(lambda row: int(row.mem_start[6:] + row.mem_start[0:2] + row.mem_start[3:5]),axis = 1)
dfControlDemoExt['mem_stop_for_sort'] = dfControlDemo.apply(lambda row: int(row.mem_stop[6:] + row.mem_stop[0:2] + row.mem_stop[3:5]),axis = 1)
dfControlDemoExt['mem_stop_converted_for_sort'] = dfControlDemo.apply(lambda row: min([dateMax,row.mem_stop_for_sort]) ,axis = 1)
dfControlDemoExt['years_stop'] = dfControlDemo.apply(lambda row: int(row.mem_stop[6:]),axis = 1)
dfControlDemoExt['years_start'] = dfControlDemo.apply(lambda row: int(row.mem_start[6:]),axis = 1)
dfControlDemoExt['years_index'] = dfControlDemo.apply(lambda row: int(row.index_date[6:]),axis = 1)
dfControlDemoExt['delta_days'] =  dfControlDemo.apply(lambda row: int((datetime.strptime(str(row.mem_stop_converted_for_sort), '%Y%m%d') - datetime.strptime(str(row.mem_start_for_sort), '%Y%m%d')).days) ,axis = 1)
dfControlDemoExt['days_after_index'] =  dfControlDemo.apply(lambda row: int((datetime.strptime(str(row.mem_stop_converted_for_sort), '%Y%m%d') - datetime.strptime(str(row.index_date), '%m/%d/%Y')).days) ,axis = 1)
dfControlDemoExt['days_before_index'] =  dfControlDemo.apply(lambda row: int((datetime.strptime(str(row.index_date), '%m/%d/%Y') - datetime.strptime(str(row.mem_start), '%m/%d/%Y')).days) ,axis = 1)

dfCaseDemoExt['index_for_sort'] = dfCaseDemo.apply(lambda row: int(row.index_date[6:] + row.index_date[0:2] + row.index_date[3:5]),axis = 1)
dfCaseDemoExt['mem_start_for_sort'] = dfCaseDemo.apply(lambda row: int(row.mem_start[6:] + row.mem_start[0:2] + row.mem_start[3:5]),axis = 1)
dfCaseDemoExt['mem_stop_for_sort'] = dfCaseDemo.apply(lambda row: int(row.mem_stop[6:] + row.mem_stop[0:2] + row.mem_stop[3:5]),axis = 1)
dfCaseDemoExt['mem_stop_converted_for_sort'] = dfCaseDemo.apply(lambda row: min([dateMax,row.mem_stop_for_sort]) ,axis = 1)
dfCaseDemoExt['years_stop'] = dfCaseDemo.apply(lambda row: int(row.mem_stop[6:]),axis = 1)
dfCaseDemoExt['years_start'] = dfCaseDemo.apply(lambda row: int(row.mem_start[6:]),axis = 1)
dfCaseDemoExt['years_index'] = dfCaseDemo.apply(lambda row: int(row.index_date[6:]),axis = 1)
dfCaseDemoExt['delta_days'] =  dfCaseDemo.apply(lambda row: int((datetime.strptime(str(row.mem_stop_converted_for_sort), '%Y%m%d') - datetime.strptime(str(row.mem_start_for_sort), '%Y%m%d')).days) ,axis = 1)
dfCaseDemoExt['days_after_index'] =  dfCaseDemo.apply(lambda row: int((datetime.strptime(str(row.mem_stop_converted_for_sort), '%Y%m%d') - datetime.strptime(str(row.index_date), '%m/%d/%Y')).days) ,axis = 1)
dfCaseDemoExt['days_before_index'] =  dfCaseDemo.apply(lambda row: int((datetime.strptime(str(row.index_date), '%m/%d/%Y') - datetime.strptime(str(row.mem_start), '%m/%d/%Y')).days) ,axis = 1)

#########################################################################
# End Date
#########################################################################

plt.figure()
binEdges = np.arange(dfControlDemoExt['years_stop'].min()-0.5,dfControlDemoExt['years_stop'].max() +  1 +0.5 )
plt.grid()
plt.hist(dfControlDemoExt['years_stop'],binEdges)
histvalControl,bins = np.histogram(dfControlDemoExt['years_stop'],binEdges)
plt.xticks(binEdges[:-1]+0.5)
plt.title('End date per year')
bins = binEdges[:-1]+0.5
dfOutControl = pd.DataFrame({'year': bins, 'hist': histvalControl, 'histNormed': histvalControl/histvalControl.sum()})
dfOutControl = dfOutControl.set_index('year')

plt.figure()
binEdges = np.arange(dfCaseDemoExt['years_stop'].min()-0.5,dfCaseDemoExt['years_stop'].max() +  1 +0.5 )
plt.grid()
plt.hist(dfCaseDemoExt['years_stop'],binEdges)
histvalCase,bins = np.histogram(dfCaseDemoExt['years_stop'],binEdges)
plt.xticks(binEdges[:-1]+0.5)
plt.title('End date per year')
bins = binEdges[:-1]+0.5
dfOutCase = pd.DataFrame({'year': bins, 'hist': histvalCase, 'histNormed': histvalCase/histvalCase.sum()})
dfOutCase = dfOutCase.set_index('year')


#Comb
#dfComb  = pd.concat([pd.Series(histvalCase/histvalCase.sum()) , pd.Series(histvalControl/histvalControl.sum())], axis = 1)
dfComb  = pd.concat([dfOutCase.histNormed , dfOutControl.histNormed], axis = 1)
dfComb.columns = ['Case','Control']
dfComb = dfComb.applymap(lambda x: 0 if x!=x else x)
plt.figure()
binsInt = [str(int(currBin)) for currBin in bins]
dfComb.plot(x = np.array(binsInt), y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of End date')
plt.grid()


#########################################################################
# Start Date
#########################################################################

plt.figure()
binEdges = np.arange(dfControlDemoExt['years_start'].min()-0.5,dfControlDemoExt['years_start'].max() +  1 +0.5 )
plt.grid()
plt.hist(dfControlDemoExt['years_start'],binEdges)
histvalControl,bins = np.histogram(dfControlDemoExt['years_start'],binEdges)
plt.xticks(binEdges[:-1]+0.5)
plt.title('Start date per year')
bins = binEdges[:-1]+0.5
dfOutControl = pd.DataFrame({'year': bins, 'hist': histvalControl, 'histNormed': histvalControl/histvalControl.sum()})
dfOutControl = dfOutControl.set_index('year')

plt.figure()
binEdges = np.arange(dfCaseDemoExt['years_start'].min()-0.5,dfCaseDemoExt['years_start'].max() +  1 +0.5 )
plt.grid()
plt.hist(dfCaseDemoExt['years_start'],binEdges)
histvalCase,bins = np.histogram(dfCaseDemoExt['years_start'],binEdges)
plt.xticks(binEdges[:-1]+0.5)
plt.title('Start date per year')
bins = binEdges[:-1]+0.5
dfOutCase = pd.DataFrame({'year': bins, 'hist': histvalCase, 'histNormed': histvalCase/histvalCase.sum()})
dfOutCase = dfOutCase.set_index('year')


#Comb
#dfComb  = pd.concat([pd.Series(histvalCase/histvalCase.sum()) , pd.Series(histvalControl/histvalControl.sum())], axis = 1)
dfComb  = pd.concat([dfOutCase , dfOutControl], axis = 1)
dfComb.columns = ['CaseNum','Cases','ControlNum','Controls']
dfComb = dfComb.applymap(lambda x: 0 if x!=x else x)
plt.figure()
binsInt = [str(int(currBin)) for currBin in dfComb.index]
dfComb.plot(x = np.array((binsInt)), y = ['Cases','Controls'],kind = 'bar')
plt.title('Distribution of Start date')
plt.grid()





#for ind,row in df.iterrows():
#    print((datetime.strptime(str(row['mem_stop_converted_for_sort']), '%Y%m%d')).day)
#def year_of_enrol(df,caseControlType):
#    stillActive = df.mem_stop_for_sort.max()
#    dfQuitMembers = df[df['mem_stop_for_sort'] != stillActive]
#    dfActiveMembers = df[df['mem_stop_for_sort'] == stillActive]
#    group_1_5 = np.sum( (1*365 <= dfQuitMembers['delta_days']) & (dfQuitMembers['delta_days']  < 5*365))
#    group_5_10 = np.sum( (5*365 <= dfQuitMembers['delta_days']) & (dfQuitMembers['delta_days']  < 10*365))
#    group_10 = np.sum( 10*365 <= dfQuitMembers['delta_days']) 
#    print(group_1_5 )
#    print(group_5_10)
#    print(group_10)
#    print(group_1_5 /dfQuitMembers.shape[0])
#    print(group_5_10/dfQuitMembers.shape[0])
#    print(group_10/dfQuitMembers.shape[0])
#    print(group_1_5 + group_10 + group_5_10)
#    print(dfQuitMembers.shape[0])
#
#    dfActiveMembers = df[df['mem_stop_for_sort'] == stillActive]
#    group_1_5 = np.sum( (1*365 <= dfActiveMembers['delta_days']) & (dfActiveMembers['delta_days']  < 5*365))
#    group_5_10 = np.sum( (5*365 <= dfActiveMembers['delta_days']) & (dfActiveMembers['delta_days']  < 10*365))
#    group_10 = np.sum( 10*365 <= dfActiveMembers['delta_days']) 
#    print(group_1_5 )
#    print(group_5_10)
#    print(group_10)
#    print(group_1_5 /dfActiveMembers.shape[0])
#    print(group_5_10/dfActiveMembers.shape[0])
#    print(group_10/dfActiveMembers.shape[0])
#    print(group_1_5 + group_10 + group_5_10)
#    print(dfActiveMembers.shape[0])

##########################################################################################
# Distribution of Enrollment End Date - Start Date
##########################################################################################


def year_of_enrol2(df,caseControlType,dateMax):
    group_1_5 = np.sum( (1*365 <= df['delta_days']) & (df['delta_days']  < 5*365))
    group_5_10 = np.sum( (5*365 <= df['delta_days']) & (df['delta_days']  < 10*365))
    group_10 = np.sum( 10*365 <= df['delta_days']) 
    
    print(group_1_5 )
    print(group_5_10)
    print(group_10)
    print(group_1_5 /df.shape[0])
    print(group_5_10/df.shape[0])
    print(group_10/df.shape[0])
    print(group_1_5 + group_10 + group_5_10)
    print(df.shape[0])
    
    return np.histogram(df['delta_days'],[1*365,5*365,10*365,np.inf])

histValCase,_ = year_of_enrol2(dfCaseDemoExt,'Case',dateMax)
histValControl,_ = year_of_enrol2(dfControlDemoExt,'Control',dateMax)

#Comb
dfComb  = pd.concat([pd.Series(histvalCase/histvalCase.sum()) , pd.Series(histvalControl/histvalControl.sum())], axis = 1)
#dfComb  = pd.concat([dfOutCase , dfOutControl], axis = 1)
dfComb.columns = ['CaseNum','Cases','ControlNum','Controls']
dfComb = dfComb.applymap(lambda x: 0 if x!=x else x)
plt.figure()
binsInt = [str(int(currBin)) for currBin in dfComb.index]
dfComb.plot(x = np.array((binsInt)), y = ['Cases','Controls'],kind = 'bar')
plt.title('Distribution of Start date')
plt.grid()

## Atlernative:
binEdges = [1*365,5*365,10*365,np.inf]
histvalCase,bins = np.histogram(dfCaseDemoExt['delta_days'],binEdges)
histvalControl,bins = np.histogram(dfControlDemoExt['delta_days'],binEdges)
dfComb  = pd.concat([pd.Series(histvalCase) ,pd.Series(histvalCase/histvalCase.sum()) , pd.Series(histvalControl),pd.Series(histvalControl/histvalControl.sum())], axis = 1)
dfComb.columns = ['CaseNum','Cases','ControlNum','Controls']
plt.figure()
dfComb.index = ['1-5 years', '5-10 years','10+ years']
dfComb.plot(y = ['Cases','Controls'],kind = 'bar')


plt.title('Distribution of EndDate - StartDate')
plt.grid()

##########################################################################################
#Merge Dx Date +  End Date - Start Date
##########################################################################################



def timeBeforeAferIndex(df):
    print(np.sum((df['days_after_index'] > 730) & (df['days_before_index'] > 365)))
    print(np.sum((df['days_after_index'] > 730) & (df['days_before_index'] > 365))/len(df))
    print(len(df))
    print(np.sum(df['days_before_index'] > 365))
    print(np.sum(df['days_before_index'] > 365)/len(df))
    
    
def number_of_patients():
    years = list(range(2005,2016))
    patInYear = dict()
    for year in years:
        patInYear[year] = np.sum((df['years_start'] < year) & (df['years_stop'] > year))
    
    
    
timeBeforeAferIndex(dfCaseDemoExt)
timeBeforeAferIndex(dfControlDemoExt)  


###############################################################################
# Distibution of year of enrollwment:
###############################################################################





def lungCancersPerYear(df,caseControlType):
    relInd = df['CODE'].apply(is_number)
    dfDxNum = df[relInd]
    dfDxNum['CODE'] = dfDxNum['CODE'].apply(float)
    dfDxNumFiltered =  dfDxNum[((dfDxNum['CODE']>= 162.2) & (dfDxNum['CODE'] <= 162.9) )]# | ((dfCaseDxNum['CODE'] >= 490) & (dfCaseDxNum['CODE'] <= 496))]
    dfDxNumFilteredgb = dfDxNumFiltered.groupby('id')
    len(dfDxNumFilteredgb.groups)
    print(" ".join(['total number',str(len(dfDxNumFilteredgb.groups))]))
    dfDxNumFiltered['year'] = dfDxNumFiltered.apply(lambda row: int(row.adate[6:]),axis = 1)
    plt.figure()
    dfDxNumFilteredgb.head(1)['year'].value_counts().plot(kind='bar')
    plt.title(caseControlType + 's - First Lung Cancer per year ')
    return dfDxNumFiltered

df = dfCaseDx;
caseControlType = 'Case'
lungCancersPerYear(df,caseControlType)