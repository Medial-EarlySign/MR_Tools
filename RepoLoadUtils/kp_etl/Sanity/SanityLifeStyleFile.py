# -*- coding: utf-8 -*-
"""
Created on Tue Mar 27 15:50:02 2018

@author: Ron
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import copyFig

fileControlCbc =  r'\controls_cbc.txt'
fileControlDemo = r'\controls_demo.txt'
fileControlLabList = [r'\controls_lab1.txt',r'\controls_lab2.txt',r'\controls_lab3.txt']

fileCaseCbc =  r'\cases_cbc.txt'
fileCaseDemo = r'\cases_demo.txt'
fileCaseLab = r'\cases_lab.txt'

sourceDir = r'D:\Databases\kpsc'
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 

dfControlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseCbc =  pd.read_csv(sourceDir + fileCaseCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 

###
# Check Diffs between smae ids (to know how to merge) - ID is unique in demo
###
gbId = dfCaseDemo.groupby('id')
np.sum(gbId.size() > 1 )


######
# BMI
######

# Case:
bmi = dfCaseDemo['BMI']
isnan = (bmi != bmi)
bmiValid = bmi[~isnan]
np.mean(bmiValid)
np.std(bmiValid)
np.median(bmiValid)

# Control:
bmi = dfControlDemo['BMI']
isnan = (bmi != bmi)
bmiValid = bmi[~isnan]
np.mean(bmiValid)
np.std(bmiValid)
np.median(bmiValid)

######
# Smoking
######

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








