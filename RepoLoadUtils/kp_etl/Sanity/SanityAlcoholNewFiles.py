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
fileCaseAlcohol = r'\cases_alcohol.txt'
fileControlAlcohol = r'\controls_alcohol.txt'


dfCaseAlcohol = pd.read_csv(sourceDir + fileCaseAlcohol, delimiter = '\t')
dfCaseAlcohol['measure_year'] = dfCaseAlcohol.apply(lambda row: int(row.measure_date[6:]), axis = 1)
dfControlAlcohol = pd.read_csv(sourceDir + fileControlAlcohol, delimiter = '\t')
dfControlAlcohol['measure_year'] = dfControlAlcohol.apply(lambda row: int(row.measure_date[6:]), axis = 1)
# Check if there are nans

len(dfCaseAlcohol.id.unique())
len(dfControlAlcohol.id.unique())

bins = np.arange(2003,2016)
binEdges = np.arange(bins[0]-0.5, bins[-1]+1.5) 
plt.figure()
caseDist,_ = np.histogram(list(dfCaseAlcohol['measure_year']),binEdges,normed = 1)
plt.figure()
controlDist,_ = np.histogram(list(dfControlAlcohol['measure_year']),binEdges,normed = 1)

dfComb  = pd.concat([pd.Series(caseDist) , pd.Series(controlDist)], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(x =  bins, y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of Alcohol Reports per year')

# Last Distribution: 
def createUniqueValueLastDf(df):
    df['measure_date_for_sort'] = df.apply(lambda row: int(row.measure_date[6:] + row.measure_date[0:2] + row.measure_date[3:5]),axis = 1)
    # arrange by year
    dfGbId = df.groupby(['id'])
    tt = dfGbId.apply(lambda x: x.sort_values('measure_date_for_sort'))
    ttt = tt.groupby('id',as_index=False)
    tttt = ttt.apply(lambda x: x.drop_duplicates(subset = 'id' ,keep = 'last'))
    return tttt


def createUniqueValueLastDf2(df):
    df['measure_date_for_sort'] = df.apply(lambda row: int(row.measure_date[6:] + row.measure_date[0:2] + row.measure_date[3:5]),axis = 1)
    # arrange by year
    dfGbId = df.groupby(['id'])
    tttt = dfGbId.apply(lambda x: x.loc[x.measure_date_for_sort.idxmax()])
    return tttt


t1 = createUniqueValueLastDf(dfCaseAlcohol)['ALCOHOL_USER'].value_counts()
t12 = createUniqueValueLastDf2(dfCaseAlcohol)['ALCOHOL_USER'].value_counts()

t2 = createUniqueValueLastDf(dfControlAlcohol)['ALCOHOL_USER'].value_counts()
t22 = createUniqueValueLastDf2(dfControlAlcohol)['ALCOHOL_USER'].value_counts()