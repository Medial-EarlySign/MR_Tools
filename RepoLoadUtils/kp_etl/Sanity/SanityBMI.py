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
fileCaseTumor = r'\cases_tumor.txt'
fileControlDx1 = r'\controls_dx1.txt'
fileControlDemo = r'\controls_demo.txt'
fileControlCbc =  r'\controls_cbc.txt'
fileCaseSmoking = r'\'cases_smoking.txt'
fileControlSmoking = r'\'controls_smoking.txt'
fileCaseBMI = r'\cases_bmi.txt'
fileControlBMI = r'\controls_bmi.txt'

dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t')

dfCaseBMI = pd.read_csv(sourceDir + fileCaseBMI, delimiter = '\t')
dfCaseBMI['measure_year'] = dfCaseBMI.apply(lambda row: int(row.measure_date[6:]), axis = 1)
dfControlBMI = pd.read_csv(sourceDir + fileControlBMI, delimiter = '\t')
dfControlBMI['measure_year'] = dfControlBMI.apply(lambda row: int(row.measure_date[6:]), axis = 1)

def testsPerPerson(df,dfDemo):
    gbId = df.groupby(['id']) 
    numTestsPerId = [group[1].shape[0] for group in gbId]
    #add 0 tests:
    numTestsPerId = numTestsPerId + [0]*(dfDemo.shape[0] - len(numTestsPerId) )
    print('mean = ' + str(np.mean(numTestsPerId)))
#    histEdges = .5 + np.arange(-1,30)
#    histEdges = np.append(histEdges, 1000)
#    histPoints = histEdges + 0.5
    histEdges = .5 + np.arange(-1,200)
    xticks = [str(int(point)) for point in histPoints[:-1]]
    xticks += ['> ' + xticks[-1]]
    
    #plt.figure()
    dist,bins = np.histogram(np.array(numTestsPerId), bins = histEdges, normed = True)
    #plt.xticks(np.arange(len(xticks)),xticks)
    #plt.title('Number of FEV1 tests per person')
     
    return dist,bins,xticks



# Check if there are nans

len(dfCaseBMI.id.unique())
len(dfControlBMI.id.unique())

# Last Distribution: 
def createUniqueValueLastDf(df):
#    df['measure_date_for_sort'] = df.apply(lambda row: int(row.measure_date[6:] + row.measure_date[0:2] + row.measure_date[3:5]),axis = 1)
    # arrange by year
    dfGbId = df.groupby(['id'])
#    tt = dfGbId.apply(lambda x: x.sort_values('measure_date_for_sort'))
#    ttt = tt.groupby('id')
    ttt = dfGbId
    tttt = ttt.apply(lambda x: x.drop_duplicates(subset = 'id' ,keep = 'last'))
    return tttt

tt = createUniqueValueLastDf(dfCaseBMI)['BMI']
tt.describe()
tt = createUniqueValueLastDf(dfControlBMI)['BMI']
tt.describe()


dfCaseBMI['BMI'] = dfCaseBMI['BMI'].apply(float)
dfControlBMI['BMI'] = dfControlBMI['BMI'].apply(float)

#
dfCaseBMI['BMI'].describe()
dfControlBMI['BMI'].describe()

bins = np.arange(2003,2016)
binEdges = np.arange(bins[0]-0.5, bins[-1]+1.5) 
plt.figure()
caseDist,_ = np.histogram(list(dfCaseBMI['measure_year']),binEdges,normed = 1)
plt.figure()
controlDist,_ = np.histogram(list(dfControlBMI['measure_year']),binEdges,normed = 1)

dfComb  = pd.concat([pd.Series(caseDist) , pd.Series(controlDist)], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(x =  bins, y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of BMI Reports per year')

caseDist,bins,xticks = testsPerPerson(dfCaseBMI,dfCaseDemo)
controlDist,bins,xticks = testsPerPerson(dfControlBMI,dfControlDemo)

dfComb  = pd.concat([pd.Series(caseDist) , pd.Series(controlDist)], axis = 1)
histPoints = bins + 0.5
xticks = [str(int(point)) for point in histPoints[:-1]]
xticks = xticks[:-1] + ['> ' + xticks[-2]]
dfComb.columns = ['Case','Control']
plt.figure()
t = dfComb.plot( y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of BMI Reports per year')
t.set_xticks(np.arange(0,len(xticks),5))
t.set_xticklabels(xticks)
plt.grid()