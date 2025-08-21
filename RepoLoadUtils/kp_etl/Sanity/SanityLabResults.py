# -*- coding: utf-8 -*-
"""
Created on Sun Mar 25 16:22:00 2018

@author: Ron
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import copyFig

fileControlCbc =  r'\03-05-2018\controls_cbc.txt'
fileControlDemo = r'\controls_demo.txt'
fileControlLabList = [r'\controls_lab1.txt',r'\controls_lab2.txt',r'\controls_lab3.txt']

fileCaseCbc =  r'\03-05-2018\cases_cbc.txt'
fileCaseDemo = r'\cases_demo.txt'
fileCaseLab = r'\cases_lab.txt'

sourceDir = r'D:\Databases\kpsc'
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 

dfControlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseCbc =  pd.read_csv(sourceDir + fileCaseCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 

dfControlLabList = []
for fileControlLab in fileControlLabList:
    dfControlLabList.append(pd.read_csv(sourceDir + fileControlLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
    
dfControlLab = pd.concat(dfControlLabList)    
dfCaseLab =  pd.read_csv(sourceDir + fileCaseLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 


def isNaN(num):
    return num != num



#####################################################################################################
# 0. Panel Size
#####################################################################################################

# Number of panels tests per patient:

# Control:
gbId = dfControlCbc.groupby(['id']) 
uniqueTestsPerId = gbId.ORDER_PROC_ID.unique()
tt = uniqueTestsPerId.apply(len)
controlsStats = tt.describe()
numTestsPerId = [len(tests) for tests in uniqueTestsPerId]
numTestsPerIdControls = numTestsPerId
#numTestsBins = np.arange(np.max(numTestsPerId) + 3)
numTestsBins = np.arange(0,20)
numTestsBins = np.append(numTestsBins,np.max(numTestsPerId)+10)

numTestsBinsEdges = numTestsBins - .5
hist,_ = np.histogram(numTestsPerId,bins = numTestsBinsEdges)
histControls = hist
plt.figure()
plt.title('Control # of Panels per ID')
plt.grid()
xticks = [str(x) for x in numTestsBins[0:-2]] + ['> ' + str(numTestsBins[-3])]

plt.xticks(numTestsBins[0:-1],xticks)
plt.bar(x = numTestsBins[0:-1],height = list(hist))
np.sum(hist)
np.mean(numTestsPerId)

# Case:
gbId = dfCaseCbc.groupby(['id']) 
uniqueTestsPerId = gbId.ORDER_PROC_ID.unique()
tt = uniqueTestsPerId.apply(len)
casesStats = tt.describe()
numTestsPerId = [len(tests) for tests in uniqueTestsPerId]
numTestsPerIdCases= numTestsPerId
numTestsBins = np.arange(0,20)
numTestsBins = np.append(numTestsBins,np.max(numTestsPerId)+10)

numTestsBinsEdges = numTestsBins - .5
hist,_ = np.histogram(numTestsPerId,bins = numTestsBinsEdges)
histCases = hist
plt.figure()
plt.title('Case # of Panels per ID')
plt.grid()
xticks = [str(x) for x in numTestsBins[0:-2]] + ['> ' + str(numTestsBins[-3])]

plt.xticks(numTestsBins[0:-1],xticks)
plt.bar(x = numTestsBins[0:-1],height = list(hist))
np.sum(hist)
np.mean(numTestsPerId)

## Combine
result = pd.DataFrame({'NumTests': xticks,'Cases': histCases/histCases.sum(),'Controls':histControls/histControls.sum()})

plt.figure()
plt.xticks(rotation=45)
result.plot(x = 'NumTests', y = ['Cases','Controls'],kind = 'bar')
plt.title('Number Of Panels Per Patient')
plt.legend(['Cases','Controls'])
plt.grid()


##########################################################################################
# Number of panels per year
##########################################################################################

# Control:
gbOrderId = dfControlCbc.groupby(['ORDER_PROC_ID']) 
testsDates = gbOrderId.order_date.head(1)
testYearsControls = pd.DataFrame(testsDates)
testYearsControls['year'] = testYearsControls.apply(lambda row: int(row.order_date[6:]), axis = 1)
testYearsControls = pd.DataFrame(testYearsControls.groupby('year').size())
testYearsControls['rel'] =testYearsControls/testYearsControls.sum() 

testYears = [int(testsDate[6:]) for testsDate in testsDates]
testYearsControls = testYears
startYear = np.min(testYears) - 1
endYear = np.max(testYears) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(testYears,bins = years)
histControls = hist
plt.figure()
plt.title('Control CBC Panels per Year Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,2)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))


# Case:
gbOrderId = dfCaseCbc.groupby(['ORDER_PROC_ID']) 
testsDates = gbOrderId.order_date.head(1)
testYearsCases = pd.DataFrame(testsDates)
testYearsCases['year'] = testYearsCases.apply(lambda row: int(row.order_date[6:]), axis = 1)
testYearsCases = pd.DataFrame(testYearsCases.groupby('year').size())
testYearsCases['rel'] =testYearsCases/testYearsCases.sum() 
testYears = [int(testsDate[6:]) for testsDate in testsDates]

startYear = np.min(testYears) - 1
endYear = np.max(testYears) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(testYears,bins = years)
histCases = hist
plt.figure()
plt.title('Case CBC Panels per Year Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,2)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))

## Combine
result = pd.DataFrame({'Year': binMiddleYears,'Cases': histCases/histCases.sum(),'Controls':histControls/histControls.sum()})

plt.figure()
plt.xticks(rotation=45)
result.plot(x = 'Year', y = ['Cases','Controls'],kind = 'bar')
plt.title('Number Of Panels Per Year')
plt.legend(['Cases','Controls'])
plt.grid()




#####
# Panel Size Distribution
#####

# Control:
gbOrderId = dfControlCbc.groupby(['ORDER_PROC_ID']) 
testSizesControl = gbOrderId.size()
dfTestSizesControl = pd.DataFrame(testSizesControl)
testSizes = list(testSizesControl)
minSize = np.min(testSizes) - 2
maxSize = np.max(testSizes) + 2
sizes = np.arange(minSize,maxSize)+.5
binMiddleSizes = np.arange(minSize + 1,maxSize)
hist,_ = np.histogram(testSizes,bins = sizes)
histControl = hist
plt.figure()
plt.title('Control CBC Panels Sizes Histogram')
plt.grid()
xticks = np.arange(minSize + 1,maxSize,1)
plt.xticks(xticks)
plt.bar(x = binMiddleSizes,height = list(hist))

# Case:
gbOrderId = dfCaseCbc.groupby(['ORDER_PROC_ID']) 
testSizesCase = gbOrderId.size()
dfTestSizesCase = pd.DataFrame(testSizesCase)
testSizes = list(testSizesCase)
minSize = np.min(testSizes) - 2
maxSize = np.max(testSizes) + 2
sizes = np.arange(minSize,maxSize)+.5
binMiddleSizes = np.arange(minSize + 1,maxSize)
hist,_ = np.histogram(testSizes,bins = sizes)
histCase = hist
plt.figure()
plt.title('Case CBC Panels Sizes Histogram')
plt.grid()
xticks = np.arange(minSize + 1,maxSize,1)
plt.xticks(xticks)
plt.bar(x = binMiddleSizes,height = list(hist))

## Combine
result = pd.DataFrame({'NumTests': binMiddleSizes,'Cases': histCase/histCase.sum(),'Controls':histControl/histControl.sum()})

plt.figure()
result.plot(x = 'NumTests', y = ['Cases','Controls'],kind = 'bar')
plt.title('Number Of Tests Per Panel')
plt.legend(['Cases','Controls'])
plt.grid()
tt = dfTestSizesCase.describe()
ttt = dfTestSizesControl.describe()

######
# Control - Check that each subject has at lest 1 CBC at age 45:
######
gbId = dfControlCbc.groupby(['id']) 
uniqueTestsPerId = gbId.order_date.unique()
numUniqueTestsPerId = uniqueTestsPerId.apply(len)
tt = pd.DataFrame(uniqueTestsPerId)
tt['NumTests'] = tt.apply(len)

numTesrPerId = dict()
for index, row in dfControlDemo.iterrows():    
    pid = str(row['id'])
    bdate = row['dob']
    byear = int(bdate[6:])
    testDates = uniqueTestsPerId[pid]
    numTesrPerId[pid] = 0
    for testDate in testDates:
        ageAtTest = int(testDate[6:]) - byear
        if ageAtTest >= 45:
            numTesrPerId[pid] += 1

numTesrPerIdList = list(numTesrPerId.values())
minNum = 0
maxNum = np.max(numTesrPerIdList) + 2
nums = np.arange(minNum,maxNum)-.5
binMiddleNums = nums[0:-1] + .5
hist,_ = np.histogram(numTesrPerIdList,bins = nums)
plt.figure()
plt.title('Num CBC Panels in age >= 45 Histogram')
plt.grid()
xticks = np.arange(minNum + 1,maxNum,2)
plt.xticks(xticks)
plt.bar(x = binMiddleNums,height = list(hist/hist.sum()))

patientsWithoutTests = [k for k, v in numTesrPerId.items() if v == 0]
len(patientsWithoutTests)
np.mean(numTesrPerIdList)

######
# Control - Check that each subject has at lest 1 CBC a year before indexing:
######
gbId = dfControlCbc.groupby(['id']) 
uniqueTestsPerId = gbId.ORDER_PROC_ID.unique()
gbIdProcId = dfControlCbc.groupby(['id','ORDER_PROC_ID']) 
numTestsPerId = dict()
numTestsPerIdInclude0 = dict()
daysTh = 365
CBC_TH = 9

for index, row in dfControlDemo.iterrows():    
    pid = str(row['id'])
    dxDate = row['index_date'] 
    reft = datetime.strptime(dxDate, "%m/%d/%Y")
    numTestsPerId[pid] = 0
    numTestsPerIdInclude0[pid] = 0
    for test in uniqueTestsPerId[pid]:
        testDate = gbIdProcId.get_group((pid,test)).iloc[0]['order_date']
        testSize = gbIdProcId.get_group((pid,test)).shape[0]
        testt = datetime.strptime(testDate, "%m/%d/%Y")
        diff = reft - testt
        if (diff.days > 0 ) and (diff.days < daysTh) and (testSize >= CBC_TH):
            numTestsPerId[pid] += 1
        if (diff.days >= 0 ) and (diff.days <= daysTh) and (testSize >= CBC_TH):
           numTestsPerIdInclude0[pid] += 1
            
patientsWithoutTests = [k for k, v in numTestsPerId.items() if v == 0]         
len(patientsWithoutTests)  
patientsWithoutTests0 = [k for k, v in numTestsPerIdInclude0.items() if v == 0]         
len(patientsWithoutTests0)  

numTestsPerIdList = list(numTestsPerId.values())
minNum = 0
maxNum = np.max(numTestsPerIdList) + 2
nums = np.arange(minNum,maxNum)-.5
binMiddleNums = nums[0:-1] + .5
hist,_ = np.histogram(numTestsPerIdList,bins = nums)
plt.figure()
plt.title('Case - Num CBC Panels Within 1 year before diagnosis')
plt.grid()
xticks = np.arange(minNum + 1,maxNum,2)
plt.xticks(xticks)
plt.bar(x = binMiddleNums,height = list(hist))

patientsWithoutTests = [k for k, v in numTestsPerId.items() if v == 0]
len(patientsWithoutTests)
np.mean(numTestsPerIdList)
                


########
# Cases: Check that each subjects has at least 1 CBC within 12 months prior to lung cancer diag:
########
gbIdProcId = dfCaseCbc.groupby(['id','ORDER_PROC_ID']) 
gbId = dfCaseCbc.groupby(['id']) 
uniqueTestsPerId = gbId.ORDER_PROC_ID.unique()

CBC_TH = 9 # Threshold for taking CBC into account 
daysTh = 365

numTestsPerId = dict()
for index, row in dfCaseDemo.iterrows():
    pid = str(row['id'])
    dxDate = row['index_date'] 
    reft = datetime.strptime(dxDate, "%m/%d/%Y")
    numTestsPerId[pid] = 0
    for test in uniqueTestsPerId[pid]:
        testDate = gbIdProcId.get_group((pid,test)).iloc[0]['order_date']
        testSize = gbIdProcId.get_group((pid,test)).shape[0]
        testt = datetime.strptime(testDate, "%m/%d/%Y")
        diff = reft - testt
        if (diff.days > 0 ) and (diff.days < daysTh) and (testSize >= CBC_TH) :
            numTestsPerId[pid] += 1
            
patientsWithoutTests = [k for k, v in numTestsPerId.items() if v == 0]         
len(patientsWithoutTests)  

numTestsPerIdList = list(numTestsPerId.values())
minNum = 0
maxNum = np.max(numTestsPerIdList) + 2
nums = np.arange(minNum,maxNum)-.5
binMiddleNums = nums[0:-1] + .5
hist,_ = np.histogram(numTestsPerIdList,bins = nums)
plt.figure()
plt.title('Case - Num CBC Panels Within 1 year before diagnosis')
plt.grid()
xticks = np.arange(minNum + 1,maxNum,2)
plt.xticks(xticks)
plt.bar(x = binMiddleNums,height = list(hist))

patientsWithoutTests = [k for k, v in numTestsPerId.items() if v == 0]
len(patientsWithoutTests)
np.mean(numTestsPerIdList)
       
########
# Cases: Check that each subjects has at least 1 CBC within 6/12/36 months prior to lung cancer diag:
########
gbIdProcId = dfCaseCbc.groupby(['id','ORDER_PROC_ID']) 
gbId = dfCaseCbc.groupby(['id']) 
uniqueTestsPerId = gbId.ORDER_PROC_ID.unique()

CBC_TH = 9 # Threshold for taking CBC into account 
daysTh_6M = 182
daysTh_12M = 365
daysTh_36M = 1095

numTestsPerId_6M = dict()
numTestsPerId_12M = dict()
numTestsPerId_36M = dict()

for index, row in dfCaseDemo.iterrows():
    pid = str(row['id'])
    dxDate = row['index_date'] 
    reft = datetime.strptime(dxDate, "%m/%d/%Y")
    numTestsPerId_6M[pid] = 0
    numTestsPerId_12M[pid] = 0
    numTestsPerId_36M[pid] = 0
    for test in uniqueTestsPerId[pid]:
        testDate = gbIdProcId.get_group((pid,test)).iloc[0]['order_date']
        testSize = gbIdProcId.get_group((pid,test)).shape[0]
        testt = datetime.strptime(testDate, "%m/%d/%Y")
        diff = reft - testt
        if (diff.days > 0 ) and (diff.days < daysTh_6M) and (testSize >= CBC_TH) :
            numTestsPerId_6M[pid] += 1
        if (diff.days > 0 ) and (diff.days < daysTh_12M) and (testSize >= CBC_TH) :
            numTestsPerId_12M[pid] += 1
        if (diff.days > 0 ) and (diff.days < daysTh_36M) and (testSize >= CBC_TH) :
            numTestsPerId_36M[pid] += 1
            
patientsWithoutTests_6M = [k for k, v in numTestsPerId_6M.items() if v == 0]         
len(patientsWithoutTests_6M)  
patientsWithoutTests_12M = [k for k, v in numTestsPerId_12M.items() if v == 0]         
len(patientsWithoutTests_6M)  
patientsWithoutTests_36M = [k for k, v in numTestsPerId_36M.items() if v == 0]         
len(patientsWithoutTests_36M)  

numTestsPerIdList_6M = list(numTestsPerId_6M.values())
numTestsPerIdList_12M = list(numTestsPerId_12M.values())
numTestsPerIdList_36M = list(numTestsPerId_36M.values())

minNum = 0
maxNum = np.max(numTestsPerIdList_36M) + 2
binEdges = np.append(np.arange(-.5,9.5),maxNum)
binMiddleNums = binEdges[0:-1] + .5
hist_6M,_ = np.histogram(numTestsPerIdList_6M,bins = binEdges)
hist_12M,_ = np.histogram(numTestsPerIdList_12M,bins = binEdges)
hist_36M,_ = np.histogram(numTestsPerIdList_36M,bins = binEdges)

plt.figure()
plt.title('Case - Num CBC Panels Within 6/12/36 Months before diagnosis')
plt.grid()

w = 0.3
plt.bar(x = binMiddleNums-w,height = list(hist_6M),color = 'b',width = w,align = 'center',label = '6M')
plt.bar(x = binMiddleNums,height = list(hist_12M),color = 'g',width = w,align = 'center',label = '12M')
plt.bar(x = binMiddleNums+w,height = list(hist_36M),color = 'r',width = w,align = 'center',label = '36M')
xticks = [str(int(num)) for num in binMiddleNums[0:-1] ] + ['>' + str(int(binMiddleNums[-2]))]
plt.xticks( binMiddleNums,xticks)
plt.legend()
plt.xlabel('Test #')
plt.ylabel('# Patients')
patientsWithoutTests_6M = [k for k, v in numTestsPerId_6M.items() if v == 0]
patientsWithoutTests_12M = [k for k, v in numTestsPerId_12M.items() if v == 0]
patientsWithoutTests_36M = [k for k, v in numTestsPerId_36M.items() if v == 0]
len(patientsWithoutTests_6M)
np.mean(numTestsPerIdList_6M)
len(patientsWithoutTests_12M)
np.mean(numTestsPerIdList_12M)
len(patientsWithoutTests_36M)
np.mean(numTestsPerIdList_36M)

########
# Check For Missing Values value vs value2
########
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
          
# Case CBC + Lab: Check value2 vs value1
deltaCaseCbc = np.array([float(x) for x in dfCaseCbc['value']]) - np.array([float(x) for x in dfCaseCbc['value2']])
np.sum(delta)

isNumInd =  [is_number(x)  for x in dfCaseLab['value']]
notIsNumInd = [not i for i in isNumInd]
dfTemp = dfCaseLab[isNumInd]
deltaCaseLab = np.array([float(x) for x in dfTemp['value']]) - np.array([float(x) for x in dfTemp['value2']])
np.sum(deltaCaseLab)
dfTemp = dfCaseLab[notIsNumInd]


# Control CBC + Lab: Check value2 vs value1

    
isNumInd =  [is_number(x)  for x in dfControlCbc['value']]
notIsNumInd = [not i for i in isNumInd]
dfTemp = dfControlCbc[isNumInd]
deltaControlCbc = np.array([float(x) for x in dfTemp['value']]) - np.array([float(x) for x in dfTemp['value2']])
np.sum(deltaControlCbc)
dfTemp = dfControlCbc[notIsNumInd]

########
# Blood Tests distribution
########

# Case : 
gdOPI = dfCaseCbc.groupby(['ORDER_PROC_ID']) 
refYears = {2009,2012,2015}
set(gdOPI.get_group('212134728585')['component'])
totalCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
HgbCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
tenCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
elevenCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
twelveCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
testOfInter = {'HGB','MCH','HCT, AUTO','MCV',"WBC'S AUTO",'PLATELETS, AUTOMATED COUNT'}
panelsSets = dict({2009 : set(), 2012 : set(), 2015 : set()})
badTest = []

for group in gdOPI:
        testDate = group[1]['order_date'].iloc[0]
        testYear = int(testDate[6:])
        if testYear in refYears:
            totalCounter[testYear] += 1
            testsSet = set(group[1]['component'])
            if testOfInter.issubset(testsSet):
                HgbCounter[testYear] += 1
            else:
                panelsSets[testYear].add(group[1]['ORDER_PROC_ID'].iloc[0])
            if len(testsSet) >= 10:
                tenCounter[testYear] += 1
                if len(testsSet) >= 11:
                    elevenCounter[testYear] += 1
                    if len(testsSet) >= 12:
                        twelveCounter[testYear] += 1
            else:
                badTest.append(group[0])

twelveCounterRel = dict()
elevenCounterRel = dict()
HgbCounterRel = dict()
tenCounterRel = dict()
for year in totalCounter:
    HgbCounterRel[year] = HgbCounter[year]/totalCounter[year]
    elevenCounterRel[year] = elevenCounter[year]/totalCounter[year]
    twelveCounterRel[year] = twelveCounter[year]/totalCounter[year]
    tenCounterRel[year] = tenCounter[year]/totalCounter[year]

# Control: 
gdOPI = dfControlCbc.groupby(['ORDER_PROC_ID']) 
refYears = {2009,2012,2015}
totalCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
HgbCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
tenCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
elevenCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})
twelveCounter = dict({2009 : 0, 2012 : 0, 2015 : 0})

panelsSets = dict({2009 : set(), 2012 : set(), 2015 : set()})
testOfInter = {'HGB','MCH','HCT, AUTO','MCV',"WBC'S AUTO",'PLATELETS, AUTOMATED COUNT'}
badTest = []

for group in gdOPI:
        testDate = group[1]['order_date'].iloc[0]
        testYear = int(testDate[6:])
        if testYear in refYears:
            totalCounter[testYear] += 1
            testsSet = set(group[1]['component'])
            if testOfInter.issubset(testsSet):
                HgbCounter[testYear] += 1
            else:
                panelsSets[testYear].add(group[1]['ORDER_PROC_ID'].iloc[0])
            if len(testsSet) >= 10:
                tenCounter[testYear] += 1
                if len(testsSet) >= 11:
                    elevenCounter[testYear] += 1
                    if len(testsSet) >= 12:
                        twelveCounter[testYear] += 1
            else:
                badTest.append(group[0])

twelveCounterRel = dict()
elevenCounterRel = dict()
HgbCounterRel = dict()
tenCounterRel = dict()
for year in totalCounter:
    HgbCounterRel[year] = HgbCounter[year]/totalCounter[year]
    elevenCounterRel[year] = elevenCounter[year]/totalCounter[year]
    twelveCounterRel[year] = twelveCounter[year]/totalCounter[year]
    tenCounterRel[year] = tenCounter[year]/totalCounter[year]

#########
#
#########



#####
# CBC : Check that 5% fal within 3 sigma + Statistcis   
#####
def testsData(dfTest,caseControlType):
    #testTypes = dfCaseCbc.component.unique()
    testDict = dict()
    statsDict = dict()
    gbComp =  dfTest.groupby('component2')
    testYearsSet = {2013, 2014, 2015}
    for group in gbComp:
        statsDict = dict()
        print(group[0])  
        values =  pd.to_numeric(group[1]['value2'])
        dates = group[1]['order_date']
        statsDict['Avg'] = np.mean(values)
        statsDict['Std'] = np.std(values)
        statsDict['Min'] = np.min(values)
        statsDict['Max'] = np.max(values)
        total = len(values)
        statsDict['Total #'] = total
        outCntr = 0
        lowTh = statsDict['Avg'] - 3 *statsDict['Std'] 
        highTh = statsDict['Avg'] + 3 *statsDict['Std'] 
        for value in values: 
            if (value < lowTh) or(value > highTh):
                outCntr += 1 
    
        statsDict['yearsTaken'] =  [int(date[6:]) for date in dates if int(date[6:]) in testYearsSet]  
        tt = [date.split("/") for date in dates] 
        statsDict['maxDate'] = dates.iloc[np.argmax([int(ttt[2]+ttt[0] + ttt[1]) for ttt in tt])] 
        statsDict['Out'] = outCntr/total
        testDict[group[0]] = statsDict
     
    testList = [testDict[t] for t in testDict]
    testNamesList = [t for t in testDict]
    sStats = pd.Series(testNamesList)
    dfStats = pd.concat([sStats, pd.DataFrame(testList)], axis=1)
    
    # Plot Tests Histograms
    dataList = []
    listXticks = []
    for key in testDict:
        dataList.append(testDict[key]['yearsTaken'])
        listXticks.append(key)
    
    binsEdges =  np.sort(list(np.array(list(testYearsSet)) - 0.5) + list(np.array(list(testYearsSet)) + 0.5))
    histData = plt.hist(dataList, bins = binsEdges, histtype='bar')  
    histDataInt = [data[::2] for data in histData[0] ]
    
    #df = pd.DataFrame(histDataInt, columns=pd.Index(['2009', '2012', '2015']), index = listXticks )
    #df.plot(kind='bar',figsize=(10,4))
    
    tt = np.array(histDataInt).transpose()
    df = pd.DataFrame(tt, columns=pd.Index( listXticks), index = [str(int(bn)) for bn in np.sort(list(testYearsSet))] )
    df.plot(kind='bar',width = 0.9,figsize=(10,10),legend=None)
    
    ax = plt.gca()
    pos = []
    for bar in ax.patches:
        pos.append(bar.get_x()+bar.get_width()/2.)
    
    ax.set_xticks(pos,minor=True)
    
    lab = []
    for i in range(len(pos)):
        l = df.columns.values[i//len(df.index.values)]
        lab.append(l)
    
    ax.set_xticklabels(lab,minor=True,rotation='vertical')
    #ax.tick_params(axis='x', which='major', pad=15, size=0)
    #plt.setp(ax.get_xticklabels(), rotation=0)
    yearsStr = ", ".join([str(int(bn)) for bn in np.sort(list(testYearsSet))])
    plt.title(caseControlType + 's - Number of Tests in years ' + yearsStr )
    plt.grid()
    plt.show()
    return dfStats


# Case:
dfTest = dfCaseCbc
caseControlType = 'Case'
dataStats = testsData(dfTest,caseControlType)
dataStats = dataStats.drop(['yearsTaken'],axis = 1)
tt = dfCaseDemo.copy()
tt['intIndexDate'] = tt.apply(lambda row : int(row.index_date[6:] + row.index_date[3:5] + row.index_date[0:2]),axis = 1)
tt['index_date'][np.argmax(tt['intIndexDate'])]

# Controls:
dfTest = dfControlCbc
caseControlType = 'Control'
dataStatsControl = testsData(dfTest,caseControlType)
dataStatsControl = dataStatsControl.drop(['yearsTaken'],axis = 1)
ttt = dfControlDemo.copy()
ttt['intIndexDate'] = ttt.apply(lambda row : int(row.index_date[6:] + row.index_date[3:5] + row.index_date[0:2]),axis = 1)
ttt['index_date'][np.argmax(ttt['intIndexDate'])]

# Lab
dfTest = dfCaseLab
caseControlType = 'Case'
dataStats = testsData(dfTest,caseControlType)
dataStats = dataStats.drop(['yearsTaken'],axis = 1)
tt = dfCaseDemo.copy()
tt['intIndexDate'] = tt.apply(lambda row : int(row.index_date[6:] + row.index_date[3:5] + row.index_date[0:2]),axis = 1)
tt['index_date'][np.argmax(tt['intIndexDate'])]

dfTest = dfControlLab
caseControlType = 'Control'
dataStats = testsData(dfTest,caseControlType)
dataStats = dataStats.drop(['yearsTaken'],axis = 1)
tt = dfCaseDemo.copy()
tt['intIndexDate'] = tt.apply(lambda row : int(row.index_date[6:] + row.index_date[3:5] + row.index_date[0:2]),axis = 1)
tt['index_date'][np.argmax(tt['intIndexDate'])]


#########################################

#####
# LAB : Check that 5% fal within 3 sigma + Statistcis   
#####
# Case:
dfTest = dfCaseLab
caseControlType = 'Case'
dataLabStats = testsData(dfTest,caseControlType)
dataLabStats = dataLabStats.drop(['yearsTaken'],axis = 1)

# Controls:
dfTest = dfControlLab
caseControlType = 'Control'
dataStatsLabControl = testsData(dfTest,caseControlType)
dataStatsLabControl = dataStatsLabControl.drop(['yearsTaken'],axis = 1)




#####
# LAB : Check that 5% fal within 3 sigma + Statistcis   
#####

# Case:
testTypes = dfCaseLab.component.unique()
testDict = dict()
statsDict = dict()
dfCaseLab['intDate'] = dfCaseLab.apply(lambda row : int(row.order_date[6:] + row.order_date[3:5] + row.order_date[0:2]),axis = 1)
gbComp =  dfCaseLab.groupby('component')
for group in gbComp:
    statsDict = dict()
    print(group[0])  
    values =  pd.to_numeric(group[1]['value2'])
    statsDict['Avg'] = np.mean(values)
    statsDict['Std'] = np.std(values)
    statsDict['Min'] = np.min(values)
    statsDict['Max'] = np.max(values)
    statsDict['Last'] = group[1]['order_date'][np.argmax(group[1]['intDate'] )]
    total = len(values)
    statsDict['Total #'] = total
    outCntr = 0
    lowTh = statsDict['Avg'] - 3 *statsDict['Std'] 
    highTh = statsDict['Avg'] + 3 *statsDict['Std'] 
    for value in values: 
        if (value < lowTh) or(value > highTh):
            outCntr += 1 
    statsDict['Out'] = outCntr/total
    testDict[group[0]] = statsDict
 
testList = [testDict[t] for t in testDict]
testNamesList = [t for t in testDict]
sStats = pd.Series(testNamesList)
dfStats = pd.concat([sStats, pd.DataFrame(testList)], axis=1)

# Control:
testTypes = dfControlLab.component.unique()
testDict = dict()
statsDict = dict()
gbComp =  dfControlLab.groupby('component')
for group in gbComp:
    statsDict = dict()
    print(group[0])  
    values =  pd.to_numeric(group[1]['value2'])
    statsDict['Avg'] = np.mean(values)
    statsDict['Std'] = np.std(values)
    statsDict['Min'] = np.min(values)
    statsDict['Max'] = np.max(values)
    total = len(values)
    statsDict['Total #'] = total
    outCntr = 0
    lowTh = statsDict['Avg'] - 3 *statsDict['Std'] 
    highTh = statsDict['Avg'] + 3 *statsDict['Std'] 
    for value in values: 
        if (value < lowTh) or(value > highTh):
            outCntr += 1 
    statsDict['Out'] = outCntr/total
    testDict[group[0]] = statsDict
 
testList = [testDict[t] for t in testNamesList]
sStats = pd.Series(testNamesList)
dfStats2 = pd.concat([sStats, pd.DataFrame(testList)], axis=1)


    
# Control:
#gbId = dfControlCbc.groupby(['id']) 
#uniqueTestsPerId = gbId.order_date.unique()
#uniqueTestsPerId[id == pid]



#####################################################################################################
#  DELETE ?? a. Distribution of the lab test panel dates - all results must be between 2003 - 2015             #
#####################################################################################################

# CBC control:
dfContorlCbc.columns   
testOrderDates = dfContorlCbc['order_date']
testYears = [int(testOrderDate[6:]) for testOrderDate in testOrderDates ]

startYear = np.min(testYears) - 1
endYear = np.max(testYears) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(testYears,bins = years)
plt.figure()
plt.title('Controls CBC tests per Year Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,2)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))

# CBC case:
dfContorlCbc.columns   
testOrderDates = dfCaseCbc['order_date']
testYears = [int(testOrderDate[6:]) for testOrderDate in testOrderDates ]

startYear = np.min(testYears) - 1
endYear = np.max(testYears) + 1
years = np.arange(startYear,endYear)+.5
binMiddleYears = np.arange(startYear + 1,endYear)
hist,_ = np.histogram(testYears,bins = years)
plt.figure()
plt.title('Case CBC tests per Year Histogram')
plt.grid()
xticks = np.arange(startYear + 1,endYear,2)
plt.xticks(xticks)
plt.bar(x = binMiddleYears,height = list(hist))

###########
# Units test
#########
tt = dfControlCbc.groupby('component').unit.unique()
dfTotal = pd.concat([dfControlCbc,dfCaseCbc])
tt = dfTotal.groupby('component').unit.unique()
ttt = dfTotal.groupby('component').unit.value_counts()

#############
# Check outpatient inpatient
#############
ttt = dfCaseCbc['component2']
tt = ttt.value_counts().sort_index()

ttt = dfControlCbc['component2']
tt = ttt.value_counts().sort_index()

gb = dfCaseCbc.groupby('component2')
dfCaseCbc['value2'] = dfCaseCbc['value2'].apply(float)
dfControlCbc['value2'] = dfControlCbc['value2'].apply(float)
print(dfCaseCbc.groupby('component2').describe().reset_index().pivot(index='component2', values='value2'))
print(dfCaseCbc.groupby('component2').describe()['value2'])


###
# Number of tests per year
####
tt = dfCaseCbc.groupby('component2').describe()['value2']
dfCaseCbc['year'] = dfCaseCbc.apply(lambda row: row.order_date[6:], axis = 1)
ttt = dfCaseCbc.groupby(['component2','year']).size()


tt = dfControlCbc.groupby('component2').describe()['value2']
dfControlCbc['year'] = dfControlCbc.apply(lambda row: row.order_date[6:], axis = 1)
ttt = dfControlCbc.groupby(['component2','year']).size()


###
# Number of tests per year (join % and #) # debug needed
####
dfControlCbc.component2.unique()

dfCaseCbc['testGroup'] = dfCaseCbc.apply(lambda row: row.component2.split()[0], axis = 1)
tt = dfCaseCbc.groupby(['ORDER_PROC_ID'], as_index = False)
tttt = tt.apply(lambda x: x.drop_duplicates(subset = 'testGroup' ,keep = 'first'))
tttttt = tttt.groupby(['testGroup','year']).size()