from Configuration import Configuration
from common import *
from signal_mapping_api import *
import os

def statsFixedSig(signalName):
    warnningMsgs = []
    cfg = Configuration()
    if not(os.path.exists(os.path.join( fixOS(cfg.work_path), 'Fixed'))):
        raise NameError('fixed_path doesn''t exists')
    if not(os.path.exists(os.path.join(os.path.join( fixOS(cfg.work_path), 'Fixed'), signalName))):
        raise NameError('signal doesn''t exists')
    fp = open( os.path.join(os.path.join( fixOS(cfg.work_path), 'Fixed') , signalName), 'r')
    line = fp.readline()
    pidCnt = set()
    lineCnt = 0
    dateVec = []
    valVec = []
    fileVals = dict()
    while line is not None and len(line) != 0:
        line = line.strip()
        tokens = line.split('\t')
        #PID, SIGNAL_NAME, DATE, VAL, (FILENAME TODO)
        if len(tokens) < 4:
            print('Error In Line %d: %s'%(lineCnt,line))
            raise NameError('Format Error %d'%(len(tokens)))
        pidCnt.add(tokens[0])
        dateVec.append(tokens[2])
        valVec.append(float(tokens[3]))
        if len(tokens) >= 5:
            if fileVals.get(tokens[4]) is None:
                fileVals[tokens[4]] = []
            fileVals[tokens[4]].append(float(tokens[3]))
            
        lineCnt = lineCnt + 1
        line = fp.readline()
    fp.close()
    
    print('Read %d lines with %d pids'%(lineCnt, len(pidCnt)))
    
    dateVec = date2Num(dateVec)
    analyzeHist(dateVec, 'Fixed_Dates_' + signalName, lambda v :  datetime.fromordinal(v).strftime('%d-%m-%Y') if datetime.fromordinal(v).year >= 1900 else '01-01-%d'%(datetime.fromordinal(v).year) , None, os.path.join(fixOS(cfg.output_path), signalName) )
    dateOk = analyzeTimeSignal(dateVec)
    if not(dateOk):
        htmlPath = os.path.join(fixOS(cfg.output_path), signalName, 'Fixed_Dates_' + signalName + '_histogram.html')
        if os.name == 'nt':
            os.system(htmlPath)
        else:
            os.system('firefox ' + htmlPath + ' &')
        msg = 'please look at date histogram, there are big jumps in time series. open "%s"'%(htmlPath)
        warnningMsgs.append(msg)
        eprint(msg)

    analyzeHist(valVec, 'Values_' + signalName, None, 0.0001 , os.path.join(fixOS(cfg.output_path), signalName))
    #normalFit = checkNormal(valVec)
    normalFit = None
    if normalFit is None:
        pass #normalfit is disabled!
    elif (normalFit < 0.95):
        htmlPath = os.path.join(fixOS(cfg.output_path), signalName, 'Values_' + signalName + '_histogram.html')
        if os.name == 'nt':
            os.system(htmlPath)
        else:
            os.system('firefox ' + htmlPath + ' &')
        msg = 'values are not from normal fit (%2.3f). open "%s"'%(normalFit, htmlPath)
        warnningMsgs.append(msg)
        eprint(msg)
    else:
        print('Good Normal fit %2.3f'%normalFit)
 
    #Check similirity between files and maccabi:
    compare_vec = []
    data_name = []
    for fileName, vals in fileVals.items():
        if len(vals) == 0:
            msg = "add empty vector"
            warnningMsgs.append(msg)
            eprint(msg)
            continue
        compare_vec.append(vals)
        data_name.append(fileName)
    #Add Maacabi
    maccabi_vals = loadMaccabiSignalStats(signalName, 0)
    if maccabi_vals is not None:
        if len(maccabi_vals) == 0:
            msg = "add empty maccabi vector"
            warnningMsgs.append(msg)
            eprint(msg)
        else:
            compare_vec.append(maccabi_vals)
            data_name.append('Maccabi')
    else:
        msg = "Couldn''t find signal in maccabi"
        warnningMsgs.append(msg)
        eprint(msg)
    msgs = compareAllHists(compare_vec, signalName, data_name, 0.0001)
    for msg in msgs:
        warnningMsgs.append(msg)
    if len(msgs)> 0:
        htmlPath = os.path.join(fixOS(cfg.output_path) , signalName , 'compare_all_series' + '.html')
        if os.name == 'nt':
            os.system(htmlPath)
        else:
            os.system('firefox ' + htmlPath + ' &')
    else:
        print('done compering to other files and maccabi with no warnnings :)')
    
    return warnningMsgs

def statsUnitedSig(signalName, searchRegex = None, onlyUnits = False):
    signalFileName = signalName.replace('/', '_over_')
    warnningMsgs = []
    cfg = Configuration()
    if not(os.path.exists(os.path.join( fixOS(cfg.work_path), 'United'))):
        raise NameError('united_path doesn''t exists')
    if not(os.path.exists(os.path.join(os.path.join( fixOS(cfg.work_path), 'United'), signalFileName))):
        raise NameError('signal doesn''t exists')
    fp = open( os.path.join(os.path.join( fixOS(cfg.work_path), 'United') , signalFileName), 'r')
    line = fp.readline()
    pidCnt = set()
    lineCnt = 0
    dateVec = []
    valVec = []
    unitsVec = dict()
    fileSet = set()
    fileVals = dict()
    ahd_lookup = get_ahd_lookup()
    while line is not None and len(line) != 0:
        line = line.strip()
        tokens = line.split('\t')
        #PID, DATE, VAL, UNITS, FILE_NAME
        if len(tokens) < 5:
            print('Error in Line %d: %s\n%s'%(lineCnt,line, '\n'.join(tokens)))
            raise NameError('Format Error %d'%(len(tokens)))
        pidCnt.add(tokens[0])
        fileSet.add(tokens[4])
        dateVec.append(tokens[1])
        valVec.append(float(tokens[2]))
        if (unitsVec.get(tokens[3]) is None):
            unitsVec[tokens[3]] = 0
        unitsVec[tokens[3]] = unitsVec[tokens[3]] + 1
        if (fileVals.get(tokens[4]) is None):
            fileVals[tokens[4]] = []
        fileVals[tokens[4]].append(float(tokens[2]))
        
        lineCnt = lineCnt + 1
        line = fp.readline()
    
    fp.close()
    print('Read %d lines with %d pids from %d files'%(lineCnt, len(pidCnt), len(fileSet)))
    dateVec = date2Num(dateVec)
    supportList = supportedFormatList(signalName)
    errorInUnits = 0
    tups = []
    for k,v in unitsVec.items():
        tups.append([k,v])
    tups = sorted(tups, key=lambda kv: kv[1], reverse = True)
    for tp in tups:
        unit_nm = tp[0]
        if supportList.get(unit_nm) is None:
            if ahd_lookup.get(unit_nm) is not None:
                unit_nm = ahd_lookup[unit_nm]
            if supportList.get(unit_nm) is None:
                errorInUnits = errorInUnits + tp[1]
    if errorInUnits > 0:
        msg = 'you have %d rows with unit errors'%errorInUnits
        warnningMsgs.append(msg)
        eprint(msg)
        for tp in tups:
            unit_nm = tp[0]
            if supportList.get(unit_nm) is not None:
                pass
                #print('unit "%s" - %d'%(tp[0], tp[1]))
            else:
                if ahd_lookup.get(unit_nm) is not None:
                    unit_nm = ahd_lookup[unit_nm]
                if supportList.get(unit_nm) is None:
                    errorInUnits = errorInUnits + tp[1]
                #eprint('unit "%s" - %d'%(tp[0], tp[1]))
    else:
        print('All Unit convertion is OK :)')

    tups_c = []
    for unit_name, unit_cnt in tups:
        if ahd_lookup.get(unit_name) is not None:
            unit_name = ahd_lookup[unit_name]
        tups_c.append( [unit_name, unit_cnt])
    tups = tups_c
    if onlyUnits:
        return warnningMsgs, tups
    
    analyzeHist(dateVec, 'United_Dates_' + signalName, lambda v :  datetime.fromordinal(v).strftime('%d-%m-%Y') if datetime.fromordinal(v).year >= 1900 else '01-01-%d'%(datetime.fromordinal(v).year), None, os.path.join(fixOS(cfg.output_path), signalFileName) )
    if searchRegex is not None:
        resFile = searchSignal(searchRegex, False)
        numOfFile = len(resFile)
        if numOfFile != len(fileSet):
            msg = 'you have more diffrent number of files matching your regex than files in united. regex_match=%d, united_file_cnt=%d\nregex=[%s]\nunited_files=[%s]'%(numOfFile, \
                len(fileSet), ', '.join(resFile) , ', '.join(fileSet) )
            warnningMsgs.append(msg)
            eprint(msg)

    dateOk = analyzeTimeSignal(dateVec)
    if not(dateOk):
        htmlPath = os.path.join(fixOS(cfg.output_path), signalFileName , 'United_Dates_' + signalName + '_histogram.html')
        if os.name == 'nt':
            os.system(htmlPath)
        else:
            os.system('firefox ' + htmlPath + ' &')
        msg = 'please look at date histogram, there are big jumps in time series. open "%s"'%(htmlPath)
        warnningMsgs.append(msg)
        eprint(msg)
    
    return warnningMsgs, tups

def numRes(num):
    res = ''
    if num-int(num) == 0:
        res = '1'
    elif (10*num-int(10*num)) == 0:
        res = '0.1'
    elif (100*num-int(100*num)) == 0:
        res = '0.01'
    return res

def getSignalUnitRes(signalName, unitName):
    unitDict = getSignalByUnit(signalName)
    if (unitDict.get(unitName) is None):
        raise NameError('unit Not Found')
    resDict = hist(list(map(lambda x: numRes(float(x)) ,unitDict[unitName])))
    tups = []
    for k,v in resDict.items():
        tups.append([k,v])
    tups = sorted(tups, key=lambda kv: kv[1], reverse = True)
    return tups[0][0]

def getSignalByUnit(signalName, ahd_lookup = None):
    cfg = Configuration()
    if not(os.path.exists(os.path.join( fixOS(cfg.work_path), 'United'))):
        raise NameError('united_path doesn''t exists')
    if not(os.path.exists(os.path.join(os.path.join( fixOS(cfg.work_path), 'United'), signalName))):
        raise NameError('signal doesn''t exists')
    fp = open( os.path.join(os.path.join( fixOS(cfg.work_path), 'United') , signalName), 'r')
    line = fp.readline()
    unitsDict = dict()
    if ahd_lookup is None:
        ahd_lookup = get_ahd_lookup()
    
    while line is not None and len(line) != 0:
        line = line.strip()
        tokens = line.split('\t')
        #PID, DATE, VAL, UNITS, FILE_NAME
        if len(tokens) < 5:
            print(line)
            raise NameError('Format Error %d'%(len(tokens)))
        val = float(tokens[2])
        unit_name = tokens[3].strip()
        if ahd_lookup is not None and ahd_lookup.get(unit_name) is not None:
            unit_name = ahd_lookup[unit_name]
        if (unitsDict.get(unit_name) is None):
            unitsDict[unit_name] = []
        unitsDict[unit_name] .append(val)
        line = fp.readline()
    fp.close()
    return unitsDict
    
if __name__ == "__main__":   
    #res = statsUnitedSig('HCG', 'HCG')
    res = statsUnitedSig('Erythrocyte','1001400138|Erythrocyte')
    #res = getSignalUnitRes('Erythrocyte', 'mm/h')