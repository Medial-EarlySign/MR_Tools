# -*- coding: utf-8 -*-
"""
Created on Wed Sep 26 12:49:46 2018

@author: Ron
"""
import pandas as pd
import matplotlib.pylab as plt


sourceDir = r'D:\Databases\kpsc'
fileControlCbc =  r'\15-07-2018\controls_cbc.txt'
fileCaseCbc = r'\15-07-2018\cases_cbc.txt'
dfControlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseCbc =  pd.read_csv(sourceDir + fileCaseCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 


dfControlCbc['value3'] = dfControlCbc['value2'].apply(float)
ttt=  dfControlCbc[dfControlCbc['component2'] == 'EOSINOPHILS']
ddd = dfCaseCbc[dfCaseCbc['component2'] == 'EOSINOPHILS']

ttt['value3'].describe()
tttt = ttt[ttt['rrange'] != '0-10%']
tttt['order_date']
tttt.describe()
ttttt = ttt[ttt['rrange'] == '0-10%']
ttttt.describe()
tttttt = ttt[ttt['rrange'] == '0-10']
tttttt.describe()


ddddd = ddd[(ddd['rrange'] == '0-10%') | (ddd['rrange'] == '0-10') ]

plt.figure()
plt.hist( list(tttt['value3']),bins = 100)
# compate dist.
plt.figure()
tt = plt.hist( list(dfControlCbc[dfControlCbc['component2'] == 'EOSINOPHILS %']['value3']),bins = 100, normed = True)
x = tt[1]
y= tt[0]
xx = (x[1:] + x[0:-1])/2
plt.hist( list(ttttt['value3']),bins = xx,normed = True)

ttt=  dfControlCbc[dfControlCbc['component2'] == 'BASOPHILS']
ddd = dfCaseCbc[dfCaseCbc['component2'] == 'BASOPHILS']
ttt['value3'] = ttt['value2'].apply(float)
ttt['value3'].describe()
plt.figure()
plt.hist( list(ttt['value3']),bins = 100)
ttt.rrange.unique()

ttt[ttt.rrange == '0-1%']['value3'].describe()
ttt[ttt.rrange == '0-1']['value3'].describe()
ttt[ttt.rrange != '0-1%']['value3'].describe()

ttttt = ttt[(ttt['rrange'] == '0-1%') | (ttt['rrange'] == '0-1')]
ddddd= ddd[(ddd['rrange'] == '0-1%')  | (ddd['rrange'] == '0-1')]
# compate dist.
plt.figure()
tt = plt.hist( list(dfControlCbc[dfControlCbc['component2'] == 'BASOPHILS %']['value3']),bins = 1000, normed = True)
x = tt[1]
y= tt[0]
xx = (x[1:] + x[0:-1])/2
plt.hist( list(ttttt['value3']),bins = xx,normed = True)


# "Monocytes#",Neutrophils,Lymphocytes
#ttt=  dfControlCbc[dfControlCbc['component2'] == 'LYMPHOCYTES']
#ttt=  dfControlCbc[dfControlCbc['component2'] == 'MONOCYTES']
ttt=  dfControlCbc[dfControlCbc['component2'] == 'NEUTROPHILS']
ttt['value3'] = ttt['value2'].apply(float)
ttt['value3'].describe()
ttt.rrange.unique()
plt.figure()
plt.hist( list(ttt['value3']),bins = 100)
ttt.rrange.unique()


# FIX!
# receives COMPONENT + RRANGE and generates new CMPONENT2
t = dfControlCbc.copy()
correctMap = dict()
correctMap['component2=EOSINOPHILS','rrange=0-10%']  = 'EOSINOPHILS %'
correctMap['component2=BASOPHILS','rrange=0-1%']  = 'BASOPHILS %'

correction = list(correctMap.items())[0]
for correction in correctMap.items():
    ind = [True] * len(dfControlCbc)
    for element in correction[0]:
        colname = element.split('=')[0]
        value =element.split('=')[1]
        ind = ind & (t[colname] == value)
    
    print(t[ind].head()) 
    print('changed component2 to ' + correction[1])
    t.loc[ind,'component2'] = correction[1]
    
    
 
    
    

