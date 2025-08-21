from common import *
from Configuration import Configuration
from signal_mapping_api import listAllTargets
from flow_api import *
from bin_selections import *
from datetime import datetime

def throwOutlyers(vec, min_th = 0.001, max_th = 0.999):
    s_vals = sorted(vec)
    min_val = s_vals[int(len(vec)* min_th)]
    max_val = s_vals[int((len(vec)-1)* max_th)]
    vec = list(map(lambda x: x if x >= min_val and x <= max_val else min_val if x< min_val else max_val ,vec))
    return vec

def getAllSignalStatus():
    signals = listAllTargets()
    signals = filter( lambda v: v != 'TBD' and v != 'NULL' ,map(lambda v: v[0],signals.items()))
    res = []
    cfg = Configuration()
    workDir = fixOS(cfg.work_path)
    if not(os.path.exists(workDir)):
        raise NameError('configuration error? can''t find work_dir')
    commonVals = os.path.join(workDir,'CommonValues')
    if not(os.path.exists(commonVals)):
        raise NameError('cant''t finc commonVal file')
    fp = open(commonVals, 'r')
    lines = fp.readlines()
    fp.close()
    sigCnt = dict()
    for line in lines:
        if len(line.strip()) == 0:
            continue
        tokens= line.split('\t')
        if len(tokens) != 3:
            raise NameError('Format Error in commonVals')
        sigKey = tokens[0].strip()
        cnt = int(tokens[1].strip())
        sigCnt[sigKey] = cnt
    return sigCnt

#sigCnt = getAllSignalStatus()
#print(len(sigCnt))
#for k, v in sigCnt.items():
#    print('%s %d'%(k,v))

def retInd(se, val):
    for i in range(len(se)):
        if se[i] == val:
            return i
    return -1

#createResolveFld('ahd.a6643')



#fp = '\\\\nas1\\Temp\\Ido\\ahd\\Common\\ESR_normal-42B6200_Erythrocyte_sedimentation_rate-1001400138'
#fp = '\\\\nas1\\Temp\\Ido\\ahd\\Common\\Erythrocyte_sedimentation_rate-42B6.00_Erythrocyte_sedimentation_rate-1001400138'
fp2 = '\\\\nas1\\Temp\\Ido\\ahd\\Common\\Electrolytes_normal-44I2.00_Sodium-1001400032'
fp = '\\\\nas1\\Temp\\Ido\\ahd\\Common\\Total_white_blood_count-42H7.00_White_blood_count-1001400056'

f= open(fp, 'r')
lines = f.readlines()
f.close()

lines = list(set(lines))
lines.sort()

data = list(map( lambda x : [float(x.split('\t')[2]), x.split('\t')[0].strip(), x.split('\t')[1].strip() ] ,lines))
#data = filter( lambda x: x[1] != 'null value' ,data)
vals  = list(map(lambda x : x[0] , data))
pids = list(map(lambda x : x[1] , data))
dates = list(map(lambda x : x[2] , data))
searchRange = 5


diffVec = []
for ind in range(len(vals)):
    pid = pids[ind]
    date = dates[ind]
    if date[-2:] == '00':
        continue
    closeVal = None
    for i in range(1,searchRange):
        indCandidate = ind + i
        if indCandidate <0 or indCandidate >= len(vals):
            continue
        if pids[indCandidate] != pid:
            continue
        dateC = dates[indCandidate]
        if dateC[-2:] == '00':
            continue
        datediff = (datetime.strptime(dateC, '%Y%m%d') -  datetime.strptime(date, '%Y%m%d')).total_seconds()  / 60/60/24
        if datediff > 10 or datediff < 0:
            continue
        
        if closeVal is None or abs(datediff) < abs(closeVal):
            closeVal = datediff
    diffVec.append(closeVal)

sDates= sorted(hist(list(map(lambda v : 1*int(v/1) if v is not None else None ,diffVec))).items(), key = lambda kv: kv[0] if kv[0] is not None else 1000)
for diffD, cnt in sDates:
    print('diffDate(new_test_date - test_date_with_zero)=%s, Count=%d'%( '[%d,%d] days'%(diffD, diffD-0) if diffD is not None else '<None>', cnt))

    
"""
zeroInds = list(filter(lambda i:  vals[i] == 0 ,range(len(vals))))
diffVec = []
valStats = []
for ind in zeroInds:
    pid = pids[ind]
    date = dates[ind]
    addedCnt = 0
    closeVal = None
    closeValZero = None
    for i in range(-searchRange, searchRange):
        if i == 0:
            continue
        indCandidate = ind + i
        if indCandidate <0 or indCandidate >= len(vals):
            continue
        if pids[indCandidate] != pid:
            continue
        dateC = dates[indCandidate]
        datediff = (datetime.strptime(dateC, '%Y%m%d') -  datetime.strptime(date, '%Y%m%d')).total_seconds()  / 60/60/24
        if datediff > 10 or datediff < 0:
            continue
        
        if vals[indCandidate] == 0:
            if closeValZero is None or abs(datediff) < abs(closeValZero):
                closeValZero = datediff
            #valStats.append('Zero Again')
            #addedCnt += 1
            continue
        
        if datediff < 10 and datediff > -10:
            if closeVal is None or abs(datediff) < abs(closeVal):
                closeVal = datediff
    if closeVal is not None:
        diffVec.append(closeVal)
        valStats.append('Has Value')
    elif closeVal is None and closeValZero is not None:
        diffVec.append(closeValZero)
        valStats.append('Zero Again')
    else:
        diffVec.append(None)
        valStats.append('No other check in 10 days')

sDates= sorted(hist(list(map(lambda v : 2*int(v/2) if v is not None else None ,diffVec))).items(), key = lambda kv: kv[0] if kv[0] is not None else 1000)
sVals = sorted(hist(valStats).items(), key = lambda kv: kv[0])
for diffD, cnt in sDates:
    print('diffDate(new_test_date - test_date_with_zero)=%s, Count=%d'%( '[%d,%d] days'%(diffD, diffD-1 if diffD <0 else diffD+1) if diffD is not None else '<None>', cnt))
print('####')
for val, cnt in sVals:
    print('Status=%s, Count=%d'%(val, cnt))
"""

"""
unitMap = set(units)
unitVec = []
for i in unitMap:
    unitVec.append(i)
unitNum = list(map( lambda x: retInd(unitVec ,x) ,units))

f= open(fp2, 'r')
lines = f.readlines()
f.close()
data = list(map( lambda x : [float(x.split('\t')[2]), x.split('\t')[3].strip() ] ,lines))
#data = filter( lambda x: x[1] != 'null value' ,data)
vals2 = list(map( lambda x : x[0] ,data))
#wrn = compareAllHists([vals, vals2], 'test', ['reg', 'pos_factor'], 0.0001)

#analyzeHist(unitNum, 'test', lambda ind: unitVec[ind], 0.001)
#vals = throwOutlyers(vals, 0.01, 0.99)
print('%f %f'%(min(vals),max(vals)))
binRange = binSelection(vals, 20)
print(binRange)
#vals = roundRange(vals, binRange)
#print(vv)

analyzeHist(vals, 'test', None,None)
vals = list(filter( lambda x: x > 0 ,vals))
#avg1 =  float(sum(vals)) / float(len(vals))
#print('avg = %2.3f'%avg1)

cfg = Configuration()
htmlPath = os.path.join(fixOS(cfg.output_path), 'test','test'  + '_histogram.html')
if os.name == 'nt':
    os.system(htmlPath)
else:
    os.system('firefox ' + htmlPath + ' &')

"""