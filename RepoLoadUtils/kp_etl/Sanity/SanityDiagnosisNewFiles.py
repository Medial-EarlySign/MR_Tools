# -*- coding: utf-8 -*-
"""
Created on Tue Apr  3 17:17:49 2018

@author: Ron
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import copyFig

fileControlDemo = r'\controls_demo.txt'
fileControlDxList =[r'\controls_dx1.txt',r'\controls_dx2.txt',r'\controls_dx3.txt',r'\03-05-2018\controls_dx_lung_ca.txt'] 
fileCaseTumor =  r'\cases_tumor.txt'
fileCaseDemo = r'\cases_demo.txt'
fileCaseDxList = [r'\cases_dx.txt',r'\03-05-2018\cases_dx_lung_ca.txt']

sourceDir = r'D:\Databases\kpsc'
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
dfCaseTumor =  pd.read_csv(sourceDir + fileCaseTumor, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    
dfControlDxList = []
for fileControlDx in fileControlDxList:
    dfControlDxList.append(pd.read_csv(sourceDir + fileControlDx, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
dfControlDx = pd.concat(dfControlDxList)    

dfCaseDxList = []
for fileCaseDx in fileCaseDxList:
    dfCaseDxList.append(pd.read_csv(sourceDir + fileCaseDx, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
dfCaseDx = pd.concat(dfCaseDxList)    


import icd9dict
icd92icd10Dict = dict()
icd102icd9Dict = dict()

#icd9dict.genIcd9Map(ignore_dict, code_map, outputDir + 'dict.icd9')
icd9dict.icd9icd10conversion3(icd92icd10Dict, icd102icd9Dict)

# convert ICD10 to ICD 9
#dfCaseDx2 = dfCaseDx.copy()
dfCaseDx['CODE'] = dfCaseDx.apply(lambda row: icd102icd9Dict[row['CODE']] if (row['CODE_SUBTYPE'] == 'ICD10') else  row['CODE'],axis = 1)
dfControlDx['CODE'] = dfControlDx.apply(lambda row: icd102icd9Dict[row['CODE']] if (row['CODE_SUBTYPE'] == 'ICD10') else  row['CODE'],axis = 1)

# https://en.wikipedia.org/wiki/List_of_ICD-9_codes_140%E2%80%93239:_neoplasms
# http://www.icd9data.com/2012/Volume1/460-519/490-496/default.htm
# COPD 491.22
# http://www.icd9data.com/2012/Volume1/140-239/160-165/162/default.htm

# Cancer 140 - 239

#########
# # Cancers Per Year:   I - not unique per person
##########
#def createUniqueIcd9Df(df):
#    df['year'] = df.apply(lambda row: int(row.adate[6:]),axis = 1)
#    df['adate_for_sort'] = df.apply(lambda row: int(row.adate[6:] + row.adate[0:2] + row.adate[3:5]),axis = 1)
#    df['index_for_sort'] = df.apply(lambda row: int(row.index_date[6:] + row.index_date[0:2] + row.index_date[3:5]),axis = 1)
#    # arrange by year
#    dfGbId = df.groupby('id')
#    tt = dfGbId.apply(lambda x: x.sort_values('adate_for_sort'))
#    ttt = tt.groupby('id')
#    tttt = ttt.apply(lambda x: x.drop_duplicates(subset = 'CODE' ,keep = 'first'))
#    return tttt

def createUniqueIcd9Df2(df):
    df['year'] = df.apply(lambda row: int(row.adate[6:]),axis = 1)
    df['adate_for_sort'] = df.apply(lambda row: int(row.adate[6:] + row.adate[0:2] + row.adate[3:5]),axis = 1)
    df['index_for_sort'] = df.apply(lambda row: int(row.index_date[6:] + row.index_date[0:2] + row.index_date[3:5]),axis = 1)
    # arrange by year
    dfGbId = df.groupby(['id','CODE'])
    tt = dfGbId.apply(lambda x: x.sort_values('adate_for_sort'))
    ttt = tt.groupby('id')
    tttt = ttt.apply(lambda x: x.drop_duplicates(subset = 'CODE' ,keep = 'first'))
    return tttt


dfCaseDxUnqiueICD9 = createUniqueIcd9Df2(dfCaseDx)
dfControlDxUnqiueICD9 = createUniqueIcd9Df2(dfControlDx)

def cancersPerYear(df,caseControlType):
    relInd = df['CODE'].apply(is_number)
    dfDxNum = df[relInd]
    dfDxNum['CODE'] = dfDxNum['CODE'].apply(float)
    dfDxNumFiltered =  dfDxNum[((dfDxNum['CODE'] >= 140) & (dfDxNum['CODE'] <= 239) & ~((dfDxNum['CODE']>= 162.2) & (dfDxNum['CODE'] <= 162.9) ))]# | ((dfCaseDxNum['CODE'] >= 490) & (dfCaseDxNum['CODE'] <= 496))]
    dfDxNumFiltered['year'] = dfDxNumFiltered.apply(lambda row: int(row.adate[6:]),axis = 1)
    plt.figure()
    cancerPerYear = dfDxNumFiltered['year'].value_counts().sort_index()
    cancerPerYear.plot(kind='bar')
    plt.title(caseControlType + 's - Cancers per year (Without Lung Cancers)')
    return cancerPerYear

 
cancerPerYearCase = cancersPerYear(df = dfCaseDxUnqiueICD9 ,caseControlType ='Case')
cancerPerYearControl = cancersPerYear(df = dfControlDxUnqiueICD9,caseControlType = 'Control')

dfComb  = pd.concat([cancerPerYearCase/cancerPerYearCase.sum() , cancerPerYearControl/cancerPerYearControl.sum()], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of cancers per year (Without Lung Cancers)')


#########
# # Cancers Per Year:   II - unique per person
##########

#def cancersPerYear(df,caseControlType):
#    relInd = df['CODE'].apply(is_number)
#    dfDxNum = df[relInd]
#    dfDxNum['CODE'] = dfDxNum['CODE'].apply(float)
#    dfDxNum['year'] = dfDxNum.apply(lambda row: int(row.adate[6:]),axis = 1)
#    # arrange by year
#    dfDxNumGbId = dfDxNum.groupby('id')
#    tt = dfDxNumGbId.apply(lambda x: x.sort_values('year'))
#    ttt = tt.groupby('id')
#    tttt = ttt.apply(lambda x: x.drop_duplicates(subset = 'CODE' ,keep = 'first'))
#
#    dfDxNumFiltered =  tttt[((tttt['CODE'] >= 140) & (tttt['CODE'] <= 239) & ~((tttt['CODE']>= 162.2) & (tttt['CODE'] <= 162.9) ))]# | ((dfCaseDxNum['CODE'] >= 490) & (dfCaseDxNum['CODE'] <= 496))]
#    plt.figure()
#    dfDxNumFiltered['year'].value_counts().plot(kind='bar')
#    plt.title(caseControlType + 's - Cancers per year (Without Lung Cancers)')
#    return tttt
#
#df = dfCaseDx;
#caseControlType = 'Case'
#dfCaseDxUnqiueICD9 = cancersPerYear(df,caseControlType)
#
#df = dfControlDx;
#caseControlType = 'Control'
#dfControlDxUnqiueICD9 = cancersPerYear(df,caseControlType)



#########
# # Cancers Types:
##########

def cancersPerType(df,caseControlType):
    relInd = df['CODE'].apply(is_number)
    dfDxNum = df[relInd]
    dfDxNum['CODE'] = dfDxNum['CODE'].apply(float)
    dfDxNumFiltered =  dfDxNum[((dfDxNum['CODE'] >= 140) & (dfDxNum['CODE'] <= 210))]# | ((dfCaseDxNum['CODE'] >= 490) & (dfCaseDxNum['CODE'] <= 496))]
    if np.sum((dfDxNum['CODE'] >=  162.2) & (dfDxNum['CODE'] <= 162.9)):
        print('There are lung cancers')
    else:
        print("There aren't lung cancers")
        
    plt.figure()
    cancerNumPerType = dfDxNumFiltered['CODE_DESC'].value_counts()
    cancerNumPerType[0:15].plot(kind='bar')
    plt.gca().yaxis.grid(True)
    plt.title(caseControlType + 's - By Cancers Type')
    return cancerNumPerType

#
#df = dfCaseDx;
#caseControlType = 'Case'
#cancersPerType(df,caseControlType)
#
#df = dfControlDx;
#caseControlType = 'Control'
#cancersPerType(df,caseControlType)

#########
# # Cancers Types: II - Only appear once
##########

cancersPerTypeCase  = cancersPerType(dfCaseDxUnqiueICD9,'Case')
cancersPerTypeControl = cancersPerType(dfControlDxUnqiueICD9,'Control')
dfComb  = pd.concat([cancersPerTypeCase , cancersPerTypeControl], axis = 1)
dfComb  = pd.concat([cancersPerTypeCase/cancersPerTypeCase.sum() , cancersPerTypeControl/cancersPerTypeControl.sum()], axis = 1)
dfComb.columns = ['Case','Control']
dfComb['Case'][(dfComb['Case'] != dfComb['Case'])] = 0
dfComb['Control'][(dfComb['Control'] != dfComb['Control'])] = 0
dfComb['mean'] = (dfComb['Case'] + dfComb['Control'])/2
dfComb = dfComb.sort_values(['mean'], ascending = [False])

plt.figure()
dfComb[0:15].plot(y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of cancers per type')

dfControlDxUnqiueICD9['CODE'] = dfControlDxUnqiueICD9.apply(lambda row: float(row.CODE) if is_number(row.CODE) else 0, axis = 1)
#Lung cancers in control:
ttt = dfControlDxUnqiueICD9[((dfControlDxUnqiueICD9['CODE']>= 162.2) & (dfControlDxUnqiueICD9['CODE'] <= 162.9))]
tttt = ttt.id.unique()
ttttt = dfControlDxUnqiueICD9[dfControlDxUnqiueICD9['id'].isin(tttt)] 
gb = ttttt.groupby('id')


ttttt['CODE'].str.contains('197.0')

#########
# ICD9 per year
##########

def ICD9PerYear(df,caseControlType):
    df['year'] = df.apply(lambda row: int(row.adate[6:]),axis = 1)
    plt.figure()
    icd9perYear = df['year'].value_counts().sort_index()
    icd9perYear.plot(kind='bar')
    plt.title(caseControlType + 's - ICD9s per year ')
    return icd9perYear

df = dfCaseDx;
caseControlType = 'Case'
icd9perYearCase = ICD9PerYear(df,caseControlType)

df = dfControlDx;
caseControlType = 'Control'
icd9perYearControl = ICD9PerYear(df,caseControlType)

dfComb  = pd.concat([icd9perYearCase/icd9perYearCase.sum() , icd9perYearControl/icd9perYearControl.sum()], axis = 1)
dfComb.columns = ['Case','Control']
dfComb['Case'][(dfComb['Case'] != dfComb['Case'])] = 0
dfComb['Control'][(dfComb['Control'] != dfComb['Control'])] = 0
dfComb['mean'] = (dfComb['Case'] + dfComb['Control'])/2
plt.figure()
dfComb.plot(y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of ICD9s per type')

# Get Number of patients per year:
def numberOfRelPatients(df,caseControlType,years):
    df['years_index'] = df.apply(lambda row: int(row.index_date[6:]),axis = 1)
    df['years_mem_start'] = df.apply(lambda row: int(row.mem_start[6:]),axis = 1)
    df['years_mem_stop'] = df.apply(lambda row: int(row.mem_stop[6:]),axis = 1)
    
    patInYear = dict()
    for year in years:
        patInYear[year] = np.sum((df['years_index'] >= year) & (df['years_index'] - 5 <= year) & (df['years_mem_start']  <= year) & (year <= df['years_mem_stop']))
    plt.figure()
    pd.Series(patInYear).sort_index().plot(kind='bar')
    plt.title(caseControlType + "s -Rel. Patients per year ")
    return pd.Series(patInYear)

patInYearCase = numberOfRelPatients(df = dfCaseDemo,caseControlType = 'Case' ,years = dfComb.index)
patInYearControl = numberOfRelPatients(df = dfControlDemo,caseControlType = 'Control' ,years = dfComb.index)

dfComb  = pd.concat([icd9perYearCase/patInYearCase , icd9perYearControl/patInYearControl], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(y = ['Case','Control'],kind = 'bar')
plt.title('#ICD9s/#Active Patients')


# Normalize by Relevant Patients


#########
# EncounterID per year
##########

def EncounterIDPerYear(df,caseControlType):
    df['year'] = df.apply(lambda row: int(row.adate[6:]),axis = 1)
    groupbyEncId = df.groupby('enc_id')
    encIdYears = groupbyEncId.year.head(1)
    plt.figure()
    encIdYears.value_counts().sort_index().plot(kind='bar')
    plt.title(caseControlType + "s - Encounter ID's  per year ")
    return encIdYears.value_counts().sort_index()


# Get Number of patients per year:
def numberOfPatients(df,caseControlType,years):
    years = list(range(2005,2016))
    patInYear = dict()
    for year in years:
        patInYear[year] = np.sum((df['years_start'] < year) & (df['years_stop'] > year))
    plt.figure()
    pd.Series(patInYear).sort_index().plot(kind='bar')
    plt.title(caseControlType + "s - Patients per year ")
    return patInYear


  
df = dfCaseDx;
caseControlType = 'Case'
caseEncPerYearCase = EncounterIDPerYear(df,caseControlType)

years = caseEncPerYearCase.index
df = dfCaseDemo;
caseControlType = 'Case'
numberRelPatientsCase = numberOfRelPatients(df,caseControlType,years)


df = dfControlDx;
caseControlType = 'Control'
controlEncPerYearControl = EncounterIDPerYear(df,caseControlType)
years = controlEncPerYearControl.index
df = dfControlDemo;
caseControlType = 'Control'
numberRelPatientsControl = numberOfRelPatients(df,caseControlType,years)

dfComb  = pd.concat([caseEncPerYearCase/caseEncPerYearCase.sum() , controlEncPerYearControl/controlEncPerYearControl.sum()], axis = 1)
dfComb.columns = ['Case','Control']
dfComb['Case'][(dfComb['Case'] != dfComb['Case'])] = 0
dfComb['Control'][(dfComb['Control'] != dfComb['Control'])] = 0
dfComb['mean'] = (dfComb['Case'] + dfComb['Control'])/2
plt.figure()
dfComb.plot(y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of Encounter IDs')

dfComb  = pd.concat([caseEncPerYearCase/patInYearCase , controlEncPerYearControl/patInYearControl], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(y = ['Case','Control'],kind = 'bar')
plt.title('# Encounter IDs/#Active Patients')
 

# Normalized Encounters per Pat:

#########
# Cases: Lung Cancers Per  per year
##########

def lungCancersPerYear(df,caseControlType):
    relInd = df['CODE'].apply(is_number)
    dfDxNum = df[relInd]
    dfDxNum['CODE'] = dfDxNum['CODE'].apply(float)
#    dfDxNum.loc[:,'CODE'] = dfDxNum['CODE'].apply(float)
#dfDxNum['CODE'] = dfDxNum.apply(lambda row: float(row.CODE), axis = 1)
    
    dfDxNumFiltered =  dfDxNum[((dfDxNum['CODE']>= 162.2) & (dfDxNum['CODE'] <= 162.9) )]# | ((dfCaseDxNum['CODE'] >= 490) & (dfCaseDxNum['CODE'] <= 496))]
    dfDxNumFilteredgb = dfDxNumFiltered.groupby('id')
    len(dfDxNumFilteredgb.groups)
    print(" ".join(['total number',str(len(dfDxNumFilteredgb.groups))]))
    dfDxNumFiltered['year'] = dfDxNumFiltered.apply(lambda row: int(row.adate[6:]),axis = 1)
    plt.figure()
    dfDxNumFilteredgb.head(1)['year'].value_counts().sort_index().plot(kind='bar')
    plt.title(caseControlType + 's - First Lung Cancer per year ')
    return dfDxNumFiltered

df = dfCaseDx;
caseControlType = 'Case'
lungCancersPerYear(df,caseControlType)

#########
# Cases: Lung Cancers  per year Unique!
##########
dfCaseDxUnqiueICD9Filtered = lungCancersPerYear(dfCaseDxUnqiueICD9,'Case')
dfControlDxUnqiueICD9Filtered = lungCancersPerYear(dfControlDxUnqiueICD9,'Control')

ttt = dfDxNumFiltered[dfDxNumFiltered['year'] < 2008]
tttt = ttt.groupby('id').head(1)

xxx =  set([str(id) for id in dfCaseDemo['id']])- set(dfCaseDxUnqiueICD9Filtered['id'])

pid = list(xxx)[5]
ttt = dfCaseDx[dfCaseDx['id'] == pid]
ttt['sort_dx_date'] = ttt.apply(lambda row: row.adate[6:]+row.adate[0:2]+row.adate[3:5],axis = 1)
ttt = ttt.sort_values('sort_dx_date')

# Dx No Cancer
list(xxx)[0] # Nothing  no hosp
list(xxx)[2] # Nothing  no hosp

# Dx No Cancer
ttt = dfCaseDx[dfCaseDx['id'] == dfCaseDxUnqiueICD9Filtered.iloc[3].id]
ttt['sort_dx_date'] = ttt.apply(lambda row: row.adate[6:]+row.adate[0:2]+row.adate[3:5],axis = 1)
ttt = ttt.sort_values('sort_dx_date')

ttt = dfCaseDxUnqiueICD9Filtered.iloc[1]
ttt = dfCaseDxUnqiueICD9Filtered.iloc[2]




# index date vs dxdate
tt = dfCaseDxUnqiueICD9.groupby('id').tail(1)
np.sum(tt['adate_for_sort'] < tt['index_for_sort'] )
np.sum(tt['adate_for_sort'] >= tt['index_for_sort'] )

tt = dfCaseDx.groupby('id')['adate_for_sort'].max()
ttt = dfCaseDx.groupby('id')['index_for_sort'].max()
np.sum(tt < ttt )
np.sum(tt >= ttt)

len(set(dfCaseDx['id']))
ttt = dfCaseDxUnqiueICD9Filtered[dfCaseDxUnqiueICD9Filtered['year'] < 2008]

#reft = datetime.strptime(refDate, "%m/%d/%Y"

## Find lung cacner 1 year before index date
dfCaseDxUnqiueICD9Filtered['delta'] = dfCaseDxUnqiueICD9Filtered.apply(lambda row: (datetime.strptime(row.index_date, "%m/%d/%Y")-datetime.strptime(row.adate, "%m/%d/%Y")).days,axis = 1)
plt.figure()
binEdges = np.append(np.append(np.array(-np.inf),np.arange(-197,1500,5)),np.inf)-0.5
plt.hist(dfCaseDxUnqiueICD9Filtered['delta'] ,binEdges)
plt.grid()
plt.title('Index Date - First ICD9 Lung Cancer Date [days]')
plt.xlabel('[days]')
                         
# Number of ICD9 Per Person - Cases vs. Control:
# Pick index date in 2015, with age 60-65:

dfCaseDemo['index_year'] = dfCaseDemo.apply(lambda row: row.index_date[6:], axis = 1)
caseIds = dfCaseDemo[(dfCaseDemo['age'] > 60) & (dfCaseDemo['age'] < 65) & (dfCaseDemo['index_year'] == '2015')]['id']
caseIds = caseIds.apply(str)
dfCaseIds = dfCaseDx[dfCaseDx['id'].isin(caseIds)]
print(dfCaseIds.shape[0]/len(caseIds))

dfControlDemo['index_year'] = dfControlDemo.apply(lambda row: row.index_date[6:], axis = 1)
controlIds = dfControlDemo[(dfControlDemo['age'] > 60) & (dfControlDemo['age'] < 65) & (dfControlDemo['index_year'] == '2015')]['id']
controlIds = controlIds.apply(str)
dfControlIds = dfControlDx[dfControlDx['id'].isin(controlIds)]
print(dfControlIds.shape[0]/len(controlIds))

