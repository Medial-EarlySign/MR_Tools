from common import *
from Configuration import Configuration

def config_set_unit(signalName, unit, value):
    if signalName is None or unit is None or value is None:
        raise NameError('values can''t be None')
    cfg = Configuration()
    instructionPath= os.path.join(fixOS(cfg.code_folder), 'unitTranslator.txt')
    fo = open(instructionPath, 'r')
    lines = fo.readlines()
    fo.close()

    setData = False
    newData = []
    for line in lines:
        tokens=line.strip().split('\t')
        if len(tokens) < 3:
            raise NameError('format Error')
        sigName = tokens[0].strip()
        unitName = tokens[1].strip()
        if signalName == sigName and (unitName == unit):
            if setData: #mutiple lines found
                continue
            line = '%s\t%s\t%s\n'%(signalName, unit, value)
            setData = True
        newData.append(line)
    if not(setData):
        if not(newData[-1].endswith('\n') or newData[-1].endswith('\r')):
            newData[-1] = newData[-1] + '\n'
        line = '%s\t%s\t%s\n'%(signalName, unit, value)
        newData.append(line)
    fw = open(instructionPath, 'w')
    fw.writelines(newData)
    fw.close()
    log_cmd('Run config_set_unit on [%s, %s, %s]'%(signalName, unit, value))

def config_rm_unit(signalName, unit = None):
    cfg = Configuration()
    instructionPath= os.path.join(fixOS(cfg.code_folder), 'unitTranslator.txt')
    fo = open(instructionPath, 'r')
    lines = fo.readlines()
    fo.close()

    pLines = 0
    for line in lines:
        tokens=line.strip().split('\t')
        if len(tokens) < 3:
            raise NameError('format Error')
        sigName = tokens[0].strip()
        unitName = tokens[1].strip()
        if signalName == sigName and (unit is None or unitName == unit):
            pLines = pLines + 1
            continue
        newData.append(line)
    fw = open(instructionPath, 'w')
    fw.writelines(newData)
    fw.close()
    unitStr = '*'
    if unit is not None:
        unitStr = unit
    log_cmd('Run config_rm_unit on [%s, %s]. deleted %d lines'%(signalName, unitStr, pLines))

def config_set_default(signalName, unit, res, ignore, factor, final_factor, suuposeMean = None):
    cfg = Configuration()
    instructionPath= os.path.join(fixOS(cfg.code_folder), 'Instructions.txt')
    fo = open(instructionPath, 'r')
    lines = fo.readlines()
    fo.close()
    supportedRes = ['1', '0.1', '0.01']
    if (supportedRes.count(res) ==0):
        raise NameError('resulotion is not supported. got %s'%res)
    if final_factor is not None and type(final_factor) == str and len(final_factor) > 0:
        try:
            float(final_factor)
        except:
            eprint('final_factor is not legal number')
            raise
    if  final_factor is not None and type(final_factor) == float:
        final_factor = str(final_factor)
    if final_factor is None:
        final_factor = ''
    ignoreStr = ''
    if ignore is not None and len(ignore) > 0:
        ignoreStr = ','.join(ignore)
    factorsStr = ''
    if factor is not None and len(factor) > 0:
        factorsStr = ','.join(map(str,factor))
    suuposeMeanStr = ''
    if suuposeMean is not None:
        suuposeMeanStr = str(suuposeMean)

    newData = [lines[0]] #take header
    lines = lines[1:]
    found = False
    for line in lines:
        tokens=line.strip().split('\t')
        if len(tokens) < 2:
            raise NameError('format Error')
        sigName = tokens[0].strip()
        if signalName == sigName:
            if found == True: #multipal lines for same signal
                continue
            line = '%s\t%s\t%s\t%s\t%s\t%s\t%s\n'%(signalName, unit, res, ignoreStr, factorsStr, final_factor,suuposeMeanStr)
            found = True
        newData.append(line)
    if not(found):
        if not(newData[-1].endswith('\n') or newData[-1].endswith('\r')):
            newData[-1] = newData[-1] + '\n'
        line = '%s\t%s\t%s\t%s\t%s\t%s\t%s\n'%(signalName, unit, res, ignoreStr, factorsStr, final_factor,suuposeMeanStr)
        newData.append(line)
    fw = open(instructionPath, 'w')
    fw.writelines(newData)
    fw.close()
    log_cmd('Run config_set_deafult with [%s, %s, %s, %s, %s, %s, %s]'%(signalName, unit, res, ignore, factor, final_factor, suuposeMeanStr))

def config_rm_default(signalName):
    cfg = Configuration()
    instructionPath= os.path.join(fixOS(cfg.code_folder), 'Instructions.txt')
    fo = open(instructionPath, 'r')
    lines = fo.readlines()
    fo.close()

    newData = [lines[0]] #take header
    lines = lines[1:]
    for line in lines:
        tokens=line.strip().split('\t')
        if len(tokens) < 2:
            raise NameError('format Error')
        sigName = tokens[0].strip()
        if signalName == sigName:
            continue
        newData.append(line)
    fw = open(instructionPath, 'w')
    fw.writelines(newData)
    fw.close()
    log_cmd('Run config_rm_deafult on %s'%(signalName))

def config_get_default(signalName):
    cfg = Configuration()
    instructionPath= os.path.join(fixOS(cfg.code_folder), 'Instructions.txt')
    fo = open(instructionPath, 'r')
    lines = fo.readlines()
    fo.close()

    lines = lines[1:]
    res = []
    for line in lines:
        tokens=line.strip().split('\t')
        if len(tokens) < 2:
            raise NameError('format Error')
        sigName = tokens[0].strip()
        if signalName == sigName:
            res = [''] * 8 #ido add TrimMax
            for i in range(len(tokens)):
                res[i] = tokens[i].strip('"')
            break
    return res

def config_get_unit(signalName, unitName):
    cfg = Configuration()
    instructionPath= os.path.join(fixOS(cfg.code_folder), 'unitTranslator.txt')
    fo = open(instructionPath, 'r')
    lines = fo.readlines()
    fo.close()

    res = ''
    for line in lines:
        tokens=line.strip().split('\t')
        if len(tokens) != 3:
            raise NameError('format Error')
        sigName = tokens[0].strip()
        unit = tokens[1].strip()
        if signalName == sigName and unit == unitName:
            res = tokens[2].strip()
            break
    return res
    
    
