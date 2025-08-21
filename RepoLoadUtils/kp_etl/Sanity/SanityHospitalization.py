# -*- coding: utf-8 -*-
"""
Created on Mon Apr 23 09:17:52 2018

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
fileControlHosp =  r'\controls_hosp.txt'
fileCaseTumor =  r'\cases_tumor.txt'
fileCaseDemo = r'\cases_demo.txt'
fileCaseDx = r'\cases_dx.txt'
fileCaseHosp =  r'\cases_hosp.txt'
fileControlHosp = r'\controls_hosp.txt'

sourceDir = r'D:\Databases\kpsc'
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
dfCaseTumor =  pd.read_csv(sourceDir + fileCaseTumor, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseHosp = pd.read_csv(sourceDir + fileCaseHosp, delimiter = '\t',dtype = str)
dfControlHosp = pd.read_csv(sourceDir + fileControlHosp, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)

###########################
# Number of Bad hospitalization records (missing icd9, adate , ddate)
##########################

badIndControl = (dfControlHosp['CODE'] != dfControlHosp['CODE']) | (dfControlHosp['adate'] != dfControlHosp['adate']) | (dfControlHosp['ddate'] != dfControlHosp['ddate'])
print(np.sum(badIndControl))
print(dfControlHosp.shape[0]) 

badIndCase = (dfCaseHosp['CODE'] != dfCaseHosp['CODE']) | (dfCaseHosp['adate'] != dfCaseHosp['adate']) | (dfCaseHosp['ddate'] != dfCaseHosp['ddate'])
print(np.sum(badIndCase))
print(dfCaseHosp.shape[0]) 

dfCaseHosp = dfCaseHosp[~badIndCase]
dfControlHosp = dfControlHosp[~badIndControl]

dfCaseHosp['index_for_sort'] = dfCaseHosp.apply(lambda row: int(row.index_date[6:] + row.index_date[0:2] + row.index_date[3:5]),axis = 1)
dfCaseHosp['adate_for_sort'] = dfCaseHosp.apply(lambda row: int(row.adate[6:] + row.adate[0:2] + row.adate[3:5]),axis = 1)
dfCaseHosp['ddate_for_sort'] = dfCaseHosp.apply(lambda row: int(row.ddate[6:] + row.ddate[0:2] + row.ddate[3:5]),axis = 1)
dfCaseHosp['adate_days'] =  dfCaseHosp.apply(lambda row: datetime.strptime(str(row.adate_for_sort), '%Y%m%d') ,axis = 1)
dfCaseHosp['ddate_days'] =  dfCaseHosp.apply(lambda row: datetime.strptime(str(row.ddate_for_sort), '%Y%m%d') ,axis = 1)
dfCaseHosp['indexdate_days'] =  dfCaseHosp.apply(lambda row: datetime.strptime(str(row.ddate_for_sort), '%Y%m%d') ,axis = 1)
dfCaseHosp['adate_year'] =  dfCaseHosp.apply(lambda row: int(row.adate[6:]) ,axis = 1)
dfCaseHosp['ddate_year'] =  dfCaseHosp.apply(lambda row: int(row.ddate[6:]) ,axis = 1)
dfCaseHosp['ddate_adate_delta_days'] =  dfCaseHosp.apply(lambda row: (row.ddate_days-row.adate_days).days ,axis = 1)

dfControlHosp['index_for_sort'] = dfControlHosp.apply(lambda row: int(row.index_date[6:] + row.index_date[0:2] + row.index_date[3:5]),axis = 1)
dfControlHosp['adate_for_sort'] = dfControlHosp.apply(lambda row: int(row.adate[6:] + row.adate[0:2] + row.adate[3:5]),axis = 1)
dfControlHosp['ddate_for_sort'] = dfControlHosp.apply(lambda row: int(row.ddate[6:] + row.ddate[0:2] + row.ddate[3:5]),axis = 1)
dfControlHosp['adate_days'] =  dfControlHosp.apply(lambda row: datetime.strptime(str(row.adate_for_sort), '%Y%m%d') ,axis = 1)
dfControlHosp['ddate_days'] =  dfControlHosp.apply(lambda row: datetime.strptime(str(row.ddate_for_sort), '%Y%m%d') ,axis = 1)
dfControlHosp['indexdate_days'] =  dfControlHosp.apply(lambda row: datetime.strptime(str(row.ddate_for_sort), '%Y%m%d') ,axis = 1)
dfControlHosp['adate_year'] =  dfControlHosp.apply(lambda row: int(row.adate[6:]) ,axis = 1)
dfControlHosp['ddate_year'] =  dfControlHosp.apply(lambda row: int(row.ddate[6:]) ,axis = 1)
dfControlHosp['ddate_adate_delta_days'] =  dfControlHosp.apply(lambda row: (row.ddate_days-row.adate_days).days ,axis = 1)


###########################
# Admissions per year
###########################

def admPerYear(df,caseControlType):
    plt.figure()
    admsperYear = df['adate_year'].value_counts().sort_index()
    admsperYear.plot(kind='bar')
    plt.title(caseControlType + 's - Hospitalization admissions per year ')
    return admsperYear 

admPerYear(dfCaseHosp,'Case')
admPerYear(dfControlHosp,'Control')

bins = np.arange(2003,2016)
binEdges = np.arange(bins[0]-0.5, bins[-1]+1.5) 
plt.figure()
caseDist,_ = np.histogram(list(dfCaseHosp['adate_year']),binEdges,normed = 1)
plt.figure()
controlDist,_ = np.histogram(list(dfControlHosp['adate_year']),binEdges,normed = 1)

dfComb  = pd.concat([pd.Series(caseDist) , pd.Series(controlDist)], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(x =  bins, y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of hospital admissions per year')

###########################
# Admissions per person
###########################

def hospitalizationsPerPerson(df,dfDemo, caseControlType):
    dfUnique = df.drop_duplicates(subset = 'enc_id' ,keep = 'first')
    gbId = dfUnique.groupby(['id']) 
    numHospPerId = [group[1].shape[0] for group in gbId]
    #add 0 tests:
    numHospPerId = numHospPerId + [0]*(dfDemo.shape[0] - len(numHospPerId) )
    histEdges = .5 + np.arange(-1,10)
    xticks = histEdges + 0.5
    
    plt.figure()
    plt.hist(numHospPerId, bins = histEdges ,normed = 1)
    plt.xticks(xticks)
    plt.title('Number of Hospitalizations tests per person')
    hist = np.histogram(numHospPerId, bins = histEdges,density = True)
    
#    testsperYear = df['year'].value_counts().sort_index()
#    testsperYear.plot(kind='bar')
#    plt.title(caseControlType + 's - Fev1 Tests per year ')
    return hist

len(dfCaseHosp.id.unique())
caseHist = hospitalizationsPerPerson(dfCaseHosp,dfCaseDemo, 'Case')
controlHist = hospitalizationsPerPerson(dfControlHosp,dfControlDemo, 'Control')

dfComb  = pd.concat([pd.Series(caseHist[0]),pd.Series(controlHist[0])], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of Hospitalizations per person')
plt.grid()

# Check  ages 60 - 65
caseIds = dfCaseDemo[(dfCaseDemo['age'] > 60) & (dfCaseDemo['age'] < 65)]['id']
controlIds = dfControlDemo[(dfControlDemo['age'] > 60) & (dfControlDemo['age'] < 65)]['id']

caseIds = caseIds.apply(str)
dfCaseIds = dfCaseHosp[dfCaseHosp['id'].isin(caseIds)]
dfCaseDemoIds = dfCaseDemo[(dfCaseDemo['age'] > 60) & (dfCaseDemo['age'] < 65)]

controlIds = controlIds.apply(str)
dfControlIds = dfControlHosp[dfControlHosp['id'].isin(controlIds)]
dfControlDemoIds = dfControlDemo[(dfControlDemo['age'] > 60) & (dfControlDemo['age'] < 65)]

caseHist = hospitalizationsPerPerson(dfCaseIds,dfCaseDemoIds, 'Case')
controlHist = hospitalizationsPerPerson(dfControlIds,dfControlDemoIds, 'Control')

dfComb  = pd.concat([pd.Series(caseHist[0]),pd.Series(controlHist[0])], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of Hospitalizations per person for ages 60-65')
plt.grid()

#############################
# Dischagre - Admission
#############################
bins = np.arange(0,365)
binEdges = np.arange(bins[0]-0.5, bins[-1]+1.5) 
plt.figure()
caseDist,_ = np.histogram(list(dfCaseHosp['ddate_adate_delta_days']),binEdges,normed = 1)
plt.figure()
controlDist,_ = np.histogram(list(dfControlHosp['ddate_adate_delta_days']),binEdges,normed = 1)

dfComb  = pd.concat([pd.Series(caseDist) , pd.Series(controlDist)], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(x =  bins, y = ['Case','Control'])
plt.title('Distribution of hospitlization lengths')

plt.grid()

####################################
# Categrories distrution
######################################

def dfs(start, code_map , visited=None,visited_code=None, children_map = None, level_map = None, level = None):
    if visited is None:
        level = 0
        visited = set()
        visited_code = set()
        children_map = dict()
        level_map = dict()
    
    if not(start in visited):
        if len(start.children) > 0:
            children_map[start.code] = [child.code for child in start.children]
        code_map[start.code] = start.descr.title()
        level_map[start.code] = level
        
    visited.add(start)
    visited_code.add(start.code)
    
    for next in set(start.children) - visited:
        dfs(next, code_map , visited,visited_code,children_map, level_map, level + 1)
    return visited,visited_code,children_map, code_map, level_map

import sys
sys.path.append('H:\\MR\\Tools\\RepoLoadUtils\\kp_etl\\icd9')
sys.path.append('/nas1/UsersData/ron/MR/Tools/RepoLoadUtils/kp_etl/icd9')
from icd9 import ICD9

tree = ICD9('H:/MR/Tools/RepoLoadUtils/kp_etl/icd9/codes.json')
code_map = dict()     
visited,visited_code,children_map, code_map, level_map = dfs(tree,code_map);
level2code = dict()
for k,v in level_map.items():
    if v in level2code:
        level2code[v].append(k)
    else:
        level2code[v] = [k]

{k:len(v) for k,v in level2code.items()}
sorted(level2code[1])
# Check that each icd9 is unique in hosp.
gbCodeControl = dfControlHosp.groupby('enc_id')
dfControlHospUniq = gbCodeControl.apply(lambda x: x.drop_duplicates(subset = 'CODE' ,keep = 'first'))

gbCodeCase = dfCaseHosp.groupby('enc_id')
dfCaseHospUniq = gbCodeCase.apply(lambda x: x.drop_duplicates(subset = 'CODE' ,keep = 'first'))

newCodes = level2code[1].copy()
newCodes = newCodes + ['280-289','740-759']
codes = sorted(newCodes) # added missing code
# creating low/high bound for each group
bordersDict = dict()
def findIcd9Group(rowCode,codes):
    rowCode = str(rowCode)
    for codeInd in range(len(codes)-1):
        start = codes[codeInd].split('-')[0]
        startNext = codes[codeInd + 1].split('-')[0]
#        print(start)
#        print(startNext)
        if (start <= rowCode < startNext):
            return codes[codeInd]
    if  (rowCode < 'V86'): #used to be if  (rowCode < 'V85'): solves one  V85.24 
        return codes[-1]
        
    return 'Unknown'

ignore_dict = dict()
     
icd92icd10Dict = dict()
icd102icd9Dict = dict()

code_map['E870-E876'] = 'Misadventures To Patients During Surgical And Medical Care'
code_map['280-289'] = 'Diseases Of The Blood And Blood-Forming Organs '
code_map['740-759'] = 'Congenital Anomalies'
#icd9dict.genIcd9Map(ignore_dict, code_map, outputDir + 'dict.icd9')
icd9dict.icd9icd10conversion3(icd92icd10Dict, icd102icd9Dict)

#Cases:
dfCaseHospUniq['ICD9_code'] = dfCaseHospUniq.apply(lambda row: icd102icd9Dict[row.CODE] if (row.CODE_SUBTYPE == 'ICD10') else row.CODE,axis = 1 )
dfCaseHospUniq['Code_Group'] = dfCaseHospUniq.apply(lambda row: findIcd9Group(row.ICD9_code,codes),axis = 1 )
#tt = dfCaseHospUniq['Code_Group'].value_counts().sort_index()
tt = dfCaseHospUniq['Code_Group'].value_counts().sort_index().reset_index()
tt.columns = ['Code_Group','Freq']
missingCodes = list(set(codes) - set(tt.Code_Group))
missingCodesSeries = pd.Series([0]*len(missingCodes),missingCodes)
dfMissingCodes = pd.DataFrame({'Code_Group':missingCodes, 'Freq':[0]*len(missingCodes)})
dfCodesHist = pd.DataFrame(pd.concat([dfMissingCodes, tt])).sort_values('Code_Group')
dfCodesHist['CodeName'] = dfCodesHist.apply(lambda row: code_map[row.Code_Group] ,axis = 1 )
FreqSum = dfCodesHist['Freq'].sum()
dfCodesHist['Prob'] = dfCodesHist.apply(lambda row: row.Freq/FreqSum ,axis = 1 )

#Controls:
dfControlHospUniq['ICD9_code'] = dfControlHospUniq.apply(lambda row: icd102icd9Dict[row.CODE] if (row.CODE_SUBTYPE == 'ICD10') else row.CODE,axis = 1 )
dfControlHospUniq['Code_Group'] = dfControlHospUniq.apply(lambda row: findIcd9Group(row.ICD9_code,codes),axis = 1 )
#tt = dfControlHospUniq['Code_Group'].value_counts().sort_index()
tt = dfControlHospUniq['Code_Group'].value_counts().sort_index().reset_index()
tt.columns = ['Code_Group','Freq']
missingCodes = list(set(codes) - set(tt.Code_Group))
missingCodesSeries = pd.Series([0]*len(missingCodes),missingCodes)
dfMissingCodes = pd.DataFrame({'Code_Group':missingCodes, 'Freq':[0]*len(missingCodes)})
dfControlCodesHist = pd.DataFrame(pd.concat([dfMissingCodes, tt])).sort_values('Code_Group')
dfControlCodesHist['CodeName'] = dfControlCodesHist.apply(lambda row: code_map[row.Code_Group] ,axis = 1 )
FreqSum = dfControlCodesHist['Freq'].sum()
dfControlCodesHist['ProbControl'] = dfControlCodesHist.apply(lambda row: row.Freq/FreqSum ,axis = 1 )


result = pd.merge(dfCodesHist, dfControlCodesHist, on='Code_Group')
dfComb = result.iloc[:,[2,3,6]]
dfComb.columns = ['GroupName','Case','Control']
dfComb['mean'] = (dfComb['Case'] + dfComb['Control'])/2
dfComb = dfComb.sort_values(['mean'], ascending = [False])

plt.figure()
plt.xticks(rotation=45)
dfComb[0:10].plot(x = 'GroupName', y = ['Case','Control'],kind = 'bar',rot = -45)
plt.title('Distribution of Hospitalizations Per ICD9 Groups')
plt.grid()


