from Configuration import Configuration
from common import *
from datetime import datetime
import re
import os

def renameSignalMap(src, target):
    cfg = Configuration()
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    if not(os.path.exists(signal_list_file)):
        raise NameError('signal list path not exists')
    f = open(signal_list_file, 'r')
    allLines = f.readlines()
    f.close()
    allLines = filter(lambda x: len(x.strip()) > 0, allLines)
    newData = []
    changeInds = []
    lineNum = 1
    for line in allLines:
        tokens=line.strip().split('\t')
        if len(tokens) != 2:
            raise NameError('read format error')
        if tokens[1].strip() == src:
            line = '%s\t%s\n'%(tokens[0], target) 
            changeInds.append(lineNum)
        newData.append(line)
        lineNum = lineNum + 1
    fo = open(signal_list_file, 'w')
    fo.writelines(newData)
    fo.close()

    log_cmd('Run Rename with "%s" to "%s" target. changed [%s] line numbers'%(src, target, ', '.join( map( lambda x: str(x) ,changeInds) ) ))
    

def commitSignal(searchRegex, mapValue):
    cfg = Configuration()
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    regex = re.compile(searchRegex, re.IGNORECASE)
    if not(os.path.exists(signal_list_file)):
        raise NameError('signal list path not exists')
    f = open(signal_list_file, 'r')
    allLines = f.readlines()
    f.close()
    allLines = filter(lambda x: len(x.strip()) > 0, allLines)
    newData = []
    changeInds = []
    lineNum = 1
    for line in allLines:
        tokens=line.strip().split('\t')
        if len(tokens) != 2:
            raise NameError('read format error')
        matchObj = regex.findall(line)
        if len(matchObj) > 0:
            line = '%s\t%s\n'%(tokens[0], mapValue) 
            changeInds.append(lineNum)
        newData.append(line)
        lineNum = lineNum + 1
    fo = open(signal_list_file, 'w')
    fo.writelines(newData)
    fo.close()

    log_cmd('Run Commit with "%s" regex to "%s" target. changed [%s] line numbers'%(searchRegex, mapValue, ', '.join( map( lambda x: str(x) ,changeInds) ) ))
               
def listAllTargets(searchRegex = None, prt = False):
    cfg = Configuration()
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    if not(os.path.exists(signal_list_file)):
        raise NameError('signal list path not exists')
    f = open(signal_list_file, 'r')
    allLines = f.readlines()
    allLines = allLines[1:]
    f.close()
    allLines = filter(lambda x: len(x.strip()) > 0, allLines)
    allTarget = dict()
    if (searchRegex is not None):
        regex = re.compile(searchRegex, re.IGNORECASE)
    for line in allLines:
        tokens=line.strip().split('\t')
        if len(tokens) != 2:
            raise NameError('read format error')
        target = tokens[1].strip()
        if (searchRegex is not None) and len(regex.findall(target)) == 0:
            continue
        if not(allTarget.get(target) is not None):
            allTarget[target] = 0
        allTarget[target] = allTarget[target] + 1
    tups = []
    for k,v in allTarget.items():
        tups.append([k,v])
    tups = sorted(tups, key=lambda kv: kv[1], reverse = True)
    if prt:
        for kv in tups:
            print('target %s appears %d'%(kv[0], kv[1]))
    return allTarget

def getTargetSources(target):
    cfg = Configuration()
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    if not(os.path.exists(signal_list_file)):
        raise NameError('signal list path not exists')
    f = open(signal_list_file, 'r')
    allLines = f.readlines()
    f.close()
    allLines = filter(lambda x: len(x.strip()) > 0, allLines)
    sourceList = list()
    for line in allLines:
        tokens=line.strip().split('\t')
        if len(tokens) != 2:
            raise NameError('read format error')
        trg = tokens[1].strip()
        src = tokens[0].strip()
        if (target == trg):
            sourceList.append(src)
    return sourceList

def searchSignal(searchRegex, prt=True):
    cfg = Configuration()
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    regex = re.compile(searchRegex, re.IGNORECASE)
    if not(os.path.exists(signal_list_file)):
        eprint(signal_list_file)
        raise NameError('signal list path not exists')
    f = open(signal_list_file, 'r')
    allLines = f.readlines()
    f.close()
    allLines = filter(lambda x: len(x.strip()) > 0, allLines)
    resList = []
    for line in allLines:
        matchObj = regex.findall(line)
        if len(matchObj) > 0:
            if prt:
                print(line.strip())
            resList.append(line.strip())
    return resList

def mapSourceTarget():
    cfg = Configuration()
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    if not(os.path.exists(signal_list_file)):
        eprint(signal_list_file)
        raise NameError('signal list path not exists')
    f = open(signal_list_file, 'r')
    allLines = f.readlines()
    f.close()
    allLines = filter(lambda x: len(x.strip()) > 0, allLines)
    resList = dict()
    for line in allLines:
        tokens = line.split('\t')
        src = tokens[0].strip()
        resList[src] = tokens[1].strip()
    return resList

def searchSignalAndTarget(searchRegex):
    print('Signal Search Results:')
    res = searchSignal(searchRegex)
    if len(res) == 0:
        print('Not found')
    else:
        print('Found %d Results in total'%len(res))
    print('\nTarget Mapping Search Results:')
    res = listAllTargets(searchRegex)
    if len(res) == 0:
        print('Not found')

def addMissingSignals():
    cfg = Configuration()
    cmPath = os.path.join( fixOS(cfg.work_path), 'Common')
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    if not(os.path.exists( cmPath)):
        raise NameError('path nor exists')
    if not(os.path.exists(signal_list_file)):
        eprint(signal_list_file)
        raise NameError('signal list path not exists')
    allFiles = os.listdir(cmPath)
    fp = open(signal_list_file, 'r')
    lines = fp.readlines()
    fp.close()
    lines = lines[1:] #skip header
    srcFile = set(list(map( lambda l : l.strip().split('\t')[0] ,lines)))
    allFiles = list(filter( lambda v: v not in srcFile ,allFiles))
    newLines = list( map(lambda v: '%s\tTBD\n'%v ,allFiles))
    if len(newLines)  == 0:
        return []
    fp = open(signal_list_file, 'a')
    fp.writelines(newLines)
    fp.close()
    return allFiles

def confirmSignal(signalName):
    cfg = Configuration()
    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(code_dir)):
        raise NameError('please add codeDir')
    fullPt = os.path.join(code_dir, 'confirm_signals.txt')
    if not(os.path.exists(fullPt)):
        fp = open(fullPt, 'w')
        fp.close()
    
    fp = open(fullPt, 'r')
    lines = fp.readlines()
    fp.close()
    nowFrm = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    #signal_name \t confrim_date
    newData = []
    setData = False
    for line in lines:
        tokens = line.split('\t')
        if (tokens[0].strip() == signalName):
            setData = True
            line = '%s\t%s\n'%(signalName, nowFrm)
        newData.append(line)

    if len(newData) > 0 and not(newData[-1].endswith('\n') or newData[-1].endswith('\r')):
        newData[-1] = newData[-1] + '\n'
    if not(setData):
        line = '%s\t%s\n'%(signalName, nowFrm)
        newData.append(line)
    
    fw = open(fullPt, 'w')
    lines = fw.writelines(newData)
    fw.close()

if __name__ == "__main__":
    #listAllTargets('HDL')
    searchSignalAndTarget('1001400138|Erythrocyte')
    #commitSignal('1001400138|Erythrocyte', 'Erythrocyte')