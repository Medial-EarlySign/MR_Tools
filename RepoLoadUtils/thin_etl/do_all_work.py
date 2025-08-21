from signal_fix_api import fixAllSignal, fixSignal
import traceback, os, socket, time
from signal_mapping_api import confirmSignal, getTargetSources, listAllTargets, mapSourceTarget
from Configuration import Configuration
from common import *
from signal_unit_api import compareUnitHist
from signal_stats_api import *

def logMsg(msg):
    cfg = Configuration()
    fullP= os.path.join( fixOS(cfg.output_path), 'log.txt')  
    serverName = socket.gethostname()
    userName = os.environ.get('USERNAME')
    if userName is None:
        userName = os.environ.get('USER')
    
    cmd ='%s\t%s\t%s\t%s\n'%(time.strftime('%d-%m-%Y %H:%M:%S', time.localtime()), serverName, userName, msg)
    fo = open(fullP, 'a')
    fo.write(cmd)
    fo.close()
    print(cmd)

def safeFix(listS):
    succList = []
    for sig in listS:
        try:
            logMsg('trying fix signal %s\n'%sig)
            fixSignal(sig)
            succList.append(sig)
            logMsg('DONE  fixing signal %s\n'%sig)
        except:
            expMsg = traceback.format_exc()
            logMsg('failed in %s. %s\n'%(sig, expMsg))
            #traceback.print_exc()
    return succList

def runTestUnitForAll(listS):
    succList = []
    sigMsgs = dict()
    for sig in listS:
        logMsg('running signal stats for %s\n'%sig)
        warningMsgs, unitStats = statsUnitedSig(sig)
        warningMsgs = list(filter(lambda msg: not(msg.startswith('please look at date histogram')) ,warningMsgs))
        sigMsgs[sig] = warningMsgs
        logMsg('Signal %s unitedStats=%s'%(sig, warningMsgs))
        
        totCnt = sum(list(map(lambda kv: kv[1] ,unitStats)))
        topTake = list(filter(lambda kv: kv[1] > 300 and float(kv[1])/totCnt > 0.00005  ,unitStats[:10]))
        unitName = list(map(lambda kv: kv[0] ,topTake))
        logMsg('running signal units stats for %s with units %s\n'%(sig, unitName))
        if len(unitName) >= 2:
            unitsMsgs = compareUnitHist(sig, unitName, 0.0001)
        else:
            unitsMsgs = ['empty units - WTF??']
        logMsg('Signal %s units warning=%s'%(sig, unitsMsgs))
        if len(unitsMsgs) == 0:
            logMsg('Units in signal %s are ok'%sig)
            succList.append(sig)
        
    return succList, sigMsgs

def runTestForAll(listS):
    succList = []
    sigMsgs = dict()
    for sig in listS:
        logMsg('running fixed signal stats for %s\n'%(sig))
        try:
            warningMsgs = statsFixedSig(sig)
            warningMsgs = list(filter(lambda msg: not(msg.startswith('please look at date histogram') and
                                    not(msg.startswith('Couldn''t find signal in maccabi')) ) ,warningMsgs))
            sigMsgs[sig] = warningMsgs
            logMsg('Signal %s fixStats=%s'%(sig, warningMsgs))
            if len(warningMsgs) == 0:
                succList.append(sig)
        except:
            msg = traceback.format_exc()
            logMsg('Error in getting stats for signal %s. Error: %s\n'%(sig, msg))
    return succList, sigMsgs

def getAllSignalCounts():
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
    srcToTargt = mapSourceTarget()
    for line in lines:
        if len(line.strip()) == 0:
            continue
        tokens= line.split('\t')
        if len(tokens) != 3:
            raise NameError('Format Error in commonVals')
        sigKey = tokens[0].strip()
        cnt = int(tokens[1].strip())
        if srcToTargt.get(sigKey) is None:
            #eprint ('Couldn''t find %s'%sigKey)
            #sigCnt[srcToTargt[sigKey]] = 0
            pass
        else:
            targetName = srcToTargt[sigKey].replace('/','_over_')
            if sigCnt.get(targetName) is None:
                sigCnt[targetName] = 0
            sigCnt[targetName] += cnt
    
    return sigCnt

def getSignalStatus(sigName):
    cfg = Configuration()
    source_dir =  os.path.join( fixOS(cfg.work_path), 'Common')
    if not(os.path.exists(source_dir)):
        raise NameError('source dir not exists. config problem?')
    sourceFiles = getTargetSources(sigName)
    allSrcExists = True
    for srcFile in sourceFiles:
        fullP = os.path.join(source_dir, srcFile)
        if not(os.path.exists(fullP)):
            allSrcExists = False
            break
    if not(allSrcExists):
        return ['Map', 'Not All Source File Exists' , None]
    
    united_dir =  os.path.join( fixOS(cfg.work_path), 'United')
    if not(os.path.exists(source_dir)):
        raise NameError('united dir not exists. config problem?')
    sigNamePath = sigName.replace('/','_over_')
    united_full = os.path.join(united_dir, sigNamePath)

    state = 'Map'
    comment = 'Waiting for Unite'
    dt=  None
    rUnited = None
    if not(os.path.exists(united_full)):
        return [state, comment, dt]
    else:
        state = 'United'
        rUnited = os.path.getmtime(united_full)
        dt = datetime.fromtimestamp(rUnited).strftime('%d-%m-%Y %H:%M:%S')
        comment = 'Waiting For Fix'
        
    fixed_dir =  os.path.join( fixOS(cfg.work_path), 'Fixed')
    if not(os.path.exists(fixed_dir)):
        raise NameError('fixed dir not exists. config problem?')
    fixed_full = os.path.join(fixed_dir, sigNamePath)
    rFixed = None
    if not(os.path.exists(fixed_full)):
        return [state, comment, dt]
    else:
        rFixed = os.path.getmtime(fixed_full)
        if rFixed < rUnited:
            comment = 'Update Fix File'
            return [state, comment, dt]
        else:
            state=  'Fixed'
            dt = datetime.fromtimestamp(rFixed).strftime('%d-%m-%Y %H:%M:%S')
            comment = 'Waiting for tests'

    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(code_dir)):
        raise NameError('please add codeDir')
    fullPt = os.path.join(code_dir, 'confirm_signals.txt')
    if not(os.path.exists(fullPt)):
        return [state, comment, dt]
    else:
        fp = open(fullPt, 'r')
        lines = fp.readlines()
        fp.close()
        for line in lines:
            tokens = line.split('\t')
            if len(tokens) != 2:
                raise NameError('Format Error %s'%line)
            if tokens[0].strip() == sigName:
                approved = datetime.strptime(tokens[1].strip(), '%d-%m-%Y %H:%M:%S')
                approveDt = (approved - datetime(1970, 1, 1)).total_seconds()
                #approveDt = approveDt.timestamp()
                if approveDt < rFixed:
                    comment = 'already approved in the past'
                else:
                    dt = tokens[1].strip()
                    state = 'Done'
                    comment = ''
                
    return [state, comment, dt]

def getAllSignalStatus():
    sigCnt = getAllSignalCounts()
    sigCnt = list(map(lambda kv: [kv[0].replace('/', '_over_'), kv[1]] ,sigCnt.items()))
    tups = list(sorted(sigCnt, key = lambda kv : kv[1], reverse = True))
    signaleOrdered = list(filter(lambda x: (x[0]!= 'TBD' and x[0]!= 'NULL') and x[1] > 100000 ,tups))
    signaleOrdered = list(map(lambda kv: kv[0],signaleOrdered))
    
    res = []
    for signal in signaleOrdered:
        status, comment, updateDate = getSignalStatus(signal)
        res.append( [signal, status, comment, updateDate ] )
    return res

def doAll(withUnited= False):
    signalStatus = getAllSignalStatus()
    toCheck = []
    toFix = []
    toApprove = []
    
    #skipList = ['INR'] #not ready
    skipList = [] #not ready
    withFactros = ['TEMP']
    #inSeperateRun = ['WBC', 'InorganicPhosphate']
    inSeperateRun = []
    for sigStat in signalStatus:
        signalName, status, comment, dateStr = sigStat
        if signalName in skipList: #skip INR not ready yet
            continue
        if signalName in withFactros: #will be taken care of seperatly, by hand
            continue
        if signalName in inSeperateRun:
            continue
        if status == 'United':
            toCheck.append(signalName)
        if status == 'Fixed' and not(comment.startswith('already approved')):
            toApprove.append(signalName)

    #TODO - remove this sectio  later
    #toCheck = toCheck + toApprove  #check also fixed for now-  remove later when done in order :)
    #toApprove = []
    #TODO - end section    
    if withUnited: 
        logMsg('Running united Stats for all %s'%toCheck)
        toFix, unitedMsgs = runTestUnitForAll(toCheck)
    else:
        unitedMsgs = []
        
    logMsg('Running fix for all %s'%toFix)
    succList = safeFix(toFix)
    toApprove = toApprove + succList
    toConfirm,fixedMsg = runTestForAll(toApprove)
    
    for sig in toConfirm:
        logMsg('can confirm %s'%sig)
        #confirmSignal(sig)
    return [[toCheck, toFix, toApprove, toConfirm], [unitedMsgs, fixedMsg]]

def handleSignal(signaleName):
    toFix, unitedMsgs = runTestUnitForAll([signaleName])
    succList = safeFix(toFix)
    toConfirm,fixedMsg = runTestForAll(succList)
    
    if len(toConfirm) > 0:
        logMsg('can confirm %s'%signaleName)

def confirmAlreadyApproved():
    signalStatus = getAllSignalStatus()
    skipList = ['INR', 'PTT'] #not ready
    withFactros = ['InorganicPhosphate']
    #inSeperateRun = ['WBC', 'InorganicPhosphate']
    inSeperateRun = []
    toConfirm = []
    for sigStat in signalStatus:
        signalName, status, comment, dateStr = sigStat
        if signalName in skipList: #skip INR not ready yet
            continue
        if signalName in withFactros: #will be taken care of seperatly, by hand
            continue
        if signalName in inSeperateRun:
            continue
        if status == 'Fixed' and comment.startswith('already approved'):
            toConfirm.append(signalName)
            
    for sig in toConfirm:
        logMsg('confirm signal %s'%sig)
        confirmSignal(sig)
        logMsg('done confirm signal %s'%sig)

if __name__ == "__main__":
    #handleSignal('UrineAlbumin_over_Creatinine')
    #allSigs = getAllSignalStatus()
    allStatuses, allMsgs = doAll()
    #confirmAlreadyApproved()
    #readySigs = ['RBC', 'EosNum', 'MonNum']
    #succList = safeFix(readySigs)
    #print('Running stats for all success')
    #toConfirm,wanrMsg = runTestForAll(succList)
    #for sig in toConfirm:
    #    print('confirm %s'%sig)
    #    confirmSignal(sig)
