from Configuration import Configuration
from common import *
import os, re, io,shutil
#handle 5 missing numeric signals form clinical with NUM_RESULTS column :  asthma, CHS - not for now
#TODO: handle all speicial signals

def getLines(basePath, fileName):
    fileP = os.path.join(basePath, fileName)
    fp = open(fileP, 'r')
    lines = fp.readlines()
    lines = list(filter(lambda x: len(x.strip()) > 0 ,lines))
    fp.close()
    return lines

def createDirs(pth, deleteBefore = False):
    if deleteBefore and os.path.exists(pth):
        shutil.rmtree(pth)
    if not(os.path.exists(pth)):
        os.makedirs(pth)

def load_parsing_config():
    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    if not(os.path.exists(code_folder)):
        raise NameError('config error - code folder not exists')
    
    lines = getLines(code_folder, 'special_signals_config.txt')
    data = lines[1:]
    res = dict()
    for line in data:
        tokens = line.split('\t')
        if len(tokens) != 6:
            raise NameError('bad format')
        data_file = tokens[0].strip()
        ahdcode = tokens[1].strip()
        column_num = tokens[3].strip()
        ahdname = tokens[2].strip()
        column_name = tokens[4].strip()
        row = {'data_file': data_file, 'column_num': column_num, 'ahdname': ahdname, 'column_name': column_name}
        res[ahdcode] = row
    return res

def loadAllSpecialSignals(specifyAhd = None):
    signals_config = load_parsing_config()
    
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

    lines = getLines(work_dir, 'ID2NR')
    id2nr = read_id2nr(lines)
    
    filterRe = re.compile('ahd\..*')
    if specifyAhd is not None:
        filterRe = re.compile(specifyAhd)
    outPath = os.path.join(work_dir, 'SpecialSignals')
    createDirs(outPath, True)

    #clear stats file:
    fw = open(os.path.join(work_dir, 'Stats', 'special_all.stats'), 'w')
    fw.close()
    #end

    in_file_names = os.listdir(raw_dir)
    in_file_names = list(filter( lambda x: filterRe.match(x) is not None,  in_file_names))
    in_file_names = list(map(lambda p : os.path.join(raw_dir ,p) ,in_file_names))
    eprint("about to process", len(in_file_names), "files")
    for in_file_name in in_file_names:
        pracid = in_file_name[-5:]
        fp = open(in_file_name, 'r')
        l = fp.readline()
        numLines = 0
        stats = {"unknown_id": 0, "bad_ahdflag": 0, "not_special":0}
        signalLines = dict()
        while (l is not None and len(l) > 0):
            patid, eventdate, ahdcode, ahdflag, data1, data2, data3, data4, data5, data6, medcode = parse_ahd_line(l)
            data = [data1, data2, data3, data4, data5, data6]
            combid = pracid + patid
            if ahdflag != 'Y':
                l = fp.readline()
                stats['bad_ahdflag'] += 1
                numLines += 1
                continue
            if combid not in id2nr:
                l = fp.readline()
                stats["unknown_id"] += 1
                numLines += 1
                continue
            if signals_config.get(ahdcode) is None: # not special signal
                l = fp.readline()
                stats["not_special"] += 1
                numLines += 1
                continue
            ourId = id2nr[combid]
            sig_cfg = signals_config[ahdcode]
            dataInd = int(sig_cfg['column_num'][4:])-1
            val = data[dataInd]
            if len(val.strip()) == 0:
                val = 'EMPTY_THIN_FIELD'
            signalName = sig_cfg['ahdname'].strip()
            if sig_cfg['column_name'] != 'QUALIFIER':
                signalName = '%s_%s'%(sig_cfg['ahdname'], sig_cfg['column_name'].replace('QUALIFIER', ''))
            signalName = signalName.replace(' ', '_')
            
            if signalLines.get(ahdcode) is None:
                signalLines[ahdcode] = []
            row = unicode('%d\t%s\t%s\t%s\n'%(ourId, signalName ,eventdate, val))
            signalLines[ahdcode].append(row)
            
            l = fp.readline()
            numLines += 1 
                
        fp.close()
        fw = open(os.path.join(work_dir, 'Stats', 'special_all.stats'), 'a')
        fw.write( '%s\t%d\t%d\t%d\t%d\n'%(pracid, stats['unknown_id'], stats['bad_ahdflag'] ,stats["not_special"], numLines))
        fw.close()
        for ahdcode, lines in signalLines.items():
            fw = io.open(os.path.join(outPath, '%s.txt'%ahdcode), 'a', newline = '')
            fw.writelines(lines)
            fw.close()
        #TODO: need to sort values!

def sortValues(specificFile = None):
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    if not(os.path.exists(work_dir)):
        raise NameError('config error - work dir wasn''t found')
    signalPath = os.path.join(work_dir, 'SpecialSignals')
    if not(os.path.exists(signalPath)):
        raise NameError('config error - signalPath dir wasn''t found')
    allFiles = os.listdir(signalPath)
    ii = 0
    for f in allFiles:
        if specificFile is not None and f != specificFile:
            continue
        fullPath = os.path.join(signalPath, f)
        fp = open(fullPath, 'r')
        newlines = []
        line = fp.readline()
        while (line is not None and len(line) > 0):
            if len(line.strip()) == 0:
                line = fp.readline()
                continue
            newlines.append(unicode(line))
            line = fp.readline()
        fp.close()
        newlines.sort(key = lambda l:[ int(l.split('\t')[0]), l.split('\t')[2] ] )
        fw = io.open(fullPath, 'w', newline = '')
        fw.writelines(newlines)
        fw.close()
        ii += 1
        print('Done %d / %d'%(ii, len(allFiles)))
        
def cleanNotFoundKeys():
    cfg = Configuration()
    work_dir = fixOS(cfg.work_path)
    doc_path = fixOS(cfg.doc_source_path)
    if not(os.path.exists(work_dir)):
        raise NameError('config error - work dir wasn''t found')
    if not(os.path.exists(doc_path)):
        raise NameError('config error - doc dir wasn''t found')
    ahd_lookup_name = list(filter(lambda f: f.startswith('AHDlookup') ,os.listdir(doc_path)))
    if len(ahd_lookup_name) != 1:
        raise NameError('coudn''t find AHDlookup')
    ahd_lookup_name = ahd_lookup_name[0]
    ahd_path = os.path.join(doc_path, ahd_lookup_name)
    if not(os.path.exists(ahd_path)):
        raise NameError('ahd_lookup file wan''t found')

    readCodesignals = ['Cervical', 'Family_History', 'Scoring_test_result', 'Allergy_over_intolerance']
    fp = open(ahd_path)
    lines = fp.readlines()
    fp.close()
    lines = list(filter(lambda line: len(line.strip()) > 0 ,lines))
    codes = set(list(map(lambda line: line[38:44].strip() ,lines)))
    codes.add('EMPTY_THIN_FIELD')
    
    signalPath = os.path.join(work_dir, 'SpecialSignals')
    if not(os.path.exists(signalPath)):
        raise NameError('config error - signalPath dir wasn''t found')
    allFiles = os.listdir(signalPath)
    ii = 0
    for f in allFiles:
        if f in readCodesignals:
            continue
        skippedCode = dict()
        fullPath = os.path.join(signalPath, f)
        fp = open(fullPath, 'r')
        newlines = []
        line = fp.readline()
        while (line is not None and len(line) > 0):
            if len(line.strip()) == 0:
                line = fp.readline()
                continue
            tokens = line.split('\t')
            if len(tokens) !=4:
                raise NameError('bad format')
            val = tokens[3].strip()
            if val not in codes:
                if skippedCode.get(val) is None:
                    skippedCode[val] = 0
                skippedCode[val] += 1
                line = fp.readline()
                continue
            newlines.append(unicode(line))
            line = fp.readline()
        fp.close()
        for val, cnt in skippedCode.items():
            eprint('Recieved unkown key "%s" in file "%s" %d time- skipping...'%(val ,f, cnt))
        newlines.sort()
        fw = io.open(fullPath, 'w', newline = '')
        fw.writelines(newlines)
        fw.close()
        ii += 1
        print('Done %d / %d'%(ii, len(allFiles)))

if __name__ == "__main__":
    loadAllSpecialSignals()
    print('cleaning not found keys...')
    cleanNotFoundKeys()
    print('sorting..')
    sortValues()