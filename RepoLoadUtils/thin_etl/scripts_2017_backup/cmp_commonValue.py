#!/bin/python
import os

def getLines(basePath, fileName):
    fileP = os.path.join(basePath, fileName)
    fp = open(fileP, 'r')
    lines = fp.readlines()
    lines = filter(lambda x: len(x.strip()) > 0 ,lines)
    fp.close()
    return lines

bs = '/server/Temp/Thin_2017_Loading/outputs'
check_col = 1 # or 2
filter_cnt = 0
shrink_th = 0

lines = getLines(bs, 'CommonValues_old')
oldD = dict()
for l in lines:
    tokens = l.split('\t')
    oldD[tokens[0]] = int(tokens[2])
lines = getLines(bs, 'CommonValues_new')
newD = dict()
for l in lines:
    tokens = l.split('\t')
    newD[tokens[0]] = int(tokens[2])

for k,cnt in oldD.items():
    if cnt <= 0:
        continue
    if newD.get(k) is None:
        print('MISSING %s\t%d\tvalues in old repository'%(k, cnt))
        continue
    cnt_new = newD[k]
    if cnt_new < cnt - shrink_th:
        print('SHRINK %s\t%d\tvalues in old repository\t%d\tin new repository. shrinked by \t%d'%(k, cnt, cnt_new, cnt-cnt_new))
        