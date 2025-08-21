from Configuration import Configuration
from common import *
import os, io
from datetime import datetime

def fetchNextId(maxId):
    num = maxId
    multy = 1
    while int(num /10) > 0:
        num = int(num / 10)
        multy *= 10
    return multy * (num+1)

def completeAllNewSignals():
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(work_dir)):
        raise NameError('config error - work dir hasn''t found')
    if not(os.path.exists(code_dir)):
        raise NameError('config error - code dir hasn''t found')
    fixed_path = os.path.join(work_dir, 'Fixed')
    allSignals = os.listdir(fixed_path)
    if not(os.path.exists(os.path.join(code_dir, 'thin.convert_config'))):
        raise NameError('thin.convert_config is missing in current dir')
    if not(os.path.exists(os.path.join(code_dir, 'thin.signals'))):
        raise NameError('thin.signals is missing in current dir')
    if not(os.path.exists(os.path.join(code_dir, 'codes_to_signals'))):
        raise NameError('codes_to_signals is missing in current dir')
    fp = open(os.path.join(code_dir, 'thin.signals'), 'r')
    lines = fp.readlines()
    fp.close()

    fp = open(os.path.join(code_dir, 'codes_to_signals'), 'r')
    codeLines = fp.readlines()
    fp.close()
    codeConvert = dict()
    for line in codeLines:
        tokens = line.split('\t')
        if len(tokens) != 2:
            raise NameError('format Error')
        codeConvert[ tokens[0].strip() ] = tokens[1].strip()
    #lines = list(filter( lambda l: len(l.strip()) > 0 and not(l.startswith('#')) ,lines))
    allSignals = list(map(lambda x: x if codeConvert.get(x) is None else codeConvert[x] ,allSignals))
    alreadySignals = set()
    newData = []
    sigIds = []
    for line in lines:
        if line.startswith('SIGNAL'):
            tokens = line.split('\t')
            if len(tokens) != 4 and len(tokens) != 5:
                raise NameError('Format Error got "%s" with %d tokens'%(line, len(tokens)))
            signalName = tokens[1].strip()
            signalId = tokens[2].strip()
            signalType = tokens[3].strip()
            signalComment = None
            if len(tokens) > 4:
                signalComment = tokens[4].strip()
            sigIds.append(int(signalId))
            sigName = signalName
            if codeConvert.get(signalName) is not None:
                sigName = codeConvert[signalName]
            if not(sigName in allSignals):
                newData.append(line)
                continue
            alreadySignals.add(sigName)
        newData.append(line)
        
    nextId = max(sigIds)
    nextId = fetchNextId(nextId)
    for signalName in allSignals:
        sigName = signalName
        if codeConvert.get(signalName) is not None:
            sigName = codeConvert[signalName]
        if sigName in alreadySignals:
            continue
        nextId += 1
        signalId = nextId
        signalType = '1'
        sigComment = 'Automaticaly added-please edit'
        line = 'SIGNAL\t%s\t%s\t%s\t%s\n'%( sigName,signalId, signalType, sigComment)
        print('Adding signal %s to thin.signals'%sigName)
        newData.append(line)

    fw = open(os.path.join(code_dir, 'thin.signals'), 'w')
    fw.writelines(newData)
    fw.close()

def completeAllNewSignalsCfg(failOnNotFound=True, override_not_found = False):
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(work_dir)):
        raise NameError('config error - work dir hasn''t found')
    if not(os.path.exists(code_dir)):
        raise NameError('config error - code dir hasn''t found')
    fixed_path = os.path.join(work_dir, 'Fixed')
    allSignals = os.listdir(fixed_path)
    
    if not(os.path.exists(os.path.join(code_dir, 'thin.convert_config'))):
        raise NameError('thin.convert_config is missing in current dir')
    if not(os.path.exists(os.path.join(code_dir, 'thin.signals'))):
        raise NameError('thin.signals is missing in current dir')
    fp = open(os.path.join(code_dir, 'thin.convert_config'), 'r')
    lines = fp.readlines()
    fp.close()

    alreadySignals = set()
    
    newData = []
    for line in lines:
        if line.startswith('DATA'):
            tokens = line.split('\t')
            if len(tokens) != 2:
                raise NameError('Format Error')
            signalPath = tokens[1].strip()
            signalName = os.path.basename(signalPath)
            if not(os.path.exists(signalPath)):
                if (not(override_not_found) or not(signalName in allSignals)) and failOnNotFound:
                    raise NameError('Missing signal %s in path %s exiting..'%(signalName, signalPath))
                if not(override_not_found) or not(signalName in allSignals): #signal not exist in our list or not to override
                    alreadySignals.add(signalName)
                    newData.append(line)
                continue #don't append line i will append it later, if signal w'll be added later
            alreadySignals.add(signalName)
        newData.append(line)
    for signalName in allSignals:
        if signalName in alreadySignals:
            continue
        line = 'DATA\t%s\n'%( os.path.join(fixed_path, signalName) )
        print('Adding signal %s to thin.convert_config'%signalName)
        newData.append(line)

    fw = open(os.path.join(code_dir, 'thin.convert_config'), 'w')
    fw.writelines(newData)
    fw.close()

def createAdditionalSignals():
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    if not(os.path.exists(work_dir)):
        raise NameError('config error - work dir hasn''t found')
    signals_path = os.path.join(work_dir, 'SpecialSignals')
    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(os.path.join(code_dir, 'thin_additional.convert_config'))):
        raise NameError('thin_additional.convert_config is missing in current dir')

    readCodesignals = ['Cervical', 'Family_History', 'Scoring_test_result', 'Allergy_over_intolerance']
    allSignals = os.listdir(signals_path)
    allSignals = list(filter(lambda x: not(x in readCodesignals) ,allSignals))
    
    fp = open(os.path.join(code_dir, 'thin_additional.convert_config'), 'r')
    lines = fp.readlines()
    fp.close()

    if not(lines[-1].endswith('\n')):
        lines[-1] = lines[-1] + '\n'
    for signalName in allSignals:
        line = 'DATA_S\t%s\n'%( os.path.join(signals_path, signalName) )
        print('Adding signal %s to thin_additional.convert_config'%signalName)
        lines.append(line)

    load_only = 'LOAD_ONLY\t%s\n'%(','.join(allSignals))
    lines.append(load_only)
    
    clines = list(map(unicode ,lines))
    fw = io.open(os.path.join(code_dir, 'thin_additional.convert_config'), 'w', newline = '')
    fw.writelines(clines)
    fw.close()

def completeNewSpecial():
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    if not(os.path.exists(work_dir)):
        raise NameError('config error - work dir hasn''t found')
    signals_path = os.path.join(work_dir, 'SpecialSignals')
    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(os.path.join(code_dir, 'thin_additional.convert_config'))):
        raise NameError('thin_additional.convert_config is missing in current dir')

    fp = open(os.path.join(code_dir, 'codes_to_signals'), 'r')
    codeLines = fp.readlines()
    fp.close()
    codeConvert = dict()
    for line in codeLines:
        tokens = line.split('\t')
        if len(tokens) != 2:
            raise NameError('format Error')
        codeConvert[ tokens[0].strip() ] = tokens[1].strip()
        
    readCodesignals = ['Cervical', 'Family_History', 'Scoring_test_result', 'Allergy_over_intolerance']
    allSignals = os.listdir(signals_path)
    allSignals = list(filter(lambda x: not(x in readCodesignals) ,allSignals))
    allSignals = list(map(lambda x: x if codeConvert.get(x) is None else codeConvert[x] ,allSignals))

    fp = open(os.path.join(code_dir, 'thin.signals'), 'r')
    lines = fp.readlines()
    fp.close()
    
    alreadySignals = set()
    newData = []
    sigIds = []
    for line in lines:
        if line.startswith('SIGNAL'):
            tokens = line.split('\t')
            if len(tokens) != 4 and len(tokens) != 5:
                raise NameError('Format Error got "%s" with %d tokens'%(line, len(tokens)))
            signalName = tokens[1].strip()
            signalId = tokens[2].strip()
            signalType = tokens[3].strip()
            signalComment = None
            if len(tokens) > 4:
                signalComment = tokens[4].strip()
            sigIds.append(int(signalId))
            sigName = signalName
            if codeConvert.get(signalName) is not None:
                sigName = codeConvert[signalName]
            if not(sigName in allSignals):
                newData.append(line)
                continue
            alreadySignals.add(sigName)
        newData.append(line)

    newData.append('#======Automaticaly added at %s =========\n'%(datetime.now().strftime('%d-%m-%Y %H:%M:%S')))
    nextId = max(sigIds)
    nextId = fetchNextId(nextId)
    for signalName in allSignals:
        if signalName in alreadySignals:
            continue
        nextId += 1
        signalId = nextId
        signalType = '1'
        sigComment = 'Automaticaly added-please edit'
        line = 'SIGNAL\t%s\t%s\t%s\t%s\n'%( signalName,signalId, signalType, sigComment)
        print('Adding signal %s to thin.signals'%signalName)
        newData.append(line)

    clines = list(map(unicode, newData))
    fw = io.open(os.path.join(code_dir, 'thin.signals'), 'w', newline = '')
    fw.writelines(clines)
    fw.close()

if __name__ == '__main__':
    #createAdditionalSignals()
    completeNewSpecial()
    #completeAllNewSignalsCfg(False)
    #completeAllNewSignals()