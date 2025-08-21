# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 12:25:45 2018

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

sourceDir = r'D:\Databases\kpsc'
fileCaseDemo = r'\cases_demo.txt'
fileCaseTumor = r'\cases_tumor.txt'
fileControlDx1 = r'\controls_dx1.txt'
fileControlDemo = r'\controls_demo.txt'
fileControlCbc =  r'\controls_cbc.txt'

dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfCaseTumor = pd.read_csv(sourceDir + fileCaseTumor, delimiter = '\t') 

dfContorlDx1 = pd.read_csv(sourceDir + fileControlDx1, delimiter = '\t') 
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
###############################################################
# 1. Demographic File
##############################################################

####
# a. 
####

numTypes = dfCaseTumor['histology'].value_counts()

ids = dfCaseTumor.id.unique()
len(ids)
typeDict = dict()
badIds = []
for index, row in dfCaseTumor.iterrows():   
    if row['id'] in typeDict:
        if  (not(row['histology'] == typeDict[row['id']])):
            print('ID : ' + str(row['id']) + ' Error! , first = ' + typeDict[row['id']] +  ' second = ' + row['histology']  )
            badIds.append(row['id'])
            
    typeDict[row['id']] = row['histology']

for badId in badIds:
    typeDict.pop(badId)

count = Counter(typeDict.values())

dfCaseTumor.groupby('histology').count()

####
# b.
####

# Control: 
# Get ID's
# all patients have IDs
idsSet = set(dfControlDemo.id.unique())
num_lines = sum(1 for line in open(sourceDir + fileControlDemo))
if len(idsSet) == num_lines-1:
    print('Good')
else:
    print('bad')

# Get Number of Gender
gender = dfControlDemo['GENDER']
np.sum(gender == 'M') + np.sum(gender == 'F')

# Check  that all are above 45 in 2008:
birthDates = dfControlDemo['dob']

cntGood = 0
badDict = dict()
refDate = '12/31/2008'
reft = datetime.strptime(refDate, "%m/%d/%Y")
ind = 0
for birthDate in birthDates:
    if int(birthDate[6:]) < 1964:
        cntGood +=1 
    else:
        badDict[dfControlDemo.iloc[ind]['id']] = birthDate[6:]
        
    ind += 1

count = Counter(badDict.values())   
np.sum(list(count.values())) 

# Case: 
idsSet = set(dfCaseDemo.id.unique())
num_lines = sum(1 for line in open(sourceDir + fileCaseDemo))
if len(idsSet) == num_lines-1:
    print('Good')
else:
    print('bad')

# Get Number of Gender
gender = dfCaseDemo['GENDER']
np.sum(gender == 'M') + np.sum(gender == 'F')

# Check  that all are above 45 in 2008:
birthDates = dfCaseDemo['dob']

cntGood = 0
badDict = dict()
refDate = '12/31/2008'
reft = datetime.strptime(refDate, "%m/%d/%Y")
ind = 0
for birthDate in birthDates:
    if int(birthDate[6:]) < 1964:
        cntGood +=1 
    else:
        badDict[dfControlDemo.iloc[ind]['id']] = birthDate[6:]
        
    ind += 1

count = Counter(badDict.values())   
np.sum(list(count.values())) 

####
# c - Distribution analysis
####

# BirthDays

# Control:
birthDates = dfControlDemo['dob']
birthYears = [int(birthDate[6:]) for birthDate in birthDates ]
years = np.arange(1900,1971)+.5
binMiddleYears = np.arange(1901,1971)
hist,_ = np.histogram(birthYears,bins = years)
plt.figure()
plt.title('Control Birth Year Histogram')
plt.grid()
plt.bar(x = binMiddleYears,height = list(hist))
mean = np.mean(birthYears)
median = np.median(birthYears)
std = np.std(birthYears)

# Case:
birthDates = dfCaseDemo['dob']
birthYears = [int(birthDate[6:]) for birthDate in birthDates ]
years = np.arange(1900,1971)+.5
binMiddleYears = np.arange(1901,1971)
hist,_ = np.histogram(birthYears,bins = years)
plt.figure()
plt.title('Case Birth Year Histogram')
plt.grid()
plt.bar(x = binMiddleYears,height = list(hist))
mean = np.mean(birthYears)
median = np.median(birthYears)
std = np.std(birthYears)

# Death Dates
# Control:
deathhDates = dfControlDemo['dod']
deathYears = [int(deathhDate[6:]) for deathhDate in deathhDates[~(isNaN(deathhDates))] ]
startYear = np.min(deathYears) - 1
endYear = np.max(deathYears) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(deathYears,bins = years)
plt.figure()
plt.title('Control Death Year Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,2)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))
aliveNum = np.sum((isNaN(deathhDates)))
deadNum = np.sum(~(isNaN(deathhDates)))
TotalDeadAlive = aliveNum + deadNum
mean = np.mean(deathYears)
median = np.median(deathYears)
std = np.std(deathYears)

# Case:
deathhDates = dfCaseDemo['dod']
deathYears = [int(deathhDate[6:]) for deathhDate in deathhDates[~(isNaN(deathhDates))] ]
startYear = np.min(deathYears) - 1
endYear = np.max(deathYears) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(deathYears,bins = years)
plt.figure()
plt.title('Case Death Year Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,2)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))
aliveNum = np.sum((isNaN(deathhDates)))
deadNum = np.sum(~(isNaN(deathhDates)))
TotalDeadAlive = aliveNum + deadNum
mean = np.mean(deathYears)
median = np.median(deathYears)
std = np.std(deathYears)


# Death Years - Birth Years:

# Control: 
deathhDates = dfControlDemo['dod']
ind = ~(isNaN(deathhDates))
deathYears = [int(deathhDate[6:]) for deathhDate in deathhDates[ind] ]
birthDates = dfControlDemo['dob']
birthYears = [int(birthDate[6:]) for birthDate in birthDates[ind] ]
deltas = np.array(deathYears) - np.array(birthYears)
startYear = np.min(deltas) - 1
endYear = np.max(deltas) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(deltas,bins = years)
plt.figure()
plt.title('Control Death Age Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,5)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))
mean = np.mean(deltas)
median = np.median(deltas)
std = np.std(deltas)

# Case: 
deathhDates = dfCaseDemo['dod']
ind = ~(isNaN(deathhDates))
deathYears = [int(deathhDate[6:]) for deathhDate in deathhDates[ind] ]
birthDates = dfCaseDemo['dob']
birthYears = [int(birthDate[6:]) for birthDate in birthDates[ind] ]
deltas = np.array(deathYears) - np.array(birthYears)
startYear = np.min(deltas) - 1
endYear = np.max(deltas) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(deltas,bins = years)
plt.figure()
plt.title('Case Death Age Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,5)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))
mean = np.mean(deltas)
median = np.median(deltas)
std = np.std(deltas)


# death of date - Dx date
dfCaseDemoDead =  dfCaseDemo[dfCaseDemo['dod']  ==  dfCaseDemo['dod']]
dfCaseDemoDead['death_after_index'] =  dfCaseDemoDead.apply(lambda row: int((datetime.strptime(str(row.dod), '%m/%d/%Y') - datetime.strptime(str(row.index_date), '%m/%d/%Y')).days) ,axis = 1)
dfControlDemoDead =  dfControlDemo[dfControlDemo['dod']  ==  dfControlDemo['dod']]
dfControlDemoDead['death_after_index'] =  dfControlDemoDead.apply(lambda row: int((datetime.strptime(str(row.dod), '%m/%d/%Y') - datetime.strptime(str(row.index_date), '%m/%d/%Y')).days) ,axis = 1)

bins = np.arange(0,3650,30)
binEdges  = np.append(bins - 0.5,bins[-1] + 0.5)
histCase,bins = np.histogram(dfCaseDemoDead['death_after_index'],bins = binEdges )
histControl,bins = np.histogram(dfControlDemoDead['death_after_index'],bins = binEdges )

dfComb  = pd.concat([pd.Series(histCase/histCase.sum()) , pd.Series(histControl/histControl.sum())], axis = 1)
dfComb.columns = ['Case','Control']
dfComb.index = np.arange(0,3650,30)
dfComb.plot( y = ['Case','Control'])
plt.title('Distribution of Death - DxDate')
plt.grid()
plt.xlabel('Days')

# Age:
def valuesDistribution(df,field):
    values = df[field]
    binEdges = np.arange(19.5, 120.5)
    hist, binEdges = np.histogram(values,bins = binEdges,normed = 1)
    return hist, binEdges


histCase, binEdgesCase = valuesDistribution(dfCaseDemo,'age')
binsCase = (binEdgesCase[0:-1] + binEdgesCase[1:])/2
histControl, binEdgesControl = valuesDistribution(dfControlDemo,'age')
binsControl = (binEdgesControl[0:-1] + binEdgesControl[1:])/2
plt.figure()
plt.plot(binsCase,histCase)
plt.plot(binsControl,histControl)
plt.xlabel('Age [years]')
plt.ylabel('pdf')
plt.title('Cases Vs. Controls Age')
plt.legend(['Cases','Controls'])
plt.grid()
tt = dfCaseDemo.age.describe()
tt = dfControlDemo.age.describe()

####
# d - Race Distribution analysis
####

#control:
race = dfControlDemo['race']
count = Counter(race)
countDict = dict(count)
relCountDict = dict()
total = np.sum(list(count.values()))
for key in countDict:
    relCountDict[key] = round(countDict[key]/ total*100,1)

labels = list(countDict.keys()) 
sizes = list(countDict.values())
colors = ['gold', 'yellowgreen', 'lightcoral', 'lightskyblue','mediumpurple']

# Plot
plt.figure()
plt.axis('equal')
plt.pie(sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', shadow=True, startangle=140)

# case:
race = dfCaseDemo['race']
count = Counter(race)
countDict = dict(count)
relCountDict = dict()
total = np.sum(list(count.values()))
for key in countDict:
    relCountDict[key] = round(countDict[key]/ total*100,1)

#labels = list(countDict.keys()) 

sizes = [countDict[label] for label in labels]
#colors = [colorsDict[label] for label in labels]
# Plot
plt.figure()
plt.axis('equal')
plt.pie(sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', shadow=True, startangle=140)




##############################################################

# Check that all patients appear in the demo file:
controlList = ['controls_cbc.txt','controls_dx1.txt','controls_dx2.txt','controls_dx3.txt','controls_hosp.txt','controls_lab1.txt','controls_lab2.txt','controls_lab3']

dfContorlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
ids = dfContorlCbc.id.unique()
cnt = 0
for id in ids:
    if int(id) in idsSet:
        cnt+=1
    else:
        print('error ' + id)
        
        
        
        

