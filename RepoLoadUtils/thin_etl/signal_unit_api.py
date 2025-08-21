from common import *
from Configuration import Configuration
from signal_stats_api import statsUnitedSig, statsFixedSig, getSignalUnitRes, getSignalByUnit
from signal_config_api import *

def ignoreRareUnits(signalName, sampleCnt, percentageCnt):
    if sampleCnt is None and percentageCnt is None:
        raise NameError('invalid args - percentageCnt or sampleCnt must be not null')
    unit_instruction = read_instructions(False)
    if (unit_instruction.get(signalName) is None):
        raise NameError('Couldn''t find current config')

    ahd_lookup = get_ahd_lookup()
    unit_dict_translator =unit_instruction[signalName]
    unitDict = getSignalByUnit(signalName, ahd_lookup)
    unitCnt = list(map( lambda kv: [kv[0], len(kv[1])] ,unitDict.items()))
    totCnt = sum(list(map(lambda kv: kv[1],unitCnt)))
    
    ignoreList = unit_dict_translator['ignore']
    for unitName,cnt in unitCnt:
        if len(unitName.strip()) == 0:
            continue
        if not((sampleCnt is None or cnt > sampleCnt) and (percentageCnt is None or (cnt/totCnt) > percentageCnt)):
            ignoreList.add(unitName) #filter unit

    resolution = unit_dict_translator['resolution']
    if resolution == "{:.0f}":
        resolution = "1"
    elif resolution == "{:.1f}":
        resolution = "0.1"
    elif resolution == "{:.2f}":
        resolution = "0.01"
    suuposeMean = unit_dict_translator['supposeMean']
    config_set_default(signalName, unit_dict_translator['base_unit'], resolution , ignoreList, unit_dict_translator['factors'], unit_dict_translator['final_factor'], suuposeMean)

def clearSupportUnits(signalName, unitStats):
    supported = supportedFormatList(signalName)
    if type(unitStats) == list:
        filtered = []
        for tp in unitStats:
            if supported.get(tp[0]) is None:
                filtered.append(tp[0])
        return filtered
    elif type(unitStats) == dict:
        filtered = dict()
        for unitName,val in unitStats.items():
            if supported.get(unitName) is None:
                filtered[unitName] = val
        return filtered

def compareUnitHist(signalName, vec_unit, removeTh = None):
    ahd_lookup = get_ahd_lookup()
    unitDict = getSignalByUnit(signalName, ahd_lookup)
    found_all = True
    i = 0
    while (found_all and i < len(vec_unit)):
        found_all = unitDict.get(vec_unit[i]) is not None
        i = i +1
    if not(found_all):
        raise NameError('missing unit in dict')
    vec_vector = []
    for unit_name in vec_unit:
        unit_vals = unitDict[unit_name]
        conv = config_get_unit(signalName, unit_name)
        if len(conv) > 0:
            unit_vals = translate(unit_vals, conv)
        vec_vector.append(unit_vals)
    return compareAllHists(vec_vector, signalName + '_units', vec_unit, removeTh)

def saveUnitsForSignal(signalName):
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    if not(os.path.exists(work_dir)):
        raise NameError('cfg error - work dir not found')
    warningMsgs, unitStat = statsUnitedSig(signalName, None, True)
    unit_stats_file= os.path.join(work_dir, 'signal_units.stats')
    lines = []
    if os.path.exists(unit_stats_file):
        fp = open(unit_stats_file, 'r')
        lines = fp.readlines()
        fp.close()
    lines =list(filter(lambda l: len(l.strip()) > 0 ,lines))
    #change or add lines in format: [signalName \t unitName \t Count \t perc_01_val \t perc_99_val \t avg_val]
    newData = []
    for line in lines:
        tokens = line.split('\t')
        if len(tokens) != 6:
            raise NameError('file format error')
        sigName = tokens[0].strip()
        if sigName == signalName:
            continue
        newData.append(line)
    #add current signal units:
    for unitName, unitCnt in unitStat:
        line = '%s\t%s\t%d\t%4.4f\t%4.4f\t%4.4f\n'%(signalName, unitName, unitCnt, 0 ,0 ,0) #not supported yet
        newData.append(line)

    fw = open(unit_stats_file, 'w')
    fw.writelines(newData)
    fw.close()

def getUnitStatsForSignal(signalName, onlyFast = False):
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    if not(os.path.exists(work_dir)):
        raise NameError('cfg error - work dir not found')
    unit_stats_file= os.path.join(work_dir, 'signal_units.stats')
    lines = []
    if os.path.exists(unit_stats_file):
        fp = open(unit_stats_file, 'r')
        lines = fp.readlines()
        fp.close()
    lines =list(filter(lambda l: len(l.strip()) > 0 ,lines))
    unitStats = []
    ahd_lookup = get_ahd_lookup()
    for line in lines:
        tokens = line.split('\t')
        if len(tokens) != 6:
            raise NameError('file format error')
        sigName = tokens[0].strip()
        if sigName == signalName:
            unit_name = tokens[1].strip()
            if ahd_lookup.get(unit_name) is not None:
                unit_name = ahd_lookup[unit_name]
            unitStats.append( [ unit_name , int(tokens[2])  ] )
    if len(unitStats) > 0 or onlyFast:
        unitStats = sorted(unitStats, key = lambda kv: kv[1], reverse = True)
        return unitStats
    else:
        saveUnitsForSignal(signalName)
        #warningMsgs, unitStats = statsUnitedSig(signalName, None, True)
    fp = open(unit_stats_file, 'r')
    lines = fp.readlines()
    fp.close()
    
    for line in lines:
        tokens = line.split('\t')
        if len(tokens) != 6:
            raise NameError('file format error')
        sigName = tokens[0].strip()
        if sigName == signalName:
            unit_name = tokens[1].strip()
            if ahd_lookup.get(unit_name) is not None:
                unit_name = ahd_lookup[unit_name]
            unitStats.append( [ unit_name , int(tokens[2])  ] )

    unitStats = sorted(unitStats, key = lambda kv: kv[1], reverse = True)
    
    return unitStats

def addAllWithFactor(signalName, vec_unit_names, factor = '1'):
    for unitName in vec_unit_names:
        config_set_unit(signalName, unitName, factor)
    