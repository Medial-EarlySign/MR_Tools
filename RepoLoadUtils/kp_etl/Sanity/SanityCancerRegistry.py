# -*- coding: utf-8 -*-
"""
Created on Tue Apr  3 10:33:26 2018

@author: Ron
"""

import pandas as pd
import numpy as np
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import copyFig

fileControlDemo = r'\controls_demo.txt'

fileCaseTumor =  r'\cases_tumor.txt'
fileCaseDemo = r'\cases_demo.txt'

sourceDir = r'D:\Databases\kpsc'
dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 

dfCaseTumor =  pd.read_csv(sourceDir + fileCaseTumor, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 


####
# distribution of Cancer per Year
####

# Case:
cancerDates = dfCaseTumor['index_date']
cancerYear = [int(cancerDate[6:]) for cancerDate in cancerDates] 
bins = np.arange(np.min(cancerYear),np.max(cancerYear) +1 )
binEdges = np.unique(np.sort(list(bins-0.5) + list(bins+0.5)))
hist,_ = np.histogram(cancerYear,bins = binEdges)
histCases = hist
plt.figure()
plt.title('Cases index date per year')
plt.grid()
xticks = bins
plt.xticks(xticks)
plt.bar(x = bins,height = list(hist))

# control:
indexDates = dfControlDemo['index_date']
indexYear = [int(indexDate[6:]) for indexDate in indexDates] 
bins = np.arange(np.min(cancerYear),np.max(cancerYear) +1 )
binEdges = np.unique(np.sort(list(bins-0.5) + list(bins+0.5)))
hist,_ = np.histogram(indexYear,bins = binEdges)
histControls = hist
plt.figure()
plt.title('Controls index date per year')
plt.grid()
xticks = bins
plt.xticks(xticks)
plt.bar(x = bins,height = list(hist))


#Comb
dfComb  = pd.concat([pd.Series(histCases/histCases.sum()) , pd.Series(histControls/histControls.sum())], axis = 1)
dfComb.columns = ['Case','Control']
plt.figure()
dfComb.plot(x = xticks, y = ['Case','Control'],kind = 'bar')
plt.title('Distribution of Number of Tests per Person')
plt.grid()

####
# distribution of Sequence Number
####

plt.figure()
seqNumCntr = dfCaseTumor['SEQUENCE_NUMBER'].value_counts()
seqNumCntrDict = dict(seqNumCntr)
seqNumCntrRel = dfCaseTumor['SEQUENCE_NUMBER'].value_counts()/np.sum(dfCaseTumor['SEQUENCE_NUMBER'].value_counts())
dfOut = pd.concat([seqNumCntr, seqNumCntrRel], axis=1).reset_index()

plt.figure()
plt.pie(list(seqNumCntrDict.values()), labels=list(seqNumCntrDict), 
        autopct='%1.1f%%', shadow=True, startangle=140)



####
# distribution of Site
####

plt.figure()
site_descCntr = dfCaseTumor['site_desc'].value_counts()
site_descCntrDict = dict(site_descCntr)
site_descCntrRel = dfCaseTumor['site_desc'].value_counts()/np.sum(dfCaseTumor['site_desc'].value_counts())
dfOut = pd.concat([site_descCntr, site_descCntrRel], axis=1).reset_index()

plt.figure()
plt.pie(list(site_descCntrDict.values()), labels=list(site_descCntrDict), 
        autopct='%1.1f%%', shadow=True, startangle=140)


####
# distribution of Stage
####

plt.figure()
stageCntr = dfCaseTumor['stage'].value_counts()
stageCntrDict = dict(stageCntr)
stageCntrRel = dfCaseTumor['stage'].value_counts()/np.sum(dfCaseTumor['stage'].value_counts())
dfOut = pd.concat([stageCntr, stageCntrRel], axis=1).reset_index()

plt.figure()
plt.pie(list(stageCntrDict.values()), labels=list(stageCntrDict), 
        autopct='%1.1f%%', shadow=True, startangle=140)

newOrder  = ['Stage 0','Stage OC','Stage I', 'Stage IA','Stage IB','Stage II','Stage IIA','Stage IIB','Stage III','Stage IIIA','Stage IIIB','Stage IIIC','Stage IV','Stage Unknown','Not Applicable']
dfOut = dfOut.set_index('index')

dfOut = dfOut.reindex(newOrder)
####
# Tumor size
####
tumorSize = dfCaseTumor['TUMOR_SIZE']
relInd = (tumorSize != '999')
np.sum(tumorSize == '999')
np.sum(tumorSize == '999')/len(relInd)
tumorSizeCleaned = tumorSize[relInd].apply(int)


tumorSizeCleaned2 = tumorSizeCleaned[tumorSizeCleaned<200]
plt.figure()
y,binEdges=np.histogram(tumorSizeCleaned2,bins=50)
bincenters = 0.5*(binEdges[1:]+binEdges[:-1])
plt.plot(bincenters,y,'-')
plt.show()


plt.figure()
plt.hist(tumorSizeCleaned,100,normed = True)


#plt.figure()
#plt.hist(tumorSizeCleaned,100,density = True)
#
#

from scipy.stats.kde import gaussian_kde
from numpy import linspace
# create fake data
data = tumorSizeCleaned2
# this create the kernel, given an array it will estimate the probability over that values
kde = gaussian_kde( data )
# these are the values over wich your kernel will be evaluated
dist_space = linspace( min(data), max(data), 100 )
# plot the results
plt.plot( dist_space, kde(dist_space) ,color = 'r')
plt.grid()
plt.title('Tumor size PDF')
plt.xlabel('Tumor Size [mm]')




#ttt = dfCaseTumor['SEQUENCE_NUMBER'].value_counts().plot(kind='pie',autopct='%1.1f%%', shadow=False, startangle=0)


