# -*- coding: utf-8 -*-
"""
Created on Thu May  3 11:18:18 2018

@author: Ron
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import copyFig


def isNaN(num):
    return num != num

sourceDir = r'D:\Databases\kpsc\03-05-2018'
fileCaseDemo = r'\cases_demo.txt'

fileCaseFev1 = r'\cases_pft.txt'
fileControlDx1 = r'\controls_dx1.txt'
fileControlDemo = r'\controls_demo.txt'
fileControlCbc =  r'\controls_cbc.txt'
fileControlFev1 = r'\controls_pft.txt'

dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t') 
dfCaseFev1 = pd.read_csv(sourceDir + fileCaseFev1, delimiter = '\t') 
dfControlFev1 = pd.read_csv(sourceDir + fileControlFev1, delimiter = '\t') 

dfControlFev1['year'] = dfControlFev1.apply(lambda row: row.measure_date[6:],axis = 1)
dfCaseFev1['year'] = dfCaseFev1.apply(lambda row: row.measure_date[6:],axis = 1)



def testsPerYear(df,caseControlType):
    plt.figure()
    testsperYear = df['year'].value_counts().sort_index()
    testsperYear.plot(kind='bar')
    plt.title(caseControlType + 's - Fev1 Tests per year ')
    return testsperYear

def testsPerPerson(df,dfDemo, caseControlType):
    gbId = df.groupby(['id']) 
    numTestsPerId = [group[1].shape[0] for group in gbId]
    #add 0 tests:
    numTestsPerId = numTestsPerId + [0]*(dfDemo.shape[0] - len(numTestsPerId) )
    histEdges = .5 + np.arange(-1,5)
    histEdges = np.append(histEdges, np.inf)
    histPoints = histEdges + 0.5
    xticks = [str(int(point)) for point in histPoints[:-1]]
    xticks += ['> ' + xticks[-1]]
    
    hist,_ = np.histogram(numTestsPerId, bins = histEdges)
    plt.figure()
    plt.hist(numTestsPerId, bins = histEdges,normed = 1)
    plt.xticks(np.arange(len(xticks)),xticks)
    plt.title('Number of FEV1 tests per person')
    
    plt.figure()
    testsperYear = df['year'].value_counts().sort_index()
    testsperYear.plot(kind='bar')
    plt.title(caseControlType + 's - Fev1 Tests per year ')
    return testsperYear,hist,xticks

def valuesDistribution(df,field):
    values = df[field]
    hist, binEdges = np.histogram(values,bins = 50,normed = 1)
    return hist, binEdges
    
    
###################################################
# Number of tests per year
###################################################

testsPerYear(dfCaseFev1,'Case')
testsPerYear(dfControlFev1,'Control')
testsperYearCase,histNumTestsPerIdCase,histPointsCase = testsPerPerson(dfCaseFev1,dfCaseDemo, 'Case')
testsperYearControl,histNumTestsPerIdControl,histPointsControl = testsPerPerson(dfControlFev1,dfControlDemo, 'Control')

dfComb  = pd.concat([pd.Series(testsperYearCase/testsperYearCase.sum()) , pd.Series(testsperYearControl/testsperYearControl.sum())], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(x =  dfComb.index, y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of Spirometry Tests per Year')

dfComb  = pd.concat([pd.Series(histNumTestsPerIdCase/histNumTestsPerIdCase.sum()) , pd.Series(histNumTestsPerIdControl/histNumTestsPerIdControl.sum())], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot( y = ['Case','Control'],kind = 'bar')
plt.title('Number of Tests per Person')
plt.grid()

histCase, binEdgesCase = valuesDistribution(dfCaseFev1,'FEV1_FVC')
binsCase = (binEdgesCase[0:-1] + binEdgesCase[1:])/2
histControl, binEdgesControl = valuesDistribution(dfControlFev1,'FEV1_FVC')
binsControl = (binEdgesControl[0:-1] + binEdgesControl[1:])/2
plt.figure()
plt.plot(binsCase,histCase)
plt.plot(binsControl,histControl)
plt.xlabel('FEV1/FVC [%]')
plt.ylabel('pdf')
plt.title('Cases Vs. Controls FEV1/FVC')

histCase, binEdgesCase = valuesDistribution(dfCaseFev1,'FEV1_PERCENT_PREDICTED')
binsCase = (binEdgesCase[0:-1] + binEdgesCase[1:])/2
histControl, binEdgesControl = valuesDistribution(dfControlFev1,'FEV1_PERCENT_PREDICTED')
binsControl = (binEdgesControl[0:-1] + binEdgesControl[1:])/2
plt.figure()
plt.plot(binsCase,histCase)
plt.plot(binsControl,histControl)
plt.xlabel('FEV1 predicted [%]')
plt.ylabel('pdf')
plt.title('Cases Vs. Controls FEV1 predicted')




