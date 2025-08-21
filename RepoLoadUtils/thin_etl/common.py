from __future__ import print_function
from collections import defaultdict
from datetime import datetime
from Configuration import Configuration
import sys, os, math, random, socket, time
#from scipy.stats.mstats import normaltest
from numpy import histogram
from bin_selections import binSelection, binarySearch, histRange
import traceback, subprocess
from scipy import stats

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def getLines(basePath, fileName):
    fileP = os.path.join(basePath, fileName)
    fp = open(fileP, 'r')
    lines = fp.readlines()
    lines = filter(lambda x: len(x.strip()) > 0 ,lines)
    fp.close()
    return lines

def clean_and_strip(x):
    return x.strip()

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def get_ahd_lookup():
    cfg = Configuration()
    raw_path = fixOS(cfg.doc_source_path)
    ahd_lookup_name = list(filter(lambda f: f.startswith('AHDlookup') ,os.listdir(raw_path)))
    if len(ahd_lookup_name) != 1:
        raise NameError('coudn''t find AHDlookup')
    ahd_lookup_name = ahd_lookup_name[0]
    ahd_lookups = {'':'NA', '<None>':'<None>'}
    fp = open(os.path.join(raw_path, ahd_lookup_name), 'r')
    lines = fp.readlines()
    fp.close()
    for l in lines:
        dataname, datadesc, lookup, lookupdesc = \
        map(clean_and_strip, [l[0:8],l[8:38],l[38:44],l[44:144]])
        ahd_lookups[lookup]=lookupdesc
    return ahd_lookups

def translate(data, translator):
    if translator == "Formula1":
        return list(map(lambda x: 100.0/x if x != 0.0 else -1.0, data))
    if translator == "Formula2":
        return list(map(lambda x: 0.09148 * x + 2.152, data))
    if translator == "F2C":
        return list(map(lambda x: (x-32.0)*(5.0/9.0), data))

    eprint("before", data[:10])
    ret = list(map(lambda x: float(translator) * x, data))
    eprint("after", ret[:10])
    return ret

def write_stats(stats, section, err_file):
    for stat_name, stat_val in stats.items():
        if type(stat_val) is defaultdict:
            for k, v in stat_val.items():
                print("\t".join([section, stat_name, str(k), str(v)]), file=err_file)
            top_5 = sorted(stat_val.items(), key=lambda x: x[1], reverse=True)[:5]
            eprint(stat_name, len(stat_val), "entries, top 5 are:", top_5)
        else:
            eprint(stat_name, stat_val)
            print("\t".join([section, stat_name, "TOTAL", str(stat_val)]), file=err_file)
    
def read_id2nr(in_ID2NR_file):
    id2nr = {}
    eprint('reading ID2NR')
    for i, l in enumerate(in_ID2NR_file):
        if i % 1000000 == 0:
            eprint(i,)
        pat_id = l.split()[1]
        combid = l.split()[0]
        id2nr[combid] = int(pat_id)
    eprint("found", len(id2nr), "THIN to medial ID translations")
    return id2nr

def parse_medical_line(l):
    return map(clean_and_strip, \
    [l[0:4],l[4:12],l[12:20],l[20:22],l[22:29],\
    l[29:30],l[30:34],l[34:35], l[35:36], l[36:39],\
    l[39:41], l[41:48], l[48:49], l[49:50], l[50:51],\
    l[51:52], l[52:53], l[53:57], l[57:61], l[61:69], l[69:70]])    
    
def parse_ahd_line(l):
    return map(clean_and_strip, [l[0:4],l[4:12],l[12:22],l[22:23],l[23:36],\
    l[36:49],l[49:62],l[62:75],l[75:88],l[88:101], l[101:108]])

def read_ahd_codes(in_AHDCodes_file):    
    ahd_codes = {}
    for l in in_AHDCodes_file:
        datafile, ahdcode, desc, data1, data2, data3 = \
        map(clean_and_strip, [l[0:8],l[8:18],l[18:118],l[118:148],l[148:178],l[178:208]])
        ahd_codes[ahdcode] = {"desc": desc, "datafile": datafile, "data1": data1, "data2": data2, "data3": data3}
    eprint("found", len(ahd_codes), "AHD codes")
    return ahd_codes

def read_ahd_codes_full(in_AHDCodes_file):    
    ahd_codes = {}
    for l in in_AHDCodes_file:
        datafile, ahdcode, desc, data1, data2, data3, data4, data5, data6 = \
        map(clean_and_strip, [l[0:8],l[8:18],l[18:118],l[118:148],l[148:178],l[178:208], l[208:238], l[238:268], l[268:]])
        ahd_codes[ahdcode] = {"desc": desc, "datafile": datafile, "data1": data1, "data2": data2, "data3": data3, "data4": data4, "data5": data5, "data6": data6}
    return ahd_codes

def read_ahd_read_codes(in_AHDReadcodes_file):    
    ahd_read_codes = {}
    for l in in_AHDReadcodes_file:
        medcode, desc = \
        map(clean_and_strip, [l[0:7],l[7:67]])
        #print("\t".join([medcode, desc]))
        ahd_read_codes[medcode] = desc
    eprint("found", len(ahd_read_codes), "AHD read codes")
    return ahd_read_codes

def fixDate(dt, monthRes = True):
    dateLen = len(dt)
    dateFormat = '%Y'
    if dateLen > 4:
        dateFormat = '%Y%m%d'
    if ((dateLen > 4 and dt[-2:] =='00') or monthRes):
        dt = dt[:-2] + '01'
    if dt[4:6] == '00':
        dt = dt[:4] + '01' + dt[6:]
    return datetime.strptime(dt, dateFormat).toordinal()

def date2Num(vector, monthRes = True):
    if len(vector) == 0:
        return []
    return list(map( lambda v: fixDate(v) ,vector))

def num2Date(vector):
    if len(vector) == 0:
        return []
    dateFormat = '%d-%m-%Y'
    return list(map( lambda x: datetime.fromordinal(x).strftime(dateFormat) ,vector))

def read_instructions(prt = False):
    '''Instructions file per signal - how to translate'''
    cfg = Configuration()
    in_unit_instructions_file = open( os.path.join(fixOS(cfg.code_folder), 'Instructions.txt'), 'r' )
    unit_instruction = {}
    in_unit_instructions_file.readline()
    for l in in_unit_instructions_file.readlines():
        a = list(map(clean_and_strip, l.split('\t')))
        b = [None] * 9 # sometimes the instructions line is shorter/longer than 6
        for i,v in enumerate(a[:9]):
            b[i] = a[i]
        signal,unit,resolution,ignore,factors,final_factor,temp_name,supposeMean,trimMax = b
        if resolution == "1":
            resolution = "{:.0f}"
        elif resolution == "1.0":
            resolution = "{:.0f}"
        elif resolution == "0.1":
            resolution = "{:.1f}"
        elif resolution == "0.01":
            resolution = "{:.2f}"
        elif resolution in ["10.0", "10"]:
            resolution = "10.0"
        else:
            raise ValueError("unknown resolution: " + resolution)
        if final_factor is None or final_factor == '':
            final_factor = 1.0
        else:
            final_factor = float(final_factor)
        if ignore is not None:
            ignore = set(map(lambda un: un.strip('"') ,ignore.split(',')))
        else:
            ignore = set([])
        if factors is not None and len(factors.strip()) > 0:
            factors = list(map(float, factors.strip().split(',')))
        else:
            factors = []

        if supposeMean is not None and len(supposeMean) >0:
            try:
                supposeMean = float(supposeMean)
            except:
                print('in line %s\nsupposeMean=%s\n'%(l, supposeMean))
                raise
        if trimMax is not None and len(trimMax)>0:
            try:
                trimMax = float(trimMax)
            except:
                print('in line %s\ntrimMax=%s\n'%(l, trimMax))
                raise
                                            
        unit_instruction[signal] = {"base_unit": unit, "resolution": resolution, "ignore": ignore,
        "factors": factors, "final_factor": final_factor, "translate": {}, "supposeMean" : supposeMean, "trimMax": trimMax}
        if prt:
            eprint(signal, unit_instruction[signal])
            
    in_unit_instructions_file.close()
    return unit_instruction


def read_unit_translation(unit_instruction, prt = False):
    '''Per unit translation instructions - 1-to-many with instructions file'''
    cfg = Configuration()
    in_unit_translation_file = open( os.path.join(fixOS(cfg.code_folder), 'unitTranslator.txt'), 'r' )
    i = 0
    for l in in_unit_translation_file:
        signal,unit,factor = map(clean_and_strip, l.split('\t'))
        unit_instruction[signal]["translate"][unit] = factor
        i += 1
        if prt:
            eprint("found", i, "unit translations")
    in_unit_translation_file.close()

def read_code_dependent():
    '''Most translation are done in the unit level, however this file provides workarounds for specific read codes, 
    we convert them to other units as they need special treatment'''
    cfg = Configuration()
    in_ahd_code_dependent_translation_file = open( os.path.join(fixOS(cfg.code_folder), 'codesDependency'), 'r' )
    ahd_code_dependent_translation = defaultdict(lambda : defaultdict(str))
    for l in in_ahd_code_dependent_translation_file.readlines():
        signal, in_unit, ahd_code, out_unit = map(clean_and_strip, l.split('\t'))
        ahd_code_dependent_translation[(signal, in_unit)][ahd_code] = out_unit
    in_ahd_code_dependent_translation_file.close()
    return ahd_code_dependent_translation 

def supportedFormatList(signalName):
    unit_instruction = read_instructions(False)
    read_unit_translation(unit_instruction, False)
    ahd_code_dependent_translation = read_code_dependent()
    if (unit_instruction.get(signalName) is None or unit_instruction[signalName].get('translate') is None):
        d = dict()
        return d
    unit_dict_translator = unit_instruction[signalName]['translate']
    ignoreSet = unit_instruction[signalName]['ignore']
    allUnits = dict()
    for k,v in unit_dict_translator.items():
        allUnits[k] = True
    for k in ignoreSet:
        allUnits[k] = True
        
    if unit_instruction[signalName]['base_unit'] is not None:
        allUnits[ unit_instruction[signalName]['base_unit'] ] = True #add default instruction unit
    return allUnits

def get_user():
    userName = os.environ.get('USERNAME')
    if userName is None:
        userName = os.environ.get('USER')
    if userName is None:
        userName = 'ido'
    return userName
    
def log_cmd(msg):
    cfg = Configuration()
    outputPath= os.path.join( fixOS(cfg.code_folder), 'log_actions')
    if not(os.path.exists(outputPath)):
        os.makedirs(outputPath)
        
    serverName = socket.gethostname()
    userName = get_user()
    
    cmd ='%s\t%s\t%s\t%s\n'%(time.strftime('%d-%m-%Y %H:%M:%S', time.localtime()), serverName, userName, msg)
    fo = open(os.path.join(outputPath, 'signal_mapping_ops.txt'), 'a')
    fo.write(cmd)
    fo.close()

def createHtmlGraph_series(x, y, seriesNum, seriesName = None):
    if len(x) != len(y):
        raise NameError('x and y vectors must be same size. x_size=%d, y_szie=%d'%(len(x), len(y)))
    if seriesName == None:
        seriesName = 'data'

    res = 'var series%d = {\n mode : \'lines+markers\',\n'%(seriesNum)
    res = res + 'x: [%s],\n'%( ', '.join( map( lambda v : '%2.4f'%v if type(v) == float else '\'%s\''%v ,x) ) )
    res = res + 'y: [%s],\n'%( ', '.join( map( lambda v : '%2.4f'%v ,y) ) )
    res = res + 'name: \'%s\' \n'%seriesName
    res = res + '};\n'
    return res

def createHtmlGraph(vec_x, vec_y, outputPath, title, xName = 'x', yName = 'y', vec_names = None):
    cfg = Configuration()
    if not(os.path.exists(fixOS(cfg.html_data_path))):
        raise NameError('please set your html_data_path in Configuration correctly')
    jsFilePath = os.path.join(fixOS(cfg.html_data_path), 'plotly-latest.min.js')
    if not(os.path.exists(jsFilePath)):
        raise NameError('please set your html_data_path in Configuration correctly - js file is missing')
    htmlPath = os.path.join(fixOS(cfg.html_data_path), 'Graph_HTML.backup.txt')
    if not(os.path.exists(htmlPath)):
        raise NameError('please set your html_data_path in Configuration correctly - html file is missing')
    if not(os.path.exists(outputPath)):
        os.makedirs(outputPath)
        #eprint(outputPath)
        #raise NameError('please pass correct output')
    need_js = len(os.path.dirname(htmlPath)) == 0
    if (len(vec_x) != len(vec_y)):
        raise NameError('vec_x and vec_y must be same size')
    if len(vec_x) == 0:
        raise NameError('got empty series to plot')
    if type(vec_x[0]) != list:
        vec_x = [vec_x]
        vec_y = [vec_y]
        vec_names = ['data']
    
    if need_js:
        fp = open(jsFilePath, 'r')
        data = fp.read()
        fp.close()
        fo = open(os.path.join(outputPath, 'plotly-latest.min.js'), 'w')
        fo.write(data)
        fo.close()

    fp = open(htmlPath, 'r')
    templateData = fp.read()
    fp.close()

    data = ''
    for i in range(len(vec_x)):
        data  = data + createHtmlGraph_series(vec_x[i], vec_y[i],  i, vec_names[i])

    data = data + 'var data = [%s];\n'%( ', '.join( map( lambda vv : 'series%d'%vv , range(len(vec_x))) ) )
    data = data + 'layout = { title:\'%s\', xaxis: { title : \'%s\' }, yaxis: { title : \'%s\' }, height : 800, width : 1200 };\n'%(title, xName, yName)
    templateData = templateData.replace('{0}', data)
    fo = open(os.path.join(outputPath, title + '.html'), 'w')
    fo.write(templateData)
    fo.close()
    

def hist(vector):
    d = dict()
    for v in vector:
        if d.get(v) is None:
            d[v] = 0
        d[v] = d[v] + 1
    return d

def analyzeTimeSignal(vector, thCheck = 0.1):
    d = hist(vector)
    xy = []
    for k,v in d.items():
        xy.append([k,v])
    xy = sorted(xy, key=lambda kv: kv[0], reverse = False)
    medianVal = xy[int(round(len(xy) / 2))][1]
    startInd = int(round(len(xy) * 0.2))
    endInd = int(round(len(xy) * 0.8))
    time_start = xy[startInd][0]
    time_end = xy[endInd][0]
    #check that there is no bigger diffrent than 10% in this [time_start -time_end] from median val
    allOk = True
    ind = startInd
    while (allOk and ind <= endInd):
        allOk = ((xy[ind][1] - medianVal) / float(medianVal)) <= thCheck
        ind = ind  + 1
    
    return allOk

def loadMaccabiRenames():
    res = dict()
    cfg = Configuration()
    code_dir = fixOS(cfg.code_folder)
    if not(os.path.exists(code_dir)):
        raise NameError('code dir wasn''t found. cfg error?')
    codeFile = os.path.join(code_dir, 'codes_to_signals')
    if not(os.path.exists(codeFile)):
        return res
    fp = open(codeFile, 'r')
    lines = fp.readlines()
    fp.close()
    for line in lines:
        if len(line.strip()) == 0:
            continue
        tokens = line.split('\t')
        if len(tokens) != 2:
            raise NameError('bad format got %s'%line)
        srcName = tokens[0].strip()
        destName = tokens[1].strip()
        res[srcName] = destName
    return res

def loadMaccabiSignalStats(signalName, binCnt = None):
    maccabiNames = loadMaccabiRenames()
    sigName = signalName
    if maccabiNames.get(signalName) is not None:
        sigName = maccabiNames[signalName]
    sigNameOut = sigName.replace('#', 'H').replace('%','P').replace('/','_over_')
    cfg = Configuration()
    cmd = cfg.flow_app
    resVec = None
    resSize = 100000
    if binCnt is None:
        binCnt = 20
    useShell = False
    if sys.platform.startswith("win"):
        # Don't display the Windows GPF dialog if the invoked program dies.
        # See comp.os.ms-windows.programmer.win32
        # How to suppress crash notification dialog?, Jan 14,2004 -
        # Raymond Chen's response [1]
        import ctypes
        SEM_NOGPFAULTERRORBOX = 0x0002 # From MSDN
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX);
        subprocess_flags = 0x8000000 #win32con.CREATE_NO_WINDOW?
        useShell = True
    else:
        subprocess_flags = 0
    try:
        #c = '%s --signal %s --age_min 20 --age_max 100 --sampleCnt 3 --binCnt 20'%(os.path.basename(cmd), sigName)
        csvData = subprocess.check_output([cmd , '--rep', fixOS(cfg.maccabi_repo), '--sig_print' ,'--sig', sigName, '--output', 'csv'
                                           ,'--age_min', '20', '--age_max', '100', '--sampleCnt', '3', '--bin_method', '"split_method=iterative_merge;binCnt=%d"'%binCnt], shell=useShell, creationflags=subprocess_flags)
        csvData = csvData.decode('ascii')
        lines = csvData.splitlines()
        lines = lines[1:]
        resVec = []
        for line in lines:
            tokens = line.split(',')
            if len(tokens) < 2:
                raise NameError('Format Error')
            val = float(tokens[0].strip())
            freq = float(tokens[1].strip())
            for i in range(int(round(resSize*freq))):
                resVec.append(val)
        #print(my_out, file = f)
    except KeyboardInterrupt:
        raise            
    except:
        eprint("failed in signal: " + signalName )
        traceback.print_exc()
        
    return resVec

def normVec(vec):
    totSum = sum(vec)
    return list(map( lambda x: x/float(totSum) ,vec))

def throwOutlyers(vec, min_th = 0.001, max_th = 0.999):
    if len(vec) == 0:
        raise NameError('vec is empty in throw outlyers')
    s_vals = sorted(vec)
    min_val = s_vals[int(len(vec)* min_th)]
    max_val = s_vals[int((len(vec)-1)* max_th)]
    #vec = list(map(lambda x: x if x >= min_val and x <= max_val else min_val if x< min_val else max_val ,vec))
    vec = list(filter(lambda x: x > 0 and x >= min_val and x <= max_val ,vec))
    return vec

def roundToBinValues(binRanges, binCnts):
    if len(binRanges) != len(binCnts) + 1:
        raise NameError('wrong params to bins - got %d, %d'%(len(binRanges),  len(binCnts)))
    v= []
    for i in range(len(binCnts)):
        tmpList = [(binRanges[i]+binRanges[i+1])/2 for k in range(int(binCnts[i]))]
        v = v + tmpList
    return v

def binVector(v1, v2, histTech):
    maxSample = 100000
    if len(v1) > maxSample:
        v1 = random.sample(v1, maxSample)
    if len(v2) > maxSample:
        v2 = random.sample(v2, maxSample)

    if histTech == 'smart':
        #v_both = [v1[i] for i in range(len(v1))]
        #for i in range(len(v2)):
        #    v_both.append(v2[i])
        binRange = binSelection(v1, 50)
        #binRange = binSelection(v_both, 50)
        h1 = histRange(v1, binRange)
        h2 = histRange(v2, binRange)
    elif histTech == 'regular':
        min_all = min([min(v1), min(v2)])
        max_all = max([max(v1), max(v2)])
        binRange = [ min_all + (float(i)/50)*(max_all - min_all)   for i in range(51)]
        #print(binRange)
        h1, binRange = histogram(v1, density = False, bins = binRange)
        h2, tmp = histogram(v2, density = False, bins = binRange)
        h1 = list(h1)
        h2 = list(h2)
        binRange = list(binRange)
        binRange = binRange[:-1]
    elif histTech == 'no':
        h_h1 = hist(v1)
        h_h2 = hist(v2)
        for k, cnt in h_h1.items():
            if h_h2.get(k) is None:
                h_h2[k] = 0
        for k, cnt in h_h2.items():
            if h_h1.get(k) is None:
                h_h1[k] = 0
                
        h1 = list(map(lambda kv: [kv[0], kv[1]] ,h_h1.items()))
        h1 = sorted(h1, key = lambda kv: kv[0])
        binRange = list(map(lambda kv: kv[0] ,h1))
        h1 = list(map(lambda kv: kv[1] ,h1))
        h2 = list(map(lambda kv: [kv[0], kv[1]] ,h_h2.items()))
        h2 = sorted(h2, key = lambda kv: kv[0])
        h2 = list(map(lambda kv: kv[1] ,h2))
    else:
        raise NameError('unsupported hist tech, please choose: regular/smart/no')

    #noramlzie h1, h2 to have sum of 10000 each on:
    s1 = 10000.0 / sum(h1)
    s2 = 10000.0 / sum(h2)
    h1 = list(map(lambda x: s1*x ,h1))
    h2 = list(map(lambda x: s2*x ,h2))
    
    return binRange, h1,h2

def compareHistDist(v1, v2, histTech = 'regular', technique = 'chi-square'):
    binRange, h1,h2 = binVector(v1, v2, histTech)
    if technique != 'chi-square':
        h1 = normVec(h1)
        h2 = normVec(h2)
    score = 0
    #kld:
    if technique == 'kld':
        #print('h1 = [%s] h2 = [%s]'%(','.join( list(map(str,h1))) , ','.join( list(map(str,h2))) ))
        for i in range(len(h1)):
            if (h1[i]> 0):
                if (h2[i] > 0):
                    score  = score + h1[i] * math.log(h1[i] /h2[i])
                else:
                    score  = score + h1[i] * math.log(1.0 / 0.1)
        return math.exp(-score)
    elif technique == 'chi-square':
    #chi-square:
        #print('h1 = [%s] h2 = [%s]'%(','.join( list(map(str,h1))) , ','.join( list(map(str,h2))) ))
        minC = 0.5
        decNoise = 0.5/100 * len(v1) # I can handle 0.5% change - the sample size is 10000 
        score1 = 0
        score2 = 0
        for i in range(len(h1)):
            d = abs(h1[i]-  h2[i])
            if d > 0 and d < decNoise:
                d = 0
            elif (d > 0):
                d = d- decNoise
            if (h1[i]> 0):
                score1  = score1 + (d*d) / h1[i]
            else:
                score1  = score1 + (d*d) / minC
            if (h2[i]> 0):
                score2  = score2 + (d*d) / h2[i]
            else:
                score2  = score2 + (d*d) / minC

        dof = len(h1) - 1
        dist = score1
        if (score2 < score1):
            dist = score2
        p_value_caliberation = 0.99
        norm_dist = stats.chi2.ppf(p_value_caliberation,dof) #the score_dist in p_value confidence based on cdf. till this value we will get this p_value for null theoram correctness
        
        if dist < norm_dist: #when we get less than p_value to denied null theoram we will caliberate it to 1 - null theoram is correct
            print('dist=%f, d1=%f, d2=%d, dof=%d, score=%f'%(dist, score1, score2, dof, 1))
            return dist, 1
        normalize_pdf = stats.chi2.pdf(norm_dist, dof) #the cliberation pdf value for this point
        prb = stats.chi2.pdf(dist, dof) / normalize_pdf #the probabilty for this "bin"
        print('dist=%f, d1=%f, d2=%d, dof=%d, score=%f, norm_dist=%f'%(dist, score1, score2, dof, prb, norm_dist))
        return dist, prb
        
        #if (score2 > score1):
        #    dist = score2    
        
        #print('h1=%s'%','.join(list(map(str,h1))))
        #print('h2=%s'%','.join(list(map(str,h2))))
        #score = stats.chi2.cdf(dist, dof) #i do 1- score. low - means not probable they are the same, high means they are the same dist
        #print('dist=%f, d1=%f, d2=%d, dof=%d, score=%f'%(dist, score1, score2, dof, 1-score))
        #if 1-score > 0.1: #means OK - 10% it will happend - caliberate to 0.98 for 0.1 and 1 for 1
        #    score = 1-( 0.98 + (1-0.98) * (1-score - 0.1)/(1-0.1))

    elif technique == 'ks':
        #h1, binRange = histogram(v1, density = False, bins = 50)
        #h2, tmp = histogram(v2, density = False, bins = binRange)
        #vv1 = roundToBinValues(binRange, h1)
        #vv2 = roundToBinValues(binRange, h2)
        stat_dist, score = stats.ks_2samp(v1, v2)
        print('p_value=%2.3f'%score)
        #stat_dist, score = stats.ks_2samp(vv1, vv2)
        score = stat_dist
        #score = 1 - score
    elif technique == 'mannw':
        tmp, score = stats.mannwhitneyu(v1, v2)
        print('p_value=%2.3f statistics='%(score, tmp))
        #score = 1 - score
    elif technique == 'all':
        tmp, score = stats.mannwhitneyu(v1, v2)
        print('mannwhitneyu p_value=%2.3f statistics=%2.3f'%(score, tmp))
        stat_dist, score = stats.ks_2samp(v1, v2)
        print('ks_2samp p_value=%2.3f, statistics=%2.3f'%(score, stat_dist))
        for i in range(len(h1)):
            if (h1[i]> 0):
                if (h2[i] > 0):
                    score  = score + h1[i] * math.log(h1[i] /h2[i])
                else:
                    score  = score + h1[i] * math.log(h1[i] / 0.0001)
        print('kld_score= %2.3f'%(score))
    else:
        raise NameError('technique not supported')
                
    return 1 - score

def strip_names(str):
    return str.replace('/','_over_')

def compareAllHists(vec_vector, signalName, vec_names, removeTh = None, histTech = 'regular', metric = 'chi-square', print_bin_cmp = True):
    warnnings = []
    if len(vec_names) == 0:
        raise NameError('please run fix again - old format without signal source names')
    if len(vec_vector) != len(vec_names):
        raise NameError('vec_vector must be same size as vec_names')
    if len(vec_vector) == 1:
        return warnnings
    cfg = Configuration()
    all_x = []
    all_y = []
    for i  in range(len(vec_vector)):
        vec = throwOutlyers(vec_vector[i])
        vec_vector[i] = vec
        d = hist(vec)
        xy = []
        for k,v in d.items():
            xy.append([k,v])
        xy = sorted(xy, key=lambda kv: kv[0], reverse = False)
        x = list(map(lambda v : v[0] ,xy))
        y = list(map(lambda v : v[1] ,xy))
        #y = normVec(y)    
        fx = []
        fy = []
        for k in range(len(y)):
            if ( removeTh is  None or y[k] >= removeTh) and x[k] > 0:
                fy.append(y[k])
                fx.append(x[k])

        all_x.append(fx)
        fy = normVec(fy)    
        all_y.append(fy)
    outPath = os.path.join(fixOS(cfg.output_path), signalName)
    if not(os.path.exists(outPath)):
        os.makedirs(outPath)
        
    createHtmlGraph(all_x, all_y, outPath, 'compare_all_series', signalName + ' Values', 'Prob', vec_names)

    #Check chi-square between all couples
    for i in range(len(vec_vector)):
        vec_i = vec_vector[i]
        for j in range(i+1,len(vec_vector)):
            vec_j = vec_vector[j]
            score = compareHistDist(vec_i, vec_j,  histTech, metric)
            if len(score) > 1:
                score = score[-1]
            if print_bin_cmp:
                all_binned_x = []
                all_binned_y = []
                binRange, h1, h2 = binVector(vec_i, vec_j, histTech)
                all_binned_x.append(binRange)
                all_binned_x.append(binRange)
                all_binned_y.append(h1)
                all_binned_y.append(h2)
                createHtmlGraph(all_binned_x, all_binned_y, outPath, 'compare_series_binned_%s_%s'%(strip_names(vec_names[i]), strip_names(vec_names[j])), signalName + ' Values', 'Prob', vec_names)
            if score < 0.98:
                msg = '%s compare to %s has diffrent of %2.3f. please check them'%(vec_names[i], vec_names[j], score)
                warnnings.append(msg)
                eprint(msg)
            else:
                print('Got good compare score = %2.3f between %s and %s'%(score, vec_names[i], vec_names[j]))

    return warnnings
        

def analyzeHist(vector, signalName, formatFunc = None, removeTh = None, outPath = None):
    cfg = Configuration()
    if (len(vector) == 0):
        return
    minVal = min(vector)
    maxVal = max(vector)
    if (formatFunc is not None):
        minVal = formatFunc(minVal)
        maxVal = formatFunc(maxVal)
    else:
        minVal = '%2.3f'%(minVal)
        maxVal = '%2.3f'%(maxVal)
    print('%s range [%s, %s]'%(signalName, minVal, maxVal))
    d = hist(vector)
    xy = []
    for k,v in d.items():
        xy.append([k,v])
    xy = sorted(xy, key=lambda kv: kv[0], reverse = False)
    x = list(map(lambda v : v[0] if formatFunc is None else formatFunc(v[0]) ,xy))
    y = list(map(lambda v : v[1] ,xy))
    if removeTh is not None:
        y = normVec(y)
        fy = []
        fx = []
        for i in range(len(y)):
            if y[i] >= removeTh:
                fx.append(x[i])
                fy.append(y[i])
        x = fx
        y = fy

    if outPath is None:
        outPath = os.path.join(fixOS(cfg.output_path), signalName)
    if not(os.path.exists(outPath)):
        os.makedirs(outPath)
    createHtmlGraph(x,y, outPath, signalName + '_histogram', signalName, 'Count')
    #print hist, check normal dist, compare to other dist, compare between files
    
def checkNormal(vector):
    return normaltest(vector).pvalue

def fixOS(pt):
    isUnixPath = pt.find('\\') == -1
    if ((os.name != 'nt' and isUnixPath) or (os.name == 'nt' and not(isUnixPath))):
        return pt
    elif (os.name == 'nt'):
        res = 'C:\\USERS\\' + get_user()
        if (pt.startswith('/nas1') or pt.startswith('/server')):
            res = '\\\\nas3'
            pt = pt.replace('/nas1', '').replace('/server', '')
        pt = pt.replace('/', '\\')
        res= res + pt
        return res
    else:
        res = ''
        if pt.startswith('\\\\nas1') or pt.startswith('\\\\nas3') :
            res = '/nas1'
            pt = pt.replace('\\\\nas1', '')
            pt = pt.replace('\\\\nas3', '')
        elif pt.startswith('C:\\Users\\') :
            res = os.environ['HOME']
            pt = pt.replace('C:\\Users\\', '')
            pt = pt[ pt.find('\\'):]
        elif pt.startswith('H:\\'):
            res = os.path.join('/nas1/UsersData', get_user().lower() )
            pt = pt.replace('H:', '')
        elif pt.startswith('W:\\'):
            res = '/nas1/Work'
            pt = pt.replace('W:', '')
        elif pt.startswith('T:\\'):
            res = '/nas1/Data'
            pt = pt.replace('T:', '')
        elif pt.startswith('U:\\'):
            res = '/nas1/UserData'
            pt = pt.replace('U:', '')
        elif pt.startswith('X:\\'):
            res = '/nas1/Temp'
            pt = pt.replace('X:', '')
        else:
            eprint('not support convertion "%s"'%pt)
            raise NameError('not supported')
        pt = pt.replace('\\', '/')
        res= res + pt
        return res

def searchAndReplaceFileTxt(filePath, sig_src, sig_tar):
    if not(os.path.exists(filePath)):
        raise NameError('file not found')
    fp = open(filePath, 'r')
    lines = fp.readlines()
    fp.close()

    for i in range(len(lines)):
        line = lines[i]
        line = re.sub('^' + sig_src + '\t', sig_tar + '\t', line)
        lines[i] = line
    
    fp = open(filePath, 'w')
    fp.writelines(lines)
    fp.close()
