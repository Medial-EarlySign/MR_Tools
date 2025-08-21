# -*- coding: utf-8 -*-
"""
Created on Sun Jul 22 10:30:00 2018

@author: Ron
"""
from collections import Counter
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
import testGroupingDictsForDistribution


def getRes(testSeries):
    sortedValues = np.sort(np.unique(np.array(testSeries)))
    cnt = testSeries.value_counts()
    
    diffCnt = Counter()
    for k in range(1,len(sortedValues)):
        currDiff = sortedValues[k] - sortedValues[k-1]
        diffCnt[currDiff] += (cnt[sortedValues[k] ] + cnt[sortedValues[k-1]])      
    
    print(str(diffCnt.most_common(4)))
    return diffCnt.most_common(1)[0][0]

def getBins(gb):
    # Get smallest resolution and define hist bins
    resVec = []
    for gr in gb:
        print(gr[0])
        print(len(gr[1]))
        if len(gr[1]) > 500:
            testSeries =  gr[1]['value2']
            testSeries = testSeries.apply(float)
            resVec.append(getRes(testSeries[testSeries == testSeries]))
            
    minVal = dfNew['value2'].min()
    maxVal = dfNew['value2'].max()
    minRes = min(resVec)
    binEdges = np.arange(minVal - minRes/2,maxVal + minRes/2,minRes)
    bins = np.arange(minVal,maxVal,minRes)
    return bins,binEdges

N = 50 # number of samples to pick  
sourceDir = r'D:\Databases\kpsc'
fileControlCbc =  '/15-07-2018/controls_cbc.txt'
fileControlLabList = ['/20-08-2018/controls_lab1.txt','/20-08-2018/controls_lab2.txt','/20-08-2018/controls_lab3.txt']

dfControlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 

dfControlLabList = []
for fileControlLab in fileControlLabList:
    dfControlLabList.append(pd.read_csv(sourceDir + fileControlLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
    
dfControlLab = pd.concat(dfControlLabList) 

fileCaseLab = '/20-08-2018/cases_lab.txt'
fileCaseCbc =  '/15-07-2018/cases_cbc.txt'
dfCaseLab =  pd.read_csv(sourceDir + fileCaseLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseCbc =  pd.read_csv(sourceDir + fileCaseCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfLabCbc  = pd.concat([dfControlCbc,dfCaseCbc])
#dfLabCbc  = pd.concat([dfCaseLab,dfControlLab])

#tests = ['GLUCOSE, BLOOD', 'GLUCOSE POST FAST','GLUCOSE, BLOOD, POCT','GLUC-FAST']
testGroupsList = list(testGroupingDictsForDistribution.testGroupRevDict)
ind = 0
for ind in range(0,len(testGroupsList)):
    testGroup = testGroupsList[ind]

    tests = testGroupingDictsForDistribution.testGroupRevDict[testGroup]
    print(testGroup)
    dfNew = dfLabCbc[dfLabCbc['component2'].isin(set(tests))]
    if len(dfNew) == 0:
        continue

    dfNew['value2'] = dfNew['value2'].apply(float) 
    if set(['procdesc','component','component2','rrange','unit']) in set(dfNew.columns):
        # Lab    
        dfNew[['procdesc','component','component2','rrange','unit']] = dfNew[['procdesc','component','component2','rrange','unit']].fillna('-666')
        gb = dfNew.groupby(['procdesc','component','component2','rrange','unit'])
    else:
        dfNew[['component','component2','rrange','unit']] = dfNew[['component','component2','rrange','unit']].fillna('-666')
        gb = dfNew.groupby(['component','component2','rrange','unit'])
        
    # 
    dfHist = pd.DataFrame([])
    maxGroup = gb.size().idxmax()
    bins,binEdges = getBins(gb)
    
    # Check t-test vs. main group
    refGroup = gb.get_group(maxGroup)
    
    
    for gr in gb:
        dfTemp = gr[1]
    #    if gr[0] == list(gb.groups.items())[0][0]:
    #        dfTemp['value2'] = 1.1*dfTemp['value2']
    #        print('changed')
        print(gr[0])
        print(len(dfTemp))
        ind1 = np.random.choice(len(refGroup), min(N,len(refGroup)), replace=False)
        ind2 = np.random.choice(len(dfTemp), min(N,len(dfTemp)), replace=False)
        ttest_res = stats.ttest_ind(refGroup.value2.iloc[ind1],gr[1].value2.iloc[ind2]) 
        print(ttest_res)  
        if ttest_res.pvalue < 0.1:
            print('ref mean = ' + str(refGroup.value2.iloc[ind1].mean()))
            print('other mean = ' + str(gr[1].value2.iloc[ind2].mean()))
            print(gr[0])
            print(dfTemp.value2.describe())
            print(maxGroup)
            print(refGroup.describe())
            tt = input("Press Enter to continue... or q to quit")
            if tt == 'q':
                break;
        
        vals = dfTemp['value2'][dfTemp['value2'] == dfTemp['value2']]
        hist,_ = np.histogram(vals,binEdges,normed = 1)
        colName = "_".join(gr[0]).replace(' ','_')
        dfHist[colName] = hist  
        
        
#    plt.figure()
#    dfHist.plot(x =  bins, y = dfHist.columns,kind = 'bar')
#    
