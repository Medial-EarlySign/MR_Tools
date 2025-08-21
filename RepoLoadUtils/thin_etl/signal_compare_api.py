from Configuration import Configuration
from common import *
from signal_mapping_api import listAllTargets
import subprocess, os, traceback

def getLines(basePath, fileName):
    fileP = os.path.join(basePath, fileName)
    fp = open(fileP, 'r')
    lines = fp.readlines()
    lines = list(filter(lambda x: len(x.strip()) > 0 ,lines))
    fp.close()
    return lines

def createDirs(pth):
    if not(os.path.exists(pth)):
        os.makedirs(pth)

def listAllSignalFromConfig():
    cfg = Configuration()
    code_dir = fixOS(cfg.code_folder)
    lines = getLines(code_dir, 'thin.signals')
    lines = list(filter(lambda line: line.startswith('SIGNAL') ,lines))
    signals = []
    for line in lines:
        tokens = line.split('\t')
        if len(tokens) < 4:
            raise NameError('format Error')
        signalName = tokens[1].strip()
        signalType = tokens[3].strip()
        if int(signalType) == 1:
            signals.append(signalName)
    return signals

def appendMulty(l, val, cnt):
    for i in range(cnt):
        l.append(val)
        
def compareRepositories(reps, signals = None, out_path = None, flow_pth = None):
    cfg = Configuration()
    if len(reps) < 2:
        raise NameError('you ,must give at least two repositories to compare')
    if flow_pth is None:
        flow_pth = cfg.flow_app
    if out_path is None:
        out_path = os.path.join(fixOS(cfg.output_path), 'CompareRepos')
    createDirs(out_path)
    fw = open(os.path.join(out_path, 'compare_all.log'), 'w')
    fw.close()
    
    if signals is None:
        #signals = listAllTargets()
        signals = listAllSignalFromConfig()
        signals = list(filter(lambda x: x!= 'NULL' and x!= 'TBD',signals))
    resSize = 10000
    for index,s in enumerate(signals):
        print("running on: %s (%d / %d) %2.1f%%"%(s, index+1, len(signals), 100*float(index+1)/len(signals) ))
        cmpVecs = []
        cmpNames = []
        for repo in reps:
            try:
                args = [flow_pth ,'--rep' , repo , '--sig_print' , '--age_min','40' ,'--age_max','80',
                                                  '--sig' , s, '--output', 'csv', '--maxPids', '0', '--sampleCnt', '1', '--bin_method', '"split_method=same_width;binCnt=0"',
                                                    '--normalize', '0', '--filterCnt', '0']
                my_out = subprocess.check_output(' '.join(args), shell = True)
                my_out = my_out.decode('ascii')
                lines = my_out.splitlines()
                lines = lines[1:]
                resVec = []
                d = dict()
                for line in lines:
                    tokens = line.split(',')
                    if len(tokens) < 2:
                        raise NameError('Format Error')
                    val = float(tokens[0].strip())
                    freq = float(tokens[1].strip())
                    d[val] = freq
                tot_cnt = 0
                for k,cnt in d.items():
                    tot_cnt += cnt
                for val,cnt in d.items():
                    for i in range(int(round(resSize*cnt/tot_cnt))):
                        resVec.append(val)
                cmpVecs.append(resVec)
                cmpNames.append( '%s_%s'%(os.path.basename(os.path.dirname( repo)) ,os.path.basename(repo)))
            except KeyboardInterrupt:
                raise            
            except:
                traceback.print_exc()
                eprint("failed in signal: " + s + " repo: " + repo + "\nCMD:\n" + ' '.join(args))
            if len(cmpVecs) > 1:
                try:
                    warnnings = compareAllHists(cmpVecs, 'Final_%s'%(s), cmpNames , 0.0001, 'regular', 'chi-square', True);
                except:
                    warnnings = []
                    warnnings.append('ERRROR: %s'%(traceback.format_exc()))
                if len(warnnings) == 0:
                    msg = 'Good Compare is signal %s between repositories %s'%(s, cmpNames)
                else:
                    msg = 'Signal %s - %s'%(s, warnnings[0])
                fw = open(os.path.join(out_path, 'compare_all.log'), 'a')
                fw.write('%s\n'%msg)
                fw.close()

def get_signal_list(repository):
    signal_name='%s.signals'%('.'.join(os.path.basename(repository).split('.')[:-1]))
    signals_path = os.path.join (os.path.dirname(repository), signal_name)
    fr=open(signals_path, 'r')
    lines=fr.readlines()
    fr.close()
    sigs = list(filter(lambda x : x.startswith('SIGNAL'),lines))
    res = []
    for sig in sigs:
        tokens = sig.strip().split('\t')
        if len(tokens) > 5:
            categ_channels = int(tokens[5])
            if categ_channels == 0:
                res.append(tokens[1])
        else:
            res.append(tokens[1])
    return res

if __name__ == "__main__":
    cfg = Configuration()
    reps = [fixOS(cfg.maccabi_repo) , fixOS('/server/Work/CancerData/Repositories/THIN/build_jan2017/thin.repository')]
    #reps = [ fixOS('/server/Work/CancerData/Repositories/THIN/build_nov2016/thin.repository'), fixOS('/server/Work/CancerData/Repositories/THIN/build_jan2017/thin.repository')]
    compareRepositories(reps)