import os, io, re, pickle
from common import *
from Configuration import Configuration

def getAllFiles():
    cfg = Configuration()
    signal_list_file = os.path.join(fixOS(cfg.code_folder), 'thin_signals_to_united.txt')
    if not(os.path.exists(signal_list_file)):
        raise NameError('signal list path not exists')
    f = open(signal_list_file, 'r')
    allLines = f.readlines()
    f.close()
    allLines = list(filter(lambda x: len(x.strip()) > 0, allLines))
    allLines = allLines[1:]
    sourceList = list()
    for line in allLines:
        tokens=line.strip().split('\t')
        if len(tokens) != 2:
            raise NameError('read format error')
        trg = tokens[1].strip()
        src = tokens[0].strip()
        if trg == 'NULL' or trg == 'TBD':
            continue
        sourceList.append(src)
    return sourceList


def getReadCodes():
    cfg = Configuration()
    f = open(os.path.join(fixOS(cfg.doc_source_path), 'Readcodes1601.txt'), 'r')
    allLines = f.readlines()
    f.close()
    res= dict()
    tps = list(map(lambda x: [x[:7].strip(), x[7:].strip()] ,allLines))
    for k,v in tps:
        res[k] = v
    return res

def print_numeric_readCodes():
    srcs = getAllFiles()
    readCodes = getReadCodes()
    allTokens =list(map(lambda x: x.split('-')[-2] ,srcs))
    codes = list(map(lambda x: x.split('_')[0].strip() ,allTokens))
    codes = list(filter(lambda x: len(x) >0,codes))
    #descs = list(map(lambda x: '_'.join(x.split('_')[1:]) ,allTokens))
    #allAhds =list(map(lambda x: x[ x.rfind('-')+1:] ,srcs))
    #uAhds = list(set(allAhds))
    cds = set(codes)
    cds.add('4425.00')
    cds.add('442U.00')
    cds = list(cds)
    res = list(map( lambda x: '%s\t-\t%s'%(x, readCodes[x] if readCodes.get(x) is not None else 'Not Found' ),cds))

    fw = io.open(r'W:\Users\Alon\thin_codes.txt', 'w', newline = '')
    fw.writelines(list(map(lambda l: l + '\n' ,res)))
    fw.close()
    #list(filter(lambda x: len(descs[x].strip()) == 0,range(len(descs))))
    #4425.00_Free_Tri-iodothyronine
    #442U.00_Free_Tri-iodothyronine

def ahdcode2readcode(specifyAhd = None):
    cfg = Configuration()
    data_path = fixOS(cfg.raw_source_path)
    filterRe = re.compile('ahd\..*')
    if specifyAhd is not None:
        filterRe = re.compile(specifyAhd)
    in_file_names = os.listdir(data_path)
    in_file_names = list(filter( lambda x: filterRe.match(x) is not None,  in_file_names))
    in_file_names = list(map(lambda p : os.path.join(data_path ,p) ,in_file_names))
    print("about to process", len(in_file_names), "files")
    ahd2med = dict()
    ii = 0
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        fp = open(in_file_name, 'r')
        l = fp.readline()
        while (l is not None and len(l) > 0):
            patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
            if ahd2med.get(ahdcode) is None:
                ahd2med[ahdcode] = dict()
            if ahd2med[ahdcode].get(medcode) is None:
                ahd2med[ahdcode][medcode] = 0
            ahd2med[ahdcode][medcode] = ahd2med[ahdcode][medcode] + 1
            l = fp.readline()
        fp.close()
        ii = ii + 1
        print("processed ", pracid, " (", ii, "/", len(in_file_names), ")")
    return ahd2med

def writeDictionary():
    #ahd2med = ahdcode2readcode('ahd\.a6641')
    ahd2med = ahdcode2readcode()
    objStr = pickle.dumps(ahd2med)
    fp = open('ahd2readcodes_dictionary.pkl', 'wb')
    fp.write(objStr)
    fp.close()

def loadDictionary():
    fp = open('ahd2readcodes_dictionary.pkl', 'rb')
    strObj = fp.read()
    fp.close()
    ahd2med = pickle.loads(strObj)
    return ahd2med

def showAhd(ahdcode, prt = True):
    ahd2med = loadDictionary()
    readCodes = getReadCodes()
    if ahd2med.get(ahdcode) is None:
        return None
    d = ahd2med[ahdcode]
    tups = sorted(list(map(lambda kv : [kv[0], kv[1], readCodes[kv[0]] if readCodes.get(kv[0]) is not None else ''] ,d.items())), key = lambda kv: kv[1], reverse = True)
    if prt:
        for kv in tups:
            print('%s - %s - %d'%(kv[0], kv[2], kv[1]))
    return tups

def convertAllAhds(topTake = 100):
    fp = open(r'W:\Users\Alon\other_signal codes.txt', 'r')
    lines = fp.readlines()
    fp.close()
    lines = list(filter(lambda line: len(line.strip()) > 0 , lines))
    ahd2med = loadDictionary()
    readCodes = getReadCodes()
    fw = open(r'W:\Users\Alon\other_signal readcodes.txt', 'w')
    fw.close()
    fw = open(r'W:\Users\Alon\other_signal readcodes.txt', 'a')
    for line in lines:
        ahdcode = re.split('\s', line)[0]
        description = line[len(ahdcode):].strip()
        if ahd2med.get(ahdcode) is None:
            d = dict()
        else:
            d = ahd2med[ahdcode]
        tups = sorted(list(map(lambda kv : [kv[0], kv[1], readCodes[kv[0]] if readCodes.get(kv[0]) is not None else ''] ,d.items())), key = lambda kv: kv[1], reverse = True)
        tups = list(filter(lambda t: t[1] >= topTake ,tups))
        if len(tups) == 0:
            eprint('coudn''t find for %s'%ahdcode)
            tups = [['', 0, 'Warning not readcode found']]
        allLines = list(map(lambda t: '%s\t%s\t%s\t%s\t%d\n'%(ahdcode, description, t[0], t[2], t[1]) ,tups))
        fw.writelines(allLines)
    fw.close()

if __name__ == '__main__':
    #writeDictionary()
    showAhd('1002010111')
    #convertAllAhds()