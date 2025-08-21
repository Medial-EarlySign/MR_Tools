# -*- coding: utf-8 -*-
"""
Created on Mon May 21 14:12:02 2018

@author: Ron
"""
import re
import numpy as np
from collections import Counter
import os.path


filesDir = 'D:/KP/'
fileIn = 'maccabi_completion_metadata'
fileOut = 'kp_completion_metadata'

def getRes(fullFileName):
    with open(fullFileName) as f:
            lines = f.readlines()
            
    values = []
    for line in lines:
        values.append(float(line.split('\t')[3]))
    
    values = np.array(values)
    sortedValues = np.sort(np.unique(values))
    
    cnt = Counter()
    for value in values:
        cnt[value] += 1
    
    diffCnt = Counter()
    for k in range(1,len(sortedValues)):
        currDiff = sortedValues[k] - sortedValues[k-1]
        diffCnt[currDiff] += (cnt[sortedValues[k] ] + cnt[sortedValues[k-1]])      
    
    print(str(diffCnt.most_common(4)))
    return diffCnt.most_common(1)[0][0]
            
# 
    
# run over metadata signals
with open(fileIn) as f:
    lines = f.readlines()

outStr = lines[0]

names = []
for line in lines[1:]:
    names.append((line.split(',')[0]))

for finalName in names:
    filename = re.sub('[^\w_#%]','',finalName) + '.txt'  
    fullFileName = filesDir + filename
    if os.path.isfile(fullFileName):
        resolution = getRes(fullFileName)
    
        outStr += finalName + ',1,' + str(resolution) + ',' + str(resolution) + '\n' 
        

with open(fileOut, "wb") as text_file:
    text_file.write(str.encode(outStr))
        