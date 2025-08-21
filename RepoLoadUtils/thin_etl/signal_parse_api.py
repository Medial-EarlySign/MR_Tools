from Configuration import Configuration
from common import *
import os, re, random
from multiprocessing import Pool

def getLines(basePath, fileName):
    fileP = os.path.join(basePath, fileName)
    fp = open(fileP, 'r')
    lines = fp.readlines()
    lines = filter(lambda x: len(x.strip()) > 0 ,lines)
    fp.close()
    return lines

def createDirs(pth):
    if not(os.path.exists(pth)):
        os.makedirs(pth)

def parseFile(args):
    in_file_name, aggBy, ahd_read_codes, ahd_codes, signalRawPath = args
    stats= { 'bad_flag' :0 , 'med_code': 0,  'ahd_code': 0}
    numLines = 0
    pracid = in_file_name[-5:]
    allCodes = [dict() for i in range(6)]
    eprint('parsing %s'%pracid)
    fp = open(in_file_name, 'r')
    l = fp.readline()
    while (l is not None and len(l) > 0):
        patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
        data = [data1, data2, data3, data4, data5, data6]
        if ahdflag != 'Y':
            stats['bad_flag'] += 1
            l = fp.readline()
            numLines += 1
            continue
        if (medcode not in ahd_read_codes) and not(aggBy == 'ahdcode'): #irelavent when agg by ahdcode
            stats['med_code'] += 1
            l = fp.readline()
            numLines += 1
            continue
        if (ahdcode not in ahd_codes) and not(aggBy == 'medcode'):
            stats['ahd_code'] += 1
            l = fp.readline()
            numLines += 1
            continue
        code = ahdcode
        codeName = ''
        if aggBy == 'medcode':
            code = medcode
            codeName = ahd_read_codes[code]
        elif aggBy == 'ahdcode':
            codeName = ahd_codes[code]['desc']
        else:
            raise NameError('bug %s'%aggBy)

        for dataChoose in range(6):
            codeLines = allCodes[dataChoose]
            if codeLines.get(code) is None:
                codeLines[code] = []
            #lin = '%d\t%s\t%s\n'%(dataChoose+1, codeName ,data[dataChoose])
            lin = '%s\n'%(data[dataChoose])
            codeLines[code].append(lin)
            
        l = fp.readline()
        numLines += 1
    fp.close()
    #write buffer lines to files
    for i in range(len(allCodes)):
        currBPath = os.path.join(signalRawPath, 'data%d'%(i+1))
        #print('data%d, dict_size=%d'%(i+1, len(allCodes[i])))
        createDirs(currBPath)
        for code,lines in allCodes[i].items():
            fileName = os.path.join(currBPath, '%s.txt'%code)
            fw = open(fileName, 'a')
            fw.writelines(lines)
            fw.close()

def parseAllSignal(aggBy = 'ahdcode', specifyAhd = None):
    cfg = Configuration()
    raw_dir = fixOS(cfg.raw_source_path)
    doc_path = fixOS(cfg.doc_source_path)
    work_dir = fixOS(cfg.work_path)
    
    if not(os.path.exists(raw_dir)):
        raise NameError('config error - raw dir wasn''t found')
    if not(os.path.exists(doc_path)):
        raise NameError('config error - doc dir wasn''t found')
    if not(os.path.exists(work_dir)):
        raise NameError('config error - work dir wasn''t found')
    if aggBy not in ['medcode', 'ahdcode']:
        raise NameError('aggBy must be medCode or ahdcode got %s'%aggBy)

    signalRawPath = os.path.join(work_dir, 'SignalRaw', aggBy)
    createDirs(signalRawPath)
    ahd_code_name = list(filter(lambda f: f.startswith('AHDCodes') ,os.listdir(doc_path)))
    if len(ahd_code_name) != 1:
        raise NameError('coudn''t find AHDCodes')
    ahd_code_name = ahd_code_name[0]
    readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(doc_path)))
    if len(readcodes_name) != 1:
        raise NameError('coudn''t find readcodes_name')
    readcodes_name = readcodes_name[0]

    lines = getLines(doc_path, ahd_code_name)
    ahd_codes = read_ahd_codes_full(lines)
    lines = getLines(doc_path, readcodes_name)
    ahd_read_codes = read_ahd_read_codes(lines)

    filterRe = re.compile('ahd\..*')
    if specifyAhd is not None:
        filterRe = re.compile(specifyAhd)
        
    in_file_names = os.listdir(raw_dir)
    in_file_names = list(filter( lambda x: filterRe.match(x) is not None,  in_file_names))
    in_file_names = list(map(lambda p : os.path.join(raw_dir ,p) ,in_file_names))
    eprint("about to process", len(in_file_names), "files")
    all_args = list(map(lambda x: [x, aggBy, ahd_read_codes, ahd_codes, signalRawPath],in_file_names))
    
    p = Pool(30)
    p.map(parseFile, all_args)
    p.close()    
    #for in_file_name in in_file_names:
    #    parseFile([in_file_name, aggBy, ahd_read_codes, ahd_codes, signalRawPath])

def getStatsForCodefile(ahd_codes, fw, codePath):
    if not(os.path.exists(codePath)):
        raise NameError('file not found')
    cfg = Configuration() 
    fp = open(codePath, 'r')
    l = fp.readline()
    vals = []
    ahdOrMed = os.path.basename( os.path.dirname(os.path.dirname(codePath)))
    dataNum = os.path.basename( os.path.dirname(codePath))
    code = os.path.basename(codePath)[:-4]
    if type(ahd_codes[code]) == dict:
        signalDesc = ahd_codes[code][dataNum]
    else:
        signalDesc = ahd_codes[code]
    if len(signalDesc.strip()) == 0:
        signalDesc = '<empty string>'
    while (l is not None and len(l) > 0):
        val = l.strip()
        vals.append(val)
        l = fp.readline()
    fp.close()

    valType = 'SINGLE_VALUE'
    sampleSize = 10000
    if len(set(vals)) == 1:
        #comment = 'all_same_value %s'%vals[0]
        v = vals[0]
        if len(v.strip()):
            v = '<empty string>'
        top_5Vals = v
        hVals = [vals[0]]
    else:
        hVals = hist(vals)
        hVals = sorted(hVals.items(), key = lambda kv: kv[1], reverse = True)
        top_5Vals = ', '.join(map(lambda kv: '%s_%d(%2.2f)'%(kv[0], kv[1], 100.0*kv[1] / float(len(vals))) ,hVals[:5]))
        #choose random 1000 and see if it's a  number
        cnt =0
        outOff = 0
        if sampleSize < len(hVals):
            for i in range(sampleSize):
                ind = random.randint(0,len(vals)-1)
                if len(vals[ind].strip()) > 0:
                    cnt += int(is_number(vals[ind]))
                    outOff += 1
        else:
            for i in range(len(hVals)):
                if len(hVals[i][0].strip()) > 0:
                    cnt += int(is_number(hVals[i][0]))*hVals[i][1]
                    outOff += hVals[i][1]
            #print('%d / %d'%(cnt, outOff))
        if outOff  > 0:
            score = cnt/ float(outOff)
        else:
            score = None
        if score is not None and score < 0.8:
            valType= 'string'
        elif score is not None and score >= 0.8:
            valType = 'numeric'
        else:
            valType = 'NULL_VALUE'
        #comment = 'type=%s, top_5_vals=[%s], tot_unique_vals=%d, total_numer=%d'%(valType, top_5Vals, len(hVals), len(vals))
    #analyze what is vals - numeric? has multiple values?
    #TODO print to csv for all files
    
    fw.write('%s\t%s\t%s\t%s\t%s\t%d\t%d\t[%s]\n'%(ahdOrMed, code,dataNum, signalDesc, valType, len(hVals), len(vals), top_5Vals))
    #print('Signal %s_%s in column %s(%s) has %s values'%(ahdOrMed, code, dataNum, signalDesc, comment))
    
def analyzeAllAhdCodes(rangeFolders = range(1,7), aggBy = 'ahdcode'):
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    ahd_code_name = list(filter(lambda f: f.startswith('AHDCodes') ,os.listdir(doc_path)))
    if len(ahd_code_name) != 1:
        raise NameError('coudn''t find AHDCodes')
    ahd_code_name = ahd_code_name[0]
    readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(doc_path)))
    if len(readcodes_name) != 1:
        raise NameError('coudn''t find readcodes_name')
    readcodes_name = readcodes_name[0]

    if aggBy == 'ahdcode':
        lines = getLines(doc_path, ahd_code_name)
        ahd_codes = read_ahd_codes_full(lines)
    elif aggBy == 'medcode':
        lines = getLines(doc_path, readcodes_name)
        ahd_codes = read_ahd_read_codes(lines)
    else:
        raise NameError('Unsupported code')
    
    basePath = os.path.join(fixOS(cfg.work_path), 'SignalRaw')
    if aggBy == 'ahdcode':
        statsPath = os.path.join(basePath, 'ahdcode.stats')
    else:
        statsPath = os.path.join(basePath, 'medcode.stats')
    fw = open(statsPath, 'w')
    fw.write('code_type\tcode\tcolumn_name\tcolumn_description\ttype\tunique_cnt\ttotal_cnt\ttop5Vals\n')
    fw.close()
    for i in rangeFolders:
        fld = 'data%d'%i
        if aggBy == 'ahdcode':
            dataPath = os.path.join(basePath, 'ahdcode' ,fld)
        else:
            dataPath = os.path.join(basePath, 'medcode' ,fld)
        allCodeFiles = os.listdir(dataPath)
        allCodeFiles = list(map(lambda x:  os.path.join(dataPath ,x) ,allCodeFiles))
        print('Analyzing all codds in folder %s have %d files to proccess'%(fld, len(allCodeFiles)))
        ii = 0
        for input_file in allCodeFiles:
            ii += 1
            fw = open(statsPath, 'a')
            getStatsForCodefile(ahd_codes, fw, input_file)
            fw.close()
            print('done analyzing %s  - %d / %d(%2.2f%%)'%(os.path.basename(input_file),  ii, len(allCodeFiles), 100.0 * float(ii) / len(allCodeFiles) ))

def addAhdCodeNames(aggBy = 'ahdcode'):
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    ahd_code_name = list(filter(lambda f: f.startswith('AHDCodes') ,os.listdir(doc_path)))
    if len(ahd_code_name) != 1:
        raise NameError('coudn''t find AHDCodes')
    ahd_code_name = ahd_code_name[0]
    readcodes_name = list(filter(lambda f: f.startswith('Readcodes') ,os.listdir(doc_path)))
    if len(readcodes_name) != 1:
        raise NameError('coudn''t find readcodes_name')
    readcodes_name = readcodes_name[0]
    
    if aggBy == 'ahdcode':
        lines = getLines(doc_path, ahd_code_name)
        ahd_codes = read_ahd_codes_full(lines)
    elif aggBy == 'medcode':
        lines = getLines(doc_path, readcodes_name)
        ahd_codes = read_ahd_read_codes(lines)
    else:
        raise NameError('Unsupported code')    

    basePath = os.path.join(fixOS(cfg.work_path), 'SignalRaw')
    if aggBy == 'ahdcode':
        statsPath = os.path.join(basePath, 'ahdcode.stats')
        statsPath2 = os.path.join(basePath, 'ahdcode.final.stats')
    else:
        statsPath = os.path.join(basePath, 'medcode.stats')
        statsPath2 = os.path.join(basePath, 'medcode.final.stats')
    
    fr = open(statsPath, 'r')
    lines = fr.readlines()
    fr.close()
    #rewrite header
    header = lines[0]
    header = '%s\t%s\t%s\n'%( header.strip(), 'ahd_name', 'data_file')
    newData = [header]
    lines = lines[1:]
    
    for line in lines:
        if len(line.strip()) == 0:
            newData.append(line)
            continue
        tokens = line.strip().split('\t')
        if len(tokens)  < 3:
            raise NameError('bad format')
        code = tokens[1].strip()
        if aggBy == 'ahdcode':
            codeName = ahd_codes[code]['desc']
            dataFile = ahd_codes[code]['datafile']
        else:
            codeName = ahd_codes[code]
            dataFile = 'ReadCode'
        line = '%s\t%s\t%s\n'%( line.strip(), codeName, dataFile)
        newData.append(line)

    fw = open(statsPath2, 'w')
    fw.writelines(newData)
    fw.close()
   
if __name__ == "__main__":
    #analyzeAllAhdCodes()
    addAhdCodeNames()
    """
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    lines = getLines(doc_path, 'AHDCodes1601.txt')
    ahd_codes = read_ahd_codes_full(lines)
    basePath = os.path.join(fixOS(cfg.work_path), 'SignalRaw')
    statsPath = os.path.join(basePath, 'ahdcode.stats')
    fw = open(statsPath, 'w')
    fw.write('code_type\tcode\tcolumn_name\tcolumn_description\ttype\tunique_cnt\ttotal_cnt\ttop5Vals\n')
    getStatsForCodefile(ahd_codes, fw, os.path.join(basePath, 'ahdcode', 'data1', '1002080700.txt'))
    fw.close()
    """
    #parseAllSignal(aggBy = 'ahdcode')
    #parseAllSignal(aggBy = 'medcode')