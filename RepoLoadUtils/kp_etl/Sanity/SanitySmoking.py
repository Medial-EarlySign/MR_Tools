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
fileCaseSmoking = r'\cases_smoking.txt'
fileControlSmoking = r'\controls_smoking.txt'

dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfCaseSmoking = pd.read_csv(sourceDir + fileCaseSmoking, delimiter = '\t') 
dfCaseSmoking['measure_date_sort'] = dfCaseSmoking.apply(lambda row: row.measure_date[6:] + row.measure_date[0:2] + row.measure_date[3:5] ,axis = 1 )
dfCaseSmoking['measure_year'] = dfCaseSmoking.apply(lambda row: int(row.measure_date[6:]), axis = 1)

dfContorlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
dfControlSmoking = pd.read_csv(sourceDir + fileControlSmoking, delimiter = '\t') 
dfControlSmoking['measure_date_sort'] = dfControlSmoking.apply(lambda row: row.measure_date[6:] + row.measure_date[0:2] + row.measure_date[3:5] ,axis = 1 )
dfControlSmoking['measure_year'] = dfControlSmoking.apply(lambda row: int(row.measure_date[6:]), axis = 1)






def checkIfSorted(df):
    prevId = '0'
    prevDate = '0'
    isSorted = True
    for ind,row in df.iterrows():
        if(row.id == prevId):
            if int(row.measure_date_sort) < int(prevDate):
                isSorted = False
                print(row.measure_date_sort)
                print(prevDate)
                print(ind)
        else:
            prevId = row.id
        
        prevDate = row.measure_date_sort
        
    return isSorted

checkIfSorted(dfControlSmoking)
checkIfSorted(dfCaseSmoking)

####################################
# measures per year
####################################

bins = np.arange(2003,2016)
binEdges = np.arange(bins[0]-0.5, bins[-1]+1.5) 
plt.figure()
caseDist,_ = np.histogram(list(dfCaseSmoking['measure_year']),binEdges,normed = 1)
plt.figure()
controlDist,_ = np.histogram(list(dfControlSmoking['measure_year']),binEdges,normed = 1)

dfComb  = pd.concat([pd.Series(caseDist) , pd.Series(controlDist)], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(x =  bins, y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of Smoking Reports per year')

#####
# Smoking
######
len(dfCaseSmoking.id.unique())
len(dfControlSmoking.id.unique())

#########
# Get Last Value
########

gbId = dfCaseSmoking.groupby('id')
ttt = gbId.tail(1)
tttt = ttt.groupby('TOBACCO_USER')
print(tttt.size())
quitCaseIds = tttt.get_group('Quit').id
neverCaseIds = tttt.get_group('Never').id
yesCaseIds = tttt.get_group('Yes').id
passiveCaseIds = tttt.get_group('Passive').id
n = len(dfCaseDemo.id.unique())
print(tttt.size()/n)
print('Unknown: ' + str(n - tttt.size().sum()))
print('Unknown: ' + str(1 - tttt.size().sum()/n))
gbIdStatusCase = tttt

gbId = dfControlSmoking.groupby('id')
ttt = gbId.tail(1)
tttt = ttt.groupby('TOBACCO_USER')
print(tttt.size())
quitControlIds = tttt.get_group('Quit').id
neverControlIds = tttt.get_group('Never').id
yesControlIds = tttt.get_group('Yes').id
passiveControlIds = tttt.get_group('Passive').id
n = len(dfControlDemo.id.unique())
print(tttt.size()/n)
print('Unknown: ' + str(n - tttt.size().sum()))
print('Unknown: ' + str(1 - tttt.size().sum()/n))
gbIdStatusControl = tttt
#np.sum(tttt.get_group('Quit')['cigquit_yrs'] == tttt.get_group('Quit')['cigquit_yrs'] )/len(tttt.get_group('Quit')['cigquit_yrs'])
#np.sum(tttt.get_group('Quit')['smoking_quit_date'] == tttt.get_group('Quit')['smoking_quit_date'] )/len(tttt.get_group('Quit')['smoking_quit_date'])
#
#
#gbId = dfControlSmoking.groupby('id')
#ttt = gbId.tail(1)
#ttt.groupby('TOBACCO_USER').size()

#########
# Check pack years 
########
###
# Case:
###

# Former:
dfTemp = dfCaseSmoking.loc[dfCaseSmoking['id'].isin(list(quitCaseIds.values))]
dfTemp.loc[:,'pkyrisnum'] = dfTemp.apply(lambda row: row.pkyr==row.pkyr, axis = 1)
tt = dfTemp.groupby('id')['pkyrisnum'].sum()
print('Case Quit has packyears:')
print(np.sum(tt == 0))
print(len(quitCaseIds))
print(np.sum(tt == 0)/len(quitCaseIds))
print(np.sum(tt != 0)/len(quitCaseIds))

print('Case Quit Quit Smoking Time:')
print(np.sum(gbIdStatusCase.get_group('Quit')['smoking_quit_date'] == gbIdStatusCase.get_group('Quit')['smoking_quit_date'] ))
print(np.sum(gbIdStatusCase.get_group('Quit')['smoking_quit_date'] == gbIdStatusCase.get_group('Quit')['smoking_quit_date'] )/len(quitCaseIds))
print(np.sum(gbIdStatusCase.get_group('Quit')['smoking_quit_date'] != gbIdStatusCase.get_group('Quit')['smoking_quit_date'] )/len(quitCaseIds))

# Yes:
dfTemp = dfCaseSmoking.loc[dfCaseSmoking['id'].isin(list(yesCaseIds.values))]
dfTemp.loc[:,'pkyrisnum'] = dfTemp.apply(lambda row: row.pkyr==row.pkyr, axis = 1)
tt = dfTemp.groupby('id')['pkyrisnum'].sum()
print('Case Smokers has packyears:')
print(np.sum(tt == 0))
print(np.sum(tt == 0)/len(yesCaseIds))
print(np.sum(tt != 0)/len(yesCaseIds))

###
# Control:
###

# Former:
dfTemp = dfControlSmoking.loc[dfControlSmoking['id'].isin(list(quitControlIds.values))]
dfTemp.loc[:,'pkyrisnum'] = dfTemp.apply(lambda row: row.pkyr==row.pkyr, axis = 1)
tt = dfTemp.groupby('id')['pkyrisnum'].sum()
print('Control Quit has packyears:')
print(np.sum(tt == 0))
print(np.sum(tt == 0)/len(quitControlIds))
print(np.sum(tt != 0)/len(quitControlIds))

print('Control Quit Quit Smoking Time:')
print(np.sum(gbIdStatusControl.get_group('Quit')['smoking_quit_date'] == gbIdStatusControl.get_group('Quit')['smoking_quit_date'] ))
print(np.sum(gbIdStatusControl.get_group('Quit')['smoking_quit_date'] == gbIdStatusControl.get_group('Quit')['smoking_quit_date'] )/len(quitControlIds))
print(np.sum(gbIdStatusControl.get_group('Quit')['smoking_quit_date'] != gbIdStatusControl.get_group('Quit')['smoking_quit_date'] )/len(quitControlIds))

# Yes:
dfTemp = dfControlSmoking.loc[dfControlSmoking['id'].isin(list(yesControlIds.values))]
dfTemp.loc[:,'pkyrisnum'] = dfTemp.apply(lambda row: row.pkyr==row.pkyr, axis = 1)
tt = dfTemp.groupby('id')['pkyrisnum'].sum()
print('Control Smokers has packyears:')
print(np.sum(tt == 0))
print(np.sum(tt == 0)/len(yesControlIds))
print(np.sum(tt != 0)/len(yesControlIds))

















##############################################################
# Case:
gbTu = dfCaseDemo.groupby('TOBACCO_USER')
sizesSeries = gbTu.size()
sizesNormSeries = gbTu.size()/np.sum(sizesSeries)
dfSizes = pd.concat([sizesSeries,sizesNormSeries],axis = 1)

sizesDict = dict(gbTu.size())
np.sum(list(gbTu.size()))

labels = list(sizesDict.keys()) 
sizes = list(sizesDict.values())
colors = ['gold', 'yellowgreen', 'lightcoral', 'lightskyblue','mediumpurple']

# Plot
plt.figure()
plt.axis('equal')
plt.pie(sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', shadow=True, startangle=140)

# Control:
gbTu = dfControlDemo.groupby('TOBACCO_USER')
sizesSeries = gbTu.size()
sizesNormSeries = gbTu.size()/np.sum(sizesSeries)
dfSizes = pd.concat([sizesSeries,sizesNormSeries],axis = 1)

sizesDict = dict(gbTu.size())
np.sum(list(gbTu.size()))

labels = list(sizesDict.keys()) 
sizes = list(sizesDict.values())
colors = ['gold', 'yellowgreen', 'lightcoral', 'lightskyblue','mediumpurple']

# Plot
plt.figure()
plt.axis('equal')
plt.pie(sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', shadow=True, startangle=140)

######
# How many has Pkg years and  quitting time:
#####

# Control:
gbTu = dfControlDemo.groupby('TOBACCO_USER')
dfControlDemo.TOBACCO_USER.unique()
cigQuitYears = gbTu.get_group('Quit')['cigquit_yrs']
len(cigQuitYears)
np.sum(cigQuitYears != cigQuitYears)/len(cigQuitYears)

gbTu = dfControlDemo.groupby('TOBACCO_USER')
pkearsYes = gbTu.get_group('Yes')['pkyr']
len(pkearsYes)
np.sum(pkearsYes != pkearsYes)/len(pkearsYes)
pkearsQuit = gbTu.get_group('Quit')['pkyr']
len(pkearsQuit)
np.sum(pkearsQuit != pkearsQuit)/len(pkearsQuit)
1 - (np.sum(pkearsYes != pkearsYes) + np.sum(pkearsQuit != pkearsQuit))/(len(pkearsQuit) + len(pkearsYes))

# Case : 
gbTu = dfCaseDemo.groupby('TOBACCO_USER')
dfControlDemo.TOBACCO_USER.unique()
cigQuitYears = gbTu.get_group('Quit')['cigquit_yrs']
len(cigQuitYears)
np.sum(cigQuitYears != cigQuitYears)/len(cigQuitYears)

gbTu = dfCaseDemo.groupby('TOBACCO_USER')
pkearsYes = gbTu.get_group('Yes')['pkyr']
len(pkearsYes)
np.sum(pkearsYes != pkearsYes)/len(pkearsYes)
pkearsQuit = gbTu.get_group('Quit')['pkyr']
len(pkearsQuit)
np.sum(pkearsQuit != pkearsQuit)/len(pkearsQuit)
(np.sum(pkearsYes != pkearsYes) + np.sum(pkearsQuit != pkearsQuit))/(len(pkearsQuit) + len(pkearsYes))

##########
# E mesus. per year
##########

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


