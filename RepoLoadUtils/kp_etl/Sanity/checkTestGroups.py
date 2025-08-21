# -*- coding: utf-8 -*-
"""
Created on Sun Sep  2 10:24:16 2018

@author: Ron
"""

import testGroupingDicts
import pandas as pd
import numpy as np

sourceDir = 'D:/Databases/kpsc'
#sourceDir = '/server/Data/kpsc'

fileCaseCbc =  '/15-07-2018/cases_cbc.txt'
fileControlCbc =  '/15-07-2018/controls_cbc.txt'
fileControlDemo = '/controls_demo.txt'
fileCaseDemo = '/cases_demo.txt'
fileControlLabList = ['/20-08-2018/controls_lab1.txt','/20-08-2018/controls_lab2.txt','/20-08-2018/controls_lab3.txt']
fileCaseLab = '/20-08-2018/cases_lab.txt'

dfCaseCbc =  pd.read_csv(sourceDir + fileCaseCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfControlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
dfControlLabList = []
for fileControlLab in fileControlLabList:
    dfControlLabList.append(pd.read_csv(sourceDir + fileControlLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
    
dfControlLab = pd.concat(dfControlLabList)  
dfCaseLab = pd.read_csv(sourceDir + fileCaseLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)

dfCaseLab.columns
numDict = dfCaseLab.groupby('component2').size()
for comp in dfCaseLab.component2.unique():
    print('======================')
    print(comp)
    if comp in testGroupingDicts.testGroupDict:
        print('GOOD!')
    else:
        print('BAD!!!!!!!!!!!!!!!!!!!!')
    
    print('num = ' + str(numDict[comp]))
        
Thresh = 1000
numDict = dfControlLab.groupby('component2').size()
for comp in dfControlLab.component2.unique():

    if numDict[comp] > Thresh:
        print('======================')
        print(comp)
        if comp in testGroupingDicts.testGroupDict:
            print('GOOD!')
        else:
            print('BAD!!!!!!!!!!!!!!!!!!!!')
        
        print('num = ' + str(numDict[comp]))

# check if exists in previos file
   
fileControlLabOldList = ['/17-06-2018/controls_lab1.txt','/17-06-2018/controls_lab2.txt','/controls_lab3.txt']
fileCaseOldLab = '/17-06-2018/cases_lab.txt'

dfControlLabList = []
for fileControlLab in fileControlLabOldList:
    dfControlLabList.append(pd.read_csv(sourceDir + fileControlLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
    
dfControlOldLab = pd.concat(dfControlLabList)  
dfCaseOldLab = pd.read_csv(sourceDir + fileCaseOldLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)

## Check new names 
tt1 = set(dfControlOldLab.component2) - set(dfControlLab.component2)
numDictOld = dfControlOldLab.groupby('component2').size()

for test in tt1:
    print('==============')
    print(test)
    print(numDictOld[test])

tt2 = set(dfControlLab.component2) - set(dfControlOldLab.component2)
total = 0
for test in tt2:
    print('==============')
    print(test)
    print(numDict[test])
    total += numDict[test]

# check number of new items
Thresh = 1000
numDict = dfControlLab.groupby('component2').size()
for comp in dfControlLab.component2.unique():

    if numDict[comp] > Thresh:
        print('======================')
        print(comp)
        if comp in testGroupingDicts.testGroupDict:
            print('GOOD!')
        else:
            print('BAD!!!!!!!!!!!!!!!!!!!!')
        
        print('num = ' + str(numDict[comp]))


# 
df = dfControlLab.copy()
df['testsGroup'] =  df['testsGroup'].map(testGroupingDicts.testGroupDict)
tt = df.drop_duplicates(["testsGroup", "unit2"])
ttt  = df[df['testsGroup'] == 'TIBC'].unit2   
ttt  = df[df['testsGroup'] == 'INR'].unit
ttt2 = df[df['component2'] == 'PT-INR'].unit
 
# check CPT:
ttt = dfControlLab.groupby('cptcode')
df2 = dfControlLab.drop_duplicates(["cptcode", "component2"])
tt = df2.groupby('cptcode').component2